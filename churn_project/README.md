# Customer Segmentation & Churn Pattern Analytics in European Banking

## Run order
```
pip install -r requirements.txt
python analysis.py       # validation, segmentation, KPIs, EDA figures  -> reports/results.json
python ml_pipeline.py    # ML: model comparison, tuning, evaluation, K-Means, scoring -> reports/ml_results.json, data/*.joblib|csv
streamlit run app.py     # interactive dashboard
node build_reports.js    # rebuild Word reports (npm i docx)
```
## Files
- `churn_utils.py`  validation, segmentation, KPI logic, ML feature engineering
- `analysis.py`     EDA + segment churn + high-value analysis
- `ml_pipeline.py`  ML pipeline (LogReg / RandomForest / tuned Gradient Boosting, CV, threshold, explainability, K-Means)
- `app.py`          Streamlit dashboard (7 modules incl. ML risk scoring and what-if predictor)
- `reports/`        Research paper, Executive summary (.docx/.pdf), results JSON
- `data/`           European_Bank.csv, scored_customers.csv, churn_model.joblib
