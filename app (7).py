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
    try:
        crime_clean = pd.read_csv("crime_clean.csv")
        marriages_clean = pd.read_csv("marriages_clean.csv")
        final_merged_df = pd.read_csv("final_merged_df.csv")
        return crime_clean, marriages_clean, final_merged_df, True
    except FileNotFoundError:
        years = [2020, 2021, 2022, 2023, 2024]
        states = ['Johor', 'Selangor', 'Pahang', 'Sabah', 'Sarawak', 'Perak', 'Pulau Pinang']
        crime_rows, marriage_rows, merged_rows = [], [], []
        for idx_y, y in enumerate(years):
            for idx_s, s in enumerate(states):
                inc = 4500 + (idx_s * 950) + (idx_y * 350)
                pris = 3200 + (idx_s * 600) + (idx_y * 120)
                marr = 22000 + (idx_s * 3500) - (idx_y * 250)
                crime_rows.append({'date': f'{y}-01-01', 'state': s, 'age': 'all', 'sex': 'both', 'prisoners': pris})
                marriage_rows.append({'date': f'{y}-01-01', 'state': s, 'age': 'all', 'sex': 'both', 'marriages': marr})
                merged_rows.append({'date': f'{y}-01-01', 'year': y, 'state': s, 'age': 'all', 'income': inc, 'prisoners': pris})
        return pd.DataFrame(crime_rows), pd.DataFrame(marriage_rows), pd.DataFrame(merged_rows), False

crime_clean, marriages_clean, final_merged_df, is_real_data = load_data()

if not is_real_data:
    st.warning("⚠️ Fail CSV sebenar (`crime_clean.csv`, `marriages_clean.csv`, `final_merged_df.csv`) tidak ditemui. Sedang memaparkan **data simulasi**.")

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
# A. Yearly Bar Chart Data (Marriages vs Prisoners)
c_filtered = crime_clean.copy()
if 'age' in c_filtered.columns and 'all' in c_filtered['age'].unique():
    c_filtered = c_filtered[c_filtered['age'] == 'all']
if 'sex' in c_filtered.columns and 'both' in c_filtered['sex'].unique():
    c_filtered = c_filtered[c_filtered['sex'] == 'both']
if 'state' in c_filtered.columns:
    c_filtered = c_filtered[~c_filtered['state'].str.contains('Malaysia', case=False, na=False)]

prisoner_col = 'prisoners' if 'prisoners' in c_filtered.columns else [
    c for c in c_filtered.select_dtypes(include='number').columns if c not in ['year', 'rate']
][0]

prisoners_yearly = (
    c_filtered
    .assign(year=pd.to_datetime(c_filtered['date']).dt.year)
    .groupby('year', as_index=False)[prisoner_col]
    .sum()
    .rename(columns={prisoner_col: 'total_prisoners'})
)

m_filtered = marriages_clean.copy()
if 'sex' in m_filtered.columns and 'both' in m_filtered['sex'].unique():
    m_filtered = m_filtered[m_filtered['sex'] == 'both']
if 'age' in m_filtered.columns and 'all' in m_filtered['age'].unique():
    m_filtered = m_filtered[m_filtered['age'] == 'all']
if 'state' in m_filtered.columns:
    m_filtered = m_filtered[~m_filtered['state'].str.contains('Malaysia', case=False, na=False)]

marriage_col = [c for c in m_filtered.select_dtypes(include='number').columns if c not in ['year', 'rate']][0]

marriages_yearly = (
    m_filtered
    .assign(year=pd.to_datetime(m_filtered['date']).dt.year)
    .groupby('year', as_index=False)[marriage_col]
    .sum()
    .rename(columns={marriage_col: 'total_marriages'})
)

# B. State-Level Scatter Plot & Correlation Heatmap Data
filtered_df = final_merged_df[final_merged_df['age'] == 'all'].copy()
filtered_df['state'] = filtered_df['state'].astype(str).str.strip("'")
if 'year' not in filtered_df.columns:
    filtered_df['year'] = pd.to_datetime(filtered_df['date']).dt.year

plot_df_all = filtered_df.groupby(['state', 'date', 'year', 'income'], as_index=False).agg({
    'prisoners': 'sum'
})
plot_df = plot_df_all[plot_df_all['year'].isin(selected_years)].copy()

# C. Yearly Summary Table (for KPI Summary Boxes)
income_yearly_all = (
    plot_df_all.groupby('year', as_index=False)['income']
    .mean()
    .rename(columns={'income': 'avg_income'})
)

full_yearly_df = (
    pd.DataFrame({'year': years_list})
    .merge(income_yearly_all, on='year', how='left')
    .merge(marriages_yearly, on='year', how='left')
    .merge(prisoners_yearly, on='year', how='left')
)

merged_yearly_df = full_yearly_df[full_yearly_df['year'].isin(selected_years)].copy()

# Helper functions for Summary Boxes
def get_value(df, yr, col):
    row = df[df['year'] == yr]
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
df_heat = plot_df.merge(
    merged_yearly_df[['year', 'total_marriages']],
    on='year',
    how='inner'
).
