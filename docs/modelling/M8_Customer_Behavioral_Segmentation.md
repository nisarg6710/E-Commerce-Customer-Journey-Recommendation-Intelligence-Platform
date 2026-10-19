# M8 — Customer Behavioral Segmentation

## 1. Objective

The objective of Milestone 8 was to identify distinct customer behavioral segments from the October 2019 e-commerce clickstream dataset.

The segmentation pipeline transforms customer-level behavioral aggregates into standardized feature vectors, evaluates multiple K-Means configurations, assigns all customers to five clusters, profiles the resulting segments, and persists the outputs in Unity Catalog.

The segments describe observed behavior during the dataset's October 2019 observation period. They should not be interpreted as permanent customer personas.

## 2. Architecture and Data Flow

The pipeline uses the following data flow:

1. **Silver event data:** `ecommerce_intelligence.silver.sessionized_clickstream_events`
2. **Gold session data:** `ecommerce_intelligence.gold.customer_sessions`
3. **Customer feature engineering:** `ecommerce_intelligence.gold.customer_behavior_features`
4. **Feature transformations:** log transformations, vector assembly, and standard scaling
5. **Model selection:** deterministic evaluation sample and K-Means candidates for k = 3, 4, 5, and 6
6. **Full-population clustering:** K-Means with k = 5
7. **Gold outputs:** customer assignments and cluster profiles
8. **MLflow artifacts:** persisted scaler, K-Means model, and segmentation metadata

## 3. Customer Feature Engineering

The customer feature table contains 3,022,290 customers.

Features include:

- Total sessions, events, views, carts, and purchases
- Distinct products, categories, and brands
- Active days
- Average session duration and average observed session price
- Cart-to-view and purchase-to-view ratios
- Sessions containing cart and purchase activity
- Events per session
- First-seen and last-seen timestamps
- Observed activity span and sessions per active day

Data quality checks confirmed that the checked numeric features had no missing values, event counts were consistent, ratios were non-negative, and customer identifiers were unique.

## 4. Clustering Features and Preprocessing

The clustering model uses 15 customer-level features:

- `total_sessions`
- `total_events`
- `total_views`
- `total_carts`
- `total_purchases`
- `distinct_products`
- `distinct_categories`
- `distinct_brands`
- `active_days`
- `avg_session_duration_seconds`
- `cart_to_view_ratio`
- `purchase_to_view_ratio`
- `sessions_with_cart_ratio`
- `sessions_with_purchase_ratio`
- `events_per_session`

Log1p transformation was applied to count-like and duration-related features to reduce skew. Ratio features were retained without this transformation.

`user_id` was excluded from the model inputs.

The transformed features were assembled using Spark ML's `VectorAssembler` and standardized using `StandardScaler` with `withMean=True` and `withStd=True`.

## 5. Model Selection

A deterministic hash-based sample containing 99,233 customers was used to compare K-Means configurations. All candidates used seed 42, a maximum of 20 iterations, tolerance 0.01, and k-means|| initialization.

| k | Sample silhouette | Training cost |
|---:|---:|---:|
| 3 | 0.3868 | 842,758.32 |
| 4 | 0.4814 | 629,543.78 |
| 5 | 0.4996 | 573,743.80 |
| 6 | 0.4046 | 539,286.83 |

The k = 5 candidate achieved the highest observed silhouette score among the evaluated configurations. It was therefore selected as the leading candidate for full-population segmentation.

This is an empirical selection among the tested configurations, not proof that five clusters are globally optimal.

## 6. Full-Population Model

The selected K-Means configuration was fitted to the complete standardized customer feature dataset using:

- Number of clusters: 5
- Random seed: 42
- Maximum iterations: 30
- Tolerance: 0.01
- Initialization: k-means||
- Initialization steps: 2

The resulting model assigned all 3,022,290 customers to exactly one cluster.

## 7. Customer Segment Profiles

The following names are descriptive interpretations of the observed cluster averages.

| Cluster | Customers | Share | Provisional interpretation |
|---:|---:|---:|---|
| 0 | 176,050 | 5.83% | High-Intent Buyers |
| 1 | 870,347 | 28.80% | One-Event Visitors |
| 2 | 1,032,095 | 34.15% | Light Browsers |
| 3 | 257,614 | 8.52% | Highly Engaged Explorers |
| 4 | 686,184 | 22.70% | Moderate Engagement Browsers |

### Cluster 0 — High-Intent Buyers

This segment has the strongest observed purchase activity. Customers averaged 2.065 purchases, 2.409 carts, and 2.43 sessions. The average purchase-to-view ratio was 0.2808, and the average session-level purchase ratio was 0.7124.

These behaviors suggest relatively strong purchase intent within the observation period.

### Cluster 1 — One-Event Visitors

Customers averaged 1.26 events, 1.26 views, and 0 purchases. Average session duration was only 0.86 seconds.

This segment represents extremely limited observed engagement. Possible explanations include brief visits, incomplete sessions, or low engagement; the available data does not establish the reason.

### Cluster 2 — Light Browsers

Customers averaged 4.52 events and 4.47 views, with only 0.038 carts and 0.011 purchases on average.

This group exhibits relatively light browsing and very limited purchase activity during the observation period.

### Cluster 3 — Highly Engaged Explorers

This segment averaged 10.22 sessions, 80.83 events, 78.14 views, and 39.88 distinct products. Customers were active on an average of 7.14 days.

The high activity and product exploration distinguish this segment. Its average of 1.205 purchases also indicates that it includes customers with observed purchasing activity, although engagement alone does not establish future purchase behavior.

### Cluster 4 — Moderate Engagement Browsers

Customers averaged 3.24 sessions, 19.28 events, and 11.87 distinct products. Average purchases were 0.083 per customer.

This segment shows more browsing activity than the light-browser group but comparatively limited cart and purchase activity.

## 8. Persisted Gold Tables

The following Unity Catalog tables were created and verified:

| Table | Rows | Purpose |
|---|---:|---|
| `ecommerce_intelligence.gold.customer_behavior_features` | 3,022,290 | Customer-level behavioral features |
| `ecommerce_intelligence.gold.customer_segment_assignments` | 3,022,290 | Customer-to-cluster assignments |
| `ecommerce_intelligence.gold.customer_segment_profiles` | 5 | Aggregate cluster profiles |

Validation confirmed that the assignment table contains 3,022,290 distinct customers, with no duplicate customer assignments and no missing cluster labels.

## 9. MLflow Tracking and Model Persistence

The segmentation experiment was tracked in:

- Experiment: `/Shared/ecommerce-customer-intelligence-m8`
- Experiment ID: `3103039662743480`
- Run ID: `6057fbc453474f58b6ed7b062fbe1997`
- Run name: `customer_behavioral_segmentation_k5_artifacts`

The run logged the fitted StandardScaler, fitted K-Means model, and segmentation metadata. Model artifacts were successfully loaded from MLflow and tested against a small customer sample.

The smoke test generated cluster assignments successfully, and the MLflow run status was `FINISHED`.

The models were logged without inferred signatures because MLflow's signature inference did not complete successfully. The saved models' loading and prediction smoke test nevertheless passed.

## 10. Limitations and Interpretation

1. **Limited observation period:** The segments represent behavior observed in October 2019 and may not reflect long-term preferences.
2. **Descriptive rather than causal:** Clusters describe patterns; they do not explain why customers behave this way.
3. **Candidate selection:** k = 5 had the best silhouette score among the tested candidates, but other feature sets or clustering methods may produce different results.
4. **Cluster identifiers:** Cluster numbers are arbitrary identifiers, not an ordering of customer value.
5. **Unusual short sessions:** The very short average session duration in cluster 1 warrants cautious interpretation.
6. **Future validation:** Segment stability, business usefulness, and performance on later time periods have not been established by this milestone.

## 11. Milestone Outcome

M8 established an end-to-end customer segmentation workflow using Spark ML and Databricks:

- Customer-level behavioral features engineered at full scale
- Four candidate cluster counts evaluated
- Five-cluster solution selected and fitted
- All 3,022,290 customers assigned
- Five cluster profiles persisted
- MLflow artifacts logged, reloaded, and smoke-tested
- Gold table integrity checks passed

The resulting segment assignments can serve as an analytical foundation for subsequent customer intelligence and recommendation work.
