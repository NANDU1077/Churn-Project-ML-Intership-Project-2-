"""Machine-learning pipeline: feature engineering -> model comparison (CV) -> tuning -> threshold selection
-> held-out evaluation -> explainability -> K-Means customer clustering -> out-of-fold risk scores -> saved model."""
import json, warnings, joblib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate, cross_val_predict, RandomizedSearchCV
from sklearn.metrics import (roc_auc_score, average_precision_score, f1_score, precision_score, recall_score, accuracy_score,
                             confusion_matrix, roc_curve, precision_recall_curve, silhouette_score)
from sklearn.inspection import permutation_importance
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from churn_utils import *
warnings.filterwarnings("ignore")
NAVY, RED, GREY = "#1F3A5F", "#C8453B", "#9AA5B1"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "figure.dpi": 130})
SEED = 42

raw, _ = load_and_validate("data/European_Bank.csv")
d, _, _ = prepare(raw)
X, y = add_features(d), d.Exited
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.25, stratify=y, random_state=SEED)
pre = lambda: ColumnTransformer([("num", StandardScaler(), ML_NUM + ML_BIN), ("cat", OneHotEncoder(drop="first"), ML_CAT)])
mk = lambda est: Pipeline([("pre", pre()), ("model", est)])
cv = StratifiedKFold(5, shuffle=True, random_state=SEED)

# ---- 1. Compare candidate models with 5-fold CV on the training set ----
cands = {"Logistic Regression": mk(LogisticRegression(max_iter=2000, class_weight="balanced")),
         "Random Forest": mk(RandomForestClassifier(300, min_samples_leaf=5, class_weight="balanced_subsample", n_jobs=-1, random_state=SEED)),
         "Gradient Boosting (default)": mk(HistGradientBoostingClassifier(random_state=SEED))}
res = {}
for n, m in cands.items():
    s = cross_validate(m, Xtr, ytr, cv=cv, scoring=["roc_auc", "average_precision"], n_jobs=-1)
    res[n] = {"cv_auc": s["test_roc_auc"].mean(), "cv_auc_std": s["test_roc_auc"].std(), "cv_pr_auc": s["test_average_precision"].mean()}

# ---- 2. Hyper-parameter tuning of gradient boosting ----
grid = {"model__learning_rate": [.03, .05, .08, .12], "model__max_depth": [2, 3, 4, 5, None], "model__max_leaf_nodes": [8, 15, 31],
        "model__min_samples_leaf": [20, 40, 80], "model__l2_regularization": [0, .5, 1, 5], "model__max_iter": [150, 250, 400]}
rs = RandomizedSearchCV(mk(HistGradientBoostingClassifier(random_state=SEED)), grid, n_iter=25, scoring="roc_auc", cv=cv, random_state=SEED, n_jobs=-1).fit(Xtr, ytr)
res["Gradient Boosting (tuned)"] = {"cv_auc": rs.best_score_, "cv_auc_std": float(rs.cv_results_["std_test_score"][rs.best_index_]),
    "cv_pr_auc": float(cross_validate(rs.best_estimator_, Xtr, ytr, cv=cv, scoring="average_precision")["test_score"].mean())}
best = rs.best_estimator_
best_params = {k.replace("model__", ""): (v if v is None or isinstance(v, str) else float(v) if isinstance(v, float) else int(v)) for k, v in rs.best_params_.items()}

# ---- 3. Decision threshold chosen on out-of-fold TRAIN predictions (no test leakage) ----
oof_tr = cross_val_predict(best, Xtr, ytr, cv=cv, method="predict_proba")[:, 1]
ths = np.linspace(.1, .7, 61); f1s = [f1_score(ytr, oof_tr >= t) for t in ths]; thr = float(ths[int(np.argmax(f1s))])

# ---- 4. Held-out test evaluation (fit on train only) ----
best.fit(Xtr, ytr)
p = best.predict_proba(Xte)[:, 1]; pred = (p >= thr).astype(int)
cm = confusion_matrix(yte, pred)
test = {"auc": roc_auc_score(yte, p), "pr_auc": average_precision_score(yte, p), "precision": precision_score(yte, pred), "recall": recall_score(yte, pred),
        "f1": f1_score(yte, pred), "accuracy": accuracy_score(yte, pred), "threshold": thr, "baseline_accuracy": float(1 - yte.mean()),
        "tn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "tp": int(cm[1, 1]), "n_test": len(yte)}
base_lr = cands["Logistic Regression"].fit(Xtr, ytr); res["Logistic Regression"]["test_auc"] = roc_auc_score(yte, base_lr.predict_proba(Xte)[:, 1])
res["Random Forest"]["test_auc"] = roc_auc_score(yte, cands["Random Forest"].fit(Xtr, ytr).predict_proba(Xte)[:, 1])
res["Gradient Boosting (default)"]["test_auc"] = roc_auc_score(yte, cands["Gradient Boosting (default)"].fit(Xtr, ytr).predict_proba(Xte)[:, 1])
res["Gradient Boosting (tuned)"]["test_auc"] = test["auc"]

# lift: top decile
o = np.argsort(-p); top10 = yte.values[o[: len(p) // 10]].mean()
test["top_decile_churn_rate"] = float(top10); test["lift_top_decile"] = float(top10 / yte.mean())

fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
fpr, tpr, _ = roc_curve(yte, p); axs[0].plot(fpr, tpr, color=RED, lw=2, label=f"Tuned GB (AUC {test['auc']:.3f})")
fl, tl, _ = roc_curve(yte, base_lr.predict_proba(Xte)[:, 1]); axs[0].plot(fl, tl, color=NAVY, lw=1.5, label=f"Logistic (AUC {res['Logistic Regression']['test_auc']:.3f})")
axs[0].plot([0, 1], [0, 1], "--", color=GREY); axs[0].set_title("ROC curve (test set)"); axs[0].set_xlabel("False positive rate"); axs[0].set_ylabel("True positive rate"); axs[0].legend(frameon=False)
pr, rc, _ = precision_recall_curve(yte, p); axs[1].plot(rc, pr, color=RED, lw=2); axs[1].axhline(yte.mean(), ls="--", color=GREY)
axs[1].set_title(f"Precision-Recall (AP {test['pr_auc']:.3f})"); axs[1].set_xlabel("Recall"); axs[1].set_ylabel("Precision")
axs[2].imshow(cm, cmap="Blues"); axs[2].set_xticks([0, 1]); axs[2].set_yticks([0, 1]); axs[2].set_xticklabels(["Pred stay", "Pred churn"]); axs[2].set_yticklabels(["Actual stay", "Actual churn"])
for i in range(2):
    for j in range(2): axs[2].text(j, i, cm[i, j], ha="center", va="center", fontsize=14, fontweight="bold", color="white" if cm[i, j] > cm.max() / 2 else "black")
axs[2].set_title(f"Confusion matrix (threshold {thr:.2f})"); [s.set_visible(False) for s in axs[2].spines.values()]
fig.tight_layout(); fig.savefig("figures/09_model_eval.png"); plt.close()

# ---- 5. Explainability: permutation importance on held-out data ----
pi = permutation_importance(best, Xte, yte, scoring="roc_auc", n_repeats=10, random_state=SEED)
imp = pd.Series(pi.importances_mean, index=X.columns).sort_values()
fig, ax = plt.subplots(figsize=(7, 4.6)); ax.barh(imp.index, imp.values, color=NAVY); ax.set_title("Permutation importance (drop in test AUC)"); fig.tight_layout(); fig.savefig("figures/08_importance.png"); plt.close()

# ---- 6. Unsupervised customer segmentation (K-Means) ----
cl_cols = ["Age", "Balance", "NumOfProducts", "IsActiveMember", "CreditScore", "Tenure", "EstimatedSalary"]
Z = StandardScaler().fit_transform(d[cl_cols])
sil = {k: float(silhouette_score(Z, KMeans(k, n_init=10, random_state=SEED).fit_predict(Z), sample_size=4000, random_state=SEED)) for k in range(3, 8)}
inertia = {k: float(KMeans(k, n_init=10, random_state=SEED).fit(Z).inertia_) for k in range(2, 9)}
K_ = 5; km = KMeans(K_, n_init=20, random_state=SEED).fit(Z); d["Cluster"] = km.labels_
prof = d.groupby("Cluster").agg(Customers=("Exited", "size"), ChurnRate=("Exited", "mean"), Age=("Age", "mean"), Balance=("Balance", "mean"), Products=("NumOfProducts", "mean"),
                                Active=("IsActiveMember", "mean"), CreditScore=("CreditScore", "mean"), Salary=("EstimatedSalary", "mean")).reset_index()
prof["ChurnRate"] *= 100
def name(r):
    t = []
    t.append("Older" if r.Age > 43 else "Young" if r.Age < 36 else "Mid-age")
    t.append("zero-balance" if r.Balance < 20000 else "high-balance" if r.Balance > 110000 else "mid-balance")
    t.append("active" if r.Active > .6 else "inactive" if r.Active < .4 else "mixed-activity")
    if r.Products > 1.8: t.append("multi-product")
    return ", ".join(t)
prof["Label"] = prof.apply(name, axis=1); prof = prof.sort_values("ChurnRate", ascending=False).reset_index(drop=True)
pc = PCA(2, random_state=SEED).fit_transform(Z)
fig, axs = plt.subplots(1, 2, figsize=(13, 4.6)); cm_ = plt.get_cmap("tab10")
for c in range(K_): axs[0].scatter(pc[d.Cluster == c, 0], pc[d.Cluster == c, 1], s=4, alpha=.45, color=cm_(c), label=f"Cluster {c}")
axs[0].legend(markerscale=4, frameon=False, fontsize=8); axs[0].set_title("K-Means clusters (PCA projection)")
order = prof.sort_values("ChurnRate"); axs[1].barh([f"C{c}: {l}" for c, l in zip(order.Cluster, order.Label)], order.ChurnRate, color=[RED if v > 20.4 else NAVY for v in order.ChurnRate])
axs[1].axvline(d.Exited.mean() * 100, ls="--", color=GREY); axs[1].set_title("Churn rate by cluster (%)"); axs[1].tick_params(axis="y", labelsize=7)
fig.tight_layout(); fig.savefig("figures/10_clusters.png"); plt.close()

# ---- 7. Out-of-fold scores for every customer (honest, no in-sample leakage) + final model ----
oof = cross_val_predict(best, X, y, cv=cv, method="predict_proba")[:, 1]
sc = pd.DataFrame({"CustomerId": d.CustomerId, "ChurnProbability": oof.round(4), "Cluster": d.Cluster})
sc["RiskTier"] = pd.cut(sc.ChurnProbability, [-.01, .2, .5, 1], labels=["Low", "Medium", "High"]).astype(str)
sc.to_csv("data/scored_customers.csv", index=False)
tier = sc.assign(Exited=y.values).groupby("RiskTier").agg(Customers=("Exited", "size"), ActualChurn=("Exited", "mean")).mul([1, 100]).round(1)
final = mk(HistGradientBoostingClassifier(random_state=SEED, **{k: v for k, v in best_params.items()})).fit(X, y)
joblib.dump({"model": final, "threshold": thr, "features": ML_FEATURES}, "data/churn_model.joblib")

out = {"models": res, "best_params": best_params, "test": test, "feature_importance": imp.sort_values(ascending=False).round(4).to_dict(),
       "silhouette": sil, "inertia": inertia, "k": K_, "clusters": prof.round(2).to_dict("records"), "tiers": tier.reset_index().to_dict("records"),
       "n_train": len(Xtr), "n_features": X.shape[1], "engineered": ["BalanceSalaryRatio", "TenureAgeRatio", "IsZeroBalance"]}
json.dump(out, open("reports/ml_results.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps({k: out[k] for k in ["models", "best_params", "test", "feature_importance", "silhouette", "tiers"]}, indent=1))
print(prof.round(1).to_string())
