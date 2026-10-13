# Customers Like You \- Mini-Project

## Data

- Source: UCI Online Retail II ([https\://archive.ics.uci.edu/dataset/502/online+retail+ii](https://archive.ics.uci.edu/dataset/502/online+retail+ii))  
- Rows loaded (both sheets combined): 1,067,371  
- Date range: 1 Dec 2009 to 9 Dec 2011  
- Unique customers (raw): 5,942 | Unique stock codes (raw): 5,305

## Success targets (J1, agreed Day 1\)

1. Size: compressed factors at least 90% smaller than the dense customer x product matrix.  
2. Speed: nightly job (fit \+ score) runs in under 60 seconds.  
3. Quality: hit rate at 10 on held-out purchases beats the best-seller baseline.  
4. Customer map: 3 to 6 segments, each named from top products and countries.  
5. Privacy: no customer IDs in the memo, slides or any figure.

## How to run

1. Put online\_retail\_II.xlsx in data/raw/ (not committed to Git).  
2. pip install \-r requirements.txt  
3. python build\_matrix.py   (rebuilds the cleaned data, split, sparse matrix and reports; seed \= 42\)  
4. Open the analysis notebook and run top to bottom.

## Roles

- Working alone: Data Engineer \+ ML Engineer


## Results summary

Test period: 9 Oct to 9 Dec 2011. Settings (k = 50, popularity weight = 2) were chosen on an earlier validation window (9 Aug to 9 Oct 2011), then scored on the test period. Hit rate at 10 is the share of test customers for whom at least one of 10 suggestions was a product they then bought for the first time (margin of error about ±1 point).

| Method | Hit rate at 10 |
| --- | --- |
| 10 best sellers (baseline) | 27.0% |
| Truncated SVD alone (k = 50, log-quantity) | 21.8% |
| Truncated SVD + popularity blend (chosen method) | **35.0%** |
| Truncated SVD on 1/0 matrix (like-for-like) | 23.6% |
| No compression (item-item cosine, 1/0 matrix, 109 MB) | 31.9% |

- **Targets:**
  - Size: met. The factors take 3.7 MB against 161 MB for the dense matrix.
  - Speed: met. The nightly job (fit, suggestions for every customer, "also bought" lists for every product) takes about 2 seconds.
  - Quality: met by the blend only. Plain SVD scored below the best-seller baseline.
  - Customer map: met. Four named groups.
  - Privacy: met. No customer IDs appear in outputs or figures.
- **Size:** the sparse matrix is about 5 MB. Most of the saving comes from skipping empty cells, not from the compression itself.
- **PCA vs SVD (ML5):** at k = 50 on the same matrix, the two methods have the same reconstruction error (a tie) and a similar fit time. Component 1 represents overall volume and popularity in both methods. With a centred customer profile, PCA scored 24.6% against 21.8% for plain SVD. This was an extra check run after the test scores were known. Both are below the best-seller baseline without the blend. SVD stays the main model because it was chosen before fitting (ML1) and works natively on sparse data.
- **Customer groups:** occasional small buyers, home-décor and sign shops, large children's and kitchen-ware wholesalers, and 12 key accounts. The groups separate mostly by buying volume rather than by taste.
- **Main risks:** new customers get no personal suggestions, products with fewer than 10 buyers are excluded, and the test window is the Christmas run-up.

## File map

| File | What it is |
| --- | --- |
| `build_matrix.py` | Rebuilds the cleaned data, time split, sparse matrices and reports from the raw Excel file (DE1 to DE6) |
| `analysis.ipynb` | Method decision, k and blend tuning, recommendations, evaluation, PCA vs SVD comparison and customer map (ML1 to ML6) |
| `decision_log.md` | Every decision with its reason (R1) |
| `ml1_decision_note.md` | Method choice written before any model was fitted (ML1) |
| `data_profile.csv`, `cleaning_log.csv`, `split_report.csv`, `matrix_report.csv` | Data profile, rows removed per cleaning rule, split report, matrix size report (DE1 to DE5) |
| `svd_k_curve.csv`, `svd_error_vs_k.png`, `tuning_grid_validation.csv` | Error against k and the validation grid used to choose k and the blend weight (ML2) |
| `diagnostics_hit_rate.csv`, `nightly_timing.csv` | Test hit rates and nightly job timing (ML4) |
| `pca_vs_svd_table.csv` | PCA vs Truncated SVD comparison table (ML5) |
| `segments.csv`, `customer_map.png`, `customer_map_draft.png` | Customer groups and map (ML6) |
| `hit_rate_chart.png`, `cleaning_funnel.png`, `size_chart.png` | Charts for the slides |
| `requirements.txt` | Pinned package versions (R6) |
| `.gitignore` | Keeps raw and processed data out of Git |

## Note on layout

Result files are at the repo root for convenience. When the notebook or script is run, they are written to an `outputs/` folder. The `data/` folder (raw and processed data, which contains customer IDs) is never committed.
