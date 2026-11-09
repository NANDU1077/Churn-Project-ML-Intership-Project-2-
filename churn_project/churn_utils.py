"""Shared data-prep and KPI logic used by both the analysis pipeline and the Streamlit app."""
import numpy as np
import pandas as pd

AGE_ORDER = ["<30", "30-45", "46-60", "60+"]
CS_ORDER = ["Low", "Medium", "High"]
TEN_ORDER = ["New (0-2y)", "Mid-term (3-6y)", "Long-term (7-10y)"]
BAL_ORDER = ["Zero balance", "Low balance", "High balance"]
SEGMENT_COLS = {
    "Geography": "Geography", "Gender": "Gender", "Age Group": "AgeGroup",
    "Credit Score Band": "CreditBand", "Tenure Group": "TenureGroup",
    "Balance Segment": "BalanceSegment", "Products Held": "ProductsGroup",
    "Active Member": "ActivityStatus",
}


def load_and_validate(path):
    """Load the CSV and run the validation checks required by the brief."""
    df = pd.read_csv(path)
    checks = {
        "rows": len(df), "columns": df.shape[1],
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_customers": int(df.CustomerId.duplicated().sum()),
        "binary_fields_valid": bool(all(df[c].isin([0, 1]).all() for c in ["HasCrCard", "IsActiveMember", "Exited"])),
        "products_range": [int(df.NumOfProducts.min()), int(df.NumOfProducts.max())],
        "geographies": sorted(df.Geography.unique().tolist()),
        "churn_label_values": sorted(df.Exited.unique().tolist()),
    }
    return df, checks


def prepare(df, hv_quantile=0.75):
    """Drop non-analytical fields and derive the segmentation fields."""
    d = df.drop(columns=[c for c in ["Surname", "Year"] if c in df.columns]).copy()
    d["AgeGroup"] = pd.cut(d.Age, [0, 29, 45, 60, 200], labels=AGE_ORDER)
    d["CreditBand"] = pd.cut(d.CreditScore, [0, 579, 739, 900], labels=CS_ORDER)
    d["TenureGroup"] = pd.cut(d.Tenure, [-1, 2, 6, 10], labels=TEN_ORDER)
    med_nz = d.loc[d.Balance > 0, "Balance"].median()
    d["BalanceSegment"] = np.where(d.Balance == 0, BAL_ORDER[0],
                           np.where(d.Balance <= med_nz, BAL_ORDER[1], BAL_ORDER[2]))
    d["BalanceSegment"] = pd.Categorical(d.BalanceSegment, BAL_ORDER)
    d["ProductsGroup"] = d.NumOfProducts.map({1: "1", 2: "2", 3: "3", 4: "4"}).astype("category")
    d["ActivityStatus"] = d.IsActiveMember.map({1: "Active", 0: "Inactive"})
    d["CardStatus"] = d.HasCrCard.map({1: "Has card", 0: "No card"})
    thr = d.Balance.quantile(hv_quantile)
    d["HighValue"] = d.Balance >= thr
    d["Status"] = d.Exited.map({1: "Churned", 0: "Retained"})
    return d, float(thr), float(med_nz)


def segment_table(d, col):
    """Churn rate, size and contribution to total churn for each segment of `col`."""
    total_churn = d.Exited.sum()
    g = d.groupby(col, observed=True).agg(Customers=("Exited", "size"), Churned=("Exited", "sum")).reset_index()
    g["ChurnRate"] = g.Churned / g.Customers * 100
    g["ShareOfCustomers"] = g.Customers / len(d) * 100
    g["ContributionToChurn"] = g.Churned / total_churn * 100 if total_churn else 0
    g["RelativeRisk"] = g.ChurnRate / (d.Exited.mean() * 100) if total_churn else 0
    return g.rename(columns={col: "Segment"})


def kpis(d):
    """The five KPIs defined in the project brief (works on any filtered frame)."""
    if len(d) == 0:
        return {}
    overall = d.Exited.mean() * 100
    hv, nhv = d[d.HighValue], d[~d.HighValue]
    act, ina = d[d.IsActiveMember == 1], d[d.IsActiveMember == 0]
    geo = (d.groupby("Geography").Exited.mean() * 100)
    out = {
        "overall_churn_rate": overall,
        "customers": len(d), "churned": int(d.Exited.sum()),
        "high_value_churn_rate": hv.Exited.mean() * 100 if len(hv) else np.nan,
        "non_high_value_churn_rate": nhv.Exited.mean() * 100 if len(nhv) else np.nan,
        "high_value_churn_ratio": (hv.Exited.mean() / nhv.Exited.mean()) if len(hv) and len(nhv) and nhv.Exited.mean() > 0 else np.nan,
        "inactive_churn_rate": ina.Exited.mean() * 100 if len(ina) else np.nan,
        "active_churn_rate": act.Exited.mean() * 100 if len(act) else np.nan,
        "engagement_drop_indicator": (ina.Exited.mean() / act.Exited.mean()) if len(ina) and len(act) and act.Exited.mean() > 0 else np.nan,
        "geographic_risk_index": {k: (v / overall * 100 if overall else np.nan) for k, v in geo.items()},
        "balance_at_risk": float(d.loc[d.Exited == 1, "Balance"].sum()),
        "balance_total": float(d.Balance.sum()),
    }
    out["balance_at_risk_pct"] = out["balance_at_risk"] / out["balance_total"] * 100 if out["balance_total"] else np.nan
    return out


ML_NUM = ["CreditScore", "Age", "Tenure", "Balance", "NumOfProducts", "EstimatedSalary", "BalanceSalaryRatio", "TenureAgeRatio"]
ML_BIN = ["HasCrCard", "IsActiveMember", "IsZeroBalance"]
ML_CAT = ["Geography", "Gender"]
ML_FEATURES = ML_NUM + ML_BIN + ML_CAT


def add_features(df):
    """Feature engineering for the ML models (works on raw or prepared frames)."""
    f = df.copy()
    f["BalanceSalaryRatio"] = f.Balance / (f.EstimatedSalary + 1)
    f["TenureAgeRatio"] = f.Tenure / f.Age
    f["IsZeroBalance"] = (f.Balance == 0).astype(int)
    return f[ML_FEATURES]
