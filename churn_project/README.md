# Customer Segmentation & Churn Pattern Analytics in European Banking

## Run
```
pip install -r requirements.txt
python analysis.py          # figures + reports/results.json  (optional, outputs already included)
streamlit run app.py        # interactive dashboard
node build_reports.js       # rebuild Word reports (needs: npm i docx)
```
## Files
- `churn_utils.py`  validation, segmentation, KPI logic (shared)
- `analysis.py`     full EDA + segmentation + ML model, saves figures/
- `app.py`          Streamlit dashboard (filters, live KPIs, drill-downs, risk scoring)
- `reports/`        Research paper (.docx/.pdf), Executive summary (.docx/.pdf), results.json
- `data/`           European_Bank.csv, churn_segmented.csv
