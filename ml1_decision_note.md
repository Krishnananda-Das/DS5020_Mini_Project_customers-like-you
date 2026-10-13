# ML1: Method decision (written BEFORE fitting any model)

## Choice
Main model: Truncated SVD (TruncatedSVD, no centring). Comparison model: PCA, same k, same matrix (ML5).

## Why
- Goal is product recommendations: SVD is the standard latent-factor method for this.
- The matrix is 98% sparse (5,471 x 3,686; 413,690 non-zeros). SVD works on sparse input natively.
- PCA centres columns, so zeros become negatives and the matrix becomes dense (161 MB vs 5 MB).
  Even with implicit centring, PCA describes deviation from the average customer, not what people buy.
- Customer and product factors come from one fit (U*S and V), which is what a recommender needs.

## Predictions (to check in ML5)
1. SVD component 1 = overall purchase volume / popular products; PCA component 1 = a contrast between customer types.
2. PCA will be slower and use more peak memory than SVD.
3. SVD hit rate at 10 >= PCA hit rate at 10.
4. Risk: SVD component 1 may encode popularity, pushing recommendations toward best sellers.
   If hit rate barely beats the baseline, we report that honestly.

## k values to test (ML2)
10, 20, 50, 100, 200. Choose k from the error curve plus the hit rate, not from one number.
