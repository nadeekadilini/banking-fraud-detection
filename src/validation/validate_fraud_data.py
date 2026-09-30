"""Validate the injected fraud and scam scenarios."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIRECTORY = PROJECT_ROOT / "data" / "synthetic_sample"

EXPECTED_SCENARIOS = {
    "account_takeover": 25,
    "new_beneficiary_scam": 25,
    "rapid_payment_burst": 25,
    "mule_account_activity": 25,
}


def run_check(
    check_name: str,
    condition: bool,
    results: list[tuple[str, bool]],
) -> None:
    """Record and display one validation result."""

    passed = bool(condition)
    results.append((check_name, passed))

    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {check_name}")


def main() -> None:
    """Load the fraud-enriched data and run validation checks."""

    print("Loading fraud-enriched banking datasets...\n")

    transactions = pd.read_csv(
        DATA_DIRECTORY / "transactions_with_fraud.csv"
    )

    devices = pd.read_csv(
        DATA_DIRECTORY / "devices_with_fraud.csv"
    )

    beneficiaries = pd.read_csv(
        DATA_DIRECTORY / "beneficiaries_with_fraud.csv"
    )

    fraud_events = pd.read_csv(
        DATA_DIRECTORY / "fraud_events.csv"
    )

    transactions["transaction_timestamp"] = pd.to_datetime(
        transactions["transaction_timestamp"],
        utc=True,
        errors="coerce",
    )

    fraud_transactions = transactions[
        transactions["is_fraud"] == 1
    ].copy()

    normal_transactions = transactions[
        transactions["is_fraud"] == 0
    ].copy()

    results: list[tuple[str, bool]] = []

    # ---------------------------------------------------------------
    # General checks
    # ---------------------------------------------------------------

    run_check(
        "Dataset contains 10,000 transactions",
        len(transactions) == 10_000,
        results,
    )

    run_check(
        "Transaction IDs remain unique",
        transactions["transaction_id"].is_unique,
        results,
    )

    run_check(
        "Exactly 100 transactions are labelled as fraud",
        len(fraud_transactions) == 100,
        results,
    )

    run_check(
        "Fraud rate equals 1%",
        round(
            len(fraud_transactions) / len(transactions),
            4,
        ) == 0.01,
        results,
    )

    run_check(
        "Fraud labels contain only zero or one",
        transactions["is_fraud"].isin([0, 1]).all(),
        results,
    )

    run_check(
        "All transaction timestamps are valid",
        transactions["transaction_timestamp"].notna().all(),
        results,
    )

    run_check(
        "All transaction amounts are positive",
        transactions["amount"].gt(0).all(),
        results,
    )

    expected_balance_after = (
        transactions["balance_before"]
        - transactions["amount"]
    ).round(2)

    run_check(
        "All balances remain correctly calculated",
        expected_balance_after.eq(
            transactions["balance_after"].round(2)
        ).all(),
        results,
    )

    # ---------------------------------------------------------------
    # Scenario-count checks
    # ---------------------------------------------------------------

    scenario_counts = (
        fraud_transactions["fraud_scenario"]
        .value_counts()
        .to_dict()
    )

    for scenario, expected_count in EXPECTED_SCENARIOS.items():
        run_check(
            f"{scenario} contains {expected_count} transactions",
            scenario_counts.get(scenario, 0) == expected_count,
            results,
        )

    # ---------------------------------------------------------------
    # Explainability checks
    # ---------------------------------------------------------------

    run_check(
        "Every fraud transaction has an event ID",
        fraud_transactions["fraud_event_id"].notna().all(),
        results,
    )

    run_check(
        "Every fraud transaction has a reason",
        fraud_transactions["fraud_reason"].notna().all(),
        results,
    )

    run_check(
        "Normal transactions do not have fraud event IDs",
        normal_transactions["fraud_event_id"].isna().all(),
        results,
    )

    # ---------------------------------------------------------------
    # Relationship checks
    # ---------------------------------------------------------------

    run_check(
        "All transaction devices exist",
        transactions["device_id"]
        .isin(devices["device_id"])
        .all(),
        results,
    )

    transaction_beneficiaries = transactions.loc[
        transactions["beneficiary_id"].notna(),
        "beneficiary_id",
    ]

    run_check(
        "All transaction beneficiaries exist",
        transaction_beneficiaries
        .isin(beneficiaries["beneficiary_id"])
        .all(),
        results,
    )

    device_customer_map = devices.set_index(
        "device_id"
    )["customer_id"]

    transaction_device_customers = transactions[
        "device_id"
    ].map(device_customer_map)

    run_check(
        "Every transaction device belongs to its customer",
        transaction_device_customers.eq(
            transactions["customer_id"]
        ).all(),
        results,
    )

    # ---------------------------------------------------------------
    # Account-takeover checks
    # ---------------------------------------------------------------

    account_takeovers = fraud_transactions[
        fraud_transactions["fraud_scenario"]
        == "account_takeover"
    ]

    trusted_device_map = devices.set_index(
        "device_id"
    )["trusted_device"]

    takeover_device_status = account_takeovers[
        "device_id"
    ].map(trusted_device_map)

    run_check(
        "Account-takeover transactions use untrusted devices",
        takeover_device_status
        .astype(str)
        .str.lower()
        .eq("false")
        .all(),
        results,
    )

    run_check(
        "Account-takeover transactions occur outside Australia",
        account_takeovers["country"].ne("AU").all(),
        results,
    )

    # ---------------------------------------------------------------
    # New-beneficiary scam checks
    # ---------------------------------------------------------------

    new_beneficiary_scams = fraud_transactions[
        fraud_transactions["fraud_scenario"]
        == "new_beneficiary_scam"
    ].copy()

    beneficiary_date_map = pd.to_datetime(
        beneficiaries.set_index(
            "beneficiary_id"
        )["date_added"],
        errors="coerce",
    )

    scam_beneficiary_dates = new_beneficiary_scams[
        "beneficiary_id"
    ].map(beneficiary_date_map)

    run_check(
        "Scam beneficiaries were added on the transaction date",
        scam_beneficiary_dates.dt.date.eq(
            new_beneficiary_scams[
                "transaction_timestamp"
            ].dt.date
        ).all(),
        results,
    )

    # ---------------------------------------------------------------
    # Rapid-burst checks
    # ---------------------------------------------------------------

    rapid_bursts = fraud_transactions[
        fraud_transactions["fraud_scenario"]
        == "rapid_payment_burst"
    ]

    burst_sizes = rapid_bursts.groupby(
        "fraud_event_id"
    ).size()

    run_check(
        "Every rapid-burst event contains five transactions",
        burst_sizes.eq(5).all(),
        results,
    )

    burst_spans = rapid_bursts.groupby(
        "fraud_event_id"
    )["transaction_timestamp"].agg(
        lambda timestamps: (
            timestamps.max() - timestamps.min()
        ).total_seconds() / 60
    )

    run_check(
        "Every rapid burst occurs within ten minutes",
        burst_spans.le(10).all(),
        results,
    )

    # ---------------------------------------------------------------
    # Mule-account checks
    # ---------------------------------------------------------------

    mule_transactions = fraud_transactions[
        fraud_transactions["fraud_scenario"]
        == "mule_account_activity"
    ]

    beneficiary_account_map = beneficiaries.set_index(
        "beneficiary_id"
    )["beneficiary_account_id"]

    mule_accounts = mule_transactions[
        "beneficiary_id"
    ].map(beneficiary_account_map)

    run_check(
        "Mule transactions use one shared beneficiary account",
        mule_accounts.nunique() == 1,
        results,
    )

    run_check(
        "Mule transactions come from 25 different customers",
        mule_transactions["customer_id"].nunique() == 25,
        results,
    )

    # ---------------------------------------------------------------
    # Fraud-event summary checks
    # ---------------------------------------------------------------

    run_check(
        "Fraud-event summary contains 56 events",
        len(fraud_events) == 56,
        results,
    )

    run_check(
        "Fraud-event summary covers all 100 fraud transactions",
        fraud_events["transaction_count"].sum() == 100,
        results,
    )

    run_check(
        "Fraud-event IDs match the transaction data",
        set(fraud_events["fraud_event_id"])
        == set(fraud_transactions["fraud_event_id"]),
        results,
    )

    # ---------------------------------------------------------------
    # Final summary
    # ---------------------------------------------------------------

    failed_checks = [
        check_name
        for check_name, passed in results
        if not passed
    ]

    print("\nFraud-data validation summary")
    print("-----------------------------")
    print(f"Checks performed: {len(results)}")
    print(f"Checks passed: {len(results) - len(failed_checks)}")
    print(f"Checks failed: {len(failed_checks)}")

    if failed_checks:
        print("\nFailed checks:")

        for failed_check in failed_checks:
            print(f"- {failed_check}")

        raise SystemExit(1)

    print("\nAll fraud-data checks passed successfully.")


if __name__ == "__main__":
    main()