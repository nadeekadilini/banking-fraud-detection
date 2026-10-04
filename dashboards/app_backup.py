"""Streamlit dashboard for fraud and scam alert investigation."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# -------------------------------------------------------------------
# Page configuration
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Fraud & Scam Intelligence",
    page_icon="🛡️",
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
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
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
            background-color: #f5f8fc;
            border: 1px solid #dbe4ef;
            border-radius: 10px;
            padding: 14px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Load project data
# -------------------------------------------------------------------

@st.cache_data
def load_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load scoring outputs created by the fraud pipeline."""

    alerts = pd.read_csv(
        DATA_DIRECTORY / "alert_queue.csv"
    )

    scored_transactions = pd.read_csv(
        DATA_DIRECTORY / "scored_transactions.csv"
    )

    rule_metrics = pd.read_csv(
        DATA_DIRECTORY / "rule_metrics.csv"
    )

    scenario_metrics = pd.read_csv(
        DATA_DIRECTORY / "scenario_metrics.csv"
    )

    alerts["transaction_timestamp"] = pd.to_datetime(
        alerts["transaction_timestamp"],
        utc=True,
        errors="coerce",
    )

    scored_transactions["transaction_timestamp"] = pd.to_datetime(
        scored_transactions["transaction_timestamp"],
        utc=True,
        errors="coerce",
    )

    alerts["fraud_scenario_display"] = (
        alerts["fraud_scenario"]
        .fillna("Normal / false positive")
        .replace("", "Normal / false positive")
    )

    return (
        alerts,
        scored_transactions,
        rule_metrics,
        scenario_metrics,
    )


try:
    (
        alerts,
        scored_transactions,
        rule_metrics,
        scenario_metrics,
    ) = load_data()

except FileNotFoundError:
    st.error(
        "Dashboard data files were not found. "
        "Run build_features.py and apply_rules.py first."
    )
    st.stop()


metrics = rule_metrics.iloc[0]


# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------

st.markdown(
    '<p class="main-title">'
    "Cloud-Native Fraud, Scam & Mule Intelligence Platform"
    "</p>",
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="subtitle">'
    "Synthetic banking alert monitoring and investigation prototype"
    "</p>",
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Sidebar filters
# -------------------------------------------------------------------

st.sidebar.header("Alert Filters")

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
    "Total alerts",
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
    "Fraud value captured",
    f"{metrics['fraud_value_capture_rate']:.1%}",
)

metric_columns[4].metric(
    "False positives",
    f"{int(metrics['false_positives']):,}",
)


# -------------------------------------------------------------------
# Dashboard tabs
# -------------------------------------------------------------------

overview_tab, alerts_tab, performance_tab = st.tabs(
    [
        "Executive Overview",
        "Investigation Queue",
        "Rule Performance",
    ]
)


# -------------------------------------------------------------------
# Executive overview
# -------------------------------------------------------------------

with overview_tab:
    st.subheader("Current Alert Position")

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
            use_container_width=True,
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
            title="Alerts by Scenario",
        )

        scenario_chart.update_layout(
            coloraxis_showscale=False,
            xaxis_title="Number of alerts",
            yaxis_title="",
        )

        st.plotly_chart(
            scenario_chart,
            use_container_width=True,
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
            "true_positive": "#1570ef",
            "false_positive": "#f04438",
        },
    )

    st.plotly_chart(
        risk_chart,
        use_container_width=True,
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
            use_container_width=True,
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

        selected_transaction = scored_transactions[
            scored_transactions["transaction_id"]
            == selected_alert["transaction_id"]
        ].iloc[0]

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

        st.dataframe(
            transaction_details,
            use_container_width=True,
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
            use_container_width=True,
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
        use_container_width=True,
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

    st.dataframe(
        scenario_table,
        use_container_width=True,
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