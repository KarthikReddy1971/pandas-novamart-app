import os
import pandas as pd
import streamlit as st
import plotly.express as px


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="NovaMart Analytics",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

.stApp {
    background-color: #F5EBDD;
}

[data-testid="stSidebar"] {
    background-color: #FBF4EC;
}

h1, h2, h3 {
    color: #70452F !important;
}

.metric-card {
    background-color: #FFFDF9;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #E3D2C0;
    box-shadow: 0 3px 10px rgba(80,50,30,0.08);
}

.header {
    background: linear-gradient(90deg, #B07A56, #70452F);
    padding: 25px;
    border-radius: 15px;
    margin-bottom: 25px;
}

.header h1 {
    color: white !important;
    margin: 0;
}

.header p {
    color: #F7EDE3;
    margin: 5px 0 0;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="header">
    <h1>🛍️ NovaMart Analytics Dashboard</h1>
    <p>Sales • Customers • Products • Profitability • Operations</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# LOAD DATA
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@st.cache_data
def load_data():

    orders_path = os.path.join(BASE_DIR, "orders.csv")
    customers_path = os.path.join(BASE_DIR, "customers.csv")
    products_path = os.path.join(BASE_DIR, "products.csv")

    orders = pd.read_csv(orders_path)
    customers = pd.read_csv(customers_path)
    products = pd.read_csv(products_path)

    # Dates
    orders["order_date"] = pd.to_datetime(
        orders["order_date"], errors="coerce"
    )

    customers["signup_date"] = pd.to_datetime(
        customers["signup_date"], errors="coerce"
    )

    products["launch_date"] = pd.to_datetime(
        products["launch_date"], errors="coerce"
    )

    # Merge orders + customers
    df = orders.merge(
        customers,
        on="customer_id",
        how="left"
    )

    # Merge products
    df = df.merge(
        products,
        on="product_id",
        how="left",
        suffixes=("", "_product")
    )

    # ========================================================
    # ENGINEERED COLUMNS
    # ========================================================

    df["gross_revenue"] = (
        df["quantity"] * df["unit_price"]
    )

    df["discount_amount"] = (
        df["gross_revenue"] * df["discount_pct"]
    )

    df["net_revenue"] = (
        df["gross_revenue"] - df["discount_amount"]
    )

    df["cost_amount"] = (
        df["quantity"] * df["cost_price"]
    )

    df["profit"] = (
        df["net_revenue"] - df["cost_amount"]
    )

    df["profit_margin_pct"] = (
        df["profit"] / df["net_revenue"].replace(0, pd.NA)
    ) * 100

    # Discount bands
    df["discount_band"] = pd.cut(
        df["discount_pct"],
        bins=[-0.01, 0, 0.10, 0.20, 0.30, 1],
        labels=[
            "No Discount",
            "Low",
            "Medium",
            "High",
            "Very High"
        ]
    )

    # Delivery buckets
    df["delivery_bucket"] = pd.cut(
        df["delivery_days"],
        bins=[-1, 2, 4, 7, float("inf")],
        labels=[
            "Fast (0-2 days)",
            "Normal (3-4 days)",
            "Slow (5-7 days)",
            "Very Slow (8+ days)"
        ]
    )

    # Month
    df["month_year"] = (
        df["order_date"]
        .dt.to_period("M")
        .astype(str)
    )

    # Year
    df["year"] = df["order_date"].dt.year

    # Customer order count
    customer_orders = (
        df.groupby("customer_id")["order_id"]
        .nunique()
        .rename("customer_order_count")
    )

    df = df.merge(
        customer_orders,
        on="customer_id",
        how="left"
    )

    return df


try:
    df = load_data()

except Exception as e:

    st.error(f"Unable to load the datasets: {e}")

    st.info(
        "Make sure app.py, customers.csv, orders.csv and "
        "products.csv are in the same folder."
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🧰 Filters")

min_date = df["order_date"].min().date()
max_date = df["order_date"].max().date()

date_range = st.sidebar.date_input(
    "Order Date",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

status_options = sorted(
    df["order_status"].dropna().unique()
)

status_filter = st.sidebar.multiselect(
    "Order Status",
    status_options,
    default=status_options
)

category_options = sorted(
    df["category"].dropna().unique()
)

category_filter = st.sidebar.multiselect(
    "Category",
    category_options
)

channel_options = sorted(
    df["sales_channel"].dropna().unique()
)

channel_filter = st.sidebar.multiselect(
    "Sales Channel",
    channel_options
)


# ============================================================
# FILTER DATA
# ============================================================

filtered = df.copy()

if len(date_range) == 2:

    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])

    filtered = filtered[
        (filtered["order_date"] >= start_date)
        &
        (filtered["order_date"] <= end_date)
    ]

if status_filter:

    filtered = filtered[
        filtered["order_status"].isin(status_filter)
    ]

if category_filter:

    filtered = filtered[
        filtered["category"].isin(category_filter)
    ]

if channel_filter:

    filtered = filtered[
        filtered["sales_channel"].isin(channel_filter)
    ]


st.sidebar.caption(
    f"{len(filtered):,} order lines selected"
)


# ============================================================
# KPI SECTION
# ============================================================

st.subheader("📊 Executive Overview")

total_revenue = filtered["net_revenue"].sum()
total_profit = filtered["profit"].sum()
total_orders = filtered["order_id"].nunique()
avg_margin = filtered["profit_margin_pct"].mean()
avg_rating = filtered["rating"].mean()

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Net Revenue",
    f"₹{total_revenue:,.0f}"
)

c2.metric(
    "Profit",
    f"₹{total_profit:,.0f}"
)

c3.metric(
    "Orders",
    f"{total_orders:,}"
)

c4.metric(
    "Avg Margin",
    f"{avg_margin:.2f}%"
)

c5.metric(
    "Avg Rating",
    f"{avg_rating:.2f} ★"
)


# ============================================================
# NAVIGATION
# ============================================================

st.sidebar.divider()

page = st.sidebar.radio(
    "📌 Analysis",
    [
        "Executive Dashboard",
        "Monthly Trends",
        "Product & Category",
        "Geography & Channels",
        "Returns Analysis",
        "Delivery & Ratings",
        "Discount Analysis",
        "Customer Analytics",
        "RFM Analysis",
        "Detailed Data"
    ]
)


# ============================================================
# 1. EXECUTIVE DASHBOARD
# ============================================================

if page == "Executive Dashboard":

    st.subheader("📈 Business Performance")

    col1, col2 = st.columns(2)

    with col1:

        category_sales = (
            filtered.groupby("category")["net_revenue"]
            .sum()
            .reset_index()
            .sort_values("net_revenue", ascending=False)
        )

        fig = px.bar(
            category_sales,
            x="category",
            y="net_revenue",
            title="Revenue by Category",
            text_auto=".2s"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        status = (
            filtered["order_status"]
            .value_counts()
            .reset_index()
        )

        status.columns = ["order_status", "count"]

        fig = px.pie(
            status,
            names="order_status",
            values="count",
            title="Order Status Distribution"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    col3, col4 = st.columns(2)

    with col3:

        channel = (
            filtered.groupby("sales_channel")["net_revenue"]
            .sum()
            .reset_index()
        )

        fig = px.bar(
            channel,
            x="sales_channel",
            y="net_revenue",
            title="Revenue by Sales Channel",
            text_auto=".2s"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col4:

        payment = (
            filtered["payment_method"]
            .value_counts()
            .reset_index()
        )

        payment.columns = ["payment_method", "count"]

        fig = px.pie(
            payment,
            names="payment_method",
            values="count",
            title="Payment Method Distribution"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# 2. MONTHLY TRENDS
# ============================================================

elif page == "Monthly Trends":

    st.subheader("📅 Monthly Sales & Profit Trends")

    monthly = (
        filtered.groupby("month_year")
        .agg(
            Revenue=("net_revenue", "sum"),
            Profit=("profit", "sum"),
            Orders=("order_id", "nunique")
        )
        .reset_index()
    )

    fig = px.line(
        monthly,
        x="month_year",
        y=["Revenue", "Profit"],
        markers=True,
        title="Monthly Revenue and Profit"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    fig2 = px.bar(
        monthly,
        x="month_year",
        y="Orders",
        title="Monthly Orders"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    st.dataframe(
        monthly,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 3. PRODUCT & CATEGORY
# ============================================================

elif page == "Product & Category":

    st.subheader("🛒 Product & Category Performance")

    col1, col2 = st.columns(2)

    with col1:

        category = (
            filtered.groupby("category")
            .agg(
                Revenue=("net_revenue", "sum"),
                Profit=("profit", "sum"),
                Quantity=("quantity", "sum")
            )
            .reset_index()
            .sort_values("Revenue", ascending=False)
        )

        fig = px.bar(
            category,
            x="category",
            y="Revenue",
            title="Revenue by Category",
            text_auto=".2s"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        top_products = (
            filtered.groupby("product_name")["net_revenue"]
            .sum()
            .reset_index()
            .sort_values("net_revenue", ascending=False)
            .head(10)
        )

        fig = px.bar(
            top_products,
            x="net_revenue",
            y="product_name",
            orientation="h",
            title="Top 10 Products by Revenue"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.subheader("Category Performance Table")

    st.dataframe(
        category,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 4. GEOGRAPHY & CHANNELS
# ============================================================

elif page == "Geography & Channels":

    st.subheader("🌍 Geography & Sales Channels")

    col1, col2 = st.columns(2)

    with col1:

        state = (
            filtered.groupby("state")
            .agg(
                Revenue=("net_revenue", "sum"),
                Profit=("profit", "sum"),
                Orders=("order_id", "nunique")
            )
            .reset_index()
            .sort_values("Revenue", ascending=False)
            .head(15)
        )

        fig = px.bar(
            state,
            x="Revenue",
            y="state",
            orientation="h",
            title="Top States by Revenue"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        city = (
            filtered.groupby("city")["net_revenue"]
            .sum()
            .reset_index()
            .sort_values("net_revenue", ascending=False)
            .head(15)
        )

        fig = px.bar(
            city,
            x="net_revenue",
            y="city",
            orientation="h",
            title="Top Cities by Revenue"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.subheader("Sales Channel Performance")

    channel = (
        filtered.groupby("sales_channel")
        .agg(
            Revenue=("net_revenue", "sum"),
            Profit=("profit", "sum"),
            Orders=("order_id", "nunique")
        )
        .reset_index()
    )

    st.dataframe(
        channel,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 5. RETURNS
# ============================================================

elif page == "Returns Analysis":

    st.subheader("↩️ Returns Analysis")

    filtered["is_returned"] = (
        filtered["order_status"]
        .astype(str)
        .str.lower()
        .str.contains("return")
    )

    returned_orders = filtered.loc[
        filtered["is_returned"],
        "order_id"
    ].nunique()

    total_orders = filtered["order_id"].nunique()

    return_rate = (
        returned_orders / total_orders * 100
        if total_orders else 0
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Returned Orders",
        f"{returned_orders:,}"
    )

    c2.metric(
        "Total Orders",
        f"{total_orders:,}"
    )

    c3.metric(
        "Return Rate",
        f"{return_rate:.2f}%"
    )

    return_category = (
        filtered[filtered["is_returned"]]
        .groupby("category")
        .size()
        .reset_index(name="Returned Lines")
        .sort_values(
            "Returned Lines",
            ascending=False
        )
    )

    fig = px.bar(
        return_category,
        x="category",
        y="Returned Lines",
        title="Returns by Category"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.dataframe(
        return_category,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 6. DELIVERY & RATINGS
# ============================================================

elif page == "Delivery & Ratings":

    st.subheader("🚚 Delivery & Customer Ratings")

    col1, col2 = st.columns(2)

    with col1:

        delivery = (
            filtered["delivery_bucket"]
            .value_counts()
            .reset_index()
        )

        delivery.columns = [
            "delivery_bucket",
            "count"
        ]

        fig = px.bar(
            delivery,
            x="delivery_bucket",
            y="count",
            title="Delivery Speed Distribution"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        rating_category = (
            filtered.groupby("category")["rating"]
            .mean()
            .reset_index()
            .sort_values("rating", ascending=False)
        )

        fig = px.bar(
            rating_category,
            x="category",
            y="rating",
            title="Average Rating by Category"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.subheader("Delivery & Rating Summary")

    summary = pd.DataFrame({
        "Metric": [
            "Average Delivery Days",
            "Median Delivery Days",
            "Average Rating",
            "Rated Orders"
        ],
        "Value": [
            filtered["delivery_days"].mean(),
            filtered["delivery_days"].median(),
            filtered["rating"].mean(),
            filtered["rating"].notna().sum()
        ]
    })

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 7. DISCOUNT ANALYSIS
# ============================================================

elif page == "Discount Analysis":

    st.subheader("🏷️ Discount Effectiveness")

    discount = (
        filtered.groupby("discount_band", observed=False)
        .agg(
            Revenue=("net_revenue", "sum"),
            Profit=("profit", "sum"),
            Quantity=("quantity", "sum"),
            Orders=("order_id", "nunique")
        )
        .reset_index()
    )

    col1, col2 = st.columns(2)

    with col1:

        fig = px.bar(
            discount,
            x="discount_band",
            y="Revenue",
            title="Revenue by Discount Band"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        fig = px.bar(
            discount,
            x="discount_band",
            y="Profit",
            title="Profit by Discount Band"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.dataframe(
        discount,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 8. CUSTOMER ANALYTICS
# ============================================================

elif page == "Customer Analytics":

    st.subheader("👥 Customer Analytics")

    customer = (
        filtered.groupby(
            [
                "customer_id",
                "customer_name",
                "segment",
                "city",
                "state",
                "gender"
            ],
            dropna=False
        )
        .agg(
            Orders=("order_id", "nunique"),
            Revenue=("net_revenue", "sum"),
            Profit=("profit", "sum"),
            Quantity=("quantity", "sum")
        )
        .reset_index()
    )

    customer["Avg Order Value"] = (
        customer["Revenue"] /
        customer["Orders"].replace(0, pd.NA)
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Unique Customers",
        f"{customer['customer_id'].nunique():,}"
    )

    c2.metric(
        "Avg Customer Revenue",
        f"₹{customer['Revenue'].mean():,.0f}"
    )

    c3.metric(
        "Avg Order Value",
        f"₹{customer['Avg Order Value'].mean():,.0f}"
    )

    segment = (
        customer.groupby("segment")
        .agg(
            Customers=("customer_id", "nunique"),
            Revenue=("Revenue", "sum"),
            Profit=("Profit", "sum")
        )
        .reset_index()
    )

    fig = px.bar(
        segment,
        x="segment",
        y="Revenue",
        title="Revenue by Customer Segment",
        text_auto=".2s"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader("Top Customers")

    top_customers = customer.sort_values(
        "Revenue",
        ascending=False
    ).head(20)

    st.dataframe(
        top_customers,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 9. RFM ANALYSIS
# ============================================================

elif page == "RFM Analysis":

    st.subheader("🎯 RFM Customer Segmentation")

    reference_date = filtered["order_date"].max() + pd.Timedelta(days=1)

    rfm = (
        filtered.groupby("customer_id")
        .agg(
            Recency=(
                "order_date",
                lambda x: (reference_date - x.max()).days
            ),
            Frequency=("order_id", "nunique"),
            Monetary=("net_revenue", "sum")
        )
        .reset_index()
    )

    if len(rfm) >= 5:

        rfm["R_Score"] = pd.qcut(
            rfm["Recency"],
            5,
            labels=[5, 4, 3, 2, 1],
            duplicates="drop"
        )

        rfm["F_Score"] = pd.qcut(
            rfm["Frequency"].rank(method="first"),
            5,
            labels=[1, 2, 3, 4, 5],
            duplicates="drop"
        )

        rfm["M_Score"] = pd.qcut(
            rfm["Monetary"].rank(method="first"),
            5,
            labels=[1, 2, 3, 4, 5],
            duplicates="drop"
        )

        rfm["RFM_Score"] = (
            rfm["R_Score"].astype(int)
            + rfm["F_Score"].astype(int)
            + rfm["M_Score"].astype(int)
        )

        def segment_customer(score):

            if score >= 13:
                return "High Value"

            elif score >= 10:
                return "Loyal"

            elif score >= 7:
                return "Potential"

            else:
                return "Needs Attention"

        rfm["Customer Segment"] = (
            rfm["RFM_Score"]
            .apply(segment_customer)
        )

        segment = (
            rfm["Customer Segment"]
            .value_counts()
            .reset_index()
        )

        segment.columns = [
            "Customer Segment",
            "Customers"
        ]

        fig = px.pie(
            segment,
            names="Customer Segment",
            values="Customers",
            title="RFM Customer Segments"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.dataframe(
            rfm.sort_values(
                "RFM_Score",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.warning(
            "Not enough customers for RFM quintile analysis."
        )


# ============================================================
# 10. DETAILED DATA
# ============================================================

elif page == "Detailed Data":

    st.subheader("📋 Combined Master Dataset")

    st.write(
        f"Rows: **{len(filtered):,}** | "
        f"Columns: **{len(filtered.columns)}**"
    )

    selected_columns = st.multiselect(
        "Select columns",
        list(filtered.columns),
        default=[
            "order_id",
            "order_date",
            "customer_id",
            "customer_name",
            "product_id",
            "product_name",
            "category",
            "subcategory",
            "quantity",
            "unit_price",
            "discount_pct",
            "net_revenue",
            "profit",
            "profit_margin_pct",
            "order_status"
        ]
    )

    if selected_columns:

        st.dataframe(
            filtered[selected_columns],
            use_container_width=True,
            hide_index=True
        )

        csv = filtered[selected_columns].to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Download Filtered Data",
            csv,
            "novamart_filtered_data.csv",
            "text/csv"
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "NovaMart Analytics • Pandas + Streamlit + Plotly"
)