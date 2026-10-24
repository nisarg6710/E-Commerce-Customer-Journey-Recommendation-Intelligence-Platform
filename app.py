
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


except Exception as exc:
    st.error("Unable to load dashboard data from Databricks.")
    st.caption(
        "Check your SQL Warehouse status, credentials, and table permissions."
    )
    st.code(f"{type(exc).__name__}: {exc}")


## python -m streamlit run app.py