# M14 — Context-Aware Recommendation Evaluation

## 1. Objective

This milestone evaluates whether recommendation performance varies with the amount of product context available for a customer. It compares three multi-product recommendation strategies across five customer context-size groups.

The goal is to identify which recommendation approach performs best for different browsing-context sizes and translate the results into actionable business insights.

## 2. Data and Evaluation Design

**Dataset:** October 2019 e-commerce clickstream dataset.

| Parameter | Value |
|---|---|
| Eligible evaluation users | 16,828 |
| Context window | October 25–28, 2019 |
| Purchase evaluation window | October 29–31, 2019 |
| Recommendation cutoff | Top 10 products |
| Context definition | Number of distinct products viewed by a user |
| Evaluation models | Multi-product co-occurrence, multi-product sequential, multi-product hybrid RRF |

The evaluation uses the existing M13 user-level evaluation results. Each user's context size was reconstructed from the sessionized clickstream events by counting distinct products viewed during the context window.

The reconstructed context counts were joined to the M13 user-level evaluation table. All 16,828 eligible users matched successfully, giving 100% context reconstruction coverage.

## 3. Context-Size Segmentation

Users were divided into five mutually exclusive groups according to the number of distinct products viewed during the context window.

| Context group | Users | Share of cohort | Average distinct viewed products |
|---|---:|---:|---:|
| 1 product | 3,556 | 21.1% | 1.00 |
| 2–3 products | 4,183 | 24.9% | 2.41 |
| 4–5 products | 2,360 | 14.0% | 4.43 |
| 6–10 products | 2,947 | 17.5% | 7.63 |
| 11+ products | 3,782 | 22.5% | 25.29 |
| **Total** | **16,828** | **100%** | — |

The 11+ group has a maximum of 326 distinct viewed products, indicating substantial variation in browsing intensity within that segment.

## 4. Evaluation Metrics

- **Mean Recall@10:** For each user, the number of future purchased products recovered in the top 10 recommendations divided by the number of distinct target products; averaged across users.
- **Hit rate:** Fraction of users for whom at least one target product appears in the top 10 recommendations.
- **Recommendation availability:** Fraction of users for whom the model returned at least one recommendation.
- **Total hits:** Sum of matched target-product counts across users.
- **Average target products:** Mean number of distinct purchased target products per user during the evaluation window.

Recall@10 measures target-product recovery, while hit rate measures whether the recommendation list recovers at least one target product. These metrics are complementary and should not be treated as interchangeable.

## 5. Results

### 5.1 Mean Recall@10 by Context Size

| Context group | Multi-product co-occurrence | Multi-product hybrid RRF | Multi-product sequential |
|---|---:|---:|---:|
| 1 product | **0.1522** | 0.1503 | 0.1363 |
| 2–3 products | **0.1492** | 0.1426 | 0.1360 |
| 4–5 products | **0.2189** | 0.2079 | 0.1977 |
| 6–10 products | **0.1990** | 0.1901 | 0.1814 |
| 11+ products | **0.1624** | 0.1590 | 0.1516 |

### 5.2 Hit Rate by Context Size

| Context group | Multi-product co-occurrence | Multi-product hybrid RRF | Multi-product sequential |
|---|---:|---:|---:|
| 1 product | **0.1803** | 0.1769 | 0.1614 |
| 2–3 products | **0.1750** | 0.1676 | 0.1590 |
| 4–5 products | **0.2551** | 0.2441 | 0.2322 |
| 6–10 products | **0.2392** | 0.2297 | 0.2195 |
| 11+ products | **0.2025** | 0.1978 | 0.1885 |

### 5.3 Recommendation Availability

| Context group | Co-occurrence | Hybrid RRF | Sequential |
|---|---:|---:|---:|
| 1 product | 0.9896 | 0.9896 | 0.9716 |
| 2–3 products | 0.9981 | 0.9981 | 0.9952 |
| 4–5 products | 0.9996 | 0.9996 | 0.9996 |
| 6–10 products | 1.0000 | 1.0000 | 0.9997 |
| 11+ products | 1.0000 | 1.0000 | 0.9992 |

## 6. Key Findings

### Finding 1 — Co-occurrence performs best across all context groups

Multi-product co-occurrence achieves the highest Recall@10 and hit rate in each of the five context-size groups. Under the current offline evaluation, it is the strongest of the three tested strategies.

### Finding 2 — The 4–5 product group has the strongest recommendation performance

The 4–5 product segment achieves Recall@10 of **0.2189** and a hit rate of **0.2551** with co-occurrence recommendations. This is the strongest performance observed among the five segments.

### Finding 3 — More context does not guarantee better recommendations

Performance does not increase monotonically with context size. Recall peaks in the 4–5 group, remains relatively high in the 6–10 group, and declines in the 11+ group.

A possible explanation is that a moderate browsing history provides useful preference signals, whereas very large histories can include less relevant or more diverse interests. This is a hypothesis suggested by the observed pattern, not a proven causal explanation.

### Finding 4 — Hybrid RRF does not outperform co-occurrence

The hybrid model combines co-occurrence and sequential recommendation signals using reciprocal-rank fusion. However, it does not outperform multi-product co-occurrence in any context group.

This suggests that combining models does not automatically improve recommendations. The fusion strategy, relative signal quality, and candidate ranking require further investigation.

### Finding 5 — Sequential recommendations trail the other strategies

Multi-product sequential recommendations have the lowest Recall@10 and hit rate in every context group. Sequence information may still provide useful complementary signals, but the tested sequential strategy does not lead on these metrics.

### Finding 6 — Recommendation availability is high

Availability ranges from 0.9716 to 1.0000 across the groups and models. Thus, recommendation absence is limited and is unlikely to explain the overall ranking of model performance by itself.

## 7. Business Implications

1. **Use co-occurrence as the leading offline baseline.** It consistently outperforms the tested hybrid and sequential strategies on Recall@10 and hit rate.
2. **Evaluate moderate-context customers carefully.** Users with 4–5 distinct viewed products show the strongest observed recommendation performance. This group is a useful segment for further experiments.
3. **Investigate large browsing histories.** Customers viewing 11 or more distinct products may benefit from context filtering, recency weighting, category-aware ranking, or intent-based diversification.
4. **Treat sequential signals as a potential enhancement.** Test alternative fusion weights and candidate-generation approaches before including sequential recommendations in production.
5. **Validate with online experiments.** Offline purchase recovery does not establish that recommendations cause more purchases, revenue, or customer engagement.

## 8. Gold Output

The cohort-level metrics are persisted in Unity Catalog:

`ecommerce_intelligence.gold.context_aware_recommendation_evaluation`

The table contains **15 rows**, representing five context-size groups across three recommendation models.

Persisted fields include:

- `context_size_group`
- `model_name`
- `users`
- `mean_recall_at_10`
- `hit_rate`
- `recommendation_availability`
- `avg_target_products`
- `total_hits`
- `evaluation_period`
- `context_period`
- `evaluation_k`

The evaluation uses \(k=10\), context dates October 25–28, 2019, and purchase evaluation dates October 29–31, 2019.

## 9. Limitations

- The analysis covers one month of historical clickstream data, with a short context and evaluation window.
- Results reflect the selected cohort and the specific model implementations evaluated in M13.
- The context groups are observational segments, not randomized experimental groups.
- The explanation that very large contexts contain noisier signals is a hypothesis and has not been directly tested.
- Recall@10 and hit rate do not measure revenue, profit, diversity, novelty, customer satisfaction, or long-term engagement.
- The evaluation does not establish causal business impact.
- The reported metrics should be revalidated on additional time periods and, where possible, through online A/B testing.

## 10. Conclusion

M14 establishes a context-aware evaluation framework for multi-product recommendations. Across all five browsing-context groups, multi-product co-occurrence leads the tested hybrid RRF and sequential strategies on Recall@10 and hit rate. Performance is strongest for users with 4–5 distinct viewed products and declines for the largest context group.

These results support co-occurrence as the leading offline baseline for the current project, while motivating further work on context filtering, sequential-signal fusion, temporal validation, and business-impact measurement.
