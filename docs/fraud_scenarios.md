# Fraud and Scam Scenario Specification

## Purpose

This document defines the suspicious behaviours simulated and detected by the Fraud and Scam Rule Optimisation and Customer Protection Analytics Platform.

All customers, accounts, devices, beneficiaries and transactions are synthetic. No genuine customer or banking information is used.

The prototype focuses on four scenarios:

1. Account takeover
2. New-beneficiary scam
3. Rapid payment burst
4. Potential mule beneficiary

---

## 1. Account Takeover

### Description

Account takeover occurs when an unauthorised person obtains access to a customer's account or digital banking credentials.

### Simulated Behaviour

- A new device appears on the customer's account.
- The transaction uses an unfamiliar IP address.
- The transaction location differs from the customer's usual location.
- The payment amount is considerably higher than the customer's normal amount.
- One or more payments occur soon after the device change.

### Behavioural Indicators

- `is_new_device`
- `is_new_ip`
- `is_country_mismatch`
- `amount_to_average_ratio`
- `transactions_last_10m`
- `value_last_10m`

### Reason Codes

- `NEW_DEVICE`
- `NEW_IP`
- `COUNTRY_MISMATCH`
- `HIGH_VALUE_VS_BASELINE`
- `RAPID_PAYMENTS`

### Possible Protective Action

A medium-risk event may require additional authentication. A high-risk event may be temporarily held and referred for investigation.

---

## 2. New-Beneficiary Scam

### Description

A new-beneficiary scam occurs when a customer is deceived or pressured into sending money to a recently added recipient.

The customer may technically authorise the transaction, but the payment results from manipulation or impersonation.

### Simulated Behaviour

- A beneficiary is recently added to the customer's account.
- A payment occurs shortly after the beneficiary is created.
- The payment is larger than the customer's normal transfer amount.
- The payment occurs from a new device or at an unusual time.
- Multiple payments may be sent to the new beneficiary.

### Behavioural Indicators

- `beneficiary_age_hours`
- `amount_to_average_ratio`
- `is_new_device`
- `is_unusual_hour`
- `transactions_last_10m`
- `value_last_10m`

### Reason Codes

- `NEW_BENEFICIARY`
- `HIGH_VALUE_VS_BASELINE`
- `NEW_DEVICE`
- `UNUSUAL_HOUR`
- `RAPID_PAYMENTS`

### Possible Protective Action

The bank may display a scam warning, request confirmation, introduce a short payment delay or refer the payment for investigation.

---

## 3. Rapid Payment Burst

### Description

A rapid payment burst occurs when several payments are made from the same account within a short period.

This may indicate an account takeover or an attempt to move funds before the customer or bank detects the activity.

### Simulated Behaviour

- Several transactions occur within ten minutes.
- Their combined value is substantially higher than normal.
- Payments are made to one or more beneficiaries.
- Transactions may occur after a device or location change.
- There are short gaps between consecutive payments.

### Behavioural Indicators

- `transactions_last_10m`
- `value_last_10m`
- `minutes_since_previous_transaction`
- `is_new_device`
- `amount_to_average_ratio`

### Reason Codes

- `HIGH_TRANSACTION_VELOCITY`
- `HIGH_VALUE_VELOCITY`
- `SHORT_TIME_GAP`
- `NEW_DEVICE`
- `HIGH_VALUE_VS_BASELINE`

### Possible Protective Action

The transactions may be prioritised for investigation, subjected to additional authentication or temporarily held.

---

## 4. Potential Mule Beneficiary

### Description

A money mule account receives or transfers funds on behalf of another person.

This prototype detects suspicious beneficiary behaviour. It does not make a final determination that an account is a money mule.

### Simulated Behaviour

- One beneficiary receives payments from several unrelated customers.
- The beneficiary receives a high total value within a short period.
- Several payments have similar values.
- The customers do not normally share beneficiaries.
- Received funds may be moved rapidly.

### Behavioural Indicators

- `beneficiary_unique_senders`
- `beneficiary_received_value`
- `beneficiary_transaction_count`
- `beneficiary_average_amount`
- `beneficiary_inflow_velocity`

### Reason Codes

- `MANY_UNIQUE_SENDERS`
- `HIGH_BENEFICIARY_VALUE`
- `HIGH_BENEFICIARY_VELOCITY`
- `REPEATED_SIMILAR_AMOUNTS`

### Possible Protective Action

The beneficiary relationship may be referred for investigation. Additional evidence and governance would be required before restricting an account.

---

## Ground-Truth Labels

The synthetic-data generator will record which scenario was deliberately injected into each suspicious transaction.

The following fields will be used:

- `is_fraud`: Indicates whether the transaction belongs to an injected suspicious event.
- `fraud_scenario`: Identifies the injected scenario.
- `fraud_event_id`: Connects transactions belonging to the same suspicious event.

Possible values for `fraud_scenario` are:

- `account_takeover`
- `new_beneficiary_scam`
- `rapid_payment_burst`
- `potential_mule_beneficiary`
- `none`

These labels will only be used to evaluate the detection rules. The rules must not read these labels when deciding whether to produce an alert.

---

## Detection Strategies

### Sensitive Strategy

The sensitive strategy uses lower thresholds. It is intended to capture more suspicious activity but may generate more alerts and false positives.

### Balanced Strategy

The balanced strategy uses higher thresholds or stronger combinations of indicators. It is intended to reduce unnecessary alerts, investigation workload and customer disruption.

---

## Evaluation Measures

The scenarios and detection strategies will be assessed using:

- Precision
- Recall
- F1 score
- False-positive ratio
- False-positive rate
- Total alert volume
- Fraud transactions detected
- Fraud value detected
- Number of genuine customers affected

Accuracy will not be used as the main measure because suspicious transactions represent only a small proportion of banking activity.

---

## Limitation

The suspicious patterns are deliberately created for a synthetic portfolio project.

The results demonstrate analytical design, rule optimisation and customer-impact assessment. They must not be presented as evidence of performance on genuine bank data.