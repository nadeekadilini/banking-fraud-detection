## Project Status

Completed independent portfolio prototype.

### Implemented Features

- Generated 10,000 synthetic banking transactions.
- Validated base banking data and simulated fraud scenarios.
- Simulated account takeover, new-beneficiary scams, rapid payment bursts and mule-account activity.
- Built behavioural features and explainable rule-based risk scores.
- Created an investigation queue and performance dashboard.
- Added interactive threshold comparison to explore detection and alert-workload trade-offs.
- Uploaded analytical tables to Google BigQuery and verified access from local Python.
- Deployed the Streamlit dashboard using synthetic CSV data.

### Baseline Results

| Metric | Result |
|---|---:|
| Synthetic transactions | 10,000 |
| Injected fraud transactions | 100 |
| Alerts generated | 102 |
| True positives | 89 |
| False positives | 13 |
| False negatives | 11 |
| Precision | 87.25% |
| Recall | 89.00% |
| F1 score | 88.12% |
| False-positive rate | 0.13% |
| Fraud value captured | 96.58% |

These results describe a controlled synthetic dataset and do not establish real-world banking performance. Payment-burst recall was 56%, highlighting an area for further improvement. Threshold comparisons use the same dataset and require separate holdout evaluation before making generalisation claims.

### Live Demonstration

[Open the dashboard](https://banking-fraud-detection-nadeeka.streamlit.app)

The hosted demonstration uses Local CSV. Google BigQuery connectivity has been verified locally; hosted BigQuery authentication is not configured.

### Scope

This release uses rule-based detection. Machine-learning models, production deployment and operational monitoring are future extensions.