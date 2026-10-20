# M12 — Standardized Recommendation Evaluation

## 1. Objective

M12 establishes a standardized offline evaluation protocol for the recommendation models developed in M9–M11. Its purpose is to compare session co-occurrence, sequential transitions, purchase popularity, and reciprocal rank fusion (RRF) using the same user context, evaluation cohort, target window, and top-10 recommendation limit.

## 2. Architecture and Data Sources

The milestone uses the existing Databricks Medallion architecture.

**Silver source**
- `ecommerce_intelligence.silver.sessionized_clickstream_events`

**Gold model inputs**
- `ecommerce_intelligence.gold.product_cooccurrence_recommendations_train_oct2019`
- `ecommerce_intelligence.gold.sequential_product_recommendations_train_oct2019`
- `ecommerce_intelligence.gold.product_popularity_train_oct2019`

**Gold evaluation outputs**
- `ecommerce_intelligence.gold.standardized_recommendation_evaluation`
- `ecommerce_intelligence.gold.standardized_recommendation_user_evaluation`

PySpark constructs recommendation sets, joins them with future purchase targets, calculates user-level metrics, and persists aggregate and per-user results as Delta tables in Unity Catalog.

## 3. Evaluation Protocol

The evaluation uses a temporal split:

| Window | Dates |
|---|---|
| Training | October 1–24, 2019 |
| Context | October 25–28, 2019 |
| Purchase targets | October 29–31, 2019 |

For personalized models, the context is represented by each user's most recently viewed product. Ties are resolved deterministically using event time, derived session ID, and product ID.

The eligible cohort consists of users who have at least one valid product view in the context window and at least one distinct product purchased in the target window.

### Cohort verification

| Metric | Result |
|---|---:|
| Users with context views | 667,222 |
| Users with target purchases | 40,588 |
| Eligible users | 16,828 |
| Average distinct target products per eligible user | 1.34995 |

The same 16,828 eligible users are evaluated for every model.

## 4. Recommendation Strategies

### 4.1 Session co-occurrence

Uses training-only product co-occurrence recommendations. For each eligible user, the model looks up recommendations associated with their last viewed product and retains up to 10 candidates.

### 4.2 Sequential transition

Uses training-only directed product-transition recommendations. The last viewed product acts as the source product for next-product suggestions.

### 4.3 Purchase popularity

Uses the top 10 products ranked by training-period purchase popularity. The same 10 products are recommended to every eligible user.

### 4.4 RRF hybrid

Combines co-occurrence and sequential rankings with reciprocal rank fusion:

`RRF = 1 / (60 + co-occurrence rank) + 1 / (60 + sequential rank)`

A missing source rank contributes zero. Candidates are sorted by the combined score and limited to the top 10 per source product.

## 5. Metrics

- **Mean user Recall@10:** For each user, the number of distinct recommended products appearing in the target purchase set divided by the number of distinct target products. The metric is averaged across eligible users.
- **Hit rate@10:** Fraction of eligible users with at least one recommended product appearing in their target purchase set.
- **Total hits:** Sum of matched recommended products across users.
- **Recommendation availability:** Fraction of eligible users receiving at least one recommendation.
- **Distinct recommended products:** Number of unique products appearing across the recommendation sets.
- **Catalog coverage:** Distinct recommended products divided by the full observed product catalog of 166,794 products.

The evaluation retains users with no personalized recommendations, assigning them zero hits. Popularity supplies 10 recommendations to every eligible user.

## 6. Standardized Results

| Model | Mean user Recall@10 | Hit rate@10 | Total hits | Availability | Distinct products | Catalog coverage |
|---|---:|---:|---:|---:|---:|---:|
| Purchase popularity | 0.152013 | 0.183147 | 3,463 | 100.00% | 10 | 0.0060% |
| Session co-occurrence | 0.150534 | 0.180354 | 3,322 | 98.12% | 18,416 | 11.0412% |
| RRF hybrid | 0.146916 | 0.176373 | 3,221 | 98.13% | 21,036 | 12.6120% |
| Sequential transition | 0.132323 | 0.160269 | 2,905 | 95.48% | 19,213 | 11.5190% |

Each model has exactly 16,828 user-level evaluation rows. The aggregate table contains four rows, and the user-level table contains 67,312 rows.

## 7. Findings

### 7.1 Popularity has the strongest relevance metrics

Purchase popularity achieved the highest mean user Recall@10 (15.20%) and hit rate@10 (18.31%) under this protocol. It also provides 100% recommendation availability.

Its catalog coverage is extremely low because every user receives the same 10 products. The result reflects strong global product demand, not personalization.

### 7.2 Co-occurrence is competitive and more diverse

Session co-occurrence achieved 15.05% mean user Recall@10 and 18.04% hit rate@10. Its relevance metrics are close to popularity, while it covers 18,416 distinct products and provides recommendations to approximately 98.12% of eligible users.

### 7.3 RRF increases coverage but not relevance

RRF has the largest catalog coverage at 12.61%, covering 21,036 distinct recommended products. However, its Recall@10 and hit rate are lower than both popularity and co-occurrence. Combining rankings did not improve these relevance metrics in this experiment.

### 7.4 Sequential transitions are weaker under this protocol

Sequential transitions achieved 13.23% Recall@10 and 16.03% hit rate@10, with 95.48% recommendation availability. The method covers 19,213 distinct products but does not match the other strategies on the primary relevance metrics.

## 8. Relationship to M9–M11

The original M9 co-occurrence evaluation reported 20.64% mean user Recall@10. That evaluation used a different recommendation-context strategy, aggregating evidence from multiple viewed products rather than relying solely on the last viewed product.

Consequently, the original M9 result must not be compared directly with the M12 standardized results as though the input conditions were identical.

M12 provides the more appropriate comparison among the four models evaluated here because the cohort, context representation, target window, and top-10 limit are aligned.

## 9. Limitations

1. The dataset represents October 2019 and does not establish performance on current shopping behavior.
2. The evaluation is offline and does not demonstrate causal lift, online conversion improvement, or revenue impact.
3. The last-viewed-product context discards information from earlier products viewed by the same user.
4. Catalog coverage measures diversity across recommendations, not recommendation relevance.
5. Popularity is a global baseline rather than a personalized recommendation method.
6. The current results do not establish whether alternative RRF parameters or multi-product context aggregation would improve performance.

## 10. Recommended Next Steps

1. Evaluate multi-product context aggregation under the same temporal split.
2. Test a co-occurrence model that aggregates evidence from all context products and compare it with the last-viewed-product variant.
3. Evaluate NDCG@10 and additional ranking metrics alongside Recall@10 and hit rate.
4. Examine performance by customer segment and product popularity.
5. Keep popularity as a strong global fallback and co-occurrence as a competitive personalized candidate source until further experiments establish a better strategy.

## 11. Verification and Status

The following tables were persisted and verified:

- `ecommerce_intelligence.gold.standardized_recommendation_evaluation`: 4 rows.
- `ecommerce_intelligence.gold.standardized_recommendation_user_evaluation`: 67,312 rows.

**M12 standardized evaluation: complete.**

The next recommended milestone is M13, focused on multi-product context aggregation and stronger personalized recommendation evaluation.