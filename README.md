# Cloud-Native Banking Fraud Detection Platform

## Project Overview

This project develops a production-style financial crime analytics platform for detecting suspicious banking transactions using behavioural rules, machine learning and cloud-based data processing.

A synthetic multi-entity banking environment is used to demonstrate realistic customer and transaction behaviour without exposing genuine customer information.

## Business Problem

Banks process large volumes of transactions across digital banking, cards, ATMs and branches. Fraudulent activity must be identified quickly while controlling false positives that can inconvenience customers and increase investigation costs.

The platform will generate explainable fraud alerts to help investigators understand why a transaction was identified as suspicious.

## Project Objectives

* Generate realistic synthetic banking data.
* Model normal customer transaction behaviour.
* Simulate recognised fraud scenarios.
* Validate and transform transaction data.
* Develop rule-based fraud detection.
* Train and evaluate machine-learning models.
* Produce explainable risk scores and reason codes.
* Build an investigator-focused Power BI dashboard.
* Demonstrate a scalable Google Cloud architecture.
* Apply production-oriented testing, monitoring and security controls.

## Planned Architecture

Synthetic banking data
→ Data validation
→ Raw and curated storage
→ Behavioural feature engineering
→ Fraud rules and machine-learning models
→ Risk scores and reason codes
→ Investigation dashboard
→ Monitoring and performance reporting

The local pipeline will be developed and validated first. Google Cloud services will then be incorporated for scalable ingestion, storage, processing and analytics.

## Core Banking Entities

* Customers
* Accounts
* Transactions
* Devices
* Beneficiaries
* Merchants
* Fraud events

## Fraud Scenarios

The initial release will simulate:

1. Unusually large transactions.
2. New-beneficiary scams.
3. Account takeover using an unfamiliar device or IP address.
4. Rapid transaction bursts.
5. Impossible geographic movement.
6. Transaction structuring designed to avoid thresholds.

## Model Evaluation

Models will be evaluated using:

* Precision
* Recall
* F1 score
* Precision-recall AUC
* False-positive rate
* Fraud value detected
* Expected financial loss

Accuracy alone will not be used because fraudulent transactions represent a small proportion of banking activity.

## Security and Privacy

* Only synthetic data will be used.
* Credentials and secrets will not be committed to GitHub.
* Access will follow the principle of least privilege.
* Sensitive fields will be classified and protected.
* Logging and auditability will be included in the design.
* Production customer data must never be stored in this public-facing portfolio project.

## Project Status

**Phase 1 — Project foundation and synthetic data design**

## Disclaimer

This is an independent portfolio project created for educational and professional demonstration purposes. It is not affiliated with or endorsed by any financial institution. All customers, accounts, transactions and fraud events are synthetic.
