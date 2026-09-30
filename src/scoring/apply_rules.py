"""Apply explainable fraud rules and generate an alert queue."""

from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIRECTORY = PROJECT_ROOT / "data" / "synthetic_sample"

ALERT_THRESHOLD = 40

FEATURE_WEIGHTS = {
    "flag_high_amount": 30,
    "flag_untrusted_device": 25,
    "flag_foreign_country": 20,
    "flag_new_beneficiary": 25,
    "flag_high_velocity": 35,
    "flag_shared_beneficiary": 40,
    "flag_balance_depletion": 15,
    "flag_unusual_hour": 5,
}

REASON_CODES = {
    "flag_high_amount": "Amount significantly above customer baseline",
    "flag_untrusted_device": "Transaction from an untrusted device",
    "flag_foreign_country": "Transaction originated outside Australia",
    "flag_new_beneficiary": "Beneficiary was recently added",
    "flag_high_velocity": "Multiple transactions within ten minutes",
    "flag_shared_beneficiary": (
        "Beneficiary account receives funds from many customers"
    ),
    "flag_balance_depletion": (
        "Transaction uses most of the available balance"
    ),
    "flag_unusual_hour": (
        "Transaction occurred during an unusual local hour"
    ),
}


def build_reason_codes(row: pd.Series) -> str:
    """Convert active indicators into readable alert reasons."""

    reasons = [
        reason
        for feature, reason in REASON_CODES.items()
        if int(row[feature]) == 1
    ]

    return " | ".join(reasons)


def calculate_rule_score(
    transactions: pd.DataFrame,
) -> pd.Series:
    """Calculate a risk score using weighted fraud indicators."""

    risk_score = pd.Series(
        0,
        index=transactions.index,
        dtype="int64",
    )

    for feature, weight in FEATURE_WEIGHTS.items():
        risk_score += transactions[feature] * weight

    # Account-takeover combination:
    # unfamiliar device plus overseas location.
    account_takeover_bonus = (
        transactions["flag_untrusted_device"].eq(1)
        & transactions["flag_foreign_country"].eq(1)
    )

    risk_score += account_takeover_bonus.astype(int) * 15

    # Scam combination:
    # newly added beneficiary plus an unusually large transfer.
    new_beneficiary_bonus = (
        transactions["flag_new_beneficiary"].eq(1)
        & transactions["flag_high_amount"].eq(1)
    )

    risk_score += new_beneficiary_bonus.astype(int) * 15

    # Mule combination:
    # a recently added beneficiary shared by several customers.
    mule_account_bonus = (
        transactions["flag_new_beneficiary"].eq(1)
        & transactions["flag_shared_beneficiary"].eq(1)
    )

    risk_score += mule_account_bonus.astype(int) * 15

    return risk_score.clip(upper=100)


def assign_alert_severity(
    risk_score: pd.Series,
) -> pd.Series:
    """Convert numeric scores into investigation priorities."""

    return pd.cut(
        risk_score,
        bins=[-1, 39, 54, 74, 100],
        labels=[
            "No alert",
            "Medium",
            "High",
            "Critical",
        ],
    ).astype(str)


def create_overall_metrics(
    scored_transactions: pd.DataFrame,
) -> pd.DataFrame:
    """Evaluate the rule engine against known fraud labels."""

    actual = scored_transactions["is_fraud"]
    predicted = scored_transactions["alert_flag"]

    true_negative, false_positive, false_negative, true_positive = (
        confusion_matrix(
            actual,
            predicted,
            labels=[0, 1],
        ).ravel()
    )

    precision = precision_score(
        actual,
        predicted,
        zero_division=0,
    )

    recall = recall_score(
        actual,
        predicted,
        zero_division=0,
    )

    f1 = f1_score(
        actual,
        predicted,
        zero_division=0,
    )

    false_positive_rate = (
        false_positive
        / (false_positive + true_negative)
        if (false_positive + true_negative) > 0
        else 0
    )

    total_fraud_value = scored_transactions.loc[
        scored_transactions["is_fraud"] == 1,
        "amount",
    ].sum()

    detected_fraud_value = scored_transactions.loc[
        (
            scored_transactions["is_fraud"] == 1
        )
        & (
            scored_transactions["alert_flag"] == 1
        ),
        "amount",
    ].sum()

    fraud_value_capture_rate = (
        detected_fraud_value / total_fraud_value
        if total_fraud_value > 0
        else 0
    )

    metrics = {
        "total_transactions": len(scored_transactions),
        "total_fraud_transactions": int(actual.sum()),
        "total_alerts": int(predicted.sum()),
        "true_positives": int(true_positive),
        "false_positives": int(false_positive),
        "true_negatives": int(true_negative),
        "false_negatives": int(false_negative),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "false_positive_rate": round(
            float(false_positive_rate),
            4,
        ),
        "total_fraud_value": round(
            float(total_fraud_value),
            2,
        ),
        "detected_fraud_value": round(
            float(detected_fraud_value),
            2,
        ),
        "fraud_value_capture_rate": round(
            float(fraud_value_capture_rate),
            4,
        ),
    }

    return pd.DataFrame([metrics])


def create_scenario_metrics(
    scored_transactions: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate detection results for each fraud scenario."""

    fraud_transactions = scored_transactions[
        scored_transactions["is_fraud"] == 1
    ].copy()

    scenario_metrics = (
        fraud_transactions
        .groupby("fraud_scenario", as_index=False)
        .agg(
            fraud_transactions=("transaction_id", "count"),
            detected_transactions=("alert_flag", "sum"),
            total_fraud_value=("amount", "sum"),
            detected_fraud_value=(
                "detected_fraud_value",
                "sum",
            ),
        )
    )

    scenario_metrics["scenario_recall"] = (
        scenario_metrics["detected_transactions"]
        / scenario_metrics["fraud_transactions"]
    ).round(4)

    scenario_metrics["value_capture_rate"] = (
        scenario_metrics["detected_fraud_value"]
        / scenario_metrics["total_fraud_value"]
    ).round(4)

    scenario_metrics["total_fraud_value"] = (
        scenario_metrics["total_fraud_value"].round(2)
    )

    scenario_metrics["detected_fraud_value"] = (
        scenario_metrics["detected_fraud_value"].round(2)
    )

    return scenario_metrics


def main() -> None:
    """Score transactions, generate alerts and evaluate performance."""

    print("Loading behavioural feature table...")

    transactions = pd.read_csv(
        DATA_DIRECTORY / "transaction_features.csv"
    )

    missing_features = [
        feature
        for feature in FEATURE_WEIGHTS
        if feature not in transactions.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing required features: {missing_features}"
        )

    # ---------------------------------------------------------------
    # Risk scoring
    # ---------------------------------------------------------------

    transactions["risk_score"] = calculate_rule_score(
        transactions
    )

    transactions["alert_flag"] = (
        transactions["risk_score"]
        .ge(ALERT_THRESHOLD)
        .astype(int)
    )

    transactions["alert_severity"] = assign_alert_severity(
        transactions["risk_score"]
    )

    transactions["reason_codes"] = transactions.apply(
        build_reason_codes,
        axis=1,
    )

    # ---------------------------------------------------------------
    # Alert identifiers
    # ---------------------------------------------------------------

    transactions["alert_id"] = ""

    alert_indices = transactions[
        transactions["alert_flag"] == 1
    ].sort_values(
        ["risk_score", "amount"],
        ascending=[False, False],
    ).index

    alert_ids = [
        f"ALERT{alert_number:06d}"
        for alert_number in range(
            1,
            len(alert_indices) + 1,
        )
    ]

    transactions.loc[
        alert_indices,
        "alert_id",
    ] = alert_ids

    # ---------------------------------------------------------------
    # Evaluation outcome
    # ---------------------------------------------------------------

    transactions["evaluation_result"] = "true_negative"

    transactions.loc[
        (
            transactions["is_fraud"] == 1
        )
        & (
            transactions["alert_flag"] == 1
        ),
        "evaluation_result",
    ] = "true_positive"

    transactions.loc[
        (
            transactions["is_fraud"] == 0
        )
        & (
            transactions["alert_flag"] == 1
        ),
        "evaluation_result",
    ] = "false_positive"

    transactions.loc[
        (
            transactions["is_fraud"] == 1
        )
        & (
            transactions["alert_flag"] == 0
        ),
        "evaluation_result",
    ] = "false_negative"

    transactions["detected_fraud_value"] = (
        transactions["amount"]
        * transactions["is_fraud"]
        * transactions["alert_flag"]
    )

    # ---------------------------------------------------------------
    # Produce investigation alert queue
    # ---------------------------------------------------------------

    alert_columns = [
        "alert_id",
        "transaction_id",
        "transaction_timestamp",
        "customer_id",
        "account_id",
        "amount",
        "currency",
        "transaction_type",
        "channel",
        "country",
        "beneficiary_id",
        "device_id",
        "risk_score",
        "alert_severity",
        "reason_codes",
        "is_fraud",
        "fraud_scenario",
        "evaluation_result",
    ]

    alert_queue = (
        transactions[
            transactions["alert_flag"] == 1
        ][alert_columns]
        .sort_values(
            ["risk_score", "amount"],
            ascending=[False, False],
        )
        .reset_index(drop=True)
    )

    overall_metrics = create_overall_metrics(
        transactions
    )

    scenario_metrics = create_scenario_metrics(
        transactions
    )

    # ---------------------------------------------------------------
    # Save outputs
    # ---------------------------------------------------------------

    transactions.to_csv(
        DATA_DIRECTORY / "scored_transactions.csv",
        index=False,
    )

    alert_queue.to_csv(
        DATA_DIRECTORY / "alert_queue.csv",
        index=False,
    )

    overall_metrics.to_csv(
        DATA_DIRECTORY / "rule_metrics.csv",
        index=False,
    )

    scenario_metrics.to_csv(
        DATA_DIRECTORY / "scenario_metrics.csv",
        index=False,
    )

    # ---------------------------------------------------------------
    # Display results
    # ---------------------------------------------------------------

    metrics = overall_metrics.iloc[0]

    print("\nRule-based scoring completed successfully.")
    print(f"Transactions scored: {len(transactions):,}")
    print(f"Alerts generated: {int(metrics['total_alerts']):,}")
    print(f"True positives: {int(metrics['true_positives']):,}")
    print(f"False positives: {int(metrics['false_positives']):,}")
    print(f"False negatives: {int(metrics['false_negatives']):,}")
    print(f"Precision: {metrics['precision']:.2%}")
    print(f"Recall: {metrics['recall']:.2%}")
    print(f"F1 score: {metrics['f1_score']:.2%}")
    print(
        "Fraud value capture rate: "
        f"{metrics['fraud_value_capture_rate']:.2%}"
    )

    print("\nScenario performance:")

    for _, scenario in scenario_metrics.iterrows():
        print(
            f"- {scenario['fraud_scenario']}: "
            f"{int(scenario['detected_transactions'])}/"
            f"{int(scenario['fraud_transactions'])} detected"
        )

    print(f"\nFiles saved to: {DATA_DIRECTORY}")


if __name__ == "__main__":
    main()