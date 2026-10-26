
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from databricks import sql
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="E-Commerce Intelligence",
    page_icon="📊",
    layout="wide",
)

st.title("E-Commerce Customer Journey & Recommendation Intelligence")
st.caption(
    "Executive Overview | October 2019 clickstream analytics"
)


def get_connection():
    hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    token = os.getenv("DATABRICKS_TOKEN")

    if not all([hostname, http_path, token]):
        raise ValueError(
            "Missing Databricks configuration. Check your local .env file."
        )

    return sql.connect(
        server_hostname=hostname,
        http_path=http_path,
        access_token=token,
    )


@st.cache_data(ttl=300)
def load_daily_performance():
    query = """
        SELECT
            event_date,
            total_events,
            active_users,
            source_sessions,
            views,
            carts,
            purchases
        FROM ecommerce_intelligence.gold.daily_performance
        ORDER BY event_date
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]

    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=300)
def load_customer_journey_funnel():
    query = """
        SELECT
            metric_name,
            entity_level,
            metric_count,
            denominator_count,
            rate,
            calculated_at
        FROM ecommerce_intelligence.gold.customer_journey_funnel
        ORDER BY entity_level, metric_name
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]

    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=300)
def load_recommendation_evaluation():
    query = """
        SELECT *
        FROM ecommerce_intelligence.gold.multi_product_recommendation_evaluation
        ORDER BY model_name
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]

    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=300)
def load_context_aware_evaluation():
    query = """
        SELECT
            context_size_group,
            model_name,
            users,
            mean_recall_at_10,
            hit_rate,
            recommendation_availability,
            avg_target_products,
            total_hits,
            evaluation_period,
            context_period,
            evaluation_k
        FROM ecommerce_intelligence.gold.context_aware_recommendation_evaluation
        ORDER BY
            CASE context_size_group
                WHEN '1' THEN 1
                WHEN '2-3' THEN 2
                WHEN '4-5' THEN 3
                WHEN '6-10' THEN 4
                WHEN '11+' THEN 5
                ELSE 6
            END,
            model_name
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]

    return pd.DataFrame(rows, columns=columns)


try:
    with st.spinner("Loading analytics from Databricks..."):
        daily = load_daily_performance()

    if daily.empty:
        st.warning("The daily performance table returned no data.")
        st.stop()

    daily["event_date"] = pd.to_datetime(daily["event_date"])

    total_events = int(daily["total_events"].sum())
    total_views = int(daily["views"].sum())
    total_carts = int(daily["carts"].sum())
    total_purchases = int(daily["purchases"].sum())
    total_sessions = int(daily["source_sessions"].sum())

    st.success("Connected to Databricks Gold tables.")

    # Executive KPIs
    st.subheader("Business Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Events", f"{total_events:,}")
    col2.metric("Views", f"{total_views:,}")
    col3.metric("Carts", f"{total_carts:,}")
    col4.metric("Purchases", f"{total_purchases:,}")
    col5.metric("Session Count Sum", f"{total_sessions:,}")

    st.caption(
        "Session Count Sum is the sum of daily sessions. "
        "Active users are reported as daily counts and should not be "
        "summed to estimate monthly unique customers."
    )

    # Daily trends
    st.subheader("Daily Activity Trends")

    metric_choice = st.selectbox(
        "Choose a metric",
        options=[
            "total_events",
            "active_users",
            "source_sessions",
            "views",
            "carts",
            "purchases",
        ],
        format_func=lambda value: {
            "total_events": "Total Events",
            "active_users": "Daily Active Users",
            "source_sessions": "Daily Sessions",
            "views": "Product Views",
            "carts": "Cart Events",
            "purchases": "Purchase Events",
        }[value],
    )

    chart = px.line(
        daily,
        x="event_date",
        y=metric_choice,
        markers=True,
        title="Daily " + metric_choice.replace("_", " ").title(),
        labels={
            "event_date": "Date",
            metric_choice: "Count",
        },
    )

    chart.update_layout(
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    st.plotly_chart(chart, use_container_width=True)

    # Daily data table
    with st.expander("Inspect daily performance data"):
        st.dataframe(
            daily,
            use_container_width=True,
            hide_index=True,
        )

    st.caption("Data source: ecommerce_intelligence.gold.daily_performance")

    # Customer Journey & Funnel
    st.divider()
    st.header("Customer Journey & Funnel")
    st.caption(
        "Session-level metrics and session-product-pair metrics "
        "are shown separately because they use different denominators."
    )

    with st.spinner("Loading customer journey funnel..."):
        funnel = load_customer_journey_funnel()

    if funnel.empty:
        st.warning("The customer journey funnel table returned no data.")
    else:
        funnel["rate_pct"] = funnel["rate"].astype(float) * 100

        session_metrics = funnel[
            funnel["entity_level"] == "session"
        ].copy()

        pair_metrics = funnel[
            funnel["entity_level"] == "session_product_pair"
        ].copy()

        st.subheader("Session-Level Journey")

        preferred_session_metrics = [
            "sessions_with_view",
            "sessions_view_then_cart",
            "sessions_with_cart",
            "sessions_cart_then_purchase",
            "sessions_with_purchase",
            "sessions_view_cart_purchase",
            "sessions_ordered_view_cart_purchase",
            "sessions_same_product_cart_purchase",
            "sessions_same_product_full_journey",
        ]

        available_session_metrics = session_metrics[
            session_metrics["metric_name"].isin(
                preferred_session_metrics
            )
        ].copy()

        if not available_session_metrics.empty:
            available_session_metrics["metric_name"] = pd.Categorical(
                available_session_metrics["metric_name"],
                categories=preferred_session_metrics,
                ordered=True,
            )

            available_session_metrics = (
                available_session_metrics.sort_values("metric_name")
            )


            session_labels = {
                "sessions_with_view": "Sessions with a view",
                "sessions_view_then_cart": "View → Cart",
                "sessions_with_cart": "Sessions with a cart",
                "sessions_cart_then_purchase": "Cart → Purchase",
                "sessions_with_purchase": "Sessions with a purchase",
                "sessions_view_cart_purchase": "View → Cart → Purchase",
                "sessions_ordered_view_cart_purchase": "Ordered full journey",
                "sessions_same_product_cart_purchase": "Same-product Cart → Purchase",
                "sessions_same_product_full_journey": "Same-product full journey",
            }

            available_session_metrics["metric_label"] = (
                available_session_metrics["metric_name"]
                .astype(str)
                .map(session_labels)
            )

            session_chart = px.bar(
                available_session_metrics,
                x="metric_label",
                y="rate_pct",
                hover_data=["metric_count", "denominator_count"],
                title="Session Journey Rates",
                labels={
                    "metric_label": "Journey Stage",
                    "rate_pct": "Rate (%)",
                    "metric_count": "Sessions",
                    "denominator_count": "Total Sessions",
                },
                text="rate_pct",
            )

            session_chart.update_traces(
                texttemplate="%{text:.2f}%",
                textposition="outside",
                cliponaxis=False,
            )

            session_chart.update_layout(
                yaxis_range=[0, 110],
                xaxis_tickangle=-30,
                margin=dict(l=20, r=20, t=60, b=110),
            )



            st.plotly_chart(
                session_chart,
                use_container_width=True,
            )

            st.dataframe(
                available_session_metrics[
                    [
                        "metric_name",
                        "metric_count",
                        "denominator_count",
                        "rate_pct",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No matching session-level metrics were found.")

        st.subheader("Session–Product-Pair Journey")


        if not pair_metrics.empty:
            pair_labels = {
                "product_pairs_view_then_cart": "View → Cart",
                "product_pairs_cart_then_purchase": "Cart → Purchase",
                "product_pairs_full_journey": "Full Journey",
            }

            available_pair_metrics = pair_metrics.copy()

            available_pair_metrics["metric_label"] = (
                available_pair_metrics["metric_name"]
                .astype(str)
                .map(pair_labels)
            )

            # Keep only the three expected metrics with readable labels.
            available_pair_metrics = available_pair_metrics.dropna(
                subset=["metric_label"]
            )

            pair_chart = px.bar(
                available_pair_metrics,
                x="metric_label",
                y="rate_pct",
                hover_data=["metric_count", "denominator_count"],
                title="Session–Product-Pair Journey Rates",
                labels={
                    "metric_label": "Journey Stage",
                    "rate_pct": "Rate (%)",
                    "metric_count": "Session–Product Pairs",
                    "denominator_count": "Total Session–Product Pairs",
                },
                text="rate_pct",
            )

            pair_chart.update_traces(
                texttemplate="%{text:.2f}%",
                textposition="outside",
                cliponaxis=False,
            )

            if not available_pair_metrics.empty:
                max_rate = float(
                    available_pair_metrics["rate_pct"].max()
                )
                pair_chart.update_layout(
                    yaxis_range=[0, max(3, max_rate * 1.25)],
                    xaxis_tickangle=-20,
                    margin=dict(l=20, r=20, t=60, b=80),
                )

            st.plotly_chart(
                pair_chart,
                use_container_width=True,
            )

            st.dataframe(
                available_pair_metrics[
                    [
                        "metric_name",
                        "metric_count",
                        "denominator_count",
                        "rate_pct",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No session–product-pair metrics were found.")


        st.caption(
            "Source: ecommerce_intelligence.gold.customer_journey_funnel"
        )

    # Recommendation Intelligence
    st.divider()
    st.header("Recommendation Intelligence")
    st.caption(
        "Multi-product recommendations evaluated on purchases "
        "from October 29–31, 2019, using browsing context "
        "from October 25–28, 2019."
    )

    with st.spinner("Loading recommendation evaluation results..."):
        recommendation_eval = load_recommendation_evaluation()

    if recommendation_eval.empty:
        st.warning("No recommendation evaluation results were found.")
    else:
        # Convert evaluation metrics to percentages for display.
        recommendation_eval["recall_pct"] = (
            recommendation_eval["mean_user_recall_at_10"].astype(float) * 100
        )
        recommendation_eval["hit_rate_pct"] = (
            recommendation_eval["hit_rate_at_10"].astype(float) * 100
        )
        recommendation_eval["availability_pct"] = (
            recommendation_eval["recommendation_availability"].astype(float) * 100
        )

        model_labels = {
            "multi_product_cooccurrence": "Multi-product Co-occurrence",
            "multi_product_hybrid_rrf": "Multi-product Hybrid RRF",
            "multi_product_sequential": "Multi-product Sequential",
        }

        recommendation_eval["model_label"] = (
            recommendation_eval["model_name"]
            .map(model_labels)
            .fillna(recommendation_eval["model_name"])
        )

        st.subheader("Model Performance Comparison")

        metric_to_plot = st.selectbox(
            "Choose an evaluation metric",
            options=[
                "recall_pct",
                "hit_rate_pct",
                "availability_pct",
            ],
            format_func=lambda value: {
                "recall_pct": "Recall@10",
                "hit_rate_pct": "Hit Rate@10",
                "availability_pct": "Recommendation Availability",
            }[value],
            key="recommendation_metric",
        )

        metric_labels = {
            "recall_pct": "Recall@10 (%)",
            "hit_rate_pct": "Hit Rate@10 (%)",
            "availability_pct": "Recommendation Availability (%)",
        }

        recommendation_chart = px.bar(
            recommendation_eval.sort_values(metric_to_plot, ascending=False),
            x="model_label",
            y=metric_to_plot,
            text=metric_to_plot,
            hover_data=[
                "eligible_users",
                "total_hits",
                "k",
            ],
            title=metric_labels[metric_to_plot],
            labels={
                "model_label": "Recommendation Model",
                metric_to_plot: metric_labels[metric_to_plot],
                "eligible_users": "Eligible Users",
                "total_hits": "Total Hits",
                "k": "Recommendations per User",
            },
        )

        recommendation_chart.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside",
            cliponaxis=False,
        )

        recommendation_chart.update_layout(
            yaxis_title=metric_labels[metric_to_plot],
            xaxis_title="Recommendation Model",
            xaxis_tickangle=-15,
            margin=dict(l=20, r=20, t=60, b=90),
        )

        st.plotly_chart(
            recommendation_chart,
            use_container_width=True,
        )

        st.subheader("Evaluation Summary")

        display_eval = recommendation_eval[
            [
                "model_label",
                "eligible_users",
                "mean_user_recall_at_10",
                "hit_rate_at_10",
                "total_hits",
                "recommendation_availability",
            ]
        ].copy()

        display_eval = display_eval.rename(
            columns={
                "model_label": "Model",
                "eligible_users": "Eligible Users",
                "mean_user_recall_at_10": "Recall@10",
                "hit_rate_at_10": "Hit Rate@10",
                "total_hits": "Total Hits",
                "recommendation_availability": "Availability",
            }
        )

        for column in ["Recall@10", "Hit Rate@10", "Availability"]:
            display_eval[column] = display_eval[column].astype(float).map(
                lambda value: f"{value:.2%}"
            )

        st.dataframe(
            display_eval,
            use_container_width=True,
            hide_index=True,
        )

        best_model = recommendation_eval.loc[
            recommendation_eval["mean_user_recall_at_10"].astype(float).idxmax()
        ]

        st.info(
            f"Best model by Recall@10: "
            f"{model_labels.get(best_model['model_name'], best_model['model_name'])}. "
            f"Recall@10 = {float(best_model['mean_user_recall_at_10']):.2%}; "
            f"Hit Rate@10 = {float(best_model['hit_rate_at_10']):.2%}."
        )


        st.subheader("Business Insights")

        insight_col1, insight_col2, insight_col3 = st.columns(3)

        best_recall = float(best_model["mean_user_recall_at_10"])
        best_hit_rate = float(best_model["hit_rate_at_10"])
        best_availability = float(best_model["recommendation_availability"])
        eligible_users = int(best_model["eligible_users"])

        insight_col1.metric(
            "Eligible Customers",
            f"{eligible_users:,}",
            help="Customers included in the common recommendation evaluation cohort.",
        )

        insight_col2.metric(
            "Purchase Target Recall@10",
            f"{best_recall:.2%}",
            help="Average fraction of each customer's held-out purchased products recovered in the top 10 recommendations.",
        )

        insight_col3.metric(
            "Recommendation Availability",
            f"{best_availability:.2%}",
            help="Fraction of eligible customers for whom recommendations were available.",
        )

        st.markdown(
            f"""
            **What this means for the business**

            - **Best current approach:** Multi-product co-occurrence achieves
              {best_recall:.2%} Recall@10 and a {best_hit_rate:.2%} hit rate
              on the evaluated cohort.
            - **Recommendation relevance:** The model recovers some of the
              products customers later purchased, but there is still room to
              improve the top-10 recommendations.
            - **Coverage:** Recommendations are available for
              {best_availability:.2%} of eligible customers. The remaining
              gap suggests that fallback recommendations could help.
            - **Business next step:** Compare performance across customer
              browsing-context sizes to determine whether the model works
              differently for customers who view few products versus many.
            """
        )

        # Customer Context Evaluation
        st.divider()
        st.header("Recommendation Performance by Customer Context")
        st.caption(
            "Compare recommendation quality across customers grouped by "
            "the number of distinct products viewed from October 25–28, 2019. "
            "Purchase targets are from October 29–31, 2019."
        )

        context_eval = load_context_aware_evaluation()

        if context_eval.empty:
            st.warning("No customer-context evaluation results were found.")
        else:
            metric_options = {
                "Recall@10": "mean_recall_at_10",
                "Hit Rate@10": "hit_rate",
                "Recommendation Availability": "recommendation_availability",
            }

            selected_metric = st.selectbox(
                "Choose a metric",
                options=list(metric_options.keys()),
                key="context_evaluation_metric",
            )

            metric_column = metric_options[selected_metric]

            context_eval["context_size_group"] = pd.Categorical(
                context_eval["context_size_group"].astype(str),
                categories=["1", "2-3", "4-5", "6-10", "11+"],
                ordered=True,
            )

            context_eval = context_eval.sort_values(
                ["context_size_group", "model_name"]
            )

            chart_data = context_eval.copy()
            chart_data["context_group_label"] = (
                chart_data["context_size_group"].astype(str)
            )
            chart_data["metric_pct"] = chart_data[metric_column] * 100

            model_labels = {
                "multi_product_cooccurrence": "Multi-product Co-occurrence",
                "multi_product_hybrid_rrf": "Multi-product Hybrid RRF",
                "multi_product_sequential": "Multi-product Sequential",
            }

            chart_data["model_label"] = (
                chart_data["model_name"].map(model_labels)
            )

            context_chart = px.bar(
                chart_data,
                x="context_group_label",
                y="metric_pct",
                color="model_label",
                barmode="group",
                category_orders={
                    "context_group_label": ["1", "2-3", "4-5", "6-10", "11+"]
                },
                title=f"{selected_metric} by Browsing Context Size",
                labels={
                    "context_group_label": "Distinct Products Viewed",
                    "metric_pct": f"{selected_metric} (%)",
                    "model_label": "Recommendation Model",
                },
                hover_data={
                    "users": True,
                    "metric_pct": ":.2f",
                    "context_group_label": True,
                    "model_label": True,
                },
            )

            context_chart.update_layout(
                hovermode="x unified",
                margin=dict(l=20, r=20, t=60, b=20),
                legend_title_text="Recommendation Model",
            )

            context_chart.update_traces(
                texttemplate="%{y:.1f}%",
                textposition="outside",
                cliponaxis=False,
            )

            st.plotly_chart(
                context_chart,
                use_container_width=True,
            )

            st.subheader("Context-Level Evaluation Summary")

            summary_columns = [
                "context_size_group",
                "model_name",
                "users",
                "mean_recall_at_10",
                "hit_rate",
                "recommendation_availability",
                "avg_target_products",
            ]

            context_summary = context_eval[
                [
                    "context_size_group",
                    "model_name",
                    "users",
                    "mean_recall_at_10",
                    "hit_rate",
                    "recommendation_availability",
                    "avg_target_products",
                ]
            ].copy()

            context_summary["context_size_group"] = (
                context_summary["context_size_group"].astype(str)
            )

            context_summary["model_name"] = (
                context_summary["model_name"].map(model_labels)
            )

            context_summary = context_summary.rename(
                columns={
                    "context_size_group": "Products Viewed",
                    "model_name": "Recommendation Model",
                    "users": "Eligible Users",
                    "mean_recall_at_10": "Recall@10",
                    "hit_rate": "Hit Rate@10",
                    "recommendation_availability": "Availability",
                    "avg_target_products": "Avg. Purchase Targets",
                }
            )

            for column in ["Recall@10", "Hit Rate@10", "Availability"]:
                context_summary[column] = context_summary[column].map(
                    "{:.2%}".format
                )

            context_summary["Avg. Purchase Targets"] = (
                context_summary["Avg. Purchase Targets"].map("{:.2f}".format)
            )

            st.dataframe(
                context_summary,
                use_container_width=True,
                hide_index=True,
            )


            best_row = context_eval.loc[
                context_eval.groupby("context_size_group", observed=True)[
                    "mean_recall_at_10"
                ].idxmax()
            ]

            st.subheader("Best Model for Each Context Group")

            st.dataframe(
                best_row[
                    [
                        "context_size_group",
                        "model_name",
                        "users",
                        "mean_recall_at_10",
                        "hit_rate",
                    ]
                ].assign(
                    context_size_group=lambda df: (
                        df["context_size_group"].astype(str)
                    ),
                    model_name=lambda df: (
                        df["model_name"].map(model_labels)
                    ),
                    mean_recall_at_10=lambda df: (
                        df["mean_recall_at_10"].map("{:.2%}".format)
                    ),
                    hit_rate=lambda df: df["hit_rate"].map("{:.2%}".format),
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Business Insights")

            best_overall = context_eval.loc[
                context_eval["mean_recall_at_10"].idxmax()
            ]

            best_context = context_eval.loc[
                context_eval.groupby("context_size_group")[
                    "mean_recall_at_10"
                ].idxmax()
            ]

            strongest_context = best_context.loc[
                best_context["mean_recall_at_10"].idxmax()
            ]

            weakest_context = best_context.loc[
                best_context["mean_recall_at_10"].idxmin()
            ]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Best Context-Group Recall@10",
                    f"{strongest_context['mean_recall_at_10']:.2%}",
                    help="Highest Recall@10 achieved by the best model within any browsing-context group.",
                )

            with col2:
                st.metric(
                    "Lowest Context-Group Recall@10",
                    f"{weakest_context['mean_recall_at_10']:.2%}",
                    help="Lowest Recall@10 achieved by the best model within any browsing-context group.",
                )

            with col3:
                st.metric(
                    "Context Groups Evaluated",
                    str(context_eval["context_size_group"].nunique()),
                )


            st.markdown("**What this means for the business**")

            st.markdown(
                f"""
                - **Best-performing context:** The **{strongest_context['context_size_group']}**
                browsing group achieved the highest best-model Recall@10 of
                **{strongest_context['mean_recall_at_10']:.2%}**.

                - **Weakest context:** The **{weakest_context['context_size_group']}**
                browsing group achieved the lowest best-model Recall@10 of
                **{weakest_context['mean_recall_at_10']:.2%}**.

                - **Model consistency:** Multi-product co-occurrence achieved
                the highest Recall@10 in all five browsing-context groups.

                - **Business opportunity:** Test context-specific ranking strategies
                and fallback recommendations, especially for browsing groups with
                lower Recall@10.

                - **Evaluation scope:** Results use browsing context from
                October 25–28, 2019, and purchase targets from October 29–31, 2019.
                These are offline evaluation results, not evidence of a live
                production uplift.
                """
            )






except Exception as exc:
    st.error("Unable to load dashboard data from Databricks.")
    st.caption(
        "Check your SQL Warehouse status, credentials, and table permissions."
    )
    st.code(f"{type(exc).__name__}: {exc}")


## python -m streamlit run app.py