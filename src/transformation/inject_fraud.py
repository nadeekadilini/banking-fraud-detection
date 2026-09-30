"""Inject controlled fraud and scam scenarios into synthetic banking data."""

from pathlib import Path

import numpy as np
import pandas as pd


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

SEED = 42

ACCOUNT_TAKEOVER_TRANSACTIONS = 25
NEW_BENEFICIARY_TRANSACTIONS = 25
RAPID_BURST_EVENTS = 5
TRANSACTIONS_PER_BURST = 5
MULE_TRANSACTIONS = 25

rng = np.random.default_rng(SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIRECTORY = PROJECT_ROOT / "data" / "synthetic_sample"


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def update_transaction_amount(
    transactions: pd.DataFrame,
    transaction_index: int,
    new_amount: float,
) -> None:
    """Update an amount and recalculate the resulting balance."""

    new_amount = round(float(new_amount), 2)

    original_balance = float(
        transactions.at[transaction_index, "balance_before"]
    )

    balance_before = max(original_balance, new_amount + 500)

    transactions.at[
        transaction_index,
        "amount",
    ] = new_amount

    transactions.at[
        transaction_index,
        "balance_before",
    ] = round(balance_before, 2)

    transactions.at[
        transaction_index,
        "balance_after",
    ] = round(balance_before - new_amount, 2)


def label_fraud(
    transactions: pd.DataFrame,
    transaction_index: int,
    scenario: str,
    event_id: str,
    reason: str,
) -> None:
    """Apply the ground-truth fraud label to a transaction."""

    transactions.at[transaction_index, "is_fraud"] = 1
    transactions.at[transaction_index, "fraud_scenario"] = scenario
    transactions.at[transaction_index, "fraud_event_id"] = event_id
    transactions.at[transaction_index, "fraud_reason"] = reason


def available_transfer_indices(
    transactions: pd.DataFrame,
    used_indices: set[int],
) -> list[int]:
    """Return unused bank-transfer transaction indices."""

    available = transactions[
        (transactions["transaction_type"] == "bank_transfer")
        & (~transactions.index.isin(used_indices))
    ]

    return available.index.tolist()


# -------------------------------------------------------------------
# Scenario 1: Account takeover
# -------------------------------------------------------------------

def inject_account_takeover(
    transactions: pd.DataFrame,
    devices: pd.DataFrame,
    used_indices: set[int],
) -> tuple[pd.DataFrame, set[int]]:
    """Inject high-value transfers from unfamiliar devices and countries."""

    available_indices = available_transfer_indices(
        transactions,
        used_indices,
    )

    selected_indices = rng.choice(
        available_indices,
        size=ACCOUNT_TAKEOVER_TRANSACTIONS,
        replace=False,
    )

    new_devices = []

    for event_number, transaction_index in enumerate(
        selected_indices,
        start=1,
    ):
        transaction_index = int(transaction_index)

        customer_id = transactions.at[
            transaction_index,
            "customer_id",
        ]

        event_id = f"EVT-ATO-{event_number:03d}"
        device_id = f"DEV-ATO-{event_number:03d}"

        transaction_timestamp = transactions.at[
            transaction_index,
            "transaction_timestamp",
        ]

        new_devices.append(
            {
                "device_id": device_id,
                "customer_id": customer_id,
                "device_type": rng.choice(
                    ["desktop", "mobile"],
                ),
                "operating_system": rng.choice(
                    ["Windows", "Android", "Linux"],
                ),
                "trusted_device": False,
                "first_seen_date": (
                    transaction_timestamp.date().isoformat()
                ),
            }
        )

        transactions.at[
            transaction_index,
            "device_id",
        ] = device_id

        transactions.at[
            transaction_index,
            "country",
        ] = rng.choice(["SG", "HK", "GB", "US"])

        transactions.at[
            transaction_index,
            "ip_address",
        ] = f"203.0.113.{event_number}"

        transactions.at[
            transaction_index,
            "channel",
        ] = "internet_banking"

        update_transaction_amount(
            transactions,
            transaction_index,
            rng.uniform(4_000, 12_000),
        )

        label_fraud(
            transactions,
            transaction_index,
            scenario="account_takeover",
            event_id=event_id,
            reason=(
                "Untrusted device; new foreign country; "
                "unusually high-value transfer"
            ),
        )

        used_indices.add(transaction_index)

    updated_devices = pd.concat(
        [devices, pd.DataFrame(new_devices)],
        ignore_index=True,
    )

    return updated_devices, used_indices


# -------------------------------------------------------------------
# Scenario 2: New-beneficiary scam
# -------------------------------------------------------------------

def inject_new_beneficiary_scam(
    transactions: pd.DataFrame,
    beneficiaries: pd.DataFrame,
    used_indices: set[int],
) -> tuple[pd.DataFrame, set[int]]:
    """Inject high-value payments to newly created beneficiaries."""

    available_indices = available_transfer_indices(
        transactions,
        used_indices,
    )

    selected_indices = rng.choice(
        available_indices,
        size=NEW_BENEFICIARY_TRANSACTIONS,
        replace=False,
    )

    new_beneficiaries = []

    for event_number, transaction_index in enumerate(
        selected_indices,
        start=1,
    ):
        transaction_index = int(transaction_index)

        customer_id = transactions.at[
            transaction_index,
            "customer_id",
        ]

        transaction_timestamp = transactions.at[
            transaction_index,
            "transaction_timestamp",
        ]

        event_id = f"EVT-NEWBEN-{event_number:03d}"
        beneficiary_id = f"BEN-SCAM-{event_number:03d}"

        new_beneficiaries.append(
            {
                "beneficiary_id": beneficiary_id,
                "customer_id": customer_id,
                "beneficiary_account_id": (
                    f"EXT-SCAM-{event_number:05d}"
                ),
                "beneficiary_country": "AU",
                "date_added": (
                    transaction_timestamp.date().isoformat()
                ),
                "beneficiary_status": "active",
            }
        )

        transactions.at[
            transaction_index,
            "beneficiary_id",
        ] = beneficiary_id

        transactions.at[
            transaction_index,
            "channel",
        ] = "mobile_banking"

        update_transaction_amount(
            transactions,
            transaction_index,
            rng.uniform(3_000, 10_000),
        )

        label_fraud(
            transactions,
            transaction_index,
            scenario="new_beneficiary_scam",
            event_id=event_id,
            reason=(
                "New beneficiary; same-day payment; "
                "unusually high-value transfer"
            ),
        )

        used_indices.add(transaction_index)

    updated_beneficiaries = pd.concat(
        [beneficiaries, pd.DataFrame(new_beneficiaries)],
        ignore_index=True,
    )

    return updated_beneficiaries, used_indices


# -------------------------------------------------------------------
# Scenario 3: Rapid payment burst
# -------------------------------------------------------------------

def inject_rapid_payment_bursts(
    transactions: pd.DataFrame,
    used_indices: set[int],
) -> set[int]:
    """Inject groups of payments occurring within a few minutes."""

    available_transactions = transactions[
        (transactions["transaction_type"] == "bank_transfer")
        & (~transactions.index.isin(used_indices))
    ]

    account_groups = available_transactions.groupby("account_id")

    eligible_accounts = [
        account_id
        for account_id, group in account_groups
        if len(group) >= TRANSACTIONS_PER_BURST
    ]

    selected_accounts = rng.choice(
        eligible_accounts,
        size=RAPID_BURST_EVENTS,
        replace=False,
    )

    for event_number, account_id in enumerate(
        selected_accounts,
        start=1,
    ):
        account_indices = available_transactions[
            available_transactions["account_id"] == account_id
        ].index.tolist()

        selected_indices = rng.choice(
            account_indices,
            size=TRANSACTIONS_PER_BURST,
            replace=False,
        )

        selected_indices = [
            int(index)
            for index in selected_indices
        ]

        event_id = f"EVT-BURST-{event_number:03d}"

        base_timestamp = transactions.at[
            selected_indices[0],
            "transaction_timestamp",
        ].floor("min")

        for position, transaction_index in enumerate(
            selected_indices
        ):
            transactions.at[
                transaction_index,
                "transaction_timestamp",
            ] = base_timestamp + pd.Timedelta(
                minutes=position * 2
            )

            transactions.at[
                transaction_index,
                "channel",
            ] = "mobile_banking"

            update_transaction_amount(
                transactions,
                transaction_index,
                rng.uniform(800, 2_500),
            )

            label_fraud(
                transactions,
                transaction_index,
                scenario="rapid_payment_burst",
                event_id=event_id,
                reason=(
                    "Multiple transfers from the same account "
                    "within ten minutes"
                ),
            )

            used_indices.add(transaction_index)

    return used_indices


# -------------------------------------------------------------------
# Scenario 4: Mule-account activity
# -------------------------------------------------------------------

def inject_mule_activity(
    transactions: pd.DataFrame,
    beneficiaries: pd.DataFrame,
    used_indices: set[int],
) -> tuple[pd.DataFrame, set[int]]:
    """Inject payments from many customers to one shared mule account."""

    available_transactions = transactions[
        (transactions["transaction_type"] == "bank_transfer")
        & (~transactions.index.isin(used_indices))
    ]

    distinct_customer_transactions = (
        available_transactions
        .drop_duplicates(subset=["customer_id"])
    )

    if len(distinct_customer_transactions) < MULE_TRANSACTIONS:
        raise ValueError(
            "Not enough distinct customers to generate mule activity."
        )

    selected_indices = rng.choice(
        distinct_customer_transactions.index.to_numpy(),
        size=MULE_TRANSACTIONS,
        replace=False,
    )

    mule_beneficiaries = []
    shared_mule_account = "EXT-MULE-00001"
    event_id = "EVT-MULE-001"

    for sequence_number, transaction_index in enumerate(
        selected_indices,
        start=1,
    ):
        transaction_index = int(transaction_index)

        customer_id = transactions.at[
            transaction_index,
            "customer_id",
        ]

        transaction_timestamp = transactions.at[
            transaction_index,
            "transaction_timestamp",
        ]

        beneficiary_id = f"BEN-MULE-{sequence_number:03d}"

        mule_beneficiaries.append(
            {
                "beneficiary_id": beneficiary_id,
                "customer_id": customer_id,
                "beneficiary_account_id": shared_mule_account,
                "beneficiary_country": "AU",
                "date_added": (
                    transaction_timestamp.date().isoformat()
                ),
                "beneficiary_status": "active",
            }
        )

        transactions.at[
            transaction_index,
            "beneficiary_id",
        ] = beneficiary_id

        update_transaction_amount(
            transactions,
            transaction_index,
            rng.uniform(500, 4_000),
        )

        label_fraud(
            transactions,
            transaction_index,
            scenario="mule_account_activity",
            event_id=event_id,
            reason=(
                "Shared beneficiary account receiving funds "
                "from many unrelated customers"
            ),
        )

        used_indices.add(transaction_index)

    updated_beneficiaries = pd.concat(
        [beneficiaries, pd.DataFrame(mule_beneficiaries)],
        ignore_index=True,
    )

    return updated_beneficiaries, used_indices


# -------------------------------------------------------------------
# Fraud-event summary
# -------------------------------------------------------------------

def create_fraud_event_summary(
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """Create one summary row for every simulated fraud event."""

    fraud_transactions = transactions[
        transactions["is_fraud"] == 1
    ].copy()

    fraud_events = (
        fraud_transactions
        .groupby(
            ["fraud_event_id", "fraud_scenario"],
            as_index=False,
        )
        .agg(
            transaction_count=("transaction_id", "count"),
            customer_count=("customer_id", "nunique"),
            total_amount=("amount", "sum"),
            first_timestamp=("transaction_timestamp", "min"),
            last_timestamp=("transaction_timestamp", "max"),
        )
    )

    fraud_events["total_amount"] = (
        fraud_events["total_amount"].round(2)
    )

    return fraud_events


# -------------------------------------------------------------------
# Main process
# -------------------------------------------------------------------

def main() -> None:
    """Load normal data, inject fraud scenarios and save new files."""

    print("Loading normal synthetic banking data...")

    transactions = pd.read_csv(
        DATA_DIRECTORY / "transactions.csv"
    )

    devices = pd.read_csv(
        DATA_DIRECTORY / "devices.csv"
    )

    beneficiaries = pd.read_csv(
        DATA_DIRECTORY / "beneficiaries.csv"
    )

    transactions["transaction_timestamp"] = pd.to_datetime(
        transactions["transaction_timestamp"],
        utc=True,
    )

    # Reset the ground-truth label fields before injecting fraud.
    transactions["is_fraud"] = 0
    transactions["fraud_scenario"] = ""
    transactions["fraud_event_id"] = ""
    transactions["fraud_reason"] = ""

    used_indices: set[int] = set()

    print("Injecting account-takeover events...")

    devices, used_indices = inject_account_takeover(
        transactions,
        devices,
        used_indices,
    )

    print("Injecting new-beneficiary scams...")

    beneficiaries, used_indices = inject_new_beneficiary_scam(
        transactions,
        beneficiaries,
        used_indices,
    )

    print("Injecting rapid payment bursts...")

    used_indices = inject_rapid_payment_bursts(
        transactions,
        used_indices,
    )

    print("Injecting mule-account activity...")

    beneficiaries, used_indices = inject_mule_activity(
        transactions,
        beneficiaries,
        used_indices,
    )

    transactions = transactions.sort_values(
        "transaction_timestamp"
    ).reset_index(drop=True)

    fraud_events = create_fraud_event_summary(transactions)

    transactions.to_csv(
        DATA_DIRECTORY / "transactions_with_fraud.csv",
        index=False,
    )

    devices.to_csv(
        DATA_DIRECTORY / "devices_with_fraud.csv",
        index=False,
    )

    beneficiaries.to_csv(
        DATA_DIRECTORY / "beneficiaries_with_fraud.csv",
        index=False,
    )

    fraud_events.to_csv(
        DATA_DIRECTORY / "fraud_events.csv",
        index=False,
    )

    fraud_transactions = transactions[
        transactions["is_fraud"] == 1
    ]

    fraud_rate = (
        len(fraud_transactions) / len(transactions)
    ) * 100

    print("\nFraud injection completed successfully.")
    print(f"Total transactions: {len(transactions):,}")
    print(f"Fraud transactions: {len(fraud_transactions):,}")
    print(f"Fraud rate: {fraud_rate:.2f}%")
    print(f"Fraud events: {len(fraud_events):,}")

    print("\nFraud transactions by scenario:")

    scenario_counts = (
        fraud_transactions["fraud_scenario"]
        .value_counts()
        .sort_index()
    )

    for scenario, count in scenario_counts.items():
        print(f"- {scenario}: {count}")

    print(f"\nFiles saved to: {DATA_DIRECTORY}")


if __name__ == "__main__":
    main()