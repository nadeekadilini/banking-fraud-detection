"""Generate linked synthetic banking data for the fraud detection project."""

from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

SEED = 42
NUMBER_OF_CUSTOMERS = 250
NUMBER_OF_ACCOUNTS = 350
NUMBER_OF_TRANSACTIONS = 10_000
SIMULATION_DAYS = 60

rng = np.random.default_rng(SEED)
fake = Faker("en_AU")
Faker.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "synthetic_sample"


# -------------------------------------------------------------------
# Customer generation
# -------------------------------------------------------------------

def generate_customers() -> pd.DataFrame:
    """Create fictional banking customers."""

    customers = []

    for customer_number in range(1, NUMBER_OF_CUSTOMERS + 1):
        customers.append(
            {
                "customer_id": f"CUST{customer_number:06d}",
                "date_of_birth": fake.date_of_birth(
                    minimum_age=18,
                    maximum_age=85,
                ),
                "postcode": fake.postcode(),
                "state": rng.choice(
                    ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"]
                ),
                "country": "AU",
                "customer_since": fake.date_between(
                    start_date="-15y",
                    end_date="-90d",
                ),
                "risk_segment": rng.choice(
                    ["low", "medium", "high"],
                    p=[0.75, 0.20, 0.05],
                ),
            }
        )

    return pd.DataFrame(customers)


# -------------------------------------------------------------------
# Account generation
# -------------------------------------------------------------------

def generate_accounts(customers: pd.DataFrame) -> pd.DataFrame:
    """Create bank accounts linked to customers."""

    accounts = []

    for account_number in range(1, NUMBER_OF_ACCOUNTS + 1):
        customer_id = rng.choice(customers["customer_id"].to_numpy())

        accounts.append(
            {
                "account_id": f"ACC{account_number:06d}",
                "customer_id": customer_id,
                "account_type": rng.choice(
                    ["transaction", "savings"],
                    p=[0.70, 0.30],
                ),
                "currency": "AUD",
                "opening_date": fake.date_between(
                    start_date="-10y",
                    end_date="-60d",
                ),
                "account_status": rng.choice(
                    ["active", "dormant"],
                    p=[0.97, 0.03],
                ),
                "current_balance": round(
                    float(rng.lognormal(mean=8.0, sigma=1.0)),
                    2,
                ),
            }
        )

    return pd.DataFrame(accounts)


# -------------------------------------------------------------------
# Device generation
# -------------------------------------------------------------------

def generate_devices(customers: pd.DataFrame) -> pd.DataFrame:
    """Create trusted devices normally used by each customer."""

    devices = []
    device_number = 1

    for customer_id in customers["customer_id"]:
        number_of_devices = int(rng.integers(1, 4))

        for _ in range(number_of_devices):
            devices.append(
                {
                    "device_id": f"DEV{device_number:06d}",
                    "customer_id": customer_id,
                    "device_type": rng.choice(
                        ["mobile", "tablet", "desktop"],
                        p=[0.70, 0.10, 0.20],
                    ),
                    "operating_system": rng.choice(
                        ["iOS", "Android", "Windows", "macOS"],
                    ),
                    "trusted_device": True,
                    "first_seen_date": fake.date_between(
                        start_date="-5y",
                        end_date="-60d",
                    ),
                }
            )

            device_number += 1

    return pd.DataFrame(devices)


# -------------------------------------------------------------------
# Beneficiary generation
# -------------------------------------------------------------------

def generate_beneficiaries(customers: pd.DataFrame) -> pd.DataFrame:
    """Create payment beneficiaries linked to customers."""

    beneficiaries = []
    beneficiary_number = 1

    for customer_id in customers["customer_id"]:
        number_of_beneficiaries = int(rng.integers(2, 6))

        for _ in range(number_of_beneficiaries):
            beneficiaries.append(
                {
                    "beneficiary_id": f"BEN{beneficiary_number:06d}",
                    "customer_id": customer_id,
                    "beneficiary_account_id": (
                        f"EXTACC{beneficiary_number:07d}"
                    ),
                    "beneficiary_country": "AU",
                    "date_added": fake.date_between(
                        start_date="-5y",
                        end_date="-60d",
                    ),
                    "beneficiary_status": "active",
                }
            )

            beneficiary_number += 1

    return pd.DataFrame(beneficiaries)


# -------------------------------------------------------------------
# Transaction generation
# -------------------------------------------------------------------

def generate_transactions(
    accounts: pd.DataFrame,
    devices: pd.DataFrame,
    beneficiaries: pd.DataFrame,
) -> pd.DataFrame:
    """Create normal banking transactions."""

    transactions = []

    devices_by_customer = {
        customer_id: group["device_id"].tolist()
        for customer_id, group in devices.groupby("customer_id")
    }

    beneficiaries_by_customer = {
        customer_id: group["beneficiary_id"].tolist()
        for customer_id, group in beneficiaries.groupby("customer_id")
    }

    end_time = pd.Timestamp.now(tz="UTC").floor("s")
    start_time = end_time - pd.Timedelta(days=SIMULATION_DAYS)
    simulation_seconds = int((end_time - start_time).total_seconds())

    account_records = accounts.to_dict("records")

    for transaction_number in range(1, NUMBER_OF_TRANSACTIONS + 1):
        account = account_records[int(rng.integers(0, len(account_records)))]

        customer_id = account["customer_id"]
        account_id = account["account_id"]

        transaction_type = rng.choice(
            ["bank_transfer", "card_purchase", "cash_withdrawal"],
            p=[0.45, 0.45, 0.10],
        )

        timestamp = start_time + pd.Timedelta(
            seconds=int(rng.integers(0, simulation_seconds))
        )

        amount = round(
            float(np.clip(rng.lognormal(mean=4.3, sigma=1.0), 5, 3000)),
            2,
        )

        device_id = rng.choice(devices_by_customer[customer_id])
        beneficiary_id = None

        if transaction_type == "bank_transfer":
            beneficiary_id = rng.choice(
                beneficiaries_by_customer[customer_id]
            )
            channel = rng.choice(["mobile_banking", "internet_banking"])
        elif transaction_type == "card_purchase":
            channel = rng.choice(["point_of_sale", "ecommerce"])
        else:
            channel = "atm"

        balance_before = round(
            float(max(account["current_balance"], amount + 50)),
            2,
        )
        balance_after = round(balance_before - amount, 2)

        transactions.append(
            {
                "transaction_id": f"TXN{transaction_number:08d}",
                "customer_id": customer_id,
                "account_id": account_id,
                "transaction_timestamp": timestamp.isoformat(),
                "transaction_type": transaction_type,
                "channel": channel,
                "amount": amount,
                "currency": "AUD",
                "beneficiary_id": beneficiary_id,
                "device_id": device_id,
                "ip_address": fake.ipv4_public(),
                "country": "AU",
                "balance_before": balance_before,
                "balance_after": balance_after,
                "is_fraud": 0,
                "fraud_scenario": "",
                "fraud_event_id": "",
            }
        )

    transactions_dataframe = pd.DataFrame(transactions)

    return transactions_dataframe.sort_values(
        "transaction_timestamp"
    ).reset_index(drop=True)


# -------------------------------------------------------------------
# Save files
# -------------------------------------------------------------------

def save_dataset(
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    devices: pd.DataFrame,
    beneficiaries: pd.DataFrame,
    transactions: pd.DataFrame,
) -> None:
    """Save all generated tables as CSV files."""

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    datasets = {
        "customers.csv": customers,
        "accounts.csv": accounts,
        "devices.csv": devices,
        "beneficiaries.csv": beneficiaries,
        "transactions.csv": transactions,
    }

    for filename, dataframe in datasets.items():
        output_path = OUTPUT_DIRECTORY / filename
        dataframe.to_csv(output_path, index=False)

        print(f"Created {filename}: {len(dataframe):,} records")


# -------------------------------------------------------------------
# Run the generator
# -------------------------------------------------------------------

def main() -> None:
    """Generate and save the complete base dataset."""

    print("Generating synthetic banking data...")

    customers = generate_customers()
    accounts = generate_accounts(customers)
    devices = generate_devices(customers)
    beneficiaries = generate_beneficiaries(customers)

    transactions = generate_transactions(
        accounts=accounts,
        devices=devices,
        beneficiaries=beneficiaries,
    )

    save_dataset(
        customers=customers,
        accounts=accounts,
        devices=devices,
        beneficiaries=beneficiaries,
        transactions=transactions,
    )

    print("\nSynthetic banking dataset generated successfully.")
    print(f"Files saved to: {OUTPUT_DIRECTORY}")


if __name__ == "__main__":
    main()