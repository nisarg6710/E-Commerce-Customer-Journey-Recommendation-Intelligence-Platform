# M13 — Multi-Product Recommendation Intelligence

## 1. Objective

Extend the M9–M12 recommendation baselines by using multiple products from a customer's recent browsing context rather than relying only on the last viewed product.

Three approaches were evaluated:

1. Multi-product co-occurrence recommendations
2. Multi-product sequential recommendations
3. Multi-product hybrid recommendations using Reciprocal Rank Fusion (RRF)

The objective was to determine whether multi-product context improves the prediction of future purchase targets.

## 2. Architecture

The implementation runs in Databricks using PySpark and Unity Catalog-managed Delta tables.

**Architecture flow:**

`Silver clickstream events → temporal context and purchase targets → multi-product candidate generation → recommendation ranking → offline evaluation → Gold Delta tables`

### Context and evaluation windows

- Training period: October 1–24, 2019
- Customer context: October 25–28, 2019
- Future purchase targets: October 29–31, 2019
- Context strategy: Up to 10 distinct recently viewed products per eligible user
- Evaluation cutoff: Top 10 recommendations
- Eligible cohort: 16,828 users

The cohort was verified against the existing M12 evaluation protocol.

## 3. Data preparation

The context analysis identified 16,828 eligible users.

Before limiting the context to the 10 most recent distinct products:

- Mean distinct context products per user: 8.45
- Median: 4
- 90th percentile: 20
- Users with at least 5 distinct context products: 7,750
- Users with at least 10 distinct context products: 4,203

After selecting up to 10 distinct recent products, the context contained 84,412 user-product rows, with a mean of approximately 5.02 products per user.

## 4. Recommendation strategies

### 4.1 Multi-product co-occurrence

For every product in a user's recent context, retrieve products associated with it in the training-only co-occurrence model. Aggregate candidate support across context products, then rank candidates to produce up to 10 recommendations per user.

Results:
- Recommendation rows: 167,323
- Users receiving recommendations: 16,782
- Distinct recommended products: 17,194

### 4.2 Multi-product sequential

Use the recent product context to retrieve candidates from the sequential transition model, aggregate candidate scores across the context, and produce up to 10 recommendations.

Results:
- Recommendation rows: 165,154
- Users receiving recommendations: 16,702
- Distinct recommended products: 21,090

### 4.3 Multi-product hybrid using RRF

Combine co-occurrence and sequential candidates using Reciprocal Rank Fusion. Candidates available from both models can benefit from evidence across both rankings; model-specific candidates remain eligible.

Results:
- Recommendation rows: 167,325
- Users receiving recommendations: 16,782
- Distinct recommended products: 19,577

Candidate source distribution:
- Co-occurrence only: 35,202
- Sequential only: 26,810
- Both models: 105,313

## 5. Evaluation methodology

Each model was evaluated on the same 16,828 eligible users and the same future purchase targets.

Metrics:

- **Mean user Recall@10:** For each user, the fraction of distinct future purchase targets appearing in the top-10 recommendation set, averaged across users.
- **Hit rate@10:** Fraction of eligible users with at least one future purchase target in the recommendations.
- **Total hits:** Sum of matched distinct purchase targets across users.
- **Recommendation availability:** Fraction of eligible users receiving at least one recommendation.

This is a temporal offline evaluation. It measures predictive performance on the specified October 2019 windows; it does not establish causal impact on purchases or online business performance.

## 6. Results

| Model | Mean Recall@10 | Hit rate@10 | Total hits | Availability |
|---|---:|---:|---:|---:|
| Multi-product co-occurrence | **0.17130** | **0.20478** | **3,807** | 99.73% |
| Multi-product hybrid RRF | 0.16541 | 0.19794 | 3,667 | 99.73% |
| Multi-product sequential | 0.15618 | 0.18701 | 3,428 | 99.25% |

### Interpretation

Multi-product co-occurrence achieved the highest Recall@10 and hit rate among the three M13 approaches.

The hybrid improved on sequential recommendations alone but did not outperform co-occurrence. Its Recall@10 was approximately 3.44% lower than the co-occurrence result on a relative basis.

The sequential approach had the lowest recall and hit rate, although it still provided recommendations to approximately 99.25% of eligible users.

The experiment therefore does not support choosing the hybrid solely because it combines two models. On this evaluation cohort, co-occurrence is the strongest M13 candidate under the primary Recall@10 metric.

## 7. Persisted outputs

### Aggregate evaluation

`ecommerce_intelligence.gold.multi_product_recommendation_evaluation`

- Verified rows: 3
- One row per M13 recommendation strategy

### User-level evaluation

`ecommerce_intelligence.gold.multi_product_recommendation_user_evaluation`

- Verified rows: 50,484
- 16,828 users × 3 models

Both tables were successfully written and verified in Databricks.

## 8. Limitations and next steps

- The experiment uses a single month of historical clickstream data.
- Results may vary across different dates, product categories, and customer populations.
- Offline recall and hit rate do not directly measure revenue, conversion lift, or user satisfaction.
- The RRF hybrid did not improve the primary metric over multi-product co-occurrence.
- Further work should investigate ranking weights, category-aware filtering, repeat-purchase suppression, and temporal validation on additional periods if data becomes available.

**Current recommendation:** Retain multi-product co-occurrence as the best-performing M13 strategy under the current offline evaluation protocol. Preserve the sequential and hybrid results as comparison baselines.
