const fs = require("fs");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, Header, Footer, PageNumber, AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType, PageBreak } = D;
const R = JSON.parse(fs.readFileSync("reports/results.json"));
const K = R.kpis, HV = R.high_value;
const pct = (v, n = 1) => v.toFixed(n) + "%";
const seg = (name, s) => R.segments[name].find(x => x.Segment === s);
const NAVY = "1F3A5F", GREY = "F2F4F7";

function runs(t, base = {}) {
  return t.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map(s => s.startsWith("**") ? new TextRun({ text: s.slice(2, -2), bold: true, ...base }) : new TextRun({ text: s, ...base }));
}
const P = (t, o = {}) => new Paragraph({ children: runs(t, o.run || {}), spacing: { after: 120, line: 276 }, alignment: o.align, ...(o.p || {}) });
const H1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const B = t => new Paragraph({ numbering: { reference: "bul", level: 0 }, children: runs(t), spacing: { after: 60, line: 276 } });
const Cap = t => new Paragraph({ children: [new TextRun({ text: t, italics: true, size: 18, color: "555555" })], alignment: AlignmentType.CENTER, spacing: { after: 200 } });
function Img(path, wDxaPx) {
  const b = fs.readFileSync(path), w = b.readUInt32BE(16), h = b.readUInt32BE(20), W = wDxaPx, H = Math.round(W * h / w);
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 60 }, children: [new ImageRun({ type: "png", data: b, transformation: { width: W, height: H }, altText: { title: path, description: path, name: path } })] });
}
const bd = { style: BorderStyle.SINGLE, size: 4, color: "C9CFD6" }, borders = { top: bd, bottom: bd, left: bd, right: bd };
function Tbl(head, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, hd) => new TableCell({ borders, width: { size: widths[i], type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: hd ? { fill: NAVY, type: ShadingType.CLEAR, color: "auto" } : undefined,
    children: [new Paragraph({ keepNext: true, alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER, children: [new TextRun({ text: String(t), bold: hd, color: hd ? "FFFFFF" : "000000", size: 19 })] })] });
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, cantSplit: true, children: head.map((h, i) => cell(h, i, true)) }), ...rows.map(r => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) }))] });
}
const spacer = () => new Paragraph({ spacing: { after: 120 }, children: [] });
const styles = {
  default: { document: { run: { font: "Calibri", size: 22 } } },
  paragraphStyles: [
    { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: "Calibri", size: 32, bold: true, color: NAVY }, paragraph: { spacing: { before: 320, after: 140 }, keepNext: true, outlineLevel: 0 } },
    { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: "Calibri", size: 26, bold: true, color: "2A5C8A" }, paragraph: { spacing: { before: 220, after: 100 }, keepNext: true, outlineLevel: 1 } },
    { id: "Title", name: "Title", basedOn: "Normal", run: { font: "Calibri", size: 52, bold: true, color: NAVY }, paragraph: { spacing: { before: 0, after: 120 }, keepNext: false } },
  ] };
const numbering = { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] };
const page = { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1200, left: 1440, right: 1440 } };
const mk = (label, children) => new Document({ styles, numbering, sections: [{ properties: { page },
  headers: { default: new Header({ children: [new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 4 } }, children: [new TextRun({ text: label, size: 18, color: "666666" })] })] }) },
  footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Page ", size: 18, color: "666666" }), new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "666666" })] })] }) },
  children }] });

// ------------ derived numbers ------------
const ger = seg("Geography", "Germany"), fra = seg("Geography", "France"), spa = seg("Geography", "Spain");
const a46 = seg("Age Group", "46-60"), a30 = seg("Age Group", "<30");
const p1 = seg("Products Held", "1"), p2 = seg("Products Held", "2"), p3 = seg("Products Held", "3"), p4 = seg("Products Held", "4");
const inact = seg("Active Member", "Inactive"), act = seg("Active Member", "Active");
const fem = seg("Gender", "Female"), male = seg("Gender", "Male");
const top = R.top_risk_combos[0];
const M = JSON.parse(fs.readFileSync("reports/ml_results.json")); const MT = M.test; const gb = { auc: MT.auc };
const segRows = n => R.segments[n].map(s => [s.Segment, s.Customers.toLocaleString(), s.Churned.toLocaleString(), pct(s.ChurnRate), pct(s.ContributionToChurn), s.RelativeRisk.toFixed(2) + "x"]);
const segHead = ["Segment", "Customers", "Churned", "Churn rate", "Share of churn", "Relative risk"], segW = [2226, 1300, 1200, 1400, 1500, 1400];
const eur = v => "€" + (v / 1e6).toFixed(1) + "m";

// =================== RESEARCH PAPER ===================
const paper = [
  new Paragraph({ spacing: { before: 1800, after: 200 }, children: [new TextRun({ text: "RESEARCH PAPER", size: 22, bold: true, color: "2A5C8A", characterSpacing: 60 })] }),
  new Paragraph({ style: "Title", children: [new TextRun("Customer Segmentation & Churn Pattern Analytics in European Banking")] }),
  new Paragraph({ spacing: { after: 400 }, border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: NAVY, space: 8 } }, children: [new TextRun({ text: "Exploratory data analysis, segment insights, predictive risk scoring and retention recommendations", size: 26, color: "444444" })] }),
  P("**Dataset:** European Bank customer file, 10,000 customers across France, Spain and Germany"),
  P("**Deliverables:** this paper · Streamlit dashboard (app.py) · ML pipeline (ml_pipeline.py) · Executive summary"),
  P("**Prepared for:** Unified Mentor – Machine Learning project submission"),
  new Paragraph({ children: [new PageBreak()] }),

  H1("Abstract"),
  P(`Customer churn is a major hidden cost in retail banking. This study analyses ${K.customers.toLocaleString()} customers of a European retail bank to establish who leaves, where, and how much value leaves with them. The overall churn rate is **${pct(K.overall_churn_rate, 2)}** (${K.churned.toLocaleString()} customers). Churn is far from uniform: Germany churns at **${pct(ger.ChurnRate)}** versus ${pct(fra.ChurnRate)} in France and ${pct(spa.ChurnRate)} in Spain; customers aged 46–60 churn at **${pct(a46.ChurnRate)}**; inactive members churn at ${pct(inact.ChurnRate)} versus ${pct(act.ChurnRate)} for active members; and customers holding 3 or 4 products churn at ${pct(p3.ChurnRate)} and ${pct(p4.ChurnRate)}. Credit score, tenure, salary and credit-card ownership show almost no relationship with churn. High-value customers (top 25% by balance) churn at ${pct(HV.churn_rate)} and account for **${pct(HV.share_of_total_churned_balance, 0)} of all balances lost**. A tuned gradient-boosting model, selected by cross-validation, reaches a held-out ROC-AUC of ${gb.auc.toFixed(2)} and finds 4.2 times more churners in its top-risk decile than random targeting; its feature importance confirms that product count, age, activity, geography and balance carry the signal. The paper ends with targeted, segment-level retention recommendations.`),

  H1("1. Background and Context"),
  P("Losing existing customers reduces lifetime value, raises acquisition costs and makes revenue unstable. Banks usually track a single headline churn rate, but that figure cannot say which customer groups are most at risk, how churn differs by country, age or financial profile, or whether churn is concentrated among high-value or low-value customers. Without that granularity, retention strategies remain generic, reactive and inefficient. This project closes that gap with a systematic, segmentation-driven analysis."),

  H1("2. Problem Statement and Objectives"),
  H2("2.1 Primary objectives"),
  B("Measure the overall churn rate."), B("Identify how churn is distributed across customer segments."), B("Compare churn behaviour across European regions."),
  H2("2.2 Secondary objectives"),
  B("Understand churn among high-value customers."), B("Evaluate engagement and tenure patterns."), B("Support strategic planning and marketing decisions."), B("Build and validate a machine-learning model that predicts individual churn risk, and discover data-driven customer clusters."),

  H1("3. Data Description and Validation"),
  P("The dataset contains one row per customer with 14 fields: CustomerId, Surname, CreditScore, Geography, Gender, Age, Tenure, Balance, NumOfProducts, HasCrCard, IsActiveMember, EstimatedSalary, Exited (target) and a constant Year field (2025). Because the data is a single snapshot, all findings describe associations at one point in time."),
  Tbl(["Validation check", "Result"], [
    ["Rows / columns", `${R.validation.rows.toLocaleString()} / ${R.validation.columns}`], ["Missing values", String(R.validation.missing_values)],
    ["Duplicate CustomerIds", String(R.validation.duplicate_customers)], ["Binary fields (HasCrCard, IsActiveMember, Exited) only 0/1", R.validation.binary_fields_valid ? "Pass" : "Fail"],
    ["NumOfProducts range", R.validation.products_range.join(" – ")], ["Geographies", R.validation.geographies.join(", ")],
    ["Churn label values", R.validation.churn_label_values.join(", ") + "  (1 = exited)"],
  ], [5200, 3826]),
  spacer(), P("The data passed every check. No imputation or row removal was needed. Surname (non-analytical, personal) and Year (constant) were dropped before analysis."),

  H1("4. Analytical Methodology"),
  P("The workflow follows the brief: ingestion and validation, cleaning and preparation, segmentation design, churn distribution analysis, comparative demographic analysis, high-value customer analysis, and KPI computation. A machine-learning layer (feature engineering, model comparison with cross-validation, hyper-parameter tuning, threshold selection, held-out evaluation, explainability and K-Means clustering) turns the segment findings into customer-level risk scores. All logic lives in churn_utils.py and analysis.py so results are reproducible."),
  H2("4.1 Segmentation design"),
  Tbl(["Dimension", "Segments", "Rule"], [
    ["Geography", "France, Spain, Germany", "As recorded"], ["Age", "<30, 30–45, 46–60, 60+", "Age in years"],
    ["Credit score", "Low, Medium, High", "<580, 580–739, 740+"], ["Tenure", "New, Mid-term, Long-term", "0–2, 3–6, 7–10 years"],
    ["Balance", "Zero, Low, High", `Zero = 0; Low/High split at the median non-zero balance (€${Math.round(R.median_nonzero_balance).toLocaleString()})`],
    ["High-value", "Premium customers", `Balance ≥ €${Math.round(HV.threshold).toLocaleString()} (top 25% of all customers)`],
  ], [1800, 3000, 4226]),
  Cap("Table 1 – Segment definitions (credit bands follow common industry cut-offs; thresholds are adjustable in the dashboard)"),
  H2("4.2 Metrics"),
  B("**Segment churn rate** = churned ÷ customers in the segment."),
  B("**Share of churn** = segment's churners ÷ all churners; compared with its share of customers to show over- or under-representation."),
  B("**Relative risk** = segment churn rate ÷ overall churn rate."),
  B("**Geographic Risk Index** = country churn rate ÷ overall rate × 100 (100 = average)."),
  B("**High-Value Churn Ratio** = churn rate of high-value customers ÷ churn rate of all other customers."),
  B("**Engagement Drop Indicator** = churn rate of inactive members ÷ churn rate of active members."),

  H1("5. Results"),
  H2("5.1 Overall churn"),
  P(`Of ${K.customers.toLocaleString()} customers, **${K.churned.toLocaleString()} exited, an overall churn rate of ${pct(K.overall_churn_rate, 2)}**: roughly one in five. Churned customers held ${eur(K.balance_at_risk)} in balances, equal to ${pct(K.balance_at_risk_pct)} of all balances in the bank.`),
  Img("figures/01_overall.png", 300),
  H2("5.2 Churn across customer segments"),
  Img("figures/02_segments.png", 590), Cap("Figure 1 – Churn rate by segment (red bars exceed the bank average)"),
  P(`**Geography.** Germany is the clear outlier at ${pct(ger.ChurnRate)}, double France (${pct(fra.ChurnRate)}) and Spain (${pct(spa.ChurnRate)}). Germany holds only ${pct(ger.ShareOfCustomers, 0)} of customers but ${pct(ger.ContributionToChurn, 0)} of all churners, and its Geographic Risk Index is ${K.geographic_risk_index.Germany.toFixed(0)} against ${K.geographic_risk_index.France.toFixed(0)} for France and ${K.geographic_risk_index.Spain.toFixed(0)} for Spain.`),
  Tbl(segHead, segMatrix("Geography"), segW), spacer(),
  P(`**Age.** Churn is strongly non-linear in age. Customers under 30 rarely leave (${pct(a30.ChurnRate)}); the 46–60 group leaves at ${pct(a46.ChurnRate)}, 2.5 times the bank average. Although the group is only ${pct(a46.ShareOfCustomers, 0)} of customers, it generates ${pct(a46.ContributionToChurn, 0)} of all churn. The 60+ group (${pct(seg("Age Group", "60+").ChurnRate)}) is also above average.`),
  Tbl(segHead, segMatrix("Age Group"), segW), spacer(),
  P(`**Credit score and tenure.** Neither separates churners from stayers. Credit bands range only from ${pct(seg("Credit Score Band", "High").ChurnRate)} to ${pct(seg("Credit Score Band", "Low").ChurnRate)}, and tenure groups from ${pct(seg("Tenure Group", "Long-term (7-10y)").ChurnRate)} to ${pct(seg("Tenure Group", "New (0-2y)").ChurnRate)}. Long-standing customers are therefore not safer: loyalty built through time alone does not protect against churn.`),
  P(`**Balance.** Zero-balance customers churn least (${pct(seg("Balance Segment", "Zero balance").ChurnRate)}); customers with money in the account churn at about ${pct(seg("Balance Segment", "High balance").ChurnRate, 0)} regardless of whether the balance is low or high.`),
  Img("figures/03_contribution.png", 560), Cap("Figure 2 – Share of customers versus share of churn"),

  H2("5.3 Churned versus retained customers"),
  Tbl(["Metric (mean)", "Churned", "Retained", "Difference"], R.profile.map(r => [r.Metric, r.Churned.toLocaleString(undefined, { maximumFractionDigits: 2 }), r.Retained.toLocaleString(undefined, { maximumFractionDigits: 2 }), (r["Diff_%"] > 0 ? "+" : "") + r["Diff_%"] + "%"]), [2800, 2000, 2000, 2226]),
  Cap("Table 2 – Profile comparison"),
  P(`Churners are about 7.4 years older on average (44.8 vs 37.4), hold about 25% higher balances, and are about one third less likely to be active members. Salary and credit score are practically identical across the two groups, so financial stability measured by these two fields does not explain churn.`),
  Img("figures/04_profiles.png", 590), Cap("Figure 3 – Distribution of age, balance and credit score"),

  H2("5.4 Comparative demographic analysis"),
  P(`**Gender.** Female customers churn at ${pct(fem.ChurnRate)} versus ${pct(male.ChurnRate)} for male customers, a gap of ${(fem.ChurnRate - male.ChurnRate).toFixed(1)} percentage points. The gap appears in every country (France ${pct(R.geo_gender[0].Female)} vs ${pct(R.geo_gender[0].Male)}; Germany ${pct(R.geo_gender[1].Female)} vs ${pct(R.geo_gender[1].Male)}; Spain ${pct(R.geo_gender[2].Female)} vs ${pct(R.geo_gender[2].Male)}).`),
  P(`**Geography × age.** The age effect appears in all three countries but is amplified in Germany, where ${pct(R.geo_age[1]["46-60"])} of 46–60-year-olds churn, compared with ${pct(R.geo_age[0]["46-60"])} in France and ${pct(R.geo_age[2]["46-60"])} in Spain. Germany is higher than the other countries in every age band.`),
  Img("figures/05_geo_age.png", 400), Cap("Figure 4 – Churn rate by geography and age group"),
  P(`**Financial stability versus churn.** Salary quartiles show a flat pattern (${pct(R.salary_quartiles[0].ChurnRate)}, ${pct(R.salary_quartiles[1].ChurnRate)}, ${pct(R.salary_quartiles[2].ChurnRate)}, ${pct(R.salary_quartiles[3].ChurnRate)} from lowest to highest), and credit-card ownership makes no difference (${pct(R.credit_card[0].ChurnRate)} with card vs ${pct(R.credit_card[1].ChurnRate)} without). Income does not predict churn; behaviour and life stage do.`),

  H2("5.5 Engagement and product holding"),
  Img("figures/07_engagement.png", 460), Cap("Figure 5 – Churn by activity status and number of products"),
  P(`**Engagement.** Inactive members churn at ${pct(inact.ChurnRate)} versus ${pct(act.ChurnRate)} for active members. The **Engagement Drop Indicator is ${K.engagement_drop_indicator.toFixed(2)}x**, and inactive members supply ${pct(inact.ContributionToChurn, 0)} of all churn. Inactivity roughly doubles churn in every balance segment.`),
  P(`**Products.** The relationship is U-shaped. Customers with two products are the most loyal (${pct(p2.ChurnRate)}); single-product customers churn at ${pct(p1.ChurnRate)}; and those with three or four products churn at ${pct(p3.ChurnRate)} and ${pct(p4.ChurnRate)}. The 3–4 product groups are small (${p3.Customers + p4.Customers} customers) but the pattern is extreme enough to warrant investigation: possible causes include mis-selling, bundling friction or fee dissatisfaction. This is a hypothesis, not something the data proves.`),
  Tbl(segHead, segMatrix("Products Held"), segW), spacer(),

  H2("5.6 High-value customer churn"),
  P(`High-value customers are defined as the top 25% by balance (≥ €${Math.round(HV.threshold).toLocaleString()}); there are ${HV.customers.toLocaleString()} of them. **${HV.churned} have churned (${pct(HV.churn_rate)})**, giving a **High-Value Churn Ratio of ${K.high_value_churn_ratio.toFixed(2)}x**: they leave about 23% more often than other customers. Because each carries a large balance, these ${HV.churned} customers took **${eur(HV.balance_lost)} (${pct(HV.share_of_total_churned_balance, 0)} of all churned balances)** with them.`),
  Img("figures/06_high_value.png", 600), Cap("Figure 6 – High-value churn, salary versus balance, and balance lost by country"),
  B(`**Salary versus balance.** High-value churners and stayers have nearly identical salaries (€${Math.round(HV.salary_churned_hv).toLocaleString()} vs €${Math.round(HV.salary_retained_hv).toLocaleString()}). Salary does not distinguish them; the balance simply makes the loss larger.`),
  B(`**Germany** accounts for ${pct(HV.by_geo[1].ContributionToChurn, 0)} of high-value churners from ${pct(HV.by_geo[1].ShareOfCustomers, 0)} of high-value customers (${pct(HV.by_geo[1].ChurnRate)} churn rate).`),
  B(`**Inactivity** is the dominant signal: ${pct(HV.inactive_share_of_hv_churn, 0)} of high-value churners were inactive members (inactive HV churn ${pct(HV.by_activity[1].ChurnRate)} vs ${pct(HV.by_activity[0].ChurnRate)} for active).`),

  H2("5.7 Highest-risk combined segments"),
  Tbl(["Geography", "Age", "Activity", "Customers", "Churned", "Churn rate"], R.top_risk_combos.slice(0, 6).map(r => [r.Geography, r.AgeGroup, r.ActivityStatus, r.n, r.churned, pct(r.rate)]), [1700, 1300, 1500, 1500, 1500, 1526]),
  Cap("Table 3 – Highest churn 3-way segments (minimum 50 customers)"),
  P(`The riskiest cell is **${top.Geography} customers aged ${top.AgeGroup} who are ${top.ActivityStatus.toLowerCase()}**: ${top.churned} of ${top.n} (${pct(top.rate, 0)}) left. Age 46–60 combined with inactivity gives churn above 60% in all three countries.`),

  H2("5.8 KPI summary"),
  Tbl(["KPI", "Value", "Interpretation"], [
    ["Overall Churn Rate", pct(K.overall_churn_rate, 2), "About 1 in 5 customers exited"],
    ["Segment Churn Rate (range)", `${pct(Math.min(...R.segments["Age Group"].map(s => s.ChurnRate)))} – ${pct(Math.max(...R.segments["Age Group"].map(s => s.ChurnRate)))}`, "Age groups: widest spread of the core segments"],
    ["High-Value Churn Ratio", K.high_value_churn_ratio.toFixed(2) + "x", `HV churn ${pct(K.high_value_churn_rate)} vs ${pct(K.non_high_value_churn_rate)} others`],
    ["Geographic Risk Index", `DE ${K.geographic_risk_index.Germany.toFixed(0)} · ES ${K.geographic_risk_index.Spain.toFixed(0)} · FR ${K.geographic_risk_index.France.toFixed(0)}`, "Germany ≈ 1.6x average exposure"],
    ["Engagement Drop Indicator", K.engagement_drop_indicator.toFixed(2) + "x", `Inactive ${pct(K.inactive_churn_rate)} vs active ${pct(K.active_churn_rate)}`],
  ], [2700, 2600, 3726]),
  Cap("Table 4 – Key performance indicators"),

  H2("5.9 Machine-learning model for churn prediction"),
  P(`The segment analysis explains where churn concentrates; a supervised model turns that into a customer-level risk score. The data was split 75/25 with stratification (${M.n_train.toLocaleString()} training, ${MT.n_test.toLocaleString()} test customers). Scaling and one-hot encoding sit inside a scikit-learn Pipeline so they are fitted only on training folds, which prevents data leakage. Three features were engineered: balance-to-salary ratio, tenure-to-age ratio and a zero-balance flag (${M.n_features} model inputs in total).`),
  P("**Model selection.** Four candidates were compared with stratified 5-fold cross-validation on the training set. Because churners are only about 20% of customers, PR-AUC is reported alongside ROC-AUC."),
  Tbl(["Model", "CV ROC-AUC (± std)", "CV PR-AUC", "Test ROC-AUC"], Object.entries(M.models).map(([n, v]) => [n, `${v.cv_auc.toFixed(3)} ± ${v.cv_auc_std.toFixed(3)}`, v.cv_pr_auc.toFixed(3), v.test_auc.toFixed(3)]), [3126, 2300, 1700, 1900]),
  Cap("Table 5 – Model comparison"),
  P(`Tree-based models clearly beat logistic regression, indicating non-linear effects such as the age and product-count patterns found in Section 5.2. Gradient boosting was then tuned with a randomised search (25 configurations × 5 folds; best: learning rate ${M.best_params.learning_rate}, max depth ${M.best_params.max_depth}, ${M.best_params.max_leaf_nodes} leaves, ${M.best_params.max_iter} iterations, L2 = ${M.best_params.l2_regularization}), lifting CV AUC to ${M.models["Gradient Boosting (tuned)"].cv_auc.toFixed(3)}.`),
  P(`**Decision threshold.** Rather than the default 0.5, the threshold (${MT.threshold}) was chosen by maximising F1 on out-of-fold predictions from the training data only, so the test set stays untouched.`),
  Tbl(["Test metric", "Value"], [["ROC-AUC", MT.auc.toFixed(3)], ["PR-AUC", MT.pr_auc.toFixed(3)], ["Recall (churners caught)", pct(MT.recall * 100)], ["Precision (flags that are correct)", pct(MT.precision * 100)],
    ["F1-score", MT.f1.toFixed(3)], ["Accuracy (vs " + pct(MT.baseline_accuracy * 100) + " for always predicting 'stay')", pct(MT.accuracy * 100)], ["Top-decile churn rate / lift", `${pct(MT.top_decile_churn_rate * 100)} / ${MT.lift_top_decile.toFixed(1)}x`]], [5600, 3426]),
  Cap("Table 6 – Held-out test performance of the tuned gradient-boosting model"),
  Img("figures/09_model_eval.png", 600), Cap("Figure 7 – ROC curve, precision-recall curve and confusion matrix on the test set"),
  P(`On the test set the model correctly identifies ${MT.tp} of ${MT.tp + MT.fn} churners (${pct(MT.recall * 100, 0)}) with ${MT.fp} false alarms. The ${MT.n_test / 10} customers it ranks as riskiest churn at ${pct(MT.top_decile_churn_rate * 100, 0)}, ${MT.lift_top_decile.toFixed(1)} times the base rate, so a retention team contacting only the top 10% would reach a far higher share of genuine churners than random outreach.`),
  P("**Explainability.** Permutation importance on held-out data measures how much AUC drops when a feature is shuffled."),
  Img("figures/08_importance.png", 400), Cap("Figure 8 – Permutation feature importance"),
  P(`**Number of products** and **age** dominate, followed by **activity status**, **geography** and **balance**. Salary, tenure, credit card ownership and the other engineered ratios add essentially nothing, which agrees with the segment analysis in Sections 5.2 to 5.6. Two independent methods therefore reach the same conclusion.`),
  P("**Calibration of risk tiers.** Every customer was scored out-of-fold (by a model that never saw them) and grouped into tiers. Actual churn rises steeply with the tier, which shows the scores are usable for prioritisation."),
  Tbl(["Risk tier", "Customers", "Actual churn rate"], ["Low", "Medium", "High"].map(t => { const r = M.tiers.find(x => x.RiskTier === t); return [t + (t === "Low" ? " (<20%)" : t === "Medium" ? " (20–50%)" : " (>50%)"), r.Customers.toLocaleString(), pct(r.ActualChurn)]; }), [3626, 2700, 2700]),
  Cap("Table 7 – Actual churn by predicted risk tier (out-of-fold)"),

  H2("5.10 Unsupervised segmentation with K-Means"),
  P(`Section 5.2 used rule-based segments. To check for natural groupings, K-Means was run on seven standardised variables (age, balance, products, activity, credit score, tenure, salary). The silhouette score was nearly flat across k = 3 to 7 (${Object.values(M.silhouette).map(v => v.toFixed(2)).join(", ")}), meaning customers form overlapping groups rather than sharply separated clusters; k = ${M.k} was chosen for interpretability. The clusters should therefore be read as descriptive personas, not hard categories.`),
  Tbl(["Cluster profile", "Customers", "Churn rate", "Avg age", "Avg products"], M.clusters.map(c => [`C${c.Cluster}: ${c.Label}`, c.Customers.toLocaleString(), pct(c.ChurnRate), c.Age.toFixed(0), c.Products.toFixed(1)]), [4026, 1200, 1300, 1200, 1300]),
  Cap("Table 8 – K-Means customer clusters, sorted by churn rate"),
  Img("figures/10_clusters.png", 590), Cap("Figure 9 – Cluster projection and churn rate by cluster"),
  P(`The highest-churn cluster (${pct(M.clusters[0].ChurnRate)}) is older, active customers with mid-sized balances (average age ${M.clusters[0].Age.toFixed(0)}), matching the 46–60 finding. The second (${pct(M.clusters[1].ChurnRate)}) is inactive, high-balance customers, the most valuable at-risk group. Young, active customers are the most loyal (${pct(M.clusters[4].ChurnRate)} to ${pct(M.clusters[3].ChurnRate)}).`),

  H1("6. Recommendations"),
  B(`**Launch a Germany retention programme.** Germany has ${pct(ger.ChurnRate, 0)} churn, 1.6x average risk, and the largest share of high-value losses. Investigate local competition, pricing and service quality before choosing the intervention.`),
  B(`**Create a 46–60 "life-stage" proposition.** This group produces ${pct(a46.ContributionToChurn, 0)} of churn from ${pct(a46.ShareOfCustomers, 0)} of customers. Proactive relationship-manager contact, savings and retirement-planning offers are natural levers.`),
  B(`**Build an early-warning trigger on inactivity.** Flag accounts that become inactive and contact them within a defined window; inactivity roughly doubles churn within every balance segment and accounts for ${pct(HV.inactive_share_of_hv_churn, 0)} of high-value churn.`),
  B("**Audit the 3–4 product bundles.** Near-total churn among multi-product customers suggests a product, pricing or service problem. Review the sales process and fees before pushing further cross-sell."),
  B(`**Protect high-value customers first.** Prioritise inactive, German, 46–60 high-balance customers; they carry the most balance at risk (${eur(HV.balance_lost)} already lost).`),
  B("**Target by behaviour, not by income, credit score or tenure.** These fields do not predict churn, so campaigns segmented on them will be poorly aimed."),
  B("**Use the risk-scoring model for outreach lists** and measure its impact with an A/B test so retention spend can be linked to retained balances."),
  B("**Investigate the gender gap.** Women churn roughly 8 to 10 points more than men in every country; review whether products, channels or service fit differ."),

  H1("7. Limitations"),
  B("The dataset is a single-year snapshot, so findings are associations, not proven causes."),
  B(`The 3-product and 4-product groups contain only ${p3.Customers} and ${p4.Customers} customers; results for them are indicative.`),
  B("Balance is used as a proxy for customer value because revenue and margin data are not available; true lifetime value may differ."),
  B("Credit-score and tenure cut-offs and the top-25% high-value threshold are analyst choices; the dashboard lets users vary the high-value threshold."),
  B("Model precision is moderate (about 64%); the model should support prioritisation, not automatic decisions about individual customers. The dataset has no time dimension, so the model cannot be validated on future data."),B("K-Means clusters overlap (low silhouette) and are descriptive rather than definitive."),

  H1("8. Conclusion"),
  P(`Churn in this bank is concentrated, not general. A small number of identifiable segments (German customers, those aged 46–60, inactive members and customers with 3–4 products) generate a disproportionate share of exits, while income, credit score and tenure matter little. High-value churn is a material revenue risk, with ${eur(HV.balance_lost)} of balances lost from just ${HV.churned} customers. Targeting retention at these segments, rather than at the customer base as a whole, is the most efficient route to reducing churn, and the accompanying dashboard lets decision-makers explore every cut of the data themselves.`),
];
function segMatrix(n) { return segRows(n); }

// =================== EXECUTIVE SUMMARY ===================
const kpiBox = (v, l) => new TableCell({ borders, width: { size: 1805, type: WidthType.DXA }, shading: { fill: GREY, type: ShadingType.CLEAR, color: "auto" }, margins: { top: 100, bottom: 100, left: 80, right: 80 },
  children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: v, bold: true, size: 36, color: NAVY })] }), new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: l, size: 16, color: "555555" })] })] });
const exec = [
  new Paragraph({ style: "Title", children: [new TextRun({ text: "Executive Summary", size: 44 })] }),
  new Paragraph({ spacing: { after: 240 }, children: [new TextRun({ text: "Customer Segmentation & Churn Pattern Analytics in European Banking", size: 26, color: "444444" })] }),
  new Table({ width: { size: 9026, type: WidthType.DXA }, columnWidths: [1805, 1805, 1805, 1805, 1806], rows: [new TableRow({ children: [
    kpiBox(pct(K.overall_churn_rate), "Overall churn rate"), kpiBox(pct(ger.ChurnRate, 0), "Germany churn (FR/ES ~16%)"), kpiBox(pct(a46.ChurnRate, 0), "Churn, ages 46–60"),
    kpiBox(K.engagement_drop_indicator.toFixed(1) + "x", "Inactive vs active members"), kpiBox(eur(HV.balance_lost), "Balance lost, high-value")] })] }),
  H1("Purpose"),
  P(`A segmentation and machine-learning analysis of ${K.customers.toLocaleString()} retail-bank customers in France, Spain and Germany: who churns, and what to do about it.`),
  H1("Key findings"),
  B(`**One in five customers leaves.** ${K.churned.toLocaleString()} of ${K.customers.toLocaleString()} customers exited (${pct(K.overall_churn_rate)}), taking ${eur(K.balance_at_risk)} in balances (${pct(K.balance_at_risk_pct, 0)} of the total).`),
  B(`**Germany is the hotspot.** Churn of ${pct(ger.ChurnRate)} is double that of France (${pct(fra.ChurnRate)}) and Spain (${pct(spa.ChurnRate)}), and Germany supplies ${pct(ger.ContributionToChurn, 0)} of all churners from a quarter of customers.`),
  B(`**Mid-life customers are most at risk.** Those aged 46–60 churn at ${pct(a46.ChurnRate)}, 2.5 times the average, and make up ${pct(a46.ContributionToChurn, 0)} of exits.`),
  B(`**Disengagement is the strongest warning sign.** Inactive members churn at ${pct(inact.ChurnRate)} against ${pct(act.ChurnRate)} for active members and account for ${pct(inact.ContributionToChurn, 0)} of exits.`),
  B(`**Multi-product customers are leaving.** Customers with 3 or 4 products churn at ${pct(p3.ChurnRate, 0)} and 100%, a signal of a possible product or service problem (small group, ${p3.Customers + p4.Customers} customers).`),
  B(`**High-value customers are a material risk.** The top 25% by balance churn ${K.high_value_churn_ratio.toFixed(2)} times as often as others; ${HV.churned} such customers took ${eur(HV.balance_lost)} (${pct(HV.share_of_total_churned_balance, 0)} of lost balances).`),
  B("**What does not matter:** credit score, tenure, salary and credit-card ownership show almost no link to churn."),
  H1("Recommended actions"),
  B("Prioritise a retention programme for German customers and for ages 46–60, where the highest-risk segments (Germany, 46–60, inactive: 81% churn) are concentrated."),
  B("Introduce early-warning triggers for customers who become inactive, with rapid personal contact for high-balance accounts."),
  B("Review the design, pricing and sales practices of 3–4 product bundles before further cross-selling."),
  B("Use the supplied risk-scoring model and dashboard to build outreach lists and to measure the effect of retention spending."),
  H1("Confidence and caveats"),
  P(`Findings come from a single-year snapshot and show associations, not proven causes. Balance is used as a stand-in for customer value. A tuned machine-learning model achieves a held-out AUC of ${gb.auc.toFixed(2)}: customers it places in its highest-risk tier churn at 76%, against 7% in the lowest tier. That is good enough to rank customers for outreach but not to make individual decisions automatically. Full method is in the research paper; the dashboard lets stakeholders explore any segment.`),
];

(async () => {
  fs.writeFileSync("reports/Research_Paper_Churn_Analytics.docx", await Packer.toBuffer(mk("Customer Segmentation & Churn Pattern Analytics in European Banking", paper)));
  fs.writeFileSync("reports/Executive_Summary.docx", await Packer.toBuffer(mk("Executive Summary – Churn Analytics, European Banking", exec)));
  console.log("done");
})();
