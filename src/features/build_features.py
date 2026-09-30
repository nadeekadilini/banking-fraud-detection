"""Build behavioural fraud-detection features from transaction data."""

from pathlib import Path

import pandas as pd


# -------------------------------------------------------------------
# File locations
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIRECTORY = PROJECT_ROOT / "data" / "synthetic_sample"


# -------------------------------------------------------------------
# Transaction velocity
# -------------------------------------------------------------------

def calculate_velocity_features(
    transactions: pd.DataFrame,
) -> pd.Series:
    """Count account transactions during the previous ten minutes."""

    velocity_counts = pd.Series(
        0,
        index=transactions.index,
        dtype="int64",
    )

    ten_minute_window = pd.Timedelta(minutes=10)

    for _, account_group in transactions.groupby("account_id"):
        ordered_group = account_group.sort_values(
            "transaction_timestamp"
        )

        ordered_indices = ordered_group.index.to_numpy()

        timestamps = ordered_group[
            "transaction_timestamp"
        ].tolist()

        left_position = 0

        for right_position in range(len(timestamps)):
            while (
                timestamps[right_position]
                - timestamps[left_position]
                > ten_minute_window
            ):
                left_position += 1

            transaction_count = (
                right_position - left_position + 1
            )

            original_index = ordered_indices[right_position]

            velocity_counts.at[
                original_index
            ] = transaction_count

    return velocity_counts


# -------------------------------------------------------------------
# Main feature-engineering process
# -------------------------------------------------------------------

def main() -> None:
    """Load fraud data, engineer features and save the result."""

    print("Loading fraud-enriched datasets...")

    transactions = pd.read_csv(
        DATA_DIRECTORY / "transactions_with_fraud.csv"
    )

    devices = pd.read_csv(
        DATA_DIRECTORY / "devices_with_fraud.csv"
    )

    beneficiaries = pd.read_csv(
        DATA_DIRECTORY / "beneficiaries_with_fraud.csv"
    )

    transactions["transaction_timestamp"] = pd.to_datetime(
        transactions["transaction_timestamp"],
        utc=True,
        errors="raise",
    )

    # ---------------------------------------------------------------
    # Device features
    # ---------------------------------------------------------------

    device_fields = devices[
        [
            "device_id",
            "trusted_device",
            "first_seen_date",
        ]
    ].copy()

    features = transactions.merge(
        device_fields,
        on="device_id",
        how="left",
        validate="many_to_one",
    )

    features["trusted_device"] = (
        features["trusted_device"]
        .astype(str)
        .str.lower()
        .eq("true")
        .astype(int)
    )

    features["flag_untrusted_device"] = (
        features["trusted_device"]
        .eq(0)
        .astype(int)
    )

    # ---------------------------------------------------------------
    # Beneficiary features
    # ---------------------------------------------------------------

    beneficiary_fields = beneficiaries[
        [
            "beneficiary_id",
            "beneficiary_account_id",
            "beneficiary_country",
            "date_added",
        ]
    ].copy()

    features = features.merge(
        beneficiary_fields,
        on="beneficiary_id",
        how="left",
        validate="many_to_one",
    )

    beneficiary_dates = pd.to_datetime(
        features["date_added"],
        errors="coerce",
    ).dt.normalize()

    transaction_dates = (
        features["transaction_timestamp"]
        .dt.tz_convert(None)
        .dt.normalize()
    )

    features["beneficiary_age_days"] = (
        transaction_dates - beneficiary_dates
    ).dt.days

    features["flag_new_beneficiary"] = (
        features["beneficiary_age_days"]
        .between(0, 1)
        .fillna(False)
        .astype(int)
    )

    # ---------------------------------------------------------------
    # Customer amount-behaviour features
    # ---------------------------------------------------------------

    features["customer_median_amount"] = (
        features.groupby("customer_id")["amount"]
        .transform("median")
        .round(2)
    )

    safe_customer_median = features[
        "customer_median_amount"
    ].clip(lower=1)

    features["amount_to_customer_median"] = (
        features["amount"] / safe_customer_median
    ).round(2)

    features["flag_high_amount"] = (
        (
            features["amount_to_customer_median"] >= 3
        )
        & (
            features["amount"] >= 1_000
        )
    ).astype(int)

    # ---------------------------------------------------------------
    # Geographic features
    # ---------------------------------------------------------------

    features["flag_foreign_country"] = (
        features["country"]
        .ne("AU")
        .astype(int)
    )

    # ---------------------------------------------------------------
    # Transaction-velocity features
    # ---------------------------------------------------------------

    features["transactions_last_10_minutes"] = (
        calculate_velocity_features(features)
    )

    features["flag_high_velocity"] = (
        features["transactions_last_10_minutes"]
        .ge(3)
        .astype(int)
    )

    # ---------------------------------------------------------------
    # Shared beneficiary and mule-account features
    # ---------------------------------------------------------------

    transactions_with_beneficiaries = features[
        features["beneficiary_account_id"].notna()
    ]

    recipient_customer_counts = (
        transactions_with_beneficiaries
        .groupby("beneficiary_account_id")["customer_id"]
        .nunique()
    )

    features["customers_to_beneficiary"] = (
        features["beneficiary_account_id"]
        .map(recipient_customer_counts)
        .fillna(0)
        .astype(int)
    )

    features["flag_shared_beneficiary"] = (
        features["customers_to_beneficiary"]
        .ge(5)
        .astype(int)
    )

    # ---------------------------------------------------------------
    # Balance-depletion features
    # ---------------------------------------------------------------

    safe_balance = features[
        "balance_before"
    ].clip(lower=1)

    features["balance_depletion_ratio"] = (
        features["amount"] / safe_balance
    ).round(4)

    features["flag_balance_depletion"] = (
        features["balance_depletion_ratio"]
        .ge(0.80)
        .astype(int)
    )

    # ---------------------------------------------------------------
    # Time-of-day features
    # ---------------------------------------------------------------

    local_transaction_time = (
        features["transaction_timestamp"]
        .dt.tz_convert("Australia/Melbourne")
    )

    features["transaction_hour_local"] = (
        local_transaction_time.dt.hour
    )

    features["flag_unusual_hour"] = (
        features["transaction_hour_local"]
        .between(0, 5)
        .astype(int)
    )

    # ---------------------------------------------------------------
    # Basic feature validation
    # ---------------------------------------------------------------

    required_feature_columns = [
        "flag_high_amount",
        "flag_untrusted_device",
        "flag_foreign_country",
        "flag_new_beneficiary",
        "flag_high_velocity",
        "flag_shared_beneficiary",
        "flag_balance_depletion",
        "flag_unusual_hour",
    ]

    missing_feature_values = (
        features[required_feature_columns]
        .isna()
        .sum()
        .sum()
    )

    if missing_feature_values > 0:
        raise ValueError(
            "One or more required feature columns contain missing values."
        )

    if len(features) != 10_000:
        raise ValueError(
            "Feature table does not contain 10,000 transactions."
        )

    # ---------------------------------------------------------------
    # Save the feature table
    # ---------------------------------------------------------------

    output_path = (
        DATA_DIRECTORY / "transaction_features.csv"
    )

    features.to_csv(
        output_path,
        index=False,
    )

    # ---------------------------------------------------------------
    # Display results
    # ---------------------------------------------------------------

    print("\nBehavioural features created successfully.")
    print(f"Transactions processed: {len(features):,}")
    print(f"Feature table saved to: {output_path}")

    print("\nFeature-flag counts:")

    for feature_name in required_feature_columns:
        flagged_count = int(
            features[feature_name].sum()
        )

        print(
            f"- {feature_name}: "
            f"{flagged_count:,}"
        )

    print("\nFraud coverage by feature:")

    fraud_transactions = features[
        features["is_fraud"] == 1
    ]

    for feature_name in required_feature_columns:
        detected_fraud_count = int(
            fraud_transactions[feature_name].sum()
        )

        print(
            f"- {feature_name}: "
            f"{detected_fraud_count}/100 fraud transactions"
        )


if __name__ == "__main__":
    main()