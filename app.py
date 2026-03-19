import streamlit as st
import pandas as pd
import requests
import re
import time
import altair as alt

# ── Config ──────────────────────────────────────────────────────────────────
REDASH_BASE_URL = "https://redash.greedyants.com"
QUERY_ID = 8738
API_KEY = st.secrets.get("REDASH_API_KEY", "vU1quYfSveoLpiETu0O20STLzSeednAUSONV3Dxp")
DATA_SOURCE_ID = 49
HEADERS = {"Authorization": f"Key {API_KEY}"}

# Brand palette
GREEN = "#57bb8a"
GREEN_DARK = "#3a9a6a"
GREEN_LIGHT = "#e8f5ee"
CHARCOAL = "#363840"
BLACK = "#1a1a1a"
WHITE = "#ffffff"
WARM_BG = "#fafaf8"
CARD_BG = "#ffffff"
BORDER = "#e8e8e5"
MUTED = "#8a8a8a"

# Pattern to find the distributor ilike clause in the SQL
ILIKE_PATTERN = re.compile(
    r"(st\.biz_org_name\s+ilike\s+')(%[^%]*%')(\s*-->.*)?",
    re.IGNORECASE,
)

# Columns to pull from query -> display name mapping
COLUMN_MAP = {
    "BIZ_ORG_NAME": "Distributor",
    "PIQ_SKU_IS_STOCKED_FLAG": "Growth Agent SKU Stocked Flag",
    "PIQ_CAMPAIGN_IS_SIGNED_FLAG": "Growth Agent Campaign Signed",
    "SUPPLIER_NAME": "Supplier",
    "GTIN": "GTIN",
    "ITEM_NAME": "Item Name",
    "ITEM_CODE": "Item Code",
    "L30D_SUPPLIER_SALES": "L30D Sales",
    "L30D_SUPPLIER_CASES": "L30D Cases",
}

# Pepper logo SVG (inline)
PEPPER_LOGO_SVG = """
<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="14" fill="#57bb8a"/>
  <text x="16" y="21" text-anchor="middle" font-family="Inter,sans-serif" font-weight="700" font-size="14" fill="white">P</text>
</svg>
"""

# ── Page setup ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pepper | Growth Agent Lookup",
    page_icon=":hot_pepper:",
    layout="wide",
)

# ── Password gate ───────────────────────────────────────────────────────────
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "pepper2026")

st.markdown(
    """
    <style>
    /* Dark backgrounds → white text */
    input[type="password"],
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        color: white !important;
        caret-color: white !important;
    }
    /* Light backgrounds → black text */
    .stApp input[type="text"],
    .stApp textarea {
        color: #1a1a1a !important;
        caret-color: #1a1a1a !important;
    }
    /* Sidebar overrides main */
    section[data-testid="stSidebar"] input[type="text"] {
        color: white !important;
        caret-color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def check_password():
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;min-height:60vh;">
            <div style="background:{CHARCOAL};border-radius:16px;padding:3rem;
                        text-align:center;max-width:400px;width:100%;">
                <div style="background:{GREEN};width:50px;height:50px;
                            border-radius:12px;display:inline-flex;
                            align-items:center;justify-content:center;
                            font-family:Lato,sans-serif;font-weight:900;
                            font-size:24px;color:white;margin-bottom:1rem;">P</div>
                <h2 style="color:white;font-family:Lato,sans-serif;
                           margin:0 0 0.3rem 0;">Pepper</h2>
                <p style="color:{GREEN};margin:0 0 1.5rem 0;font-size:0.9rem;">
                    Growth Agent - Distributor Lookup</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    password = st.text_input("Enter password to continue", type="password")
    if st.button("Sign in", use_container_width=True):
        if password == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not check_password():
    st.stop()

# ── Full theme ──────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Lato:wght@300;400;700;900&display=swap');

    /* ── Base ─────────────────────────────────────────────────── */
    .stApp {{
        background: {WARM_BG};
        font-family: 'Inter', -apple-system, sans-serif;
        -webkit-font-smoothing: antialiased;
    }}

    header[data-testid="stHeader"] {{
        background: {CHARCOAL} !important;
    }}

    .block-container {{
        padding: 1.5rem 2rem 3rem 2rem;
        max-width: 1400px;
    }}

    /* ── Hero header ──────────────────────────────────────────── */
    .hero {{
        background: linear-gradient(135deg, {CHARCOAL} 0%, #2a2c32 50%, #1f2024 100%);
        border-radius: 16px;
        padding: 2.5rem 3rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }}
    .hero::before {{
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(87,187,138,0.15) 0%, transparent 70%);
        border-radius: 50%;
    }}
    .hero::after {{
        content: '';
        position: absolute;
        bottom: -30%;
        left: 20%;
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(87,187,138,0.08) 0%, transparent 70%);
        border-radius: 50%;
    }}
    .hero-content {{
        position: relative;
        z-index: 1;
    }}
    .hero-brand {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 1rem;
    }}
    .hero-brand .logo {{
        width: 36px;
        height: 36px;
        background: {GREEN};
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Lato', sans-serif;
        font-weight: 900;
        font-size: 18px;
        color: white;
    }}
    .hero-brand .brand-name {{
        font-family: 'Lato', sans-serif;
        font-weight: 700;
        font-size: 1.1rem;
        color: rgba(255,255,255,0.6);
        letter-spacing: 2px;
        text-transform: uppercase;
    }}
    .hero h1 {{
        color: {WHITE} !important;
        font-family: 'Lato', sans-serif !important;
        font-size: 2rem !important;
        font-weight: 900 !important;
        margin: 0 0 0.4rem 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
    }}
    .hero .subtitle {{
        color: {GREEN} !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        margin: 0 !important;
    }}

    /* ── Search card ──────────────────────────────────────────── */
    .search-label {{
        color: {WHITE} !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        margin-bottom: 0.3rem !important;
    }}

    [data-testid="stForm"] {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}

    /* ── Buttons ──────────────────────────────────────────────── */
    .stFormSubmitButton > button {{
        background: linear-gradient(135deg, {GREEN} 0%, {GREEN_DARK} 100%) !important;
        color: {WHITE} !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        padding: 0.65rem 2rem !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(87,187,138,0.3);
    }}
    .stFormSubmitButton > button:hover {{
        box-shadow: 0 4px 16px rgba(87,187,138,0.4) !important;
        transform: translateY(-1px);
    }}

    .stDownloadButton > button {{
        background: {CHARCOAL} !important;
        color: {WHITE} !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease;
    }}
    .stDownloadButton > button:hover {{
        background: {BLACK} !important;
    }}

    /* ── Metric cards ─────────────────────────────────────────── */
    div[data-testid="stMetric"] {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        position: relative;
        overflow: hidden;
    }}
    div[data-testid="stMetric"]::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, {GREEN} 0%, {GREEN_DARK} 100%);
        border-radius: 4px 0 0 4px;
    }}
    div[data-testid="stMetric"] label {{
        color: {MUTED} !important;
        font-weight: 600 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {CHARCOAL} !important;
        font-family: 'Lato', sans-serif !important;
        font-weight: 900 !important;
        font-size: 1.7rem !important;
    }}

    /* ── Sidebar ──────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {{
        background: {CHARCOAL} !important;
    }}
    section[data-testid="stSidebar"] h2 {{
        color: {WHITE} !important;
        font-family: 'Lato', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        border-bottom: 2px solid {GREEN};
        padding-bottom: 0.6rem;
        margin-bottom: 1rem;
    }}
    section[data-testid="stSidebar"] label {{
        color: rgba(255,255,255,0.7) !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    section[data-testid="stSidebar"] .stMultiSelect label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stTextInput label {{
        color: rgba(255,255,255,0.7) !important;
    }}
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {{
        color: rgba(255,255,255,0.85) !important;
    }}
    section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {{
        background: {GREEN} !important;
        color: {WHITE} !important;
        border-radius: 6px !important;
    }}

    /* ── Tabs ─────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background: {CARD_BG};
        border-radius: 12px 12px 0 0;
        border: 1px solid {BORDER};
        border-bottom: none;
        padding: 0 0.5rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 0.85rem 1.5rem;
        font-weight: 500;
        color: {MUTED};
        font-size: 0.9rem;
    }}
    .stTabs [aria-selected="true"] {{
        color: {CHARCOAL} !important;
        font-weight: 700 !important;
        border-bottom: 3px solid {GREEN} !important;
    }}
    .stTabs [data-baseweb="tab-panel"] {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-top: none;
        border-radius: 0 0 12px 12px;
        padding: 1.5rem;
    }}

    /* ── Data table ───────────────────────────────────────────── */
    .stDataFrame {{
        font-size: 15px;
        border-radius: 8px;
        overflow: hidden;
    }}
    /* Ensure columns don't truncate text */
    .stDataFrame [data-testid="stDataFrameResizable"] {{
        min-width: 100%;
    }}
    .stDataFrame td, .stDataFrame th {{
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: unset !important;
        padding: 8px 12px !important;
    }}

    /* ── Dividers ─────────────────────────────────────────────── */
    hr {{
        border: none !important;
        height: 1px !important;
        background: {BORDER} !important;
        margin: 1.5rem 0 !important;
    }}

    /* ── Text colors ──────────────────────────────────────────── */
    h3 {{
        color: {CHARCOAL} !important;
        font-family: 'Lato', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.2rem !important;
    }}
    h4, .stMarkdown p, .stMarkdown strong {{
        color: {CHARCOAL} !important;
    }}
    .hero .subtitle {{
        color: {GREEN} !important;
    }}

    /* ── Spinner ──────────────────────────────────────────────── */
    .stSpinner > div {{
        border-top-color: {GREEN} !important;
    }}

    /* ── Caption ──────────────────────────────────────────────── */
    .stCaption, [data-testid="stCaptionContainer"] {{
        color: {MUTED} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Hero header ─────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-content">
            <div class="hero-brand">
                <div class="logo">P</div>
                <span class="brand-name">Pepper</span>
            </div>
            <h1>Distributor Lookup</h1>
            <p class="subtitle">Growth Agent Stocking</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Helper: fetch query SQL, swap distributor, execute, return results ──────
def run_redash_query(distributor_name: str) -> pd.DataFrame:
    """
    Fetch the SQL from the saved query, swap the distributor name IN MEMORY
    ONLY, then execute as an ad-hoc query. The saved query is NEVER modified.
    """
    query_url = f"{REDASH_BASE_URL}/api/queries/{QUERY_ID}"
    resp = requests.get(query_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    original_sql = resp.json()["query"]

    safe_name = distributor_name.replace("'", "''")
    new_pattern = rf"\1%{safe_name}%'\3"
    modified_sql, count = ILIKE_PATTERN.subn(new_pattern, original_sql)
    if count == 0:
        st.error("Could not find the distributor name placeholder in the query SQL.")
        return pd.DataFrame()

    exec_url = f"{REDASH_BASE_URL}/api/query_results"
    payload = {
        "data_source_id": DATA_SOURCE_ID,
        "query": modified_sql,
        "max_age": 0,
    }
    resp = requests.post(exec_url, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    body = resp.json()

    if "query_result" in body:
        rows = body["query_result"]["data"]["rows"]
        return pd.DataFrame(rows)

    job = body.get("job", {})
    job_id = job.get("id")
    if not job_id:
        st.error("Unexpected Redash response.")
        st.json(body)
        return pd.DataFrame()

    poll_url = f"{REDASH_BASE_URL}/api/jobs/{job_id}"
    with st.spinner("Running query... this may take a minute."):
        for _ in range(180):
            time.sleep(1)
            poll = requests.get(poll_url, headers=HEADERS, timeout=15).json()
            status = poll["job"]["status"]
            if status == 3:
                result_id = poll["job"]["query_result_id"]
                break
            if status == 4:
                st.error(f"Query failed: {poll['job'].get('error', 'unknown error')}")
                return pd.DataFrame()
        else:
            st.error("Query timed out after 3 minutes.")
            return pd.DataFrame()

    result_url = f"{REDASH_BASE_URL}/api/query_results/{result_id}"
    result_resp = requests.get(result_url, headers=HEADERS, timeout=30)
    result_resp.raise_for_status()
    rows = result_resp.json()["query_result"]["data"]["rows"]
    return pd.DataFrame(rows)


# ── Search input ────────────────────────────────────────────────────────────
st.markdown(
    f'<p class="search-label">Input Distributor Name below</p>',
    unsafe_allow_html=True,
)
with st.form("query_form"):
    distributor = st.text_input(
        "Distributor Name",
        placeholder="e.g. Favorite Foods, McDonald Wholesale, MJ Kellnar ...",
        help="Partial match - wildcards are added automatically.",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Search", use_container_width=True)

# ── Execute & display ──────────────────────────────────────────────────────
if submitted:
    if not distributor.strip():
        st.warning("Please enter a distributor name.")
        st.stop()

    search_term = distributor.strip()

    try:
        df = run_redash_query(search_term)
    except Exception as e:
        st.error(f"Query failed: {e}")
        st.stop()

    if df.empty:
        st.warning("No results found for that distributor name.")
        st.stop()

    # Normalize and rename columns
    df.columns = [c.upper().strip() for c in df.columns]
    available = [c for c in COLUMN_MAP if c in df.columns]
    df = df[available]
    df = df.rename(columns=COLUMN_MAP)

    for col in ["L30D Sales", "L30D Cases"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Cache results so sidebar filters don't lose data on rerun
    st.session_state["df"] = df
    st.session_state["search_term"] = search_term

# ── Display results (from session state) ────────────────────────────────────
if "df" in st.session_state:
    df = st.session_state["df"]
    search_term = st.session_state["search_term"]

    # ── Summary metrics ─────────────────────────────────────────────────
    st.markdown("")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total SKUs", f"{len(df):,}")
    if "Supplier" in df.columns:
        col2.metric("Suppliers", df["Supplier"].nunique())
    if "L30D Sales" in df.columns:
        col3.metric("L30D Sales", f"${df['L30D Sales'].sum():,.2f}")
    if "L30D Cases" in df.columns:
        col4.metric("L30D Cases", f"{df['L30D Cases'].sum():,.0f}")

    st.markdown("")

    # ── Sidebar filters ─────────────────────────────────────────────────
    st.sidebar.markdown("## Filters")
    filtered = df.copy()

    filter_cols = [
        "Distributor",
        "Growth Agent SKU Stocked Flag",
        "Growth Agent Campaign Signed",
        "Supplier",
    ]
    for col in filter_cols:
        if col not in filtered.columns:
            continue
        unique_vals = sorted(filtered[col].dropna().unique().tolist())
        if not unique_vals:
            continue
        selected = st.sidebar.multiselect(col, options=unique_vals, default=[])
        if selected:
            filtered = filtered[filtered[col].isin(selected)]

    for col in ["L30D Sales", "L30D Cases"]:
        if col not in filtered.columns:
            continue
        non_null = filtered[col].dropna()
        if non_null.empty:
            continue
        min_val = float(non_null.min())
        max_val = float(non_null.max())
        if min_val == max_val:
            continue
        lo, hi = st.sidebar.slider(
            col,
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val),
            format="%.2f" if col == "L30D Sales" else "%.0f",
        )
        filtered = filtered[
            (filtered[col].isna()) | ((filtered[col] >= lo) & (filtered[col] <= hi))
        ]

    if "Item Name" in filtered.columns:
        item_search = st.sidebar.text_input("Search Item Name", "")
        if item_search:
            filtered = filtered[
                filtered["Item Name"].str.contains(
                    item_search, case=False, na=False
                )
            ]

    # ── Tabs: Charts | Data ──────────────────────────────────────────────
    tab_charts, tab_data = st.tabs(["Supplier Insights", "Full Data"])

    # ── Charts tab ───────────────────────────────────────────────────────
    with tab_charts:
        if "Supplier" not in filtered.columns:
            st.info("No supplier data available for charts.")
        else:
            supplier_agg = (
                filtered.groupby("Supplier", as_index=False)
                .agg(
                    **{
                        "Total SKUs": ("Supplier", "count"),
                        "Stocked SKUs": (
                            "Growth Agent SKU Stocked Flag",
                            lambda x: x.isin(["Yes", "TRUE", "true", "yes"]).sum(),
                        ),
                        "L30D Sales": ("L30D Sales", "sum"),
                        "L30D Cases": ("L30D Cases", "sum"),
                    }
                )
                .sort_values("L30D Sales", ascending=False)
            )
            supplier_agg["Not Stocked"] = (
                supplier_agg["Total SKUs"] - supplier_agg["Stocked SKUs"]
            )

            top = supplier_agg.head(15)

            st.markdown("### Supplier Opportunity Overview")
            st.caption(
                "Top suppliers by L30D sales — stocked vs. unstocked SKUs show where the growth potential is."
            )

            # Sorted supplier order for consistent axis
            supplier_order = top.sort_values("L30D Sales", ascending=True)["Supplier"].tolist()

            y_axis = alt.Y(
                "Supplier:N",
                sort=supplier_order,
                axis=alt.Axis(
                    labelAlign="right",
                    labelBaseline="middle",
                    labelFontSize=13,
                    labelLimit=250,
                ),
                title=None,
            )

            st.markdown("**L30D Sales by Supplier**")
            sales_c = (
                alt.Chart(top)
                .mark_bar(color=GREEN, cornerRadiusEnd=4)
                .encode(
                    x=alt.X("L30D Sales:Q", title="L30D Sales", axis=alt.Axis(format="$,.0f")),
                    y=y_axis,
                    tooltip=["Supplier", alt.Tooltip("L30D Sales:Q", format="$,.2f")],
                )
                .properties(height=500)
            )
            st.altair_chart(sales_c, use_container_width=True)

            st.markdown("---")

            st.markdown("**L30D Cases by Supplier**")
            cases_c = (
                alt.Chart(top)
                .mark_bar(color=GREEN, cornerRadiusEnd=4)
                .encode(
                    x=alt.X("L30D Cases:Q", title="L30D Cases", axis=alt.Axis(format=",.0f")),
                    y=y_axis,
                    tooltip=["Supplier", alt.Tooltip("L30D Cases:Q", format=",.0f")],
                )
                .properties(height=500)
            )
            st.altair_chart(cases_c, use_container_width=True)

            st.markdown("---")

            st.markdown("**SKU Stocking Status by Supplier**")
            st.caption(
                "Green = stocked, gray = not yet stocked (growth opportunity)."
            )
            stocking_data = top[["Supplier", "Stocked SKUs", "Not Stocked"]].melt(
                id_vars="Supplier", var_name="Status", value_name="Count"
            )
            stocking_c = (
                alt.Chart(stocking_data)
                .mark_bar(cornerRadiusEnd=4)
                .encode(
                    x=alt.X("Count:Q", title="SKUs", stack="zero"),
                    y=alt.Y(
                        "Supplier:N",
                        sort=supplier_order,
                        axis=alt.Axis(
                            labelAlign="right",
                            labelBaseline="middle",
                            labelFontSize=13,
                            labelLimit=250,
                        ),
                        title=None,
                    ),
                    color=alt.Color(
                        "Status:N",
                        scale=alt.Scale(
                            domain=["Stocked SKUs", "Not Stocked"],
                            range=[GREEN, "#d4d4d4"],
                        ),
                        legend=alt.Legend(title=None, orient="top"),
                    ),
                    tooltip=["Supplier", "Status", "Count"],
                )
                .properties(height=500)
            )
            st.altair_chart(stocking_c, use_container_width=True)

            st.markdown("---")
            st.markdown("**Supplier Summary**")
            summary_display = supplier_agg.copy()
            summary_display["L30D Sales"] = summary_display["L30D Sales"].apply(
                lambda x: f"${x:,.2f}" if pd.notna(x) else ""
            )
            summary_display["L30D Cases"] = summary_display["L30D Cases"].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else ""
            )
            st.dataframe(
                summary_display[
                    [
                        "Supplier",
                        "Total SKUs",
                        "Stocked SKUs",
                        "Not Stocked",
                        "L30D Sales",
                        "L30D Cases",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Supplier": st.column_config.TextColumn(width="medium"),
                },
            )

    # ── Data tab ─────────────────────────────────────────────────────────
    with tab_data:
        st.markdown(f"### Results ({len(filtered):,} rows)")

        display_df = filtered.copy()
        if "L30D Sales" in display_df.columns:
            display_df["L30D Sales"] = display_df["L30D Sales"].apply(
                lambda x: f"${x:,.2f}" if pd.notna(x) else ""
            )
        if "L30D Cases" in display_df.columns:
            display_df["L30D Cases"] = display_df["L30D Cases"].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else ""
            )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=600,
            column_config={
                "Distributor": st.column_config.TextColumn(width="large"),
                "Supplier": st.column_config.TextColumn(width="large"),
                "Item Name": st.column_config.TextColumn(width="large"),
                "GTIN": st.column_config.TextColumn(width="medium"),
            },
        )

        csv_bytes = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name=f"distributor_{search_term.replace(' ', '_')}.csv",
            mime="text/csv",
        )
