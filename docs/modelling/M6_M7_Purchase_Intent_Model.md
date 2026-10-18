# M6–M7: Customer Behavioral Features & Purchase-Intent Modeling

## 1. Objective

Build a session-level purchase-intent prediction model using early customer behavior from e-commerce clickstream events.

The model predicts whether a customer session will contain a purchase after its first three events, provided that no purchase occurred in those first three events.

This is a session-level prediction task, not a prediction of whether a customer will ever purchase.

## 2. Data Source

**Gold feature table:** `ecommerce_intelligence.gold.purchase_intent_features`

**Total eligible sessions:** 3,952,405

**Positive sessions:** 331,472

**Negative sessions:** 3,620,933

**Positive rate:** 8.3866%

Sessions with fewer than three events and sessions containing a purchase in the first three events were excluded from the modeling cohort.

## 3. Feature Engineering

The model uses six features derived from the first three events of each eligible session:

| Feature | Description |
|---|---|
| `views_first3` | Number of view events in the first three events |
| `carts_first3` | Number of cart events in the first three events |
| `unique_products_first3` | Number of distinct products interacted with |
| `unique_categories_first3` | Number of distinct categories interacted with |
| `avg_price_first3` | Average observed price in the first three events |
| `elapsed_seconds_first3` | Time elapsed between the first and third events |

**Target:** `will_purchase_later`

- `1`: A purchase occurs later in the same derived session.
- `0`: No purchase is observed later in the same derived session.

## 4. Train, Validation and Test Split

A deterministic user-level split was created using `pmod(xxhash64(user_id), 100)`.

| Split | Sessions | Positive sessions |
|---|---:|---:|
| Train | 2,772,221 | 232,128 |
| Validation | 587,914 | 49,335 |
| Test | 592,270 | 50,009 |
| **Total** | **3,952,405** | **331,472** |

Users were assigned to only one split to prevent user overlap across training, validation and test data.

## 5. Models Evaluated

### Logistic Regression

The baseline used a Spark ML pipeline consisting of VectorAssembler, StandardScaler and LogisticRegression.

Configuration:
- Maximum iterations: 50
- Regularization parameter: 0.01
- Elastic net parameter: 0.0

Validation results:
- ROC-AUC: 0.6751
- PR-AUC: 0.2293
- Best observed F1-score: 0.3222
- Selected threshold: 0.20

Test results at threshold 0.20:
- ROC-AUC: 0.67435
- PR-AUC: 0.22501
- Precision: 0.42099
- Recall: 0.25085
- F1-score: 0.31438

### Random Forest

Configuration:
- Number of trees: 50
- Maximum depth: 8
- Random seed: 42

Validation results:
- ROC-AUC: 0.6757
- PR-AUC: 0.2550
- Best observed F1-score: 0.3223
- Selected threshold: 0.20

Test results at threshold 0.20:
- ROC-AUC: 0.67451
- PR-AUC: 0.24814
- Precision: 0.42094
- Recall: 0.25093
- F1-score: 0.31443

## 6. Final Model Selection

Random Forest was retained as the leading candidate because it achieved higher PR-AUC than Logistic Regression on validation and test data.

However, the F1-score improvement was negligible. Random Forest should therefore be described as the leading candidate, not as conclusively superior on every metric.

The probability threshold of 0.20 was selected using validation results, not test results.

## 7. Random Forest Feature Importance

| Feature | Importance |
|---|---:|
| `carts_first3` | 55.21% |
| `views_first3` | 36.56% |
| `unique_products_first3` | 5.47% |
| `elapsed_seconds_first3` | 1.23% |
| `avg_price_first3` | 1.06% |
| `unique_categories_first3` | 0.48% |

Cart and view activity together account for approximately 91.76% of total Random Forest feature importance.

These scores describe the trained model's reliance on the features. They do not establish causal effects.

## 8. MLflow and Unity Catalog

**MLflow experiment:** `/Shared/ecommerce-customer-intelligence-m6`

**Signed model run ID:** `7f1a06d00f4f4f6298dad1bb475a47ce`

**Registered model:** `ecommerce_intelligence.gold.purchase_intent_rf`

**Registered version:** `1`

**Model status:** READY

**Model URI:** `models:/ecommerce_intelligence.gold.purchase_intent_rf/1`

The registered Spark ML pipeline was loaded from Unity Catalog and successfully passed an inference smoke test.

The raw pipeline returns `prediction`, `probability` and `rawPrediction`. The selected threshold of 0.20 is applied separately by the inference logic; it is not embedded in the registered Spark pipeline.

## 9. Limitations

1. The target represents purchase behavior later in the same derived session, not lifetime customer purchase propensity.
2. The original source does not contain a unique event ID, so the true order of events with identical timestamps and ordering attributes cannot always be recovered.
3. A positive prediction does not guarantee a purchase.
4. A negative label means no later purchase was observed in that session; it does not mean the customer never purchases.
5. Random Forest's F1-score is almost identical to Logistic Regression's despite its higher PR-AUC.
6. Further work could investigate probability calibration, alternative models, cost-sensitive threshold selection and more extensive validation.

## 10. Reproducibility References

- Databricks notebook: `M6_01_Customer_Behavioral_Features`
- Feature table: `ecommerce_intelligence.gold.purchase_intent_features`
- Registered model URI: `models:/ecommerce_intelligence.gold.purchase_intent_rf/1`
- MLflow signed run: `7f1a06d00f4f4f6298dad1bb475a47ce`

This report records the implemented pipeline and measured results. It does not claim that production serving, automated retraining or real-time inference has been implemented.