"""Streamlit dashboard for fraud and scam alert investigation."""

import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
pio.templates["fraud_workspace"] = pio.templates["plotly_white"]
pio.templates["fraud_workspace"].layout.update(
    font=dict(family="Arial, sans-serif", size=12, color="#52637a"),
    title=dict(font=dict(size=16, color="#142d4e")),
    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
    margin=dict(l=30, r=25, t=65, b=40),
    xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#edf1f6"),
    legend=dict(orientation="h", y=-0.2, x=0),
)
pio.templates.default = "fraud_workspace"
px.defaults.color_discrete_sequence = ["#142d4e", "#537292", "#91a7bd"]
import streamlit as st


# -------------------------------------------------------------------
# Page configuration
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Fraud & Scam Intelligence",
    page_icon="🔎",
    layout="wide",
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIRECTORY = PROJECT_ROOT / "data" / "synthetic_sample"


# -------------------------------------------------------------------
# Styling
# -------------------------------------------------------------------

st.markdown(
    """
    <style>
        .stApp { background: #f4f7fb; color: #142d4e; }
        [data-testid="stSidebar"] { background: #eaf0f7; }
        h1, h2, h3, h4 { color: #142d4e; }
        div[data-testid="stMetric"] label { color: #52637a; }
        div[data-testid="stMetricValue"] { color: #142d4e; }
        .context-banner {
            background: #142d4e; color: #fff; padding: 14px 20px;
            border-radius: 12px; margin: 0.5rem 0 1.3rem;
            font-size: 0.95rem;
        }
        button[data-baseweb="tab"] { font-weight: 600; }
        .block-container {
            padding-top: 2.5rem;
            max-width: 1500px;
            padding-bottom: 2rem;
        }

        [data-testid="stMetricLabel"] p { font-size: 0.86rem; }
        [data-testid="stMetricValue"] { font-size: clamp(1.5rem, 2.6vw, 2.1rem); }
        [data-testid="stCaptionContainer"] { color: #617189; }
        h1 { font-size: clamp(1.7rem, 3vw, 2.5rem) !important; letter-spacing: -0.03em; }
        [data-testid="stPlotlyChart"] {
            background: white; border: 1px solid #dbe4ef;
            border-radius: 12px; padding: 6px;
        }
        .main-title {
            font-size: 2.1rem;
            font-weight: 700;
            color: #12355b;
            margin-bottom: 0;
        }

        .subtitle {
            color: #5f6b7a;
            margin-top: 0.2rem;
            margin-bottom: 1.5rem;
        }

        div[data-testid="stMetric"] {
            background-color: #ffffff;
            min-height: 112px;
            box-shadow: 0 3px 12px rgba(20,45,78,0.04);
            border: 1px solid #dbe4ef;
            border-radius: 12px;
            padding: 16px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Load project data
# -------------------------------------------------------------------

# Choose the source before loading data. Local CSV remains the default.
st.sidebar.markdown("### Intelligence Workspace")
st.sidebar.caption("Independent portfolio project")
st.sidebar.subheader("Data source")
data_source = st.sidebar.radio(
    "Read data from",
    options=["Local CSV", "Google BigQuery"],
)
project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "elegant-azimuth-491717-a4")
dataset_id = os.getenv("BIGQUERY_DATASET", "fraud_analytics")
location = os.getenv("BIGQUERY_LOCATION", "australia-southeast2")
TABLE_NAMES = (
    "alert_queue", "scored_transactions", "rule_metrics", "scenario_metrics"
)


@st.cache_data(ttl=600, show_spinner=False)
def load_data(source: str, project: str, dataset: str, region: str):
    """Read all four pipeline outputs, caching results for ten minutes."""
    frames = {}
    if source == "Local CSV":
        for table in TABLE_NAMES:
            frames[table] = pd.read_csv(DATA_DIRECTORY / f"{table}.csv")
    else:
        # Imported only in cloud mode, so local mode works without cloud packages.
        from google.cloud import bigquery

        # Credentials are loaded from this laptop's ADC login, never from GitHub.
        with bigquery.Client(project=project, location=region) as client:
            for table in TABLE_NAMES:
                # Table names are fixed above; project and dataset use configuration.
                sql = f"SELECT * FROM `{project}.{dataset}.{table}`"
                job_config = bigquery.QueryJobConfig(
                    maximum_bytes_billed=100_000_000,
                    use_query_cache=True,
                )
                job = client.query(sql, job_config=job_config, location=region)
                frames[table] = job.to_dataframe(create_bqstorage_client=False)

    alerts = frames["alert_queue"]
    scored = frames["scored_transactions"]
    rule_metrics = frames["rule_metrics"]
    scenario_metrics = frames["scenario_metrics"]

    required = {
        "alert_queue": {
            "alert_id", "transaction_id", "transaction_timestamp", "customer_id",
            "account_id", "amount", "risk_score", "alert_severity", "fraud_scenario",
            "reason_codes", "country", "transaction_type", "channel", "beneficiary_id",
            "device_id", "evaluation_result",
        },
        "scored_transactions": {
            "transaction_id", "transaction_timestamp", "flag_high_amount",
            "flag_untrusted_device", "flag_foreign_country", "flag_new_beneficiary",
            "flag_high_velocity", "flag_shared_beneficiary", "flag_balance_depletion",
            "flag_unusual_hour",
        },
        "rule_metrics": {
            "total_alerts", "precision", "recall", "fraud_value_capture_rate",
            "true_positives", "false_positives", "false_negatives", "f1_score",
        },
        "scenario_metrics": {
            "fraud_scenario", "fraud_transactions", "detected_transactions",
            "total_fraud_value", "detected_fraud_value", "scenario_recall",
            "value_capture_rate",
        },
    }
    for table, columns in required.items():
        missing = columns - set(frames[table].columns)
        if missing:
            raise ValueError(f"{table} is missing columns: {', '.join(sorted(missing))}")
    if rule_metrics.empty:
        raise ValueError("rule_metrics is empty. Run the scoring pipeline first.")

    for frame in (alerts, scored):
        frame["transaction_timestamp"] = pd.to_datetime(
            frame["transaction_timestamp"], utc=True, errors="coerce"
        )
        if frame["transaction_timestamp"].isna().any():
            raise ValueError("The transaction data contains invalid timestamps.")
        frame["transaction_id"] = frame["transaction_id"].astype("string")
    alerts["amount"] = pd.to_numeric(alerts["amount"], errors="raise").astype(float)
    alerts["risk_score"] = pd.to_numeric(alerts["risk_score"], errors="raise").astype(float)
    for column in required["rule_metrics"]:
        rule_metrics[column] = pd.to_numeric(rule_metrics[column], errors="raise").astype(float)
    for column in required["scenario_metrics"] - {"fraud_scenario"}:
        scenario_metrics[column] = pd.to_numeric(
            scenario_metrics[column], errors="raise"
        ).astype(float)
    alerts["fraud_scenario_display"] = (
        alerts["fraud_scenario"].fillna("Normal / false positive")
        .replace("", "Normal / false positive")
    )
    return alerts, scored, rule_metrics, scenario_metrics, datetime.now(timezone.utc).isoformat()


if st.sidebar.button("Refresh data"):
    load_data.clear()

try:
    with st.spinner(f"Loading data from {data_source}..."):
        alerts, scored_transactions, rule_metrics, scenario_metrics, loaded_at = load_data(
            data_source, project_id, dataset_id, location
        )
except Exception as error:
    st.error(f"Could not load {data_source} data: {error}")
    if data_source == "Google BigQuery":
        st.info(
            "Check your Google login and the four BigQuery tables. "
            "You can select Local CSV to use the local prototype."
        )
    else:
        st.info("Check the CSV files in data/synthetic_sample and run the scoring pipeline.")
    st.stop()

st.sidebar.caption(f"Connected · {data_source}")
st.sidebar.caption(f"Transactions loaded: {len(scored_transactions):,}")
if data_source == "Google BigQuery":
    st.sidebar.caption(f"Project: {project_id} | Dataset: {dataset_id} | Region: {location}")
st.sidebar.caption("Data is cached for ten minutes. Use Refresh data after updating it.")


metrics = rule_metrics.iloc[0]

SCENARIO_NAMES = {
    "account_takeover": "Account takeover",
    "new_beneficiary_scam": "Beneficiary scam",
    "rapid_payment_burst": "Payment burst",
    "mule_account_activity": "Mule activity",
    "Normal / false positive": "Normal / false positive",
}
alerts["fraud_scenario_display"] = alerts["fraud_scenario_display"].replace(SCENARIO_NAMES)
# Give investigators the most urgent/highest-value items first.
alerts = alerts.sort_values(
    ["risk_score", "amount", "transaction_timestamp"],
    ascending=[False, False, False], kind="stable"
).reset_index(drop=True)
refresh_display = datetime.fromisoformat(loaded_at).strftime("%d %b %Y, %H:%M UTC")
st.sidebar.caption(f"Last data load: {refresh_display}")



# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------

st.title("Fraud & Scam Intelligence")
st.markdown("**Banking risk analytics · Alert investigation · Strategy evaluation**")


# -------------------------------------------------------------------
# Sidebar filters
# -------------------------------------------------------------------

st.markdown(
    f'<div class="context-banner"><b>Synthetic data prototype</b> &nbsp; | &nbsp; '
    f'{data_source} &nbsp; | &nbsp; Last data load: {refresh_display}</div>',
    unsafe_allow_html=True,
)
st.caption("Known scenario labels support simulation evaluation; they are not model predictions. Summary cards cover the full dataset; sidebar filters apply to the alert views.")

st.sidebar.divider()
st.sidebar.subheader("Investigation filters")

severity_options = [
    severity
    for severity in ["Critical", "High", "Medium"]
    if severity in alerts["alert_severity"].unique()
]

selected_severities = st.sidebar.multiselect(
    "Alert severity",
    options=severity_options,
    default=severity_options,
)

scenario_options = sorted(
    alerts["fraud_scenario_display"]
    .dropna()
    .unique()
    .tolist()
)

selected_scenarios = st.sidebar.multiselect(
    "Scenario",
    options=scenario_options,
    default=scenario_options,
)

minimum_risk_score = st.sidebar.slider(
    "Minimum risk score",
    min_value=0,
    max_value=100,
    value=40,
    step=5,
)

filtered_alerts = alerts[
    alerts["alert_severity"].isin(selected_severities)
    & alerts["fraud_scenario_display"].isin(
        selected_scenarios
    )
    & alerts["risk_score"].ge(minimum_risk_score)
].copy()


# -------------------------------------------------------------------
# Performance indicators
# -------------------------------------------------------------------

metric_columns = st.columns(5)

metric_columns[0].metric(
    "Alert volume",
    f"{int(metrics['total_alerts']):,}",
)

metric_columns[1].metric(
    "Precision",
    f"{metrics['precision']:.1%}",
)

metric_columns[2].metric(
    "Fraud recall",
    f"{metrics['recall']:.1%}",
)

metric_columns[3].metric(
    "Value captured",
    f"{metrics['fraud_value_capture_rate']:.1%}",
)

metric_columns[4].metric(
    "False positives",
    f"{int(metrics['false_positives']):,}",
)


# -------------------------------------------------------------------
# Dashboard tabs
# -------------------------------------------------------------------

overview_tab, alerts_tab, performance_tab, optimisation_tab = st.tabs(
    [
        "Executive Overview",
        "Investigation Queue",
        "Rule Performance",
        "Rule Optimisation",
    ]
)


# -------------------------------------------------------------------
# Executive overview
# -------------------------------------------------------------------

with overview_tab:
    st.subheader("Operational Overview")
    st.caption("Current alert workload after applying your sidebar filters.")
    if not scenario_metrics.empty:
        weakest = scenario_metrics.loc[scenario_metrics["scenario_recall"].idxmin()]
        weakest_name = SCENARIO_NAMES.get(weakest["fraud_scenario"], weakest["fraud_scenario"])
        st.markdown(
            f"**Detection gap to investigate:** {weakest_name} — "
            f"{weakest['scenario_recall']:.0%} recall on injected fraud. "
            "Use Rule Optimisation to explore the detection–workload trade-off."
        )

    overview_columns = st.columns(3)

    overview_columns[0].metric(
        "Filtered alerts",
        f"{len(filtered_alerts):,}",
    )

    overview_columns[1].metric(
        "Value under review",
        f"${filtered_alerts['amount'].sum():,.0f}",
    )

    critical_alerts = filtered_alerts[
        filtered_alerts["alert_severity"] == "Critical"
    ]

    overview_columns[2].metric(
        "Critical alerts",
        f"{len(critical_alerts):,}",
    )

    chart_column_1, chart_column_2 = st.columns(2)

    with chart_column_1:
        severity_counts = (
            filtered_alerts["alert_severity"]
            .value_counts()
            .rename_axis("Severity")
            .reset_index(name="Alerts")
        )

        severity_chart = px.bar(
            severity_counts,
            x="Severity",
            y="Alerts",
            color="Severity",
            color_discrete_map={
                "Critical": "#b42318",
                "High": "#f79009",
                "Medium": "#175cd3",
            },
            title="Alerts by Severity",
        )

        severity_chart.update_layout(
            showlegend=False,
            xaxis_title="",
            yaxis_title="Number of alerts",
        )

        st.plotly_chart(
            severity_chart,
            width="stretch",
        )

    with chart_column_2:
        scenario_counts = (
            filtered_alerts[
                "fraud_scenario_display"
            ]
            .value_counts()
            .rename_axis("Scenario")
            .reset_index(name="Alerts")
        )

        scenario_chart = px.bar(
            scenario_counts,
            x="Alerts",
            y="Scenario",
            orientation="h",
            color="Alerts",
            color_continuous_scale="Blues",
            title="Alerts by Known Simulation Scenario",
        )

        scenario_chart.update_layout(
            coloraxis_showscale=False,
            xaxis_title="Number of alerts",
            yaxis_title="",
        )

        st.plotly_chart(
            scenario_chart,
            width="stretch",
        )

    risk_chart = px.histogram(
        filtered_alerts,
        x="risk_score",
        color="evaluation_result",
        nbins=10,
        barmode="group",
        title="Alert Risk-Score Distribution",
        labels={
            "risk_score": "Risk score",
            "evaluation_result": "Evaluation result",
        },
        color_discrete_map={
            "true_positive": "#142d4e",
            "false_positive": "#8b9db4",
        },
    )

    st.plotly_chart(
        risk_chart,
        width="stretch",
    )


# -------------------------------------------------------------------
# Investigation queue
# -------------------------------------------------------------------

with alerts_tab:
    st.subheader("Investigator Alert Queue")

    if filtered_alerts.empty:
        st.warning(
            "No alerts match the selected filters."
        )

    else:
        display_columns = [
            "alert_id",
            "transaction_timestamp",
            "customer_id",
            "amount",
            "risk_score",
            "alert_severity",
            "fraud_scenario_display",
            "reason_codes",
        ]

        alert_display = filtered_alerts[
            display_columns
        ].copy()

        alert_display["reason_codes"] = alert_display["reason_codes"].fillna("").str.replace(" | ", " • ", regex=False)

        alert_display = alert_display.rename(
            columns={
                "alert_id": "Alert ID",
                "transaction_timestamp": "Timestamp",
                "customer_id": "Customer",
                "amount": "Amount",
                "risk_score": "Risk Score",
                "alert_severity": "Severity",
                "fraud_scenario_display": "Scenario",
                "reason_codes": "Reason Codes",
            }
        )

        st.dataframe(
            alert_display,
            width="stretch",
            hide_index=True,
            column_config={
                "Amount": st.column_config.NumberColumn(
                    format="$%.2f"
                ),
                "Risk Score": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                ),
            },
        )

        st.subheader("Alert Detail")

        selected_alert_id = st.selectbox(
            "Select an alert for investigation",
            options=filtered_alerts["alert_id"].tolist(),
        )

        selected_alert = filtered_alerts[
            filtered_alerts["alert_id"]
            == selected_alert_id
        ].iloc[0]

        matches = scored_transactions[
            scored_transactions["transaction_id"] == selected_alert["transaction_id"]
        ]
        if matches.empty:
            st.error("This alert has no matching scored transaction. Refresh or re-upload matching tables.")
            st.stop()
        selected_transaction = matches.iloc[0]

        detail_columns = st.columns(4)

        detail_columns[0].metric(
            "Risk score",
            int(selected_alert["risk_score"]),
        )

        detail_columns[1].metric(
            "Severity",
            selected_alert["alert_severity"],
        )

        detail_columns[2].metric(
            "Transaction amount",
            f"${selected_alert['amount']:,.2f}",
        )

        detail_columns[3].metric(
            "Country",
            selected_alert["country"],
        )

        st.caption("Alert queue is ordered by risk score, then transaction amount and recency.")
        st.markdown("#### Alert Reasons")

        reasons = str(
            selected_alert["reason_codes"]
        ).split(" | ")

        for reason in reasons:
            if reason:
                st.write(f"- {reason}")

        st.markdown("#### Transaction Details")

        transaction_details = pd.DataFrame(
            {
                "Field": [
                    "Transaction ID",
                    "Customer ID",
                    "Account ID",
                    "Timestamp",
                    "Transaction type",
                    "Channel",
                    "Beneficiary ID",
                    "Device ID",
                    "Actual scenario",
                    "Evaluation result",
                ],
                "Value": [
                    selected_alert["transaction_id"],
                    selected_alert["customer_id"],
                    selected_alert["account_id"],
                    selected_alert["transaction_timestamp"],
                    selected_alert["transaction_type"],
                    selected_alert["channel"],
                    selected_alert["beneficiary_id"],
                    selected_alert["device_id"],
                    selected_alert[
                        "fraud_scenario_display"
                    ],
                    selected_alert["evaluation_result"],
                ],
            }
        )

        transaction_details["Value"] = transaction_details["Value"].map(str)

        st.dataframe(
            transaction_details,
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### Behavioural Indicators")

        indicator_columns = [
            "flag_high_amount",
            "flag_untrusted_device",
            "flag_foreign_country",
            "flag_new_beneficiary",
            "flag_high_velocity",
            "flag_shared_beneficiary",
            "flag_balance_depletion",
            "flag_unusual_hour",
        ]

        indicator_names = {
            "flag_high_amount": "High amount",
            "flag_untrusted_device": "Untrusted device",
            "flag_foreign_country": "Foreign country",
            "flag_new_beneficiary": "New beneficiary",
            "flag_high_velocity": "High velocity",
            "flag_shared_beneficiary": "Shared beneficiary",
            "flag_balance_depletion": "Balance depletion",
            "flag_unusual_hour": "Unusual hour",
        }

        indicator_data = pd.DataFrame(
            {
                "Indicator": [
                    indicator_names[column]
                    for column in indicator_columns
                ],
                "Triggered": [
                    "Yes"
                    if int(selected_transaction[column]) == 1
                    else "No"
                    for column in indicator_columns
                ],
            }
        )

        st.dataframe(
            indicator_data,
            width="stretch",
            hide_index=True,
        )


# -------------------------------------------------------------------
# Rule performance
# -------------------------------------------------------------------

with performance_tab:
    st.subheader("Detection Performance")

    performance_columns = st.columns(4)

    performance_columns[0].metric(
        "True positives",
        int(metrics["true_positives"]),
    )

    performance_columns[1].metric(
        "False positives",
        int(metrics["false_positives"]),
    )

    performance_columns[2].metric(
        "False negatives",
        int(metrics["false_negatives"]),
    )

    performance_columns[3].metric(
        "F1 score",
        f"{metrics['f1_score']:.1%}",
    )

    scenario_chart_data = scenario_metrics.copy()
    scenario_chart_data["fraud_scenario"] = scenario_chart_data["fraud_scenario"].replace(SCENARIO_NAMES)

    scenario_chart_data["Recall Percentage"] = (
        scenario_chart_data["scenario_recall"] * 100
    )

    scenario_performance_chart = px.bar(
        scenario_chart_data,
        x="fraud_scenario",
        y="Recall Percentage",
        color="Recall Percentage",
        color_continuous_scale="Blues",
        text="Recall Percentage",
        title="Recall by Fraud Scenario",
        labels={
            "fraud_scenario": "Fraud scenario",
        },
    )

    scenario_performance_chart.update_traces(
        texttemplate="%{text:.0f}%",
        textposition="outside",
    )

    scenario_performance_chart.update_layout(
        yaxis_range=[0, 110],
        coloraxis_showscale=False,
        xaxis_title="",
    )

    st.plotly_chart(
        scenario_performance_chart,
        width="stretch",
    )

    scenario_table = scenario_metrics.rename(
        columns={
            "fraud_scenario": "Scenario",
            "fraud_transactions": "Fraud Transactions",
            "detected_transactions": "Detected",
            "total_fraud_value": "Total Fraud Value",
            "detected_fraud_value": "Detected Value",
            "scenario_recall": "Recall",
            "value_capture_rate": "Value Capture",
        }
    )

    scenario_table["Scenario"] = scenario_table["Scenario"].replace(SCENARIO_NAMES)
    scenario_table["Recall"] *= 100
    scenario_table["Value Capture"] *= 100

    st.dataframe(
        scenario_table,
        width="stretch",
        hide_index=True,
        column_config={
            "Total Fraud Value": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
            "Detected Value": (
                st.column_config.NumberColumn(
                    format="$%.2f"
                )
            ),
            "Recall": st.column_config.NumberColumn(
                format="%.1%%"
            ),
            "Value Capture": (
                st.column_config.NumberColumn(
                    format="%.1%%"
                )
            ),
        },
    )

    st.info(
        "This dashboard uses synthetic data. "
        "Performance results demonstrate the prototype methodology "
        "and must not be interpreted as production-bank results."
    )


# -------------------------------------------------------------------
# Threshold comparison: simulation evaluation, not production tuning.
# -------------------------------------------------------------------

def prepare_threshold_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Require observed synthetic labels; never infer fraud from risk scores."""
    result = frame.copy()
    for column in ("risk_score", "amount"):
        if column not in result:
            raise ValueError(f"scored_transactions needs {column} for threshold comparisons.")
        result[column] = pd.to_numeric(result[column], errors="raise").astype(float)
        if result[column].isna().any():
            raise ValueError(f"{column} contains missing values.")
    if not result["risk_score"].between(0, 100).all():
        raise ValueError("Risk scores must be between 0 and 100.")
    if result["amount"].lt(0).any():
        raise ValueError("Transaction amounts must not be negative.")
    label_column = next((c for c in ("is_fraud", "fraud_label") if c in result), None)
    if label_column:
        labels = pd.to_numeric(result[label_column], errors="raise")
        if labels.isna().any() or not labels.isin([0, 1]).all():
            raise ValueError(f"{label_column} must contain only 0 and 1.")
        result["actual_fraud"] = labels.astype(bool)
    elif "evaluation_result" in result:
        labels = result["evaluation_result"].astype("string").str.lower().str.strip()
        allowed = {"true_positive", "false_positive", "true_negative", "false_negative"}
        if labels.isna().any() or not labels.isin(allowed).all():
            raise ValueError("Evaluation labels must cover every scored transaction.")
        result["actual_fraud"] = labels.isin(["true_positive", "false_negative"])
    else:
        raise ValueError("Upload scored_transactions with is_fraud or fraud_label (0/1), or complete evaluation_result labels.")
    return result


def threshold_metrics(frame: pd.DataFrame, threshold: int) -> dict:
    predicted = frame["risk_score"].ge(threshold)
    actual = frame["actual_fraud"]
    tp = int((predicted & actual).sum())
    fp = int((predicted & ~actual).sum())
    fn = int((~predicted & actual).sum())
    tn = int((~predicted & ~actual).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    fraud_value = float(frame.loc[actual, "amount"].sum())
    detected_value = float(frame.loc[predicted & actual, "amount"].sum())
    return {
        "threshold": threshold, "alerts": tp + fp, "tp": tp, "fp": fp,
        "fn": fn, "tn": tn, "precision": precision, "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "fpr": fp / (fp + tn) if fp + tn else 0.0,
        "value_capture": detected_value / fraud_value if fraud_value else 0.0,
        "detected_value": detected_value,
    }


with optimisation_tab:
    st.subheader("Compare Alert Thresholds")
    st.caption("Threshold comparison on synthetic data • Baseline: score ≥ 40 • Full dataset, independent of sidebar filters")
    st.info(
        "This changes the score needed to create an alert. It does not change the underlying rules "
        "or update the investigation queue. These are exploratory results on the same synthetic dataset, "
        "not evidence of performance on unseen banking transactions."
    )
    try:
        comparison_data = prepare_threshold_data(scored_transactions)
    except (ValueError, TypeError) as error:
        st.warning(str(error))
    else:
        threshold = st.slider("Comparison threshold", 0, 100, 40, 1, key="comparison_threshold")
        baseline = threshold_metrics(comparison_data, 40)
        candidate = threshold_metrics(comparison_data, threshold)
        comparison_columns = st.columns(5)
        comparison_columns[0].metric("Proposed alerts", f"{candidate['alerts']:,}",
            f"{candidate['alerts'] - baseline['alerts']:+,} alerts", delta_color="off")
        comparison_columns[1].metric("Precision", f"{candidate['precision']:.1%}",
            f"{100*(candidate['precision']-baseline['precision']):+.1f} pp", delta_color="off")
        comparison_columns[2].metric("Recall", f"{candidate['recall']:.1%}",
            f"{100*(candidate['recall']-baseline['recall']):+.1f} pp", delta_color="off")
        comparison_columns[3].metric("Value captured", f"{candidate['value_capture']:.1%}",
            f"{100*(candidate['value_capture']-baseline['value_capture']):+.1f} pp", delta_color="off")
        comparison_columns[4].metric("False positives", f"{candidate['fp']:,}",
            f"{candidate['fp']-baseline['fp']:+,} alerts", delta_color="off")
        st.caption("pp = percentage points. Extra alerts represent extra potential investigations, not measured staffing hours.")

        rows = []
        for label, key, percentage in [
            ("Alerts / potential investigations", "alerts", False),
            ("True positives", "tp", False), ("False positives", "fp", False),
            ("Missed fraud transactions", "fn", False), ("Precision", "precision", True),
            ("Recall", "recall", True), ("F1 score", "f1", True),
            ("False-positive rate among normal transactions", "fpr", True),
            ("Fraud value captured", "value_capture", True),
        ]:
            left, right = baseline[key], candidate[key]
            rows.append({"Measure": label,
                "Baseline (40)": f"{left:.2%}" if percentage else f"{left:,}",
                f"Comparison ({threshold})": f"{right:.2%}" if percentage else f"{right:,}",
                "Change": f"{100*(right-left):+.2f} pp" if percentage else f"{right-left:+,}"})
        # Avoid duplicate DataFrame column names at the baseline position.
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        alert_change = candidate["alerts"] - baseline["alerts"]
        fraud_change = candidate["tp"] - baseline["tp"]
        value_change = candidate["detected_value"] - baseline["detected_value"]
        st.markdown("#### Investigation Trade-off")
        st.write(
            f"Compared with threshold 40: {alert_change:+,} alerts, {fraud_change:+,} detected fraud "
            f"transactions and AUD {value_change:+,.2f} in simulated fraud value detected. "
            "Detected value is not a claim of prevented loss."
        )
        curve = pd.DataFrame([threshold_metrics(comparison_data, t) for t in range(0,101,5)])
        curve["Precision"] = curve["precision"] * 100
        curve["Recall"] = curve["recall"] * 100
        chart_left, chart_right = st.columns(2)
        with chart_left:
            chart = px.line(curve, x="threshold", y=["Precision", "Recall"],
                color_discrete_sequence=["#142d4e", "#6f8ba9"],
                labels={"threshold":"Risk-score threshold", "value":"Percentage", "variable":"Measure"},
                title="Detection vs Alert Quality")
            chart.add_vline(x=threshold, line_dash="dot", line_color="#64748b")
            chart.update_yaxes(range=[0,105])
            chart.update_layout(legend_title_text="")
            st.plotly_chart(chart, width="stretch")
        with chart_right:
            chart = px.line(curve, x="threshold", y="alerts",
                labels={"threshold":"Risk-score threshold", "alerts":"Potential investigations"},
                title="Investigation Workload")
            chart.update_traces(line_color="#142d4e")
            chart.add_vline(x=threshold, line_dash="dot", line_color="#64748b")
            st.plotly_chart(chart, width="stretch")
        st.caption("Charts use thresholds in steps of five; cards calculate the exact selected threshold.")

        st.markdown("#### Detection by Known Fraud Scenario")
        if "fraud_scenario" in comparison_data:
            scenario_rows = []
            fraud_only = comparison_data[comparison_data["actual_fraud"]].copy()
            fraud_only["fraud_scenario"] = fraud_only["fraud_scenario"].fillna("Unspecified")
            for scenario, group in fraud_only.groupby("fraud_scenario", sort=True):
                base_count = int(group["risk_score"].ge(40).sum())
                proposed_count = int(group["risk_score"].ge(threshold).sum())
                scenario_rows.append({"Scenario": SCENARIO_NAMES.get(scenario, scenario),
                    "Fraud transactions": len(group), "Baseline detected": base_count,
                    "Comparison detected": proposed_count, "Change": proposed_count-base_count,
                    "Baseline recall (%)": 100*base_count/len(group),
                    "Comparison recall (%)": 100*proposed_count/len(group)})
            st.dataframe(pd.DataFrame(scenario_rows), hide_index=True, width="stretch")
        else:
            st.caption("Scenario comparison needs fraud_scenario in scored_transactions.")
        st.download_button("Download threshold comparison", pd.DataFrame(rows).to_csv(index=False),
            file_name=f"synthetic_threshold_comparison_{threshold}.csv", mime="text/csv")
        st.caption(
            "Use this view to form a hypothesis. Tune on development data, then evaluate on a separate "
            "holdout dataset before recommending a threshold. Zero alerts or zero labelled fraud use "
            "0% for undefined ratios. Red/amber in this dashboard are reserved for alert severity."
        )
