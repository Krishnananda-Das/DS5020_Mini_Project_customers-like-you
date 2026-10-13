# Decision Log

## DE2 Cleaning

- Removed lines with no Customer ID: cannot be linked to a customer.  
- Removed cancellations (Invoice starts with C): not purchases.  
- Removed Quantity \<= 0 and Price \<= 0: returns, adjustments, free or accounting lines.  
- Kept only StockCodes matching 5 digits \+ optional letters: removes postage, fees, manual entries, vouchers and test codes, which are not recommendable products.  
- Normalised StockCode (strip, uppercase) so variants like 'm' and 'M' are treated alike.  
- Rule order matters for the log: each row is counted under the first rule that removes it.  
- Not done: duplicate lines were kept (repeated lines can be genuine repeat purchases).  
- Removed two purchases that were fully reversed by an exact-quantity cancellation (80,995 units of 23843, cancelled by C581484; 74,215 units of 23166, cancelled by C541433). The pipeline drops cancellation lines but not the orders they reverse, so these two would have stayed as phantom purchases. Not done: netting every cancellation against its original order; the other reversals are small and are damped by log(1 \+ quantity).

## DE3 Split (three periods)

- Test \= last 2 months (from 9 Oct 2011). Validation \= the 2 months before (from 9 Aug 2011). Train \= everything earlier.  
- Two phases: TUNING fits on train and is scored on validation (used to choose k and the blend weight). FINAL fits on train \+ validation and is scored on test, once. This keeps test data out of every modelling choice (R2).  
- Customers not seen in the fit period are excluded from evaluation (cold start) and counted in split\_report.csv.  
- Held-out \= products a customer never bought in the fit period, so we measure discovery, not repeat buying.  
- Assertions check no date overlap and no customer-product pair overlap in both phases.  
- The 80,995-unit order (9 Dec 2011\) is removed in DE2, so it cannot appear as a held-out purchase.  
- The validation window (Aug-Oct) is less Christmas-heavy than the test window (Oct-Dec), so the best settings may transfer imperfectly.

## DE4 Matrix

- Purchase value \= log(1 \+ total quantity per customer-product pair); sum first, then log.  
- Raw quantity rejected: a few very large wholesale lines (thousands of units) would dominate. Log-quantity vs 1/0 compared in ML4/ML5; raw counts not tested.  
- Product filter: bought by \>= 10 distinct customers in the FIT period only (R2), recomputed in each phase.  
- Evaluation pairs on filtered-out products or unknown customers are dropped and counted.  
- Tuning files carry the suffix \_tune; final files keep the plain names. Index maps contain customer IDs: never committed or shown (R4).

## DE5 Matrix report

- Dense vs sparse vs k=50 factors measured in matrix\_report.csv.  
- Finding: sparse storage already gives most of the size saving (161 MB dense, 5 MB sparse, 3.7 MB factors). SVD's value is a compact model that scores quickly; on its own it did not beat the best-seller baseline (see ML4).

# ML1: Method decision (written BEFORE fitting any model)

## Choice

Main model: Truncated SVD (TruncatedSVD, no centring). Comparison model: PCA, same k, same matrix (ML5).

## Why

- Goal is product recommendations: SVD is the standard latent-factor method for this.  
- The matrix is 98% sparse (5,471 x 3,686; 413,690 non-zeros). SVD works on sparse input natively.  
- PCA centres columns, so zeros become negatives and the matrix becomes dense (161 MB vs 5 MB). Even with implicit centring, PCA describes deviation from the average customer, not what people buy.  
- Customer and product factors come from one fit (U\*S and V), which is what a recommender needs.

## Predictions (to check in ML5)

1. SVD component 1 \= overall purchase volume / popular products; PCA component 1 \= a contrast between customer types.  
2. PCA will be slower and use more peak memory than SVD.  
3. SVD hit rate at 10 \>= PCA hit rate at 10\.  
4. Risk: SVD component 1 may encode popularity, pushing recommendations toward best sellers. If hit rate barely beats the baseline, we report that honestly.

## k values to test (ML2)

10, 20, 50, 100, 200\. Choose k from the error curve plus the hit rate, not from one number.

## ML2/ML4 Tuning on the VALIDATION period (test data not used)

- Fit on data before 9 Aug 2011 (matrix 5,149 x 3,492); scored on the 9 Aug \- 9 Oct purchases of 1,400 customers.  
- Rule fixed BEFORE seeing results: take the best validation hit rate, then the smallest k (then smallest blend weight) within 1 standard error of it.  
- Grid: k in {10, 20, 50, 100, 200} x popularity weight w in {0, 0.5, 1, 2, 4, 8}. Full table: outputs/tuning\_grid\_validation.csv.  
- Result: best cell k=50, w=2 at 34.5% (+/-1.3). Nothing else within 1 SE, so chosen: k=50, w=2.  
- Best-seller baseline on validation: 25.6% (+/-1.2). Plain SVD (w=0) at k=50: 22.4%, below the baseline.  
- The optimum is inside the grid (w=4: 29.8%, w=8: 27.1%), so the grid was wide enough.  
- 34.5% is the maximum over 30 settings, so it is optimistic. The test period is evaluated once, with these settings fixed.

## ML4 Test evaluation (run once, settings fixed on validation: k=50, w=2)

- Test: fit before 9 Oct 2011 (matrix 5,471 x 3,686), scored on 1,913 customers' first-time purchases from 9 Oct to 9 Dec.  
- Best-seller baseline 27.0% (+/-1.0). Plain SVD on log-quantity: 21.8% (+/-0.9), below the baseline.  
- SVD k=50 \+ popularity blend (w=2): 35.0% (+/-1.1). Paired difference vs baseline: \+8.0 points (+/-0.9).  
- Validation said 34.5% and test says 35.0%, so the tuned settings did not overfit the validation window.  
- Like-for-like compression cost: SVD on 1/0 matrix 23.6% vs uncompressed item-item cosine 31.9% (about 8 points).  
- The blend (35.0%) exceeds the uncompressed table (31.9%), but this is not like-for-like: the blend adds a popularity term and the uncompressed table has none.  
- Test results were not used to choose k, w or anything else. Target 'beat the baseline': MET by the blend, MISSED by plain SVD.  
- Risks: the test window is the Christmas run-up (validation was less seasonal); 380 test customers are new (cold start) and get no personal suggestions.

## ML4 Nightly job timing (k=50, w=2, with the popularity blend)

- Fit \+ suggestions for all 5,471 customers \+ 'also bought' list for all 3,686 products: median 1.4 s (range 1.3-1.4 s over 5 runs, after one warm-up run).  
- Components (median): fit 0.51 s, customer suggestions 0.60 s, product lists 0.26 s. Details: outputs/nightly\_timing.csv.  
- Timings vary between Colab sessions (an earlier session measured a 2.0 s median, range 1.3-2.3 s), so the memo quotes 'about 2 seconds (1.3 to 2.3 across runs)'.  
- Target 'nightly job under 60 seconds': MET with a wide margin.

## ML5 PCA vs SVD (k=50, same matrix)

- Relative error vs A: PCA 0.789, SVD 0.790: a tie.  
- Hit rate at 10: SVD 21.8% (+/-0.9%); PCA with an uncentred customer profile 21.3% (+/-0.9%); PCA with a centred customer profile 24.6% (+/-1.0%).  
- Centred PCA minus SVD: \+2.8 points (+/-0.8, paired). Both are below the best-seller baseline (27.0%).  
- Fit time (median of 3): PCA 0.80 s, SVD 0.51 s. Peak memory (separate pass): PCA 8.3 MB, SVD 9.7 MB. Neither difference matters for a nightly job.  
- scikit-learn centres sparse input implicitly, so PCA stays cheap here. Centring A explicitly as a dense matrix would need 161.3 MB.  
- Component 1 is volume/popularity in BOTH methods (SVD: customer score corr 0.89 with products bought, loadings corr 0.94 with popularity; PCA: 0.89 and 0.91). Top products: SVD PACK OF 72 RETROSPOT CAKE CASES, WHITE HANGING HEART T-LIGHT HOLDER, JUMBO BAG RED RETROSPOT; PCA PACK OF 72 RETROSPOT CAKE CASES, JUMBO BAG RED RETROSPOT, LUNCH BAG RED RETROSPOT.  
- ML1 predictions: (1) component 1 differs between methods: WRONG. (2) PCA slower: right; PCA more peak memory: wrong. (3) SVD hit rate \>= PCA: wrong (PCA with a centred profile).  
- PCA explained variance (34.9% of centred variance) and SVD information kept (37.6%) use different denominators: not comparable.  
- SVD stays the main model: chosen before fitting (ML1), native sparse, no centring step; quality is within about 3 points of PCA.  
- Untested: PCA with column scaling; PCA \+ popularity blend.

## ML6 Customer map

- KMeans on the first 2 SVD components of the customer factors. Silhouette by number of groups: 3 groups 0.682 (sizes \[4749, 709, 13\]); 4 groups 0.562 (sizes \[3994, 1112, 353, 12\]); 5 groups 0.546 (sizes \[3809, 1177, 262, 211, 12\]); 6 groups 0.567 (sizes \[3829, 674, 600, 199, 157, 12\]).  
- Every solution from 3 to 6 groups contains a tiny group of about 12 customers (the key accounts). We chose 4 groups because it also separates two mid-size groups that marketing can name (home-decor and sign shops; children's and kitchen-ware wholesalers).  
- Groups mostly separate by SIZE (component 1 is overall volume); the taste signal in component 2 is weaker. The small-buyer group has no product with lift above 1 among products at least 10% of it buys, so it is defined by buying little, not by a taste.  
- Key accounts (12 customers): lift values are noise at that size, so they are described by volume only.  
- Lift is bounded by 1/group share, so lifts are not comparable across groups.  
- Only aggregates and anonymised group labels are shown (R4).

## ML6 final segments (training-period revenue, before returns)

- Occasional small buyers: 73.0% of customers, 23.0% of revenue, median 27 products, UK share 92%.  
- Home-décor & sign shops: 20.3% of customers, 33.8% of revenue, median 122 products, UK share 92%.  
- Large children's & kitchen-ware wholesalers: 6.5% of customers, 30.6% of revenue, median 268 products, UK share 84%.  
- Key accounts: 0.2% of customers, 12.6% of revenue, median 839 products, UK share 67%.  
- Figure: outputs/customer\_map.png, zoomed on the main cloud, key accounts noted off-chart, no customer IDs (R4).