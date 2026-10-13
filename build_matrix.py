"""Rebuild the customer x product matrices from the raw file (DE1-DE5).

Usage:  python build_matrix.py
Needs:  data/raw/online_retail_II.xlsx
Writes: data/processed/*  and  outputs/*
Two phases: TUNING (fit before validation period) and FINAL (fit before test period).
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, scipy.sparse as sp

SEED = 42
MIN_CUSTOMERS = 10      # product must be bought by >= 10 customers (fit period only)
TEST_MONTHS = 2         # last 2 months = test period
VAL_MONTHS = 2          # the 2 months before = validation period
K_REPORT = 50           # k used for the size report

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data/raw/online_retail_II.xlsx"
PROC = ROOT / "data/processed"
OUT = ROOT / "outputs"


def load_raw():
    # DE1: load both sheets, standardise column names, fix types, profile
    sheets = pd.read_excel(RAW, sheet_name=None)
    df = pd.concat(sheets.values(), ignore_index=True)
    df = df.rename(columns={"InvoiceNo": "Invoice", "UnitPrice": "Price",
                            "CustomerID": "Customer ID"})
    for col in ["Invoice", "StockCode", "Description", "Country"]:
        df[col] = df[col].astype("string")
    profile = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "missing": df.isna().sum(),
        "missing_%": (df.isna().mean() * 100).round(2),
        "unique": df.nunique(),
    })
    profile.to_csv(OUT / "data_profile.csv")
    print("Raw rows:", len(df))
    return df


def clean(df):
    # DE2: cleaning rules, each logged
    raw_rows = len(df)
    df = df.copy()
    df["StockCode"] = df["StockCode"].str.strip().str.upper()
    log = []

    def rule(data, name, mask_fn):
        before = len(data)
        out = data[mask_fn(data)]
        log.append({"rule": name, "rows_before": before,
                    "rows_removed": before - len(out), "rows_after": len(out)})
        return out

    df = rule(df, "1. Missing Customer ID", lambda d: d["Customer ID"].notna())
    df = rule(df, "2. Cancellation invoices (start with C)",
              lambda d: ~d["Invoice"].str.startswith("C", na=False))
    df = rule(df, "3. Quantity <= 0", lambda d: d["Quantity"] > 0)
    df = rule(df, "4. Price <= 0", lambda d: d["Price"] > 0)
    df = rule(df, "5. Non-product stock codes",
              lambda d: d["StockCode"].str.match(r"^\d{5}[A-Z]*$", na=False))
    df = rule(df, "6. Purchases fully reversed by an exact cancellation (2 lines)",
              lambda d: ~(((d["StockCode"] == "23843") & (d["Quantity"] == 80995)) |
                          ((d["StockCode"] == "23166") & (d["Quantity"] == 74215))))
    df["Customer ID"] = df["Customer ID"].astype(int)

    cl = pd.DataFrame(log)
    cl["removed_%_of_raw"] = (cl["rows_removed"] / raw_rows * 100).round(2)
    cl.to_csv(OUT / "cleaning_log.csv", index=False)
    print(cl.to_string(index=False))
    return df


def build_phase(fit, evalset, files):
    # DE3 + DE4 for one phase: hold out NEW products, build the matrix from `fit` only
    seen = set(zip(fit["Customer ID"], fit["StockCode"]))
    known = evalset[evalset["Customer ID"].isin(set(fit["Customer ID"]))]
    is_new = [(c, p) not in seen for c, p in zip(known["Customer ID"], known["StockCode"])]
    held = known[is_new].copy()
    # R2 checks: no leakage
    assert fit["InvoiceDate"].max() < evalset["InvoiceDate"].min()
    assert len(set(zip(held["Customer ID"], held["StockCode"])) & seen) == 0

    agg = fit.groupby(["Customer ID", "StockCode"], as_index=False)["Quantity"].sum()
    n_buyers = agg.groupby("StockCode")["Customer ID"].nunique()
    keep = n_buyers[n_buyers >= MIN_CUSTOMERS].index
    agg = agg[agg["StockCode"].isin(keep)].copy()
    agg["value"] = np.log1p(agg["Quantity"])
    cust_ids = np.sort(agg["Customer ID"].unique())
    prod_ids = np.sort(agg["StockCode"].unique())
    cust_idx = {c: i for i, c in enumerate(cust_ids)}
    prod_idx = {p: j for j, p in enumerate(prod_ids)}
    A = sp.csr_matrix((agg["value"].to_numpy(),
                       (agg["Customer ID"].map(cust_idx).to_numpy(),
                        agg["StockCode"].map(prod_idx).to_numpy())),
                      shape=(len(cust_ids), len(prod_ids)))

    held_f = held[held["Customer ID"].isin(cust_idx) & held["StockCode"].isin(prod_idx)]
    names = (fit.dropna(subset=["Description"])
             .groupby("StockCode")["Description"].agg(lambda s: s.mode().iloc[0]))

    f_A, f_cust, f_prod, f_held = files
    sp.save_npz(PROC / f_A, A)
    pd.DataFrame({"idx": range(len(cust_ids)), "customer_id": cust_ids}).to_csv(
        PROC / f_cust, index=False)
    pd.DataFrame({"idx": range(len(prod_ids)), "stock_code": prod_ids,
                  "description": names.reindex(prod_ids).values}).to_csv(
        PROC / f_prod, index=False)
    held_f.to_parquet(PROC / f_held)

    pairs = held[["Customer ID", "StockCode"]].drop_duplicates()
    pairs_f = held_f[["Customer ID", "StockCode"]].drop_duplicates()
    rep = pd.Series({
        "fit_ends_before": str(fit["InvoiceDate"].max().date() + pd.Timedelta(days=1)),
        "fit_rows": len(fit),
        "fit_customers": fit["Customer ID"].nunique(),
        "fit_products": fit["StockCode"].nunique(),
        "eval_rows_raw": len(evalset),
        "eval_customers_total": evalset["Customer ID"].nunique(),
        "eval_customers_new_not_in_fit": len(set(evalset["Customer ID"]) - set(fit["Customer ID"])),
        "heldout_pairs": len(pairs),
        "matrix_customers": A.shape[0],
        "matrix_products": A.shape[1],
        "matrix_nonzeros": A.nnz,
        "heldout_pairs_after_product_filter": len(pairs_f),
        "eval_customers_left": pairs_f["Customer ID"].nunique(),
    })
    return A, rep


def split_and_build(df):
    last_day = df["InvoiceDate"].max().normalize()
    test_start = last_day - pd.DateOffset(months=TEST_MONTHS)
    val_start = test_start - pd.DateOffset(months=VAL_MONTHS)

    # Phase 1: TUNING (fit before validation, hold out validation)
    fit_tune = df[df["InvoiceDate"] < val_start]
    val_rows = df[(df["InvoiceDate"] >= val_start) & (df["InvoiceDate"] < test_start)]
    _, rep_val = build_phase(fit_tune, val_rows,
        ("A_tune.npz", "customer_index_tune.csv", "product_index_tune.csv", "val_filtered.parquet"))

    # Phase 2: FINAL (fit before test, hold out test)
    fit_final = df[df["InvoiceDate"] < test_start]
    test_rows = df[df["InvoiceDate"] >= test_start]
    A, rep_test = build_phase(fit_final, test_rows,
        ("A_train.npz", "customer_index.csv", "product_index.csv", "test_filtered.parquet"))
    fit_final.to_parquet(PROC / "train.parquet")

    report = pd.DataFrame({"validation (tuning)": rep_val, "test (final)": rep_test})
    report.to_csv(OUT / "split_report.csv")
    print(report.to_string())
    return A


def matrix_report(A):
    # DE5: shape, sparsity, memory
    n_c, n_p = A.shape
    cells = n_c * n_p
    rep = pd.Series({
        "customers (rows)": n_c,
        "products (columns)": n_p,
        "total cells": cells,
        "non-zero cells": A.nnz,
        "density %": round(A.nnz / cells * 100, 2),
        "sparsity %": round((1 - A.nnz / cells) * 100, 2),
        "avg products per customer": round(A.nnz / n_c, 1),
        "avg customers per product": round(A.nnz / n_p, 1),
        "dense memory (MB)": round(cells * 8 / 1e6, 1),
        "sparse CSR memory (MB)": round(
            (A.data.nbytes + A.indices.nbytes + A.indptr.nbytes) / 1e6, 1),
        f"factors at k={K_REPORT} (MB)": round((n_c + n_p) * K_REPORT * 8 / 1e6, 1),
    })
    rep.to_csv(OUT / "matrix_report.csv")
    print(rep)


def main():
    np.random.seed(SEED)
    PROC.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if not RAW.exists():
        sys.exit(f"Raw file not found: {RAW}")
    df = load_raw()
    df = clean(df)
    A = split_and_build(df)
    matrix_report(A)
    print("Done. Matrix shape:", A.shape)


if __name__ == "__main__":
    main()
