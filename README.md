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
