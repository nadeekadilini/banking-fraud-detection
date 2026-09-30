"""Validate the generated synthetic banking datasets."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIRECTORY = PROJECT_ROOT / "data" / "synthetic_sample"


def run_check(
    check_name: str,
    condition: bool,
    results: list[tuple[str, bool]],
) -> None:
    """Record and display the result of one validation check."""

    passed = bool(condition)
    results.append((check_name, passed))

    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {check_name}")


def main() -> None:
    """Load the datasets and run quality checks."""

    print("Loading synthetic banking datasets...\n")

    customers = pd.read_csv(DATA_DIRECTORY / "customers.csv")
    accounts = pd.read_csv(DATA_DIRECTORY / "accounts.csv")
    devices = pd.read_csv(DATA_DIRECTORY / "devices.csv")
    beneficiaries = pd.read_csv(DATA_DIRECTORY / "beneficiaries.csv")
    transactions = pd.read_csv(DATA_DIRECTORY / "transactions.csv")

    results: list[tuple[str, bool]] = []

    # ---------------------------------------------------------------
    # Record-count checks
    # ---------------------------------------------------------------

    run_check(
        "Customers table contains records",
        len(customers) > 0,
        results,
    )

    run_check(
        "Accounts table contains records",
        len(accounts) > 0,
        results,
    )

    run_check(
        "Transactions table contains 10,000 records",
        len(transactions) == 10_000,
        results,
    )

    # ---------------------------------------------------------------
    # Duplicate-ID checks
    # ---------------------------------------------------------------

    run_check(
        "Customer IDs are unique",
        customers["customer_id"].is_unique,
        results,
    )

    run_check(
        "Account IDs are unique",
        accounts["account_id"].is_unique,
        results,
    )

    run_check(
        "Device IDs are unique",
        devices["device_id"].is_unique,
        results,
    )

    run_check(
        "Beneficiary IDs are unique",
        beneficiaries["beneficiary_id"].is_unique,
        results,
    )

    run_check(
        "Transaction IDs are unique",
        transactions["transaction_id"].is_unique,
        results,
    )

    # ---------------------------------------------------------------
    # Missing-value checks
    # ---------------------------------------------------------------

    required_transaction_columns = [
        "transaction_id",
        "customer_id",
        "account_id",
        "transaction_timestamp",
        "transaction_type",
        "channel",
        "amount",
        "currency",
        "device_id",
        "country",
        "balance_before",
        "balance_after",
        "is_fraud",
    ]

    run_check(
        "Required transaction fields contain no missing values",
        transactions[required_transaction_columns]
        .isna()
        .sum()
        .sum()
        == 0,
        results,
    )

    # ---------------------------------------------------------------
    # Relationship checks
    # ---------------------------------------------------------------

    run_check(
        "All accounts belong to existing customers",
        accounts["customer_id"].isin(customers["customer_id"]).all(),
        results,
    )

    run_check(
        "All transaction customers exist",
        transactions["customer_id"]
        .isin(customers["customer_id"])
        .all(),
        results,
    )

    run_check(
        "All transaction accounts exist",
        transactions["account_id"]
        .isin(accounts["account_id"])
        .all(),
        results,
    )

    run_check(
        "All transaction devices exist",
        transactions["device_id"]
        .isin(devices["device_id"])
        .all(),
        results,
    )

    transfer_beneficiaries = transactions.loc[
        transactions["beneficiary_id"].notna(),
        "beneficiary_id",
    ]

    run_check(
        "All transaction beneficiaries exist",
        transfer_beneficiaries
        .isin(beneficiaries["beneficiary_id"])
        .all(),
        results,
    )

    # ---------------------------------------------------------------
    # Customer ownership checks
    # ---------------------------------------------------------------

    account_customer_map = accounts.set_index(
        "account_id"
    )["customer_id"]

    expected_account_customers = transactions[
        "account_id"
    ].map(account_customer_map)

    run_check(
        "Transaction customer matches account owner",
        expected_account_customers.eq(
            transactions["customer_id"]
        ).all(),
        results,
    )

    device_customer_map = devices.set_index(
        "device_id"
    )["customer_id"]

    expected_device_customers = transactions[
        "device_id"
    ].map(device_customer_map)

    run_check(
        "Transaction device belongs to the customer",
        expected_device_customers.eq(
            transactions["customer_id"]
        ).all(),
        results,
    )

    # ---------------------------------------------------------------
    # Financial-value checks
    # ---------------------------------------------------------------

    run_check(
        "All transaction amounts are positive",
        transactions["amount"].gt(0).all(),
        results,
    )

    expected_balance_after = (
        transactions["balance_before"] - transactions["amount"]
    ).round(2)

    run_check(
        "Transaction balances are calculated correctly",
        expected_balance_after.eq(
            transactions["balance_after"].round(2)
        ).all(),
        results,
    )

    run_check(
        "Account balances are not negative",
        accounts["current_balance"].ge(0).all(),
        results,
    )

    # ---------------------------------------------------------------
    # Timestamp and fraud-label checks
    # ---------------------------------------------------------------

    parsed_timestamps = pd.to_datetime(
        transactions["transaction_timestamp"],
        errors="coerce",
        utc=True,
    )

    run_check(
        "All transaction timestamps are valid",
        parsed_timestamps.notna().all(),
        results,
    )

    run_check(
        "Fraud labels contain only zero or one",
        transactions["is_fraud"].isin([0, 1]).all(),
        results,
    )

    # ---------------------------------------------------------------
    # Final result
    # ---------------------------------------------------------------

    failed_checks = [
        check_name
        for check_name, passed in results
        if not passed
    ]

    print("\nValidation summary")
    print("------------------")
    print(f"Checks performed: {len(results)}")
    print(f"Checks passed: {len(results) - len(failed_checks)}")
    print(f"Checks failed: {len(failed_checks)}")

    if failed_checks:
        print("\nThe dataset failed validation:")

        for failed_check in failed_checks:
            print(f"- {failed_check}")

        raise SystemExit(1)

    print("\nAll data-quality checks passed successfully.")


if __name__ == "__main__":
    main()