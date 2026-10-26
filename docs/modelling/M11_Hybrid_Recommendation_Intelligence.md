# M11 — Hybrid Recommendation Intelligence

## 1. Objective

M11 evaluates whether combining session co-occurrence recommendations, sequential product transitions, and purchase popularity improves product recommendation quality.

The milestone builds on the M9 co-occurrence and popularity baselines and the M10 sequential transition model. It implements rank fusion and fallback experiments, evaluates them on a consistent temporal cohort, and persists the results in Unity Catalog Gold tables.

## 2. Architecture

The implementation uses the existing Medallion architecture.

### Silver source

- `ecommerce_intelligence.silver.sessionized_clickstream_events`

### Gold model tables

- `ecommerce_intelligence.gold.product_cooccurrence_recommendations_train_oct2019`
- `ecommerce_intelligence.gold.sequential_product_recommendations_train_oct2019`
- `ecommerce_intelligence.gold.product_popularity_train_oct2019`
- `ecommerce_intelligence.gold.hybrid_product_recommendations_train_oct2019`

### Gold evaluation tables

- `ecommerce_intelligence.gold.hybrid_recommendation_user_evaluation`
- `ecommerce_intelligence.gold.hybrid_recommendation_evaluation`
- `ecommerce_intelligence.gold.hybrid_popularity_fallback_user_evaluation`
- `ecommerce_intelligence.gold.hybrid_popularity_fallback_evaluation`

PySpark performs candidate generation, ranking, fallback construction, and offline evaluation. Delta tables persist the outputs in Unity Catalog.

## 3. Training-Only Co-Occurrence Reconstruction

The original co-occurrence recommendation table was trained over the full October dataset, so it was unsuitable for leakage-free evaluation.

M11 reconstructed co-occurrence recommendations using October 1–24 training data only.

The pipeline:
1. Selects valid product-view events from the training window.
2. Deduplicates product views within each derived session.
3. Retains at most the first 20 distinct products per session.
4. Generates unordered product pairs.
5. Counts distinct sessions supporting each pair.
6. Keeps pairs supported by at least three sessions.
7. Creates bidirectional product recommendations and retains the top 10 per source product.

### Reconstructed training statistics

| Metric | Result |
|---|---:|
| Training session-product rows | 20,393,844 |
| Supported unordered pairs | 3,369,042 |
| Directed recommendation rows | 736,139 |
| Source products | 96,688 |
| Maximum rank | 10 |

The reconstructed statistics match the training-only co-occurrence statistics recorded during M9.

## 4. Experiment A — Reciprocal Rank Fusion

The first hybrid combines co-occurrence and sequential rankings using reciprocal rank fusion:

`RRF = 1 / (60 + co-occurrence rank) + 1 / (60 + sequential rank)`

A missing rank contributes zero. Candidates are sorted by combined score, and the top 10 products per source product are retained.

### Persisted model

`ecommerce_intelligence.gold.hybrid_product_recommendations_train_oct2019`

| Metric | Result |
|---|---:|
| Recommendation rows | 736,970 |
| Source products | 96,832 |
| Maximum rank | 10 |
| Average hybrid score | 0.019844 |

### Evaluation

| Metric | Result |
|---|---:|
| Eligible users | 16,828 |
| Mean user Recall@10 | 0.146916 |
| Hit rate@10 | 0.176373 |
| Total hits | 3,221 |
| Users receiving recommendations | 16,513 |
| Distinct recommended products | 21,036 |
| Catalog coverage | 12.612% |

Catalog coverage uses the full observed catalog of 166,794 products as the denominator.

## 5. Experiment B — Co-Occurrence-First Personalized Ranking

The second experiment gives co-occurrence recommendations priority and uses sequential candidates to fill remaining positions.

Candidates are deduplicated by user and product. Co-occurrence candidates rank first, followed by sequential candidates.

### Evaluation

| Metric | Result |
|---|---:|
| Eligible users | 16,828 |
| Mean user Recall@10 | 0.150534 |
| Hit rate@10 | 0.180354 |
| Total hits | 3,322 |
| Users receiving recommendations | 16,513 |
| Distinct recommended products | 74,006 |
| Source products | 96,832 |

**Catalog coverage clarification:** Catalog coverage depends on the recommendation output being measured. The candidate-level distinct-product count and the final evaluation's distinct recommended-product count are not necessarily equivalent. The standardized evaluation should be used for cross-model catalog coverage comparisons.

This experiment does not outperform the original M9 co-occurrence baseline. It also uses only each user's last viewed product, rather than aggregating evidence from all context products as the original M9 user-level evaluation did.

## 6. Experiment C — Popularity Fallback

The third experiment adds training-only purchase popularity as a fallback.

The strategy:
1. Generate personalized candidates using co-occurrence-first ranking with sequential fallback.
2. Identify users with fewer than 10 personalized candidates.
3. Fill remaining positions with products from the top-100 training-only popularity table.
4. Exclude products already recommended to the user.
5. Rank personalized candidates before popularity candidates and retain 10 recommendations per user.

### Persisted evaluation tables

- `ecommerce_intelligence.gold.hybrid_popularity_fallback_user_evaluation`
- `ecommerce_intelligence.gold.hybrid_popularity_fallback_evaluation`

### Evaluation results

| Metric | Result |
|---|---:|
| Eligible users | 16,828 |
| Mean user Recall@10 | 0.152487 |
| Hit rate@10 | 0.182791 |
| Total hits | 3,367 |
| Users receiving recommendations | 16,828 |
| Recommendation rows | 168,280 |
| Distinct recommended products | 18,431 |
| Full catalog size | 166,794 |
| Catalog coverage | 11.050% |

The fallback ensures that every eligible user receives 10 recommendations. However, higher recommendation availability does not guarantee higher relevance.

**Persistence verification**

The aggregate and user-level evaluation tables were successfully written to Unity Catalog Gold and subsequently read back for verification.

| Verification | Result |
|---|---:|
| User-level evaluation rows | 16,828 |
| Distinct evaluated users | 16,828 |
| Aggregate summary rows | 1 |
| Mean user Recall@10 | 0.152487 |
| Hit rate@10 | 0.182791 |
| Total hits | 3,367 |

The persisted evaluation metadata confirms a context window of October 25–28, 2019, and a purchase-target window of October 29–31, 2019. The verified aggregate metrics match the original fallback evaluation.

## 7. Evaluation Protocol

The same temporal protocol was used for the hybrid user-level evaluations:

- **Training:** October 1–24, 2019
- **Context:** October 25–28, 2019
- **Target:** October 29–31, 2019
- **Eligible users:** 16,828

The user's most recently viewed product in the context window is used as the source product. The target set contains distinct products purchased by that user in the target window.

Users without personalized candidates remain in the cohort. For the popularity fallback experiment, popularity recommendations fill missing positions.

### Metrics

- **Mean user Recall@10:** Average of each user's recommendation hits divided by the number of distinct target products.
- **Hit rate@10:** Fraction of eligible users with at least one recommended target product.
- **Total hits:** Sum of matched recommended products across users.
- **Catalog coverage:** Distinct recommended products divided by the full observed product catalog.
- **Recommendation availability:** Fraction of eligible users receiving recommendations.

## 8. Overall Comparison

| Model | Mean user Recall@10 | Hit rate@10 | Total hits | Catalog coverage |
|---|---:|---:|---:|---:|
| M9 session co-occurrence | 0.206393 | 0.243285 | 4,559 | 11.041% |
| M11 hybrid + popularity fallback | 0.152487 | 0.182791 | 3,367 | 11.050% |
| M9 purchase popularity | 0.152013 | 0.183147 | 3,463 | 0.006% |
| M11 RRF hybrid | 0.146916 | 0.176373 | 3,221 | 12.612% |
| M10 sequential transition | 0.132323 | 0.160269 | 2,905 | 11.519% |

Session co-occurrence remains the strongest model on Recall@10 and Hit Rate@10 under the reported results. The RRF hybrid provides the broadest catalog coverage, while the popularity-fallback strategy guarantees recommendation availability for all 16,828 eligible users. These results illustrate a trade-off between relevance, catalog diversity, and recommendation availability. Because the evaluation contexts differ between some experiments, these findings should be interpreted as evidence from the reported experiments rather than a definitive ranking under a fully standardized protocol.

The original M9 co-occurrence evaluation remains the strongest reported result.

The M11 hybrid experiments do not establish an improvement over the co-occurrence baseline. The fallback experiment provides complete recommendation availability, but its Recall@10 remains substantially lower.

## 9. Interpretation and Limitations

1. **Different recommendation contexts:** M9's co-occurrence evaluation aggregates evidence from multiple context products, while the M10/M11 experiments use only the last viewed product. The metrics therefore compare models under different candidate-generation strategies, even though the cohort and time windows match.
2. **Limited sequential contribution:** Sequential transitions add only a small number of candidates beyond co-occurrence in the tested source-product candidate set.
3. **Popularity fallback:** Popularity improves availability but does not establish improved relevance.
4. **Historical data:** The dataset covers October 2019 only.
5. **Offline evaluation:** The metrics do not prove causal lift, incremental revenue, or online effectiveness.
6. **No parameter tuning:** RRF and fallback settings were tested as initial baselines rather than exhaustively optimized.
7. **Catalog coverage:** Coverage uses the full observed product catalog as the denominator and should not be confused with the fraction of target-window purchased products covered.
8. **Fallback strategy distinction:** The co-occurrence-first fallback experiment prioritizes co-occurrence candidates, uses sequential candidates to fill remaining positions, and then uses training-only popularity candidates. This is a different ranking strategy from the RRF hybrid. Its results should therefore be reported separately rather than treated as another evaluation of the same model.

## 10. Recommended Next Steps

1. Standardize the evaluation protocol so all candidate-generation strategies use the same context information.
2. Evaluate co-occurrence recommendations using the same last-viewed-product context as M10/M11.
3. Test multi-product context aggregation for sequential and hybrid models.
4. Compare Recall@K, hit rate@K, NDCG@K, recommendation availability, and catalog coverage.
5. Keep co-occurrence as the strongest current baseline until a comparable experiment demonstrates improvement.
6. Consider learned ranking or more advanced sequence models only after consistent evaluation is established.

## 11. Verification

The following M11 evaluation tables were verified:

- `hybrid_recommendation_user_evaluation`: 16,828 rows.
- `hybrid_recommendation_evaluation`: 1 row.
- `hybrid_popularity_fallback_user_evaluation`: 16,828 rows.
- `hybrid_popularity_fallback_evaluation`: 1 row.

The popularity-fallback evaluation was independently verified after persistence. The aggregate table returned one row, and the user-level table returned 16,828 rows for 16,828 distinct users. The persisted metrics matched the computed evaluation, including Recall@10 of 0.152487, Hit Rate@10 of 0.182791, and 3,367 total hits.

The training-only co-occurrence table, RRF hybrid table, and fallback outputs were persisted in the Gold layer.

## 12. Milestone Status

**M11 implementation and offline experiments: complete.**

Three hybrid strategies were tested and documented. The results support retaining M9 co-occurrence as the strongest current recommendation baseline and improving the evaluation protocol before introducing further model complexity.