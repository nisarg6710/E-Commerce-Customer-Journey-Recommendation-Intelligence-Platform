# M9 — Product Recommendation Baseline

## 1. Objective

M9 establishes a product recommendation baseline using the October 2019 e-commerce clickstream dataset. The goal is to recommend related products based on observed session behavior and compare the approach with a simple purchase-popularity baseline.

The milestone includes session-level product co-occurrence, ranked recommendations, Delta persistence, and a temporal offline evaluation.

## 2. Data Sources

The primary source is:

`ecommerce_intelligence.silver.sessionized_clickstream_events`

The source contains 42,448,764 events across three event types:

- Views: 40,779,399
- Carts: 926,516
- Purchases: 742,849

The dataset covers October 1–31, 2019. Recommendation analysis uses customer IDs, product IDs, event types, timestamps, and derived session IDs.

The derived session identifier is used instead of the original source session identifier because sessionization applies a 30-minute inactivity threshold.

## 3. Initial Data Analysis

The usable interaction dataset contained 42,448,764 events.

Session-level product diversity was:

- Derived sessions: 7,796,425
- Average distinct products per session: 3.48
- Median distinct products per session: 2
- 90th percentile: 8 products
- Maximum: 979 products

Each derived session was associated with exactly one distinct user in the validation performed.

## 4. Session-Based Co-Occurrence Baseline

### 4.1 Session-product preparation

Only product views were used to create the initial co-occurrence baseline. Repeated views of the same product within a session were deduplicated.

To control pair-generation cost, sessions were capped at 20 distinct products. Products were selected deterministically by earliest observed view timestamp, with product ID as a tie-breaker.

| Metric | Result |
|---|---:|
| Distinct session-product view rows before cap | 27,156,197 |
| Rows after cap | 25,950,000 |
| Sessions exceeding the cap | 111,189 |

The cap removes some products from unusually large sessions and can omit products viewed later in those sessions.

### 4.2 Pair generation

Unordered product pairs were generated from products appearing in the same derived session. Pair support was measured by the number of distinct sessions containing both products.

Only pairs supported by at least three sessions were retained.

| Metric | Result |
|---|---:|
| Generated session-product pair rows | 86,717,843 |
| Retained supported product pairs | 4,205,897 |

The pairs were converted into bidirectional recommendations and ranked by raw co-occurrence session counts. The top 10 recommendations were retained for each source product.

### 4.3 Full-period recommendation output

The full-October baseline was persisted to:

`ecommerce_intelligence.gold.product_cooccurrence_recommendations`

| Metric | Result |
|---|---:|
| Recommendation rows | 826,476 |
| Source products with recommendations | 106,212 |

Example: source product `1004767` received `1004856` as its highest-ranked recommendation, supported by 35,380 co-occurrence sessions.

This full-period table is descriptive and must not be used as a leakage-free test artifact because it includes observations from the entire month.

## 5. Purchase-Popularity Baseline

A popularity baseline was built by counting purchase events per product and ranking products by purchase-event count, with product ID as a deterministic tie-breaker.

The full-period top 100 were persisted to:

`ecommerce_intelligence.gold.product_popularity_recommendations`

For the temporal evaluation, a separate training-only top-100 popularity table was created:

`ecommerce_intelligence.gold.product_popularity_train_oct2019`

It uses purchase events from October 1–24 only.

## 6. Temporal Evaluation Design

The training period was October 1–24, 2019. The original temporal split contained:

| Event type | Training | Test |
|---|---:|---:|
| Views | 31,991,157 | 8,788,242 |
| Carts | 751,582 | 174,934 |
| Purchases | 590,462 | 152,387 |
| Total events | 33,333,201 | 9,115,563 |

The refined evaluation used an earlier context window and a later target window:

- **Training data:** October 1–24
- **Context views:** October 25–28
- **Purchase targets:** October 29–31

Users were eligible when they had both context views and at least one distinct purchase target in the later target window.

The evaluation cohort contained 16,828 eligible users and 22,717 distinct user-product purchase targets.

This is a conditional offline evaluation of later purchases given earlier browsing context. It is not a live recommendation experiment and does not establish that recommendations cause purchases.

## 7. Evaluation Methodology

The co-occurrence model was rebuilt using training-period views only. The same 20-product session cap and minimum support threshold of three sessions were applied.

Training-only co-occurrence results:

| Metric | Result |
|---|---:|
| Capped session-product rows | 20,393,844 |
| Supported product pairs | 3,369,042 |
| Ranked recommendation rows | 736,139 |
| Source products with recommendations | 96,688 |

For each eligible user, recommendations were generated from products viewed in the October 25–28 context window. Candidate scores were aggregated across the user's viewed source products and ranked, retaining up to 10 unique recommended products.

The popularity model returned the same top 10 training-period purchase-popularity products to every eligible user.

Mean user Recall@10 was calculated as the number of distinct target products recovered in the recommendation list divided by the user's number of distinct purchase targets. Hit rate@10 is the fraction of eligible users with at least one recovered target product.

## 8. Evaluation Results

| Metric | Session co-occurrence | Purchase popularity |
|---|---:|---:|
| Eligible users | 16,828 | 16,828 |
| Mean user Recall@10 | 0.2064 | 0.1520 |
| Hit rate@10 | 0.2433 | 0.1831 |
| Total hits | 4,559 | 3,463 |
| Catalog coverage | 10,860 | 10 |

On this evaluation cohort, session co-occurrence achieved approximately 35.8% higher relative mean Recall@10 and 32.8% higher relative hit rate than the popularity baseline.

The co-occurrence model generated recommendations for 16,782 eligible users. The remaining 46 users had no recommendation candidates and were assigned zero recall. The average recommendation-list size among users with candidates was approximately 9.97, with a minimum of one and a maximum of ten.

Catalog coverage is the number of distinct recommended products appearing across the recommendation lists.

These results support retaining co-occurrence as the stronger initial baseline for this particular evaluation. They do not establish generalization to other periods, customers without observed context, or online business outcomes.

## 9. Persisted Gold Tables

| Table | Purpose |
|---|---|
| `ecommerce_intelligence.gold.product_cooccurrence_recommendations` | Full-period co-occurrence recommendations |
| `ecommerce_intelligence.gold.product_popularity_recommendations` | Full-period top-100 purchase-popularity products |
| `ecommerce_intelligence.gold.product_popularity_train_oct2019` | Training-only popularity baseline |
| `ecommerce_intelligence.gold.recommendation_baseline_evaluation` | Model-level evaluation metrics and temporal-window metadata |
| `ecommerce_intelligence.gold.recommendation_baseline_user_evaluation` | Per-user metrics for both evaluated models |

The model-level evaluation table contains two rows, one for each model. The user-level evaluation table contains 33,656 rows: 16,828 users for each model.

## 10. Limitations

1. **Conditional cohort:** Evaluation includes users with both context views and later purchases, rather than all visitors.
2. **Observed behavior is not causal evidence:** A recovered purchase target does not demonstrate that a recommendation influenced the purchase.
3. **Catalog cold start:** Products without sufficient training-period co-occurrence evidence may not receive recommendations.
4. **Session cap:** The 20-product cap can omit later products in unusually large sessions.
5. **Raw co-occurrence score:** Popularity and session frequency influence the score; normalized association measures have not yet been compared.
6. **Single temporal split:** The evaluation uses one October 2019 context/target split. Results may vary across other periods.
7. **No online experiment:** Latency, click-through rate, conversion lift, and revenue impact have not been measured.
8. **Ranking metrics:** The current evaluation reports Recall@10 and hit rate@10. Ranking-sensitive metrics such as NDCG@10 and MAP@10 have not been evaluated.

## 11. Milestone Outcome

M9 established an end-to-end product recommendation baseline using Spark and Delta Lake:

- Session-product interactions prepared at scale
- Co-occurrence pairs generated and filtered by minimum support
- Full-period top-10 recommendations persisted
- Purchase-popularity baseline established
- Training-only recommenders built for temporal evaluation
- Recall@10, hit rate, and catalog coverage compared
- Model-level and user-level evaluation artifacts persisted

The co-occurrence baseline outperformed the popularity baseline on the current conditional offline evaluation and provides a foundation for the next milestone: sequential recommendation.
