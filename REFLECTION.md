# Individual Reflection

## What I did

I worked alone and took both roles. As Data Engineer, I profiled and cleaned the Online Retail II data, logged every rule, split the data by time into train, validation and test periods with leak checks, built the sparse customer x product matrix, and wrote `build_matrix.py` so the whole pipeline rebuilds from the raw file. As ML Engineer, I chose Truncated SVD before fitting anything, tuned k and a popularity blend on the validation period only, scored the test period once, compared PCA with SVD at the same k, and built a four-group customer map. I then wrote the memo for Sarah.

## What I learned

The biggest lesson was that a model can lose to the simple baseline. Plain SVD scored 21.8% against 27.0% for the best sellers, and only the popularity blend beat them (35.0%). Reporting that honestly mattered more to me than a flattering result. I also learned that most of the size saving came from storing only the non-zero cells (161 MB down to 5 MB), not from the compression itself (3.7 MB). Setting up the validation window kept the test data out of every choice, and it showed me why that rule exists: the validation and test scores agreed (34.5% and 35.0%), which gave me confidence the tuning had not overfit. My prediction that PCA and SVD would differ in what component 1 means was wrong; both mostly captured overall volume and popularity.

## What I would change

I would give the uncompressed table the same popularity blend, so the cost of compression can be measured fairly, because my comparison with it was not like-for-like. I would score the product-page "also bought" lists, which I only checked by eye. I would also test a different time of year, since the test period was the Christmas run-up, and measure how varied the blended suggestions are. Finally, I would start the Git repository on Day 1 and commit as I went, rather than uploading at the end.
