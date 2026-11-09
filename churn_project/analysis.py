"""End-to-end analysis: validation -> segmentation -> churn analytics -> ML model -> figures + results.json"""
import json, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix, recall_score, precision_score
from churn_utils import *
warnings.filterwarnings("ignore")

NAVY, RED, GREY, TEAL = "#1F3A5F", "#C8453B", "#9AA5B1", "#2A9D8F"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "figure.dpi": 130})
FIG = "figures/"

df, checks = load_and_validate("data/European_Bank.csv")
d, hv_thr, med_nz = prepare(df)
K = kpis(d)
overall = K["overall_churn_rate"]
R = {"validation": checks, "kpis": K, "hv_threshold": hv_thr, "median_nonzero_balance": med_nz, "segments": {}}

def bar(ax, tab, title, order=None):
    t = tab.copy()
    cols = [RED if v > overall else NAVY for v in t.ChurnRate]
    b = ax.bar(t.Segment.astype(str), t.ChurnRate, color=cols)
    ax.axhline(overall, color=GREY, ls="--", lw=1); ax.text(len(t) - .5, overall + .6, f"avg {overall:.1f}%", ha="right", color="#555", fontsize=8)
    for r, v, n in zip(b, t.ChurnRate, t.Customers):
        ax.text(r.get_x() + r.get_width() / 2, v + .8, f"{v:.1f}%", ha="center", fontsize=9, fontweight="bold")
        ax.text(r.get_x() + r.get_width() / 2, 1, f"n={n:,}", ha="center", fontsize=7, color="white")
    ax.set_title(title); ax.set_ylabel("Churn rate (%)"); ax.set_ylim(0, max(t.ChurnRate) * 1.2)

# ---- 1. Overall + segment churn ----
fig, ax = plt.subplots(figsize=(4.5, 4))
ax.pie([K["customers"] - K["churned"], K["churned"]], labels=["Retained", "Churned"], colors=[NAVY, RED], autopct="%.1f%%",
       startangle=90, wedgeprops=dict(width=.4), textprops={"color": "black"})
ax.set_title("Overall churn: %d of %s customers" % (K["churned"], f"{K['customers']:,}")); fig.tight_layout(); fig.savefig(FIG + "01_overall.png"); plt.close()

for name, col in SEGMENT_COLS.items():
    R["segments"][name] = segment_table(d, col).round(2).to_dict("records")

fig, axs = plt.subplots(2, 3, figsize=(15, 8))
for ax, n in zip(axs.flat, ["Geography", "Age Group", "Credit Score Band", "Tenure Group", "Balance Segment", "Products Held"]):
    bar(ax, pd.DataFrame(R["segments"][n]), f"Churn by {n}")
fig.tight_layout(); fig.savefig(FIG + "02_segments.png"); plt.close()

# contribution vs size (Pareto-style)
fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
for ax, n in zip(axs, ["Geography", "Age Group"]):
    t = pd.DataFrame(R["segments"][n]); x = np.arange(len(t)); w = .38
    ax.bar(x - w / 2, t.ShareOfCustomers, w, color=GREY, label="% of customers")
    ax.bar(x + w / 2, t.ContributionToChurn, w, color=RED, label="% of all churn")
    ax.set_xticks(x); ax.set_xticklabels(t.Segment); ax.set_title(f"Size vs churn contribution: {n}"); ax.legend(frameon=False); ax.set_ylabel("%")
fig.tight_layout(); fig.savefig(FIG + "03_contribution.png"); plt.close()

# ---- 2. Churned vs retained profile ----
num = ["CreditScore", "Age", "Tenure", "Balance", "NumOfProducts", "EstimatedSalary", "IsActiveMember", "HasCrCard"]
prof = d.groupby("Status")[num].mean().T.round(2); prof["Diff_%"] = ((prof.Churned / prof.Retained - 1) * 100).round(1)
R["profile"] = prof.reset_index().rename(columns={"index": "Metric"}).to_dict("records")
fig, axs = plt.subplots(1, 3, figsize=(14, 4))
for ax, c in zip(axs, ["Age", "Balance", "CreditScore"]):
    for s, col in [("Retained", NAVY), ("Churned", RED)]:
        ax.hist(d.loc[d.Status == s, c], bins=30, alpha=.6, color=col, label=s, density=True)
    ax.set_title(f"{c}: churned vs retained"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIG + "04_profiles.png"); plt.close()

# ---- 3. Demographic interactions ----
gg = d.groupby(["Geography", "Gender"]).Exited.mean().mul(100).unstack().round(2)
R["geo_gender"] = gg.reset_index().to_dict("records")
ga = d.pivot_table(index="Geography", columns="AgeGroup", values="Exited", aggfunc="mean", observed=True).mul(100).round(1)
R["geo_age"] = ga.reset_index().to_dict("records")
fig, ax = plt.subplots(figsize=(6.5, 3.8))
im = ax.imshow(ga.values, cmap="Reds"); ax.set_xticks(range(4)); ax.set_xticklabels(ga.columns); ax.set_yticks(range(3)); ax.set_yticklabels(ga.index)
for i in range(3):
    for j in range(4): ax.text(j, i, f"{ga.values[i, j]:.1f}%", ha="center", va="center", fontweight="bold", color="white" if ga.values[i, j] > 40 else "black")
ax.set_title("Churn % by Geography x Age"); [s.set_visible(False) for s in ax.spines.values()]; fig.colorbar(im, shrink=.8); fig.tight_layout(); fig.savefig(FIG + "05_geo_age.png"); plt.close()

# financial stability: salary-to-balance, activity x products
d["SalaryBand"] = pd.qcut(d.EstimatedSalary, 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])
sal = segment_table(d, "SalaryBand"); R["salary_quartiles"] = sal.round(2).to_dict("records")
act_bal = d.groupby(["ActivityStatus", "BalanceSegment"], observed=True).Exited.mean().mul(100).unstack().round(1)
R["activity_balance"] = act_bal.reset_index().to_dict("records")
R["credit_card"] = segment_table(d, "CardStatus").round(2).to_dict("records")

# ---- 4. High-value customers ----
hv = d[d.HighValue]; nh = d[~d.HighValue]
R["high_value"] = {
    "threshold": hv_thr, "customers": len(hv), "churned": int(hv.Exited.sum()), "churn_rate": hv.Exited.mean() * 100,
    "balance_lost": float(hv.loc[hv.Exited == 1, "Balance"].sum()),
    "share_of_total_churned_balance": float(hv.loc[hv.Exited == 1, "Balance"].sum() / d.loc[d.Exited == 1, "Balance"].sum() * 100),
    "salary_churned_hv": float(hv.loc[hv.Exited == 1, "EstimatedSalary"].mean()), "salary_retained_hv": float(hv.loc[hv.Exited == 0, "EstimatedSalary"].mean()),
    "avg_balance_churned_all": float(d.loc[d.Exited == 1, "Balance"].mean()), "avg_balance_retained_all": float(d.loc[d.Exited == 0, "Balance"].mean()),
    "by_geo": segment_table(hv, "Geography").round(2).to_dict("records"),
    "by_activity": segment_table(hv, "ActivityStatus").round(2).to_dict("records"),
    "inactive_share_of_hv_churn": float((hv[hv.Exited == 1].IsActiveMember == 0).mean() * 100),
}
fig, axs = plt.subplots(1, 3, figsize=(15, 4.3))
bar(axs[0], segment_table(d, "HighValue").replace({True: "High-value", False: "Others"}), "Churn: high-value vs others")
axs[1].scatter(d.loc[d.Exited == 0, "EstimatedSalary"], d.loc[d.Exited == 0, "Balance"], s=3, c=NAVY, alpha=.25, label="Retained")
axs[1].scatter(d.loc[d.Exited == 1, "EstimatedSalary"], d.loc[d.Exited == 1, "Balance"], s=4, c=RED, alpha=.5, label="Churned")
axs[1].axhline(hv_thr, color="k", ls="--", lw=1); axs[1].set_xlabel("Estimated salary"); axs[1].set_ylabel("Balance"); axs[1].set_title("Salary vs balance"); axs[1].legend(frameon=False, markerscale=4)
gb = hv.groupby("Geography").agg(c=("Exited", "sum"), b=("Balance", lambda s: s[hv.loc[s.index, "Exited"] == 1].sum() / 1e6))
axs[2].bar(gb.index, gb.b, color=RED); axs[2].set_title("Balance lost from high-value churners (EUR m)")
for i, v in enumerate(gb.b): axs[2].text(i, v + .3, f"{v:.1f}", ha="center", fontweight="bold")
fig.tight_layout(); fig.savefig(FIG + "06_high_value.png"); plt.close()

# engagement x products
fig, axs = plt.subplots(1, 2, figsize=(11, 4))
bar(axs[0], segment_table(d, "ActivityStatus"), "Churn by activity status"); bar(axs[1], segment_table(d, "ProductsGroup"), "Churn by number of products")
fig.tight_layout(); fig.savefig(FIG + "07_engagement.png"); plt.close()

# ---- 5. Highest-risk segment combos ----
combo = d.groupby(["Geography", "AgeGroup", "ActivityStatus"], observed=True).agg(n=("Exited", "size"), churned=("Exited", "sum"), rate=("Exited", "mean")).reset_index()
combo["rate"] *= 100; top = combo[combo.n >= 50].sort_values("rate", ascending=False).head(8).round(1)
R["top_risk_combos"] = top.to_dict("records")

# ---- 6. Predictive model (supporting analysis) ----
feat = pd.get_dummies(d[["CreditScore", "Geography", "Gender", "Age", "Tenure", "Balance", "NumOfProducts", "HasCrCard", "IsActiveMember", "EstimatedSalary"]], drop_first=True)
Xtr, Xte, ytr, yte = train_test_split(feat, d.Exited, test_size=.25, stratify=d.Exited, random_state=42)
models = {"Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")),
          "Gradient Boosting": GradientBoostingClassifier(random_state=42, n_estimators=200, max_depth=3, learning_rate=.08)}
R["models"] = {}
for n, m in models.items():
    m.fit(Xtr, ytr); p = m.predict_proba(Xte)[:, 1]; thr = .5 if n.startswith("Log") else .3
    pred = (p >= thr).astype(int)
    R["models"][n] = {"auc": roc_auc_score(yte, p), "cv_auc": cross_val_score(m, feat, d.Exited, cv=5, scoring="roc_auc").mean(),
                      "recall": recall_score(yte, pred), "precision": precision_score(yte, pred), "threshold": thr}
best = models["Gradient Boosting"]
pi = permutation_importance(best, Xte, yte, scoring="roc_auc", n_repeats=8, random_state=42)
imp = pd.Series(pi.importances_mean, index=feat.columns).sort_values()
R["feature_importance"] = imp.sort_values(ascending=False).round(4).to_dict()
fig, ax = plt.subplots(figsize=(7, 4.2)); ax.barh(imp.index, imp.values, color=NAVY); ax.set_title("Permutation importance (drop in AUC)"); fig.tight_layout(); fig.savefig(FIG + "08_importance.png"); plt.close()

with open("reports/results.json", "w") as f: json.dump(R, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
d.to_csv("data/churn_segmented.csv", index=False)
print(json.dumps({k: R[k] for k in ["high_value", "top_risk_combos", "models", "feature_importance", "salary_quartiles", "geo_gender", "geo_age", "activity_balance", "profile", "credit_card"]}, indent=1, default=str)[:7000])
