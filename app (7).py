import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Scientific Visualisation Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Scientific Visualisation Assignment")
st.subheader("Income, Marriages, and Prison Statistics in Malaysia (2020–2024)")

# --------------------------------------------------
# 2. LOAD AND PROCESS DATA
# --------------------------------------------------
@st.cache_data
def load_data():
    income_df = pd.read_csv("income.csv")
    marriages_df = pd.read_csv("marriages_age.csv")
    crime_df = pd.read_csv("crime.csv")

    # Convert date and extract year
    for df in [income_df, marriages_df, crime_df]:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["year"] = df["date"].dt.year

    # Filter data from 2020 to 2024
    income_df = income_df[income_df["year"].between(2020, 2024)].copy()
    marriages_df = marriages_df[marriages_df["year"].between(2020, 2024)].copy()
    crime_df = crime_df[crime_df["year"].between(2020, 2024)].copy()

    # Convert numerical columns
    income_df["income"] = pd.to_numeric(income_df["income"].replace("?", pd.NA), errors="coerce")
    marriages_df["abs"] = pd.to_numeric(marriages_df["abs"], errors="coerce")
    crime_df["prisoners"] = pd.to_numeric(crime_df["prisoners"], errors="coerce")

    # Clean text columns
    for df in [income_df, marriages_df, crime_df]:
        for col in ["state", "sex", "age", "variable"]:
            if col in df.columns:
                df[col] = df[col].astype("string").str.strip().str.strip("'")

    return income_df, marriages_df, crime_df

try:
    income_df, marriages_df, crime_df = load_data()
except Exception as e:
    st.error(f"Error loading datasets: {e}")
    st.stop()

# --------------------------------------------------
# 3. SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("⚙️ Dashboard Controls")
years_list = [2020, 2021, 2022, 2023, 2024]

selected_years = st.sidebar.multiselect(
    "Filter Chart Years:",
    options=years_list,
    default=years_list
)

if not selected_years:
    st.error("Please select at least one year in the sidebar.")
    st.stop()

summary_year = st.sidebar.selectbox(
    "Select Year for Summary Box:",
    options=sorted(selected_years),
    index=len(selected_years) - 1
)

# --------------------------------------------------
# 4. DATA PREPARATION FOR CHARTS & SUMMARY BOXES
# --------------------------------------------------
# A. National Yearly Aggregations (for Bar Chart & Summary Metrics)
inc_mean = income_df[income_df["variable"].str.lower() == "mean"].copy() if "variable" in income_df.columns else income_df.copy()

income_yearly_all = (
    inc_mean.groupby("year", as_index=False)["income"]
    .mean()
    .rename(columns={"income": "avg_income"})
)

m_all = marriages_df[marriages_df["age"].str.lower() == "all"].copy() if "age" in marriages_df.columns else marriages_df.copy()
if "sex" in m_all.columns and "both" in m_all["sex"].str.lower().unique():
    m_all = m_all[m_all["sex"].str.lower() == "both"]
if "state" in m_all.columns:
    m_all = m_all[~m_all["state"].str.lower().eq("malaysia")]

marriages_yearly_all = (
    m_all.groupby("year", as_index=False)["abs"]
    .sum(min_count=1)
    .rename(columns={"abs": "total_marriages"})
)

c_all = crime_df.copy()
if "sex" in c_all.columns and "both" in c_all["sex"].str.lower().unique():
    c_all = c_all[c_all["sex"].str.lower() == "both"]
if "age" in c_all.columns and "all" in c_all["age"].str.lower().unique():
    c_all = c_all[c_all["age"].str.lower() == "all"]

if "state" in c_all.columns and "malaysia" in c_all["state"].str.lower().unique():
    c_nat = c_all[c_all["state"].str.lower() == "malaysia"]
else:
    c_nat = c_all

prisoners_yearly_all = (
    c_nat.groupby("year", as_index=False)["prisoners"]
    .sum(min_count=1)
    .rename(columns={"prisoners": "total_prisoners"})
)

full_yearly_df = (
    pd.DataFrame({"year": years_list})
    .merge(income_yearly_all, on="year", how="left")
    .merge(marriages_yearly_all, on="year", how="left")
    .merge(prisoners_yearly_all, on="year", how="left")
)

merged_yearly_df = full_yearly_df[full_yearly_df["year"].isin(selected_years)].copy()

# B. State-Level Scatter Plot Data (Income vs Prisoners)
inc_state = inc_mean[~inc_mean["state"].str.lower().eq("malaysia")].groupby(["state", "year"], as_index=False)["income"].mean()
c_state = c_all[~c_all["state"].str.lower().eq("malaysia")].groupby(["state", "year"], as_index=False)["prisoners"].sum()

plot_df = inc_state.merge(c_state, on=["state", "year"], how="inner")
plot_df = plot_df[plot_df["year"].isin(selected_years)].copy()
plot_df["date"] = plot_df["year"].astype(str)

# Helper functions for Summary Boxes
def get_value(df, yr, col):
    row = df[df["year"] == yr]
    if row.empty or pd.isna(row[col].iloc[0]):
        return None
    return float(row[col].iloc[0])

def calc_pct_change(curr, prev):
    if curr is None or prev is None or prev == 0:
        return None
    return ((curr - prev) / abs(prev)) * 100

def fmt_num(val, prefix="", suffix="", decimals=0):
    if val is None:
        return "N/A"
    return f"{prefix}{val:,.{decimals}f}{suffix}"

# Current & Previous Year Metrics
curr_income = get_value(full_yearly_df, summary_year, "avg_income")
prev_income = get_value(full_yearly_df, summary_year - 1, "avg_income")
income_chg = calc_pct_change(curr_income, prev_income)

curr_marriages = get_value(full_yearly_df, summary_year, "total_marriages")
prev_marriages = get_value(full_yearly_df, summary_year - 1, "total_marriages")
marriage_chg = calc_pct_change(curr_marriages, prev_marriages)

curr_prisoners = get_value(full_yearly_df, summary_year, "total_prisoners")
prev_prisoners = get_value(full_yearly_df, summary_year - 1, "total_prisoners")
prisoner_chg = calc_pct_change(curr_prisoners, prev_prisoners)

# Correlation data for Heatmap & Summary Box
df_heat = merged_yearly_df[["avg_income", "total_marriages"]].dropna()
corr_val = (
    df_heat["avg_income"].corr(df_heat["total_marriages"])
    if len(df_heat) >= 2 else None
)

# --------------------------------------------------
# 5. DASHBOARD TABS WITH SUMMARY BOXES
# --------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "📈 Income vs Prisoners",
    "📊 Marriages vs Prisoners",
    "🔥 Income vs Marriages"
])

# === TAB 1: SCATTER PLOT + SUMMARY BOX ===
with tab1:
    st.header("1. Relationship Between Household Income and Prisoner Statistics")
    st.markdown("### 📊 Summary Metrics")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label=f"Average Household Income ({summary_year})",
            value=fmt_num(curr_income, prefix="RM ", decimals=2),
            delta=f"{income_chg:+.2f}%" if income_chg is not None else None
        )
    with col2:
        st.metric(
            label=f"Total Prisoners ({summary_year})",
            value=fmt_num(curr_prisoners),
            delta=f"{prisoner_chg:+.2f}%" if prisoner_chg is not None else None,
            delta_color="inverse"
        )
    with col3:
        st.metric(
            label="Income YoY Change (%)",
            value=fmt_num(income_chg, suffix="%", decimals=2)
        )

    st.caption("Summary metrics compare the selected summary year with the previous year.")
    st.divider()

    if plot_df.empty:
        st.warning("No matching state-level income and prisoner records for the selected years.")
    else:
        fig_scatter = px.scatter(
            plot_df,
            x="income",
            y="prisoners",
            color="state",
            hover_name="state",
            hover_data=["date"],
            trendline="ols",
            trendline_scope="overall",
            title=f"Household Income vs Prisoner Statistics ({min(selected_years)}–{max(selected_years)})",
            labels={
                "income": "Average Household Income (RM)",
                "prisoners": "Number of Prisoners",
                "state": "State",
                "date": "Year"
            },
            template="plotly_white"
        )
        fig_scatter.update_traces(marker=dict(size=9, opacity=0.85))
        fig_scatter.update_layout(height=600, title_font_size=18, legend_title_text="State")
        st.plotly_chart(fig_scatter, use_container_width=True)

# === TAB 2: DUAL-AXIS BAR CHART + SUMMARY BOX ===
with tab2:
    st.header("2. National Yearly Marriages vs Total Prisoners")
    st.markdown("### 📊 Summary Metrics")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label=f"Total Marriages ({summary_year})",
            value=fmt_num(curr_marriages),
            delta=f"{marriage_chg:+.2f}%" if marriage_chg is not None else None
        )
    with col2:
        st.metric(
            label=f"Total Prisoners ({summary_year})",
            value=fmt_num(curr_prisoners),
            delta=f"{prisoner_chg:+.2f}%" if prisoner_chg is not None else None,
            delta_color="inverse"
        )
    with col3:
        st.metric(
            label="Marriage YoY Change (%)",
            value=fmt_num(marriage_chg, suffix="%", decimals=2)
        )

    st.caption("Summary metrics compare the selected summary year with the previous year.")
    st.divider()

    fig_bar = make_subplots(specs=[[{"secondary_y": True}]])

    fig_bar.add_trace(
        go.Bar(
            x=merged_yearly_df["year"],
            y=merged_yearly_df["total_marriages"],
            name="Total Marriages",
            marker_color="rgb(158,202,225)",
            offsetgroup=1
        ),
        secondary_y=False
    )

    fig_bar.add_trace(
        go.Bar(
            x=merged_yearly_df["year"],
            y=merged_yearly_df["total_prisoners"],
            name="Total Prisoners",
            marker_color="rgb(227,119,194)",
            offsetgroup=2
        ),
        secondary_y=True
    )

    fig_bar.update_layout(
        title_text=f"National Yearly Marriages vs Total Prisoners ({min(selected_years)}–{max(selected_years)})",
        xaxis_title="Year",
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=selected_years
        ),
        barmode="group",
        template="plotly_white",
        height=550,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_bar.update_yaxes(title_text="Total Marriages", secondary_y=False, showgrid=True)
    fig_bar.update_yaxes(title_text="Total Prisoners", secondary_y=True, showgrid=False)
    st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander("View Annual Summary Table"):
        st.dataframe(merged_yearly_df, use_container_width=True)

# === TAB 3: CORRELATION HEATMAP + SUMMARY BOX ===
with tab3:
    st.header("3. Correlation Heatmap: Income vs Marriages")
    st.markdown("### 📊 Summary Metrics")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label=f"Average Household Income ({summary_year})",
            value=fmt_num(curr_income, prefix="RM ", decimals=2)
        )
    with col2:
        st.metric(
            label=f"Total Marriages ({summary_year})",
            value=fmt_num(curr_marriages)
        )
    with col3:
        st.metric(
            label="Correlation Coefficient (r)",
            value=fmt_num(corr_val, decimals=3)
        )

    st.caption("Correlation coefficient is calculated across the selected years.")
    st.divider()

    if len(df_heat) < 2:
        st.warning("Not enough matching observations to calculate correlation. Please select at least 2 years.")
    else:
        corr_matrix = df_heat[["avg_income", "total_marriages"]].corr()
        fig_heat = px.imshow(
            corr_matrix,
            text_auto=".3f",
            aspect="auto",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            labels=dict(color="Correlation Coefficient"),
            x=["Average Income", "Total Marriages"],
            y=["Average Income", "Total Marriages"],
            title=f"Correlation Heatmap: Average Income vs Total Marriages ({min(selected_years)}–{max(selected_years)})"
        )
        fig_heat.update_layout(template="plotly_white", height=500)
        st.plotly_chart(fig_heat, use_container_width=True)

# --------------------------------------------------
# 6. FOOTER
# --------------------------------------------------
st.divider()
st.caption("Data Source: Department of Statistics Malaysia (DOSM) and Malaysia Open Data.")
st.caption("Scientific Visualisation Assignment | 2020–2024")
