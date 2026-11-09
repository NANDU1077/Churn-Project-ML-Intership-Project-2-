"""Streamlit dashboard - Customer Segmentation & Churn Pattern Analytics in European Banking.
Run:  streamlit run app.py
"""
import numpy as np, pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
from churn_utils import *

st.set_page_config(page_title="European Bank Churn Analytics", page_icon="🏦", layout="wide")
NAVY, RED, GREY = "#1F3A5F", "#C8453B", "#9AA5B1"
st.markdown("""<style>.block-container{padding-top:1.5rem}
div[data-testid="stMetric"]{background:#F4F6F9;border-left:4px solid #1F3A5F;padding:10px 14px;border-radius:6px}
div[data-testid="stMetric"] label{color:#444}</style>""", unsafe_allow_html=True)


@st.cache_data
def get_raw(file):
    return load_and_validate(file)

st.sidebar.title("🏦 Churn Analytics")
up = st.sidebar.file_uploader("Upload dataset (optional)", type="csv")
from pathlib import Path
HERE = Path(__file__).resolve().parent
CANDIDATES = [HERE / "data" / "European_Bank.csv", HERE / "European_Bank.csv", HERE.parent / "data" / "European_Bank.csv",
              HERE.parent / "European_Bank.csv", Path.cwd() / "data" / "European_Bank.csv", Path.cwd() / "European_Bank.csv"]
default_csv = next((p for p in CANDIDATES if p.exists()), None)
if up is None and default_csv is None:
    st.title("🏦 Churn Analytics")
    st.error("European_Bank.csv was not found in the repository. Upload it in the sidebar, or add it to a `data/` folder next to app.py and push it to GitHub.")
    st.stop()
raw, checks = get_raw(up if up else str(default_csv))
hv_q = st.sidebar.slider("High-value = balance in top …%", 5, 50, 25, 5, help="Customers whose balance is in the top X% of all customers") / 100
data, hv_thr, _ = prepare(raw, 1 - hv_q)

st.sidebar.header("Segment filters")
def ms(label, col, order=None):
    opts = order or sorted(data[col].astype(str).unique())
    return st.sidebar.multiselect(label, opts, default=opts)
f_geo = ms("Geography", "Geography"); f_gen = ms("Gender", "Gender")
f_age = ms("Age group", "AgeGroup", AGE_ORDER); f_cs = ms("Credit score band", "CreditBand", CS_ORDER)
f_ten = ms("Tenure group", "TenureGroup", TEN_ORDER); f_bal = ms("Balance segment", "BalanceSegment", BAL_ORDER)
f_act = ms("Activity", "ActivityStatus"); f_prod = ms("Products held", "ProductsGroup")
d = data[data.Geography.isin(f_geo) & data.Gender.isin(f_gen) & data.AgeGroup.astype(str).isin(f_age) & data.CreditBand.astype(str).isin(f_cs)
         & data.TenureGroup.astype(str).isin(f_ten) & data.BalanceSegment.astype(str).isin(f_bal) & data.ActivityStatus.isin(f_act)
         & data.ProductsGroup.astype(str).isin(f_prod)]

st.title("Customer Segmentation & Churn Pattern Analytics")
st.caption("European Banking · France, Spain, Germany · All KPIs update with the sidebar filters")
if d.empty:
    st.warning("No customers match the selected filters."); st.stop()

K, KA = kpis(d), kpis(data)
overall_all = KA["overall_churn_rate"]
def bar(tab, title, x="Segment", h=360, avg=None):
    avg = overall_all if avg is None else avg
    fig = go.Figure(go.Bar(x=tab[x].astype(str), y=tab.ChurnRate, marker_color=[RED if v > avg else NAVY for v in tab.ChurnRate],
                           text=[f"{v:.1f}%" for v in tab.ChurnRate], textposition="outside", customdata=np.c_[tab.Customers, tab.Churned, tab.ContributionToChurn],
                           hovertemplate="%{x}<br>Churn rate: %{y:.1f}%<br>Customers: %{customdata[0]:,}<br>Churned: %{customdata[1]:,}<br>Share of churn: %{customdata[2]:.1f}%<extra></extra>"))
    fig.add_hline(y=avg, line_dash="dash", line_color=GREY, annotation_text=f"bank avg {avg:.1f}%")
    fig.update_layout(title=title, height=h, yaxis_title="Churn rate (%)", yaxis_range=[0, max(tab.ChurnRate.max() * 1.2, 5)], margin=dict(t=50, b=10), plot_bgcolor="white")
    return fig

def kpi_row():
    c = st.columns(5)
    c[0].metric("Overall Churn Rate", f"{K['overall_churn_rate']:.1f}%", f"{K['overall_churn_rate'] - overall_all:+.1f} pp vs bank", delta_color="inverse")
    c[1].metric("Customers / Churned", f"{K['customers']:,} / {K['churned']:,}")
    hvr = K["high_value_churn_rate"]
    c[2].metric("High-Value Churn Ratio", "n/a" if np.isnan(K["high_value_churn_ratio"]) else f"{K['high_value_churn_ratio']:.2f}x", None if np.isnan(hvr) else f"HV churn {hvr:.1f}%", delta_color="off",
                help="Churn rate of high-value customers ÷ churn rate of other customers")
    e = K["engagement_drop_indicator"]
    c[3].metric("Engagement Drop Indicator", "n/a" if np.isnan(e) else f"{e:.2f}x", None if np.isnan(e) else f"Inactive {K['inactive_churn_rate']:.1f}% vs Active {K['active_churn_rate']:.1f}%", delta_color="off",
                help="Churn rate of inactive members ÷ churn rate of active members")
    c[4].metric("Balance at Risk", f"€{K['balance_at_risk'] / 1e6:,.1f}m", f"{K['balance_at_risk_pct']:.1f}% of balances", delta_color="off")
kpi_row(); st.divider()

t1, t2, t3, t4, t5, t6 = st.tabs(["📊 Overview", "🌍 Geography", "👥 Age & Tenure", "💎 High-Value Explorer", "🔎 Segment Drill-down", "🧠 Risk Scoring"])

with t1:
    a, b = st.columns([1, 2])
    pie = px.pie(d, names="Status", color="Status", color_discrete_map={"Retained": NAVY, "Churned": RED}, hole=.55, title="Churned vs retained")
    pie.update_layout(height=360, margin=dict(t=50, b=10)); a.plotly_chart(pie, width="stretch")
    dim = b.selectbox("Segment dimension", list(SEGMENT_COLS), index=0)
    tab = segment_table(d, SEGMENT_COLS[dim])
    b.plotly_chart(bar(tab, f"Churn rate by {dim}"), width="stretch")
    st.subheader("Churn contribution vs segment size")
    m = tab.melt("Segment", ["ShareOfCustomers", "ContributionToChurn"], var_name="Metric", value_name="%")
    m["Metric"] = m.Metric.map({"ShareOfCustomers": "% of customers", "ContributionToChurn": "% of all churn"})
    st.plotly_chart(px.bar(m, x="Segment", y="%", color="Metric", barmode="group", color_discrete_sequence=[GREY, RED], height=330), width="stretch")
    st.subheader("Churned vs retained profile")
    prof = d.groupby("Status")[["CreditScore", "Age", "Tenure", "Balance", "NumOfProducts", "EstimatedSalary", "IsActiveMember"]].mean().T
    if {"Churned", "Retained"} <= set(prof.columns):
        prof["Difference %"] = (prof.Churned / prof.Retained - 1) * 100
    st.dataframe(prof.round(2), width="stretch")

with t2:
    gt = segment_table(d, "Geography")
    c1, c2 = st.columns(2)
    c1.plotly_chart(bar(gt, "Churn rate by country"), width="stretch")
    gri = pd.DataFrame({"Country": list(K["geographic_risk_index"]), "Index": list(K["geographic_risk_index"].values())})
    fig = px.bar(gri, x="Country", y="Index", text=gri.Index.round(0), title="Geographic Risk Index (100 = average)", color="Index", color_continuous_scale=["#2A9D8F", "#F4D35E", RED])
    fig.add_hline(y=100, line_dash="dash"); fig.update_layout(height=360, coloraxis_showscale=False, margin=dict(t=50, b=10)); c2.plotly_chart(fig, width="stretch")
    c3, c4 = st.columns(2)
    ga = d.pivot_table(index="Geography", columns="AgeGroup", values="Exited", aggfunc="mean", observed=True).mul(100)
    c3.plotly_chart(px.imshow(ga, text_auto=".1f", color_continuous_scale="Reds", title="Geography × Age: churn %", aspect="auto"), width="stretch")
    gg = d.groupby(["Geography", "Gender"]).Exited.mean().mul(100).reset_index()
    c4.plotly_chart(px.bar(gg, x="Geography", y="Exited", color="Gender", barmode="group", text_auto=".1f", title="Churn % by country & gender", color_discrete_sequence=[RED, NAVY]).update_yaxes(title="Churn %"), width="stretch")
    st.dataframe(gt.round(1), width="stretch", hide_index=True)

with t3:
    c1, c2 = st.columns(2)
    c1.plotly_chart(bar(segment_table(d, "AgeGroup"), "Churn rate by age group"), width="stretch")
    c2.plotly_chart(bar(segment_table(d, "TenureGroup"), "Churn rate by tenure group"), width="stretch")
    pv = d.pivot_table(index="AgeGroup", columns="TenureGroup", values="Exited", aggfunc="mean", observed=True).mul(100)
    st.plotly_chart(px.imshow(pv, text_auto=".1f", color_continuous_scale="Reds", title="Age × Tenure: churn %", aspect="auto", height=330), width="stretch")
    ag = d.groupby("Age").Exited.mean().mul(100).rolling(3, center=True, min_periods=1).mean().reset_index()
    st.plotly_chart(px.line(ag, x="Age", y="Exited", title="Churn rate by individual age (3-yr rolling mean)").update_yaxes(title="Churn %"), width="stretch")

with t4:
    st.markdown(f"**High-value definition:** balance ≥ **€{hv_thr:,.0f}** (top {int(hv_q * 100)}% of all customers). Change in the sidebar.")
    hv, oth = d[d.HighValue], d[~d.HighValue]
    if hv.empty:
        st.info("No high-value customers in the current filter selection.")
    else:
        c = st.columns(4)
        c[0].metric("High-value customers", f"{len(hv):,}"); c[1].metric("HV churn rate", f"{hv.Exited.mean() * 100:.1f}%")
        c[2].metric("Balance lost (HV churners)", f"€{hv.loc[hv.Exited == 1, 'Balance'].sum() / 1e6:,.1f}m")
        tot = d.loc[d.Exited == 1, "Balance"].sum(); c[3].metric("Share of all churned balance", f"{(hv.loc[hv.Exited == 1, 'Balance'].sum() / tot * 100 if tot else 0):.1f}%")
        c1, c2 = st.columns(2)
        tmp = d.assign(Group=np.where(d.HighValue, "High-value", "Other")); c1.plotly_chart(bar(segment_table(tmp, "Group"), "Churn: high-value vs other"), width="stretch")
        c2.plotly_chart(bar(segment_table(hv, "Geography"), "High-value churn by country"), width="stretch")
        samp = d.sample(min(4000, len(d)), random_state=1)
        st.plotly_chart(px.scatter(samp, x="EstimatedSalary", y="Balance", color="Status", opacity=.5, color_discrete_map={"Retained": NAVY, "Churned": RED},
                                   title="Salary vs balance (sample)", height=420).add_hline(y=hv_thr, line_dash="dash"), width="stretch")
        st.subheader("High-value churners – customer list")
        st.dataframe(hv[hv.Exited == 1].sort_values("Balance", ascending=False)[["CustomerId", "Geography", "Gender", "Age", "Tenure", "Balance", "EstimatedSalary", "NumOfProducts", "IsActiveMember"]].head(200),
                     width="stretch", hide_index=True)

with t5:
    c1, c2 = st.columns(2)
    r = c1.selectbox("Rows", list(SEGMENT_COLS), 0, key="r"); cc = c2.selectbox("Columns", list(SEGMENT_COLS), 2, key="c")
    if r == cc: st.info("Pick two different dimensions.")
    else:
        pv = d.pivot_table(index=SEGMENT_COLS[r], columns=SEGMENT_COLS[cc], values="Exited", aggfunc="mean", observed=True).mul(100)
        cnt = d.pivot_table(index=SEGMENT_COLS[r], columns=SEGMENT_COLS[cc], values="Exited", aggfunc="size", observed=True)
        st.plotly_chart(px.imshow(pv, text_auto=".1f", color_continuous_scale="Reds", aspect="auto", title=f"Churn % : {r} × {cc}"), width="stretch")
        st.caption("Customer counts"); st.dataframe(cnt, width="stretch")
    st.subheader("Highest-risk 3-way segments")
    combo = d.groupby(["Geography", "AgeGroup", "ActivityStatus"], observed=True).agg(Customers=("Exited", "size"), Churned=("Exited", "sum"), ChurnRate=("Exited", "mean")).reset_index()
    combo["ChurnRate"] *= 100
    min_n = st.slider("Minimum segment size", 10, 300, 50)
    st.dataframe(combo[combo.Customers >= min_n].sort_values("ChurnRate", ascending=False).head(12).round(1), width="stretch", hide_index=True)

with t6:
    import json, joblib
    ML_JSON, SCORES, MODEL = HERE / "reports" / "ml_results.json", HERE / "data" / "scored_customers.csv", HERE / "data" / "churn_model.joblib"
    if not (ML_JSON.exists() and SCORES.exists() and MODEL.exists()):
        st.info("Run `python ml_pipeline.py` once to generate the model files (reports/ml_results.json, data/scored_customers.csv, data/churn_model.joblib), then refresh.")
    else:
        ML = json.loads(ML_JSON.read_text()); T = ML["test"]
        st.markdown("**Model:** tuned Gradient Boosting, selected from 4 candidates by 5-fold cross-validation. Scores below are **out-of-fold** (each customer is scored by a model that never saw them), so they are not inflated by training on the same data.")
        c = st.columns(5)
        c[0].metric("Test ROC-AUC", f"{T['auc']:.3f}"); c[1].metric("PR-AUC", f"{T['pr_auc']:.3f}"); c[2].metric("Recall", f"{T['recall'] * 100:.0f}%")
        c[3].metric("Precision", f"{T['precision'] * 100:.0f}%"); c[4].metric("Top-decile lift", f"{T['lift_top_decile']:.1f}x")
        m1, m2 = st.tabs(["Risk tiers & priority list", "What-if predictor"])
        with m1:
            sc = d.merge(pd.read_csv(SCORES)[["CustomerId", "ChurnProbability", "RiskTier", "Cluster"]], on="CustomerId", how="left").dropna(subset=["ChurnProbability"])
            tier = sc.groupby("RiskTier").agg(Customers=("Exited", "size"), ActualChurnRate=("Exited", "mean"), BalanceAtStake=("Balance", "sum")).reindex(["Low", "Medium", "High"]).dropna().reset_index()
            tier["ActualChurnRate"] *= 100
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.bar(tier, x="RiskTier", y="ActualChurnRate", color="RiskTier", text_auto=".1f", color_discrete_map={"Low": "#2A9D8F", "Medium": "#F4D35E", "High": RED},
                                   title="Actual churn rate by predicted risk tier (%)"), width="stretch")
            c2.dataframe(tier.round(1), width="stretch", hide_index=True)
            st.subheader("Data-driven customer clusters (K-Means)")
            cl = pd.DataFrame(ML["clusters"]).rename(columns={"ChurnRate": "Churn %"})[["Cluster", "Label", "Customers", "Churn %", "Age", "Balance", "Products", "Active"]]
            st.dataframe(cl.round(1), width="stretch", hide_index=True)
            st.subheader("Top 100 at-risk customers still with the bank")
            st.dataframe(sc[sc.Exited == 0].sort_values("ChurnProbability", ascending=False).head(100)[["CustomerId", "Geography", "Age", "NumOfProducts", "IsActiveMember", "Balance", "ChurnProbability", "RiskTier"]].round(3),
                         width="stretch", hide_index=True)
            st.download_button("⬇ Download scored customers (CSV)", sc.to_csv(index=False), "scored_customers.csv", "text/csv")
        with m2:
            st.caption("Enter a customer profile to get a churn probability from the trained model.")
            a, b, c3 = st.columns(3)
            geo = a.selectbox("Geography", ["France", "Spain", "Germany"]); gen = a.selectbox("Gender", ["Female", "Male"])
            age = b.slider("Age", 18, 92, 45); ten = b.slider("Tenure (years)", 0, 10, 5)
            bal = c3.number_input("Balance (€)", 0.0, 300000.0, 100000.0, 5000.0); sal = c3.number_input("Estimated salary (€)", 0.0, 250000.0, 100000.0, 5000.0)
            a2, b2, c4 = st.columns(3)
            npr = a2.selectbox("Number of products", [1, 2, 3, 4], 0); cs = b2.slider("Credit score", 350, 850, 650)
            act_ = c4.checkbox("Active member", True); card = c4.checkbox("Has credit card", True)
            pack = joblib.load(MODEL)
            row = pd.DataFrame([dict(CreditScore=cs, Geography=geo, Gender=gen, Age=age, Tenure=ten, Balance=bal, NumOfProducts=npr, HasCrCard=int(card), IsActiveMember=int(act_), EstimatedSalary=sal)])
            prob = float(pack["model"].predict_proba(add_features(row))[0, 1])
            tier_ = "High" if prob > .5 else "Medium" if prob > .2 else "Low"
            g = go.Figure(go.Indicator(mode="gauge+number", value=prob * 100, number={"suffix": "%"}, title={"text": f"Churn probability · {tier_} risk"},
                                       gauge={"axis": {"range": [0, 100]}, "bar": {"color": RED if tier_ == "High" else "#F4A261" if tier_ == "Medium" else "#2A9D8F"},
                                              "steps": [{"range": [0, 20], "color": "#E8F5F3"}, {"range": [20, 50], "color": "#FFF6DA"}, {"range": [50, 100], "color": "#FBE3E0"}]}))
            g.update_layout(height=300, margin=dict(t=60, b=10)); st.plotly_chart(g, width="stretch")
