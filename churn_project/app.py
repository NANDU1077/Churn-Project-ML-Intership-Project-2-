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
    st.markdown("A gradient-boosting model trained on the full dataset ranks customers by churn probability, so retention teams can prioritise outreach.")
    @st.cache_resource
    def train(file_key, n):
        from sklearn.ensemble import GradientBoostingClassifier
        X = pd.get_dummies(data[["CreditScore", "Geography", "Gender", "Age", "Tenure", "Balance", "NumOfProducts", "HasCrCard", "IsActiveMember", "EstimatedSalary"]], drop_first=True)
        return GradientBoostingClassifier(random_state=42, n_estimators=200, max_depth=3, learning_rate=.08).fit(X, data.Exited), list(X.columns)
    model, cols = train(str(up.name if up else "default"), len(data))
    X = pd.get_dummies(d[["CreditScore", "Geography", "Gender", "Age", "Tenure", "Balance", "NumOfProducts", "HasCrCard", "IsActiveMember", "EstimatedSalary"]], drop_first=True).reindex(columns=cols, fill_value=0)
    sc = d.assign(ChurnProbability=model.predict_proba(X)[:, 1])
    sc["RiskTier"] = pd.cut(sc.ChurnProbability, [-.01, .2, .5, 1], labels=["Low", "Medium", "High"])
    tier = sc.groupby("RiskTier", observed=True).agg(Customers=("Exited", "size"), ActualChurnRate=("Exited", "mean"), BalanceAtStake=("Balance", "sum")).reset_index()
    tier["ActualChurnRate"] *= 100
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(tier, x="RiskTier", y="Customers", color="RiskTier", color_discrete_map={"Low": "#2A9D8F", "Medium": "#F4D35E", "High": RED}, title="Customers by predicted risk tier"), width="stretch")
    c2.dataframe(tier.round(1), width="stretch", hide_index=True)
    st.caption("Note: scores are in-sample (model trained on the same data) and shown for prioritisation; out-of-sample AUC is reported in the research paper.")
    st.subheader("Top 100 at-risk customers still with the bank")
    st.dataframe(sc[sc.Exited == 0].sort_values("ChurnProbability", ascending=False).head(100)[["CustomerId", "Geography", "Age", "NumOfProducts", "IsActiveMember", "Balance", "ChurnProbability"]].round(3), width="stretch", hide_index=True)
    st.download_button("⬇ Download scored customers (CSV)", sc.drop(columns=["Status"]).to_csv(index=False), "scored_customers.csv", "text/csv")
