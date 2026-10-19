# M10 — Sequential Product Recommendation

## 1. Objective

M10 implements a sequential product recommendation baseline for the E-Commerce Customer Journey & Recommendation Intelligence Platform.

The objective is to predict products a customer may purchase based on the last product they viewed, using historical product-to-product transitions learned from clickstream sessions.

The model is evaluated against the co-occurrence and purchase-popularity baselines developed in M9.

## 2. Architecture

The implementation follows the existing Medallion architecture:

- **Silver:** `ecommerce_intelligence.silver.sessionized_clickstream_events`
- **Gold training model:** `ecommerce_intelligence.gold.sequential_product_recommendations_train_oct2019`
- **Gold user-level evaluation:** `ecommerce_intelligence.gold.sequential_recommendation_user_evaluation`
- **Gold aggregate evaluation:** `ecommerce_intelligence.gold.sequential_recommendation_evaluation`

PySpark performs session-level sequence construction, transition aggregation, recommendation ranking, and offline evaluation. Delta tables persist the outputs in Unity Catalog.

## 3. Training Data and Sequence Construction

Training period: October 1–24, 2019.

The pipeline selects valid product-view events with non-null session IDs, product IDs, and event timestamps.

Events are ordered within each derived session by event timestamp, with product ID used as a deterministic tie-breaker. Consecutive repeated views of the same product are removed before generating transitions.

| Metric | Result |
|---|---:|
| Raw training view events | 31,991,157 |
| Events after consecutive-repeat removal | 23,919,085 |
| Adjacent transition observations | 17,811,983 |
| Supported directed transitions (support ≥ 3 sessions) | 891,017 |
| Distinct source products with supported transitions | 59,905 |

The average sequence length after consecutive-repeat removal was approximately 3.92 products, with a median of 2.

## 4. Transition Model

For each session, adjacent product pairs are extracted to form directed transitions:

`Product A → Product B`

Transition support is calculated as the number of distinct sessions containing the directed pair. Transitions supported by fewer than three sessions are excluded.

For each source product, candidate next products are ranked by supporting-session count in descending order. Product ID provides deterministic tie-breaking.

The top 10 candidates per source product are retained.

### Persisted Model Statistics

| Metric | Result |
|---|---:|
| Recommendation rows | 317,487 |
| Source products | 59,905 |
| Maximum recommendations per source product | 10 |
| Training window | October 1–24, 2019 |

The model is a frequency-based sequential transition recommender, not a neural sequence model.

## 5. Temporal Evaluation Design

The evaluation uses the same eligible customer cohort and time windows as M9.

- **Training:** October 1–24, 2019
- **Context:** October 25–28, 2019
- **Target:** October 29–31, 2019
- **Eligible users:** 16,828

For each eligible user, the most recently viewed product during the context window is selected. The model returns up to 10 products associated with that source product in the training transition table.

The target set consists of distinct products purchased by that user during the target window.

Users without a matching source-product transition remain in the evaluation and receive zero hits. This avoids evaluating only users for whom recommendations are available.

### Metrics

- **Mean user Recall@10:** Per-user hits divided by distinct target products, averaged over all eligible users.
- **Hit rate@10:** Fraction of eligible users with at least one target product in their recommendations.
- **Total hits:** Sum of matched recommended products across users.
- **Catalog coverage:** Distinct recommended products divided by the full observed product catalog.

## 6. Evaluation Results

| Metric | Sequential model |
|---|---:|
| Eligible users | 16,828 |
| Mean user Recall@10 | 0.132323 |
| Hit rate@10 | 0.160269 |
| Total hits | 2,905 |
| Users receiving recommendations | 16,067 |
| Users without recommendations | 761 |
| Recommendation availability | 95.48% |
| Distinct products recommended | 19,213 |
| Full observed product catalog | 166,794 |
| Catalog coverage | 11.519% |

The user-level evaluation contains 16,828 rows. The aggregate evaluation contains one row for the sequential model and its evaluation-window metadata.

## 7. Comparison with M9

The models use the same 16,828 eligible users and the same context and target windows.

| Metric | Session co-occurrence | Purchase popularity | Sequential transition |
|---|---:|---:|---:|
| Mean user Recall@10 | 0.206393 | 0.152013 | 0.132323 |
| Hit rate@10 | 0.243285 | 0.183147 | 0.160269 |
| Total hits | 4,559 | 3,463 | 2,905 |
| Users receiving recommendations | 16,782 | 16,828 | 16,067 |

The sequential transition model does not outperform either M9 baseline on Recall@10 or hit rate@10 in this experiment.

Compared with session co-occurrence, sequential Recall@10 is approximately 35.9% lower, and hit rate@10 is approximately 34.1% lower.

This is a descriptive offline comparison, not evidence of causal business impact.

## 8. Interpretation

The sequential model uses only the user's last viewed product in the context window. It therefore has less information about the user's browsing behavior than the co-occurrence baseline, which can aggregate recommendation evidence from multiple viewed products.

The sequential model also returns no recommendations for 761 eligible users because their last viewed products have no matching supported transition in the training model.

These factors are plausible explanations for the observed results; they have not been independently established through ablation experiments.

## 9. Limitations

1. **Single context product:** Only the most recently viewed product is used for inference.
2. **Timestamp ties:** Product ID provides deterministic ordering when events share a timestamp, but this does not establish their true chronological order.
3. **Popularity bias:** Ranking by transition support favors frequent product transitions.
4. **Sparse transitions:** Source products without a supported transition produce no recommendations.
5. **Historical scope:** The dataset covers October 2019 only; results may not generalize to current e-commerce behavior.
6. **Offline evaluation:** Purchase matching does not demonstrate causal lift, incremental revenue, or online recommendation effectiveness.
7. **No advanced sequence architecture:** The current model is a transition-frequency baseline rather than a learned neural sequential recommender.

## 10. Recommended Next Improvements

1. Combine sequential transitions with co-occurrence and popularity as fallback strategies.
2. Use a longer browsing context instead of only the last viewed product.
3. Experiment with recency-weighted transition scores.
4. Compare Recall@K, NDCG@K, and catalog coverage at multiple values of K.
5. Evaluate performance by customer segment and activity level.
6. Consider advanced sequential models only after establishing stronger baselines and evaluation controls.

## 11. Verification

The following Gold tables were verified after persistence:

- `ecommerce_intelligence.gold.sequential_product_recommendations_train_oct2019` — 317,487 rows.
- `ecommerce_intelligence.gold.sequential_recommendation_user_evaluation` — 16,828 rows.
- `ecommerce_intelligence.gold.sequential_recommendation_evaluation` — 1 row.

## 12. Milestone Status

**M10 core implementation and offline evaluation: complete.**

The sequential baseline is implemented, persisted, evaluated, and compared with M9. Its performance limitations are documented, and the results provide a foundation for hybrid recommendation strategies and subsequent improvements.