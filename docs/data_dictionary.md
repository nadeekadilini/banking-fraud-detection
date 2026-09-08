# Banking Fraud Detection Data Dictionary

## Purpose

This document defines the synthetic datasets used by the Cloud-Native Banking Fraud Detection Platform.

All records are fictional and generated specifically for this portfolio project. The data model supports behavioural analysis, fraud-rule development, machine-learning models and investigator reporting.

## Data Standards

- All identifier fields use synthetic string IDs.
- Timestamps use UTC and follow ISO 8601 format.
- Monetary values use two decimal places.
- Currency values use ISO 4217 codes such as `AUD`.
- Country values use ISO country codes such as `AU`.
- Missing values are permitted only where identified.
- No genuine customer or financial information is used.

---

## 1. Customers

**Table name:** `customers`

**Purpose:** Stores synthetic customer details and general risk characteristics.

| Column | Data type | Required | Key | Description |
|---|---|---:|---|---|
| customer_id | STRING | Yes | Primary key | Unique synthetic customer identifier |
| date_of_birth | DATE | Yes |  | Synthetic date of birth |
| customer_since | DATE | Yes |  | Date the customer joined the bank |
| occupation_category | STRING | Yes |  | Broad synthetic occupation group |
| annual_income | NUMERIC | Yes |  | Estimated annual income in AUD |
| residential_postcode | STRING | Yes |  | Australian residential postcode |
| residential_state | STRING | Yes |  | Australian state or territory |
| home_country | STRING | Yes |  | Customer’s primary country |
| customer_segment | STRING | Yes |  | Retail, affluent or business segment |
| customer_risk_rating | STRING | Yes |  | Low, medium or high customer-risk classification |
| pep_flag | BOOLEAN | Yes |  | Indicates a simulated politically exposed person |
| account_status | STRING | Yes |  | Active, restricted, suspended or closed |
| created_at | TIMESTAMP | Yes |  | Record creation timestamp |
| updated_at | TIMESTAMP | Yes |  | Most recent record update timestamp |

---

## 2. Accounts

**Table name:** `accounts`

**Purpose:** Stores accounts owned by synthetic customers.

| Column | Data type | Required | Key | Description |
|---|---|---:|---|---|
| account_id | STRING | Yes | Primary key | Unique synthetic account identifier |
| customer_id | STRING | Yes | Foreign key | References `customers.customer_id` |
| account_type | STRING | Yes |  | Transaction, savings or credit account |
| account_open_date | DATE | Yes |  | Date the account was opened |
| currency | STRING | Yes |  | Account currency code |
| current_balance | NUMERIC | Yes |  | Current simulated account balance |
| available_balance | NUMERIC | Yes |  | Balance available for transactions |
| credit_limit | NUMERIC | No |  | Credit limit where applicable |
| account_status | STRING | Yes |  | Active, restricted, frozen or closed |
| home_branch_code | STRING | No |  | Synthetic account branch code |
| digital_banking_enabled | BOOLEAN | Yes |  | Whether digital banking is enabled |
| created_at | TIMESTAMP | Yes |  | Record creation timestamp |
| updated_at | TIMESTAMP | Yes |  | Most recent record update timestamp |

---

## 3. Devices

**Table name:** `devices`

**Purpose:** Stores devices used by customers to access digital banking.

| Column | Data type | Required | Key | Description |
|---|---|---:|---|---|
| device_id | STRING | Yes | Primary key | Unique synthetic device identifier |
| customer_id | STRING | Yes | Foreign key | References `customers.customer_id` |
| device_type | STRING | Yes |  | Mobile phone, tablet or computer |
| operating_system | STRING | Yes |  | Device operating system |
| browser_name | STRING | No |  | Browser used for digital banking |
| device_fingerprint | STRING | Yes |  | Synthetic device fingerprint |
| first_seen_at | TIMESTAMP | Yes |  | First recorded use of the device |
| last_seen_at | TIMESTAMP | Yes |  | Most recent recorded use |
| trusted_device_flag | BOOLEAN | Yes |  | Whether the customer previously trusted the device |
| compromised_device_flag | BOOLEAN | Yes |  | Simulated indicator of a compromised device |
| usual_country | STRING | Yes |  | Country from which the device is normally used |
| usual_city | STRING | Yes |  | City from which the device is normally used |

---

## 4. Beneficiaries

**Table name:** `beneficiaries`

**Purpose:** Stores recipients registered by customers for money transfers.

| Column | Data type | Required | Key | Description |
|---|---|---:|---|---|
| beneficiary_id | STRING | Yes | Primary key | Unique synthetic beneficiary identifier |
| customer_id | STRING | Yes | Foreign key | Customer who registered the beneficiary |
| beneficiary_account_id | STRING | Yes |  | Masked synthetic destination account |
| beneficiary_bank_code | STRING | Yes |  | Synthetic destination bank code |
| beneficiary_country | STRING | Yes |  | Destination country |
| beneficiary_type | STRING | Yes |  | Individual or business |
| date_added | TIMESTAMP | Yes |  | Time the beneficiary was registered |
| first_payment_at | TIMESTAMP | No |  | Time of the first payment |
| trusted_beneficiary_flag | BOOLEAN | Yes |  | Whether the beneficiary is trusted |
| external_beneficiary_flag | BOOLEAN | Yes |  | Whether the beneficiary is held at another bank |
| beneficiary_risk_rating | STRING | Yes |  | Low, medium or high simulated risk |

---

## 5. Merchants

**Table name:** `merchants`

**Purpose:** Stores merchants involved in card and purchase transactions.

| Column | Data type | Required | Key | Description |
|---|---|---:|---|---|
| merchant_id | STRING | Yes | Primary key | Unique synthetic merchant identifier |
| merchant_name | STRING | Yes |  | Fictional merchant name |
| merchant_category_code | STRING | Yes |  | Merchant category code |
| merchant_category | STRING | Yes |  | Merchant industry category |
| merchant_country | STRING | Yes |  | Country where the merchant operates |
| merchant_city | STRING | Yes |  | Merchant city |
| online_merchant_flag | BOOLEAN | Yes |  | Whether transactions occur online |
| merchant_risk_rating | STRING | Yes |  | Low, medium or high simulated risk |
| active_flag | BOOLEAN | Yes |  | Whether the merchant is active |
| created_at | TIMESTAMP | Yes |  | Record creation timestamp |

---

## 6. Transactions

**Table name:** `transactions`

**Purpose:** Stores banking transactions used for fraud detection and behavioural analysis.

| Column | Data type | Required | Key | Description |
|---|---|---:|---|---|
| transaction_id | STRING | Yes | Primary key | Unique synthetic transaction identifier |
| account_id | STRING | Yes | Foreign key | References `accounts.account_id` |
| customer_id | STRING | Yes | Foreign key | References `customers.customer_id` |
| transaction_timestamp | TIMESTAMP | Yes |  | Date and time of the transaction |
| transaction_type | STRING | Yes |  | Purchase, transfer, withdrawal, deposit or payment |
| channel | STRING | Yes |  | Mobile, internet, card, ATM or branch |
| amount | NUMERIC | Yes |  | Transaction amount |
| currency | STRING | Yes |  | Transaction currency |
| amount_aud | NUMERIC | Yes |  | AUD-equivalent transaction amount |
| merchant_id | STRING | No | Foreign key | References `merchants.merchant_id` for purchases |
| beneficiary_id | STRING | No | Foreign key | References `beneficiaries.beneficiary_id` for transfers |
| device_id | STRING | No | Foreign key | References `devices.device_id` for digital transactions |
| ip_address | STRING | No |  | Synthetic IP address |
| transaction_country | STRING | Yes |  | Country in which the transaction occurred |
| transaction_city | STRING | Yes |  | City in which the transaction occurred |
| latitude | FLOAT | No |  | Approximate synthetic geographic latitude |
| longitude | FLOAT | No |  | Approximate synthetic geographic longitude |
| balance_before | NUMERIC | Yes |  | Account balance before the transaction |
| balance_after | NUMERIC | Yes |  | Account balance after the transaction |
| transaction_status | STRING | Yes |  | Approved, declined, pending or reversed |
| authentication_method | STRING | No |  | Password, biometric, PIN or multi-factor authentication |
| is_fraud | BOOLEAN | Yes |  | Ground-truth synthetic fraud label |
| fraud_scenario | STRING | No |  | Fraud typology injected into the transaction |
| created_at | TIMESTAMP | Yes |  | Record creation timestamp |

### Transaction rules

- `amount` must be greater than zero.
- `transaction_id` must be unique.
- `customer_id` and `account_id` must exist in their parent tables.
- A purchase may contain `merchant_id`.
- A transfer may contain `beneficiary_id`.
- Digital transactions may contain `device_id` and `ip_address`.
- A legitimate transaction must have `is_fraud = false`.
- A deliberately injected fraudulent transaction must have `is_fraud = true` and a populated `fraud_scenario`.

---

## 7. Fraud Events

**Table name:** `fraud_events`

**Purpose:** Groups related fraudulent transactions into identifiable fraud events.

| Column | Data type | Required | Key | Description |
|---|---|---:|---|---|
| fraud_event_id | STRING | Yes | Primary key | Unique synthetic fraud-event identifier |
| customer_id | STRING | Yes | Foreign key | References `customers.customer_id` |
| account_id | STRING | Yes | Foreign key | References `accounts.account_id` |
| fraud_scenario | STRING | Yes |  | Type of simulated fraud |
| event_start_timestamp | TIMESTAMP | Yes |  | Beginning of the fraud event |
| event_end_timestamp | TIMESTAMP | Yes |  | End of the fraud event |
| number_of_transactions | INTEGER | Yes |  | Number of transactions within the event |
| total_fraud_amount | NUMERIC | Yes |  | Total value of fraudulent transactions |
| fraud_status | STRING | Yes |  | Simulated confirmed, suspected or rejected outcome |
| detection_source | STRING | Yes |  | Rule, machine-learning model or combined detection |
| scenario_description | STRING | Yes |  | Explanation of the injected fraud behaviour |
| created_at | TIMESTAMP | Yes |  | Record creation timestamp |

---

## Entity Relationships

- One customer may own multiple accounts.
- One customer may register multiple devices.
- One customer may register multiple beneficiaries.
- One account may contain multiple transactions.
- One merchant may appear in multiple transactions.
- One beneficiary may receive multiple transfers.
- One fraud event may contain one or more fraudulent transactions.

## Initial Dataset Size

| Dataset | Initial target |
|---|---:|
| Customers | 2,000 |
| Accounts | Approximately 3,000 |
| Devices | Approximately 3,500 |
| Beneficiaries | Approximately 6,000 |
| Merchants | 500 |
| Transactions | 50,000 |
| Fraud events | Determined by the 1% target fraud rate |

The initial version will be validated locally before increasing the transaction volume and migrating the processing workflow to Google Cloud.