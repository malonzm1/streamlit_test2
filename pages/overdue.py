import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Overdue",
    layout="wide"
)


# ============================================================
# LOGIN CHECK
# ============================================================

if st.session_state.get("logged_in_user") is None:
    st.switch_page("pages/home.py")


# ============================================================
# GET SESSION DATA
# ============================================================

logged_in_user = st.session_state.get("logged_in_user")
user_role = st.session_state.get("user_role")

working_data = st.session_state.get("working_data")

if working_data is None:
    st.error("No working data found. Please return to the Home page.")
    st.stop()

working_data = working_data.copy()


# ============================================================
# HELPER FUNCTION
# ============================================================

def find_column(df, possible_names):
    """
    Return the first matching column from possible_names.
    """
    for col in possible_names:
        if col in df.columns:
            return col
    return None


# ============================================================
# IDENTIFY COLUMNS
# ============================================================

loan_col = find_column(
    working_data,
    ["Loan amount", "Loan.amount"]
)

overdue_col = find_column(
    working_data,
    ["Overdue total", "Overdue.total"]
)

client_col = find_column(
    working_data,
    ["Client name", "Client.name"]
)

fdo_col = find_column(
    working_data,
    ["Credit officer", "Credit.officer"]
)

branch_col = find_column(
    working_data,
    ["Branch name", "Branch.name"]
)

area_col = find_column(
    working_data,
    ["Area", "Area.name"]
)

days_col = find_column(
    working_data,
    ["Days in arrears", "Days.in.arrears"]
)

cycle_col = find_column(
    working_data,
    ["Loan Cycle", "Loan.Cycle"]
)

product_col = find_column(
    working_data,
    ["Product name", "Product.name"]
)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = {
    "Loan amount": loan_col,
    "Overdue total": overdue_col,
    "Client name": client_col,
    "Credit officer": fdo_col,
    "Branch name": branch_col,
    "Area": area_col
}

missing_columns = [
    name
    for name, column in required_columns.items()
    if column is None
]

if missing_columns:
    st.error(
        "The following required columns were not found in the data: "
        + ", ".join(missing_columns)
    )
    st.stop()


# ============================================================
# NUMERIC CONVERSION
# ============================================================

working_data[loan_col] = pd.to_numeric(
    working_data[loan_col],
    errors="coerce"
).fillna(0)

working_data[overdue_col] = pd.to_numeric(
    working_data[overdue_col],
    errors="coerce"
).fillna(0)

if days_col is not None:
    working_data[days_col] = pd.to_numeric(
        working_data[days_col],
        errors="coerce"
    )


# ============================================================
# MAIN DATASET
# ============================================================

combined_data = working_data.copy()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Filters")


# ============================================================
# CREDIT OFFICER FILTER
# ============================================================

credit_officers = sorted(
    [
        str(x).strip()
        for x in combined_data[fdo_col].dropna().unique()
        if str(x).strip()
        and str(x).strip().lower()
        not in ["unknown", "nan", "none"]
    ]
)


if user_role == "credit_officer":

    selected_credit_officer = st.sidebar.selectbox(
        "Credit Officer:",
        [str(logged_in_user)],
        index=0,
        key="overdue_credit_officer"
    )

else:

    selected_credit_officer = st.sidebar.selectbox(
        "Credit Officer:",
        ["All Credit Officers"] + credit_officers,
        index=0,
        key="overdue_credit_officer"
    )


if selected_credit_officer != "All Credit Officers":

    combined_data = combined_data[
        combined_data[fdo_col]
        .astype(str)
        .str.strip()
        ==
        str(selected_credit_officer).strip()
    ].copy()


# ============================================================
# PRESERVE ALL DATA BEFORE OVERDUE FILTER
# ============================================================

# all_data = all loans for the selected role / Credit Officer
#
# combined_data = overdue records only

all_data = combined_data.copy()

combined_data = combined_data[
    combined_data[overdue_col] > 0
].copy()


# ============================================================
# CHECK FOR DATA
# ============================================================

if all_data.empty:
    st.warning(
        "No data available for the selected Credit Officer."
    )
    st.stop()

if combined_data.empty:
    st.warning(
        "There are no overdue records for the selected Credit Officer."
    )


# ============================================================
# FIRST SELECTION
# ============================================================

selection1 = st.sidebar.radio(
    "Choose an option:",
    [
        "Total loan",
        "Overdue total",
        "Days in arrears",
        "Loan cycle"
    ],
    key="overdue_selection1"
)


# ============================================================
# SECOND SELECTION
# ============================================================

selection2 = st.sidebar.radio(
    "Choose an option:",
    [
        "Branch",
        "Product name",
        "FDO"
    ],
    key="overdue_selection2"
)


# ============================================================
# DETERMINE GROUPING COLUMN
# ============================================================

if selection2 == "Branch":

    selected_column = branch_col

elif selection2 == "Product name":

    if product_col is None:
        st.error("Product name column was not found.")
        st.stop()

    selected_column = product_col

else:

    selected_column = fdo_col


# ============================================================
# CHECK SELECTED COLUMN
# ============================================================

if selected_column is None:
    st.error("The selected grouping column was not found.")
    st.stop()


# ============================================================
# SORTING OPTION
# ============================================================

selection3 = st.sidebar.radio(
    "Sort by:",
    [
        "Alphabetical",
        "Total loan",
        "Overdue loan",
        "Total client",
        "Overdue client"
    ],
    key="overdue_sort"
)


# ============================================================
# CLEAN GROUPING VALUES
# ============================================================

all_data[selected_column] = (
    all_data[selected_column]
    .fillna("Unknown")
    .astype(str)
    .str.strip()
)

combined_data[selected_column] = (
    combined_data[selected_column]
    .fillna("Unknown")
    .astype(str)
    .str.strip()
)


# ============================================================
# DETERMINE GROUP ORDER
# ============================================================

if selection3 == "Alphabetical":

    selection_values = sorted(
        [
            x
            for x in combined_data[selected_column].unique()
            if str(x).strip()
            and str(x).lower() not in ["nan", "none"]
        ]
    )

elif selection3 == "Total loan":

    sort_data = (
        all_data
        .groupby(selected_column, dropna=False)[loan_col]
        .sum()
        .sort_values(ascending=False)
    )

    selection_values = sort_data.index.astype(str).tolist()

elif selection3 == "Overdue loan":

    sort_data = (
        combined_data
        .groupby(selected_column, dropna=False)[overdue_col]
        .sum()
        .sort_values(ascending=False)
    )

    selection_values = sort_data.index.astype(str).tolist()

elif selection3 == "Total client":

    sort_data = (
        all_data
        .groupby(selected_column, dropna=False)[client_col]
        .nunique()
        .sort_values(ascending=False)
    )

    selection_values = sort_data.index.astype(str).tolist()

else:

    sort_data = (
        combined_data
        .groupby(selected_column, dropna=False)[client_col]
        .nunique()
        .sort_values(ascending=False)
    )

    selection_values = sort_data.index.astype(str).tolist()


# ============================================================
# REMOVE EMPTY GROUPS
# ============================================================

selection_values = [
    str(x)
    for x in selection_values
    if str(x).strip()
    and str(x).lower() not in ["nan", "none"]
]


if not selection_values:
    st.warning(
        "No groups are available for the selected filters."
    )
    st.stop()


# ============================================================
# SELECT GROUP
# ============================================================

selected_value = st.sidebar.selectbox(
    "Select:",
    selection_values,
    key="overdue_selected_group"
)


# ============================================================
# DATA FOR SELECTED GROUP
# ============================================================

# ALL records for selected group
all_data0 = all_data[
    all_data[selected_column].astype(str)
    ==
    str(selected_value)
].copy()


# OVERDUE records for selected group
combined_data0 = combined_data[
    combined_data[selected_column].astype(str)
    ==
    str(selected_value)
].copy()


# ============================================================
# PAGE TITLE
# ============================================================

st.title("Overdue")

st.markdown(
    f"### {selection2}: {selected_value}"
)


# ============================================================
# SUMMARY METRICS
# ============================================================

total_loan = all_data0[loan_col].sum()

total_overdue = combined_data0[overdue_col].sum()

total_clients = all_data0[client_col].nunique()

overdue_clients = combined_data0[client_col].nunique()

if total_loan > 0:
    overdue_rate = (
        total_overdue / total_loan
    ) * 100
else:
    overdue_rate = 0


metric1, metric2, metric3, metric4, metric5 = st.columns(5)


with metric1:
    st.metric(
        "Total Loan",
        f"₱{total_loan:,.2f}"
    )


with metric2:
    st.metric(
        "Overdue Total",
        f"₱{total_overdue:,.2f}"
    )


with metric3:
    st.metric(
        "Total Clients",
        f"{total_clients:,}"
    )


with metric4:
    st.metric(
        "Overdue Clients",
        f"{overdue_clients:,}"
    )


with metric5:
    st.metric(
        "Overdue Rate",
        f"{overdue_rate:.1f}%"
    )


# ============================================================
# DETERMINE HISTOGRAM VARIABLE
# ============================================================

if selection1 == "Total loan":

    histogram_column = loan_col
    x_title = "Loan Value"

    # ALL records
    histogram_source = all_data0.copy()


elif selection1 == "Overdue total":

    histogram_column = overdue_col
    x_title = "Overdue Value"

    # OVERDUE records only
    histogram_source = combined_data0.copy()


elif selection1 == "Days in arrears":

    if days_col is None:
        st.error("Days in arrears column was not found.")
        st.stop()

    histogram_column = days_col
    x_title = "Days in Arrears"

    # OVERDUE records only
    histogram_source = combined_data0.copy()


else:

    if cycle_col is None:
        st.error("Loan Cycle column was not found.")
        st.stop()

    histogram_column = cycle_col
    x_title = "Loan Cycle"

    # OVERDUE records only
    histogram_source = combined_data0.copy()


# ============================================================
# BUILD HISTOGRAM DATA
# ============================================================

# IMPORTANT:
#
# We need ALL FOUR of these columns:
#
# 1. histogram_column
# 2. client_col
# 3. loan_col
# 4. overdue_col
#
# The previous version only included histogram_column,
# client_col and overdue_col.
#
# Therefore this line:
#
# total_loan=(loan_col, "sum")
#
# caused:
#
# KeyError: "Label(s) ['Loan amount'] do not exist"
#
# because Loan amount was not present in hist_data.
#
# This version explicitly includes loan_col.

hist_required_columns = [
    histogram_column,
    client_col,
    loan_col,
    overdue_col
]


# Remove duplicates while preserving order
hist_required_columns = list(
    dict.fromkeys(hist_required_columns)
)


# Keep only columns that actually exist
hist_required_columns = [
    col
    for col in hist_required_columns
    if col is not None
    and col in histogram_source.columns
]


hist_data = histogram_source[
    hist_required_columns
].copy()


# ============================================================
# CHECK REQUIRED HISTOGRAM COLUMNS
# ============================================================

missing_hist_columns = [
    col
    for col in [
        histogram_column,
        client_col,
        loan_col,
        overdue_col
    ]
    if col is not None
    and col not in hist_data.columns
]


if missing_hist_columns:

    st.error(
        "The following columns required for the histogram "
        "were not found: "
        + ", ".join(missing_hist_columns)
    )

    st.stop()


# ============================================================
# NUMERIC CONVERSION
# ============================================================

hist_data[histogram_column] = pd.to_numeric(
    hist_data[histogram_column],
    errors="coerce"
)

hist_data[loan_col] = pd.to_numeric(
    hist_data[loan_col],
    errors="coerce"
).fillna(0)

hist_data[overdue_col] = pd.to_numeric(
    hist_data[overdue_col],
    errors="coerce"
).fillna(0)


# Remove rows without a histogram value
hist_data = hist_data.dropna(
    subset=[histogram_column]
).copy()


if hist_data.empty:
    st.warning(
        "No numeric data is available for the selected histogram."
    )
    st.stop()


# ============================================================
# HISTOGRAM BINNING
# ============================================================

min_value = hist_data[histogram_column].min()
max_value = hist_data[histogram_column].max()


if min_value == max_value:

    # Avoid zero-width bins
    if min_value == 0:

        bin_edges = np.array([
            -0.5,
            0.5
        ])

    else:

        padding = abs(min_value) * 0.05

        if padding == 0:
            padding = 0.5

        bin_edges = np.array([
            min_value - padding,
            max_value + padding
        ])

else:

    # 10 equal-width bins
    bin_edges = np.linspace(
        min_value,
        max_value,
        11
    )


# ============================================================
# ASSIGN EACH RECORD TO A BIN
# ============================================================

hist_data["bin"] = pd.cut(
    hist_data[histogram_column],
    bins=bin_edges,
    include_lowest=True,
    duplicates="drop"
)


# ============================================================
# TOTAL CLIENT DENOMINATOR
# ============================================================

if selection1 == "Overdue total":

    # Overdue clients / total overdue clients

    total_clients_for_percentage = (
        hist_data.loc[
            hist_data[overdue_col] > 0,
            client_col
        ]
        .nunique()
    )

else:

    # Clients / total clients

    total_clients_for_percentage = (
        hist_data[client_col]
        .nunique()
    )


# ============================================================
# BASIC BIN SUMMARY
# ============================================================

bin_summary = (
    hist_data
    .groupby(
        "bin",
        observed=False
    )
    .agg(
        records=(
            client_col,
            "size"
        ),

        clients=(
            client_col,
            "nunique"
        ),

        total_loan=(
            loan_col,
            "sum"
        ),

        total_overdue=(
            overdue_col,
            "sum"
        )
    )
    .reset_index()
)


# ============================================================
# OVERDUE CLIENTS PER BIN
# ============================================================

overdue_by_bin = (
    hist_data.loc[
        hist_data[overdue_col] > 0
    ]
    .groupby(
        "bin",
        observed=False
    )[client_col]
    .nunique()
    .rename("overdue_clients")
    .reset_index()
)


bin_summary = bin_summary.merge(
    overdue_by_bin,
    on="bin",
    how="left"
)


bin_summary["overdue_clients"] = (
    bin_summary["overdue_clients"]
    .fillna(0)
    .astype(int)
)


# ============================================================
# CALCULATE PERCENTAGE
# ============================================================

if selection1 == "Overdue total":

    # Overdue clients in bin /
    # total overdue clients

    if total_clients_for_percentage > 0:

        bin_summary["percentage_clients"] = (
            bin_summary["overdue_clients"]
            /
            total_clients_for_percentage
            *
            100
        )

    else:

        bin_summary["percentage_clients"] = 0.0

else:

    # Clients in bin /
    # total clients

    if total_clients_for_percentage > 0:

        bin_summary["percentage_clients"] = (
            bin_summary["clients"]
            /
            total_clients_for_percentage
            *
            100
        )

    else:

        bin_summary["percentage_clients"] = 0.0


# ============================================================
# CREATE READABLE BIN LABEL
# ============================================================

def format_bin_label(interval):

    if pd.isna(interval):
        return ""

    left = interval.left
    right = interval.right

    return (
        f"{left:,.0f} – {right:,.0f}"
    )


bin_summary["bin_label"] = (
    bin_summary["bin"]
    .apply(format_bin_label)
)


# ============================================================
# REMOVE EMPTY BINS
# ============================================================

bin_summary = bin_summary[
    bin_summary["records"] > 0
].copy()


if bin_summary.empty:
    st.warning(
        "No histogram bins contain data."
    )
    st.stop()


# ============================================================
# HISTOGRAM
# ============================================================

fig = go.Figure()


fig.add_trace(
    go.Bar(

        x=bin_summary["bin_label"],

        y=bin_summary["records"],

        customdata=bin_summary[
            [
                "clients",
                "overdue_clients",
                "percentage_clients",
                "total_loan",
                "total_overdue"
            ]
        ],

        hovertemplate=(
            "<b>%{x}</b><br>"
            "Records: %{y:,}<br>"
            "Clients: %{customdata[0]:,}<br>"
            "Overdue Clients: %{customdata[1]:,}<br>"
            "% Clients in Range: %{customdata[2]:.1f}%<br>"
            "Total Loan: ₱%{customdata[3]:,.2f}<br>"
            "Total Overdue: ₱%{customdata[4]:,.2f}"
            "<extra></extra>"
        )
    )
)


# ============================================================
# HISTOGRAM LAYOUT
# ============================================================

fig.update_layout(

    title=(
        f"{selection1} Distribution — "
        f"{selection2}: {selected_value}"
    ),

    xaxis=dict(
        title=x_title,
        tickangle=-45
    ),

    yaxis=dict(
        title="Number of Records"
    ),

    height=550,

    margin=dict(
        l=70,
        r=40,
        t=100,
        b=130
    ),

    hovermode="closest"
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# INFORMATION BELOW CHART
# ============================================================

if selection1 == "Total loan":

    st.caption(
        "Percentage = number of unique clients in the "
        "loan-value range ÷ total unique clients "
        "in the selected group."
    )

elif selection1 == "Overdue total":

    st.caption(
        "Percentage = number of unique overdue clients "
        "in the overdue-value range ÷ total unique "
        "overdue clients in the selected group."
    )

else:

    st.caption(
        "Percentage = number of unique clients in the "
        "selected range ÷ total unique clients in "
        "the selected group."
    )


# ============================================================
# DETAILED TABLE
# ============================================================

st.subheader("Selected Group Details")


display_data = combined_data0.copy()


# Select useful columns for display
display_columns = []

for col in [
    client_col,
    fdo_col,
    branch_col,
    area_col,
    product_col,
    loan_col,
    overdue_col,
    days_col,
    cycle_col
]:

    if col is not None and col in display_data.columns:

        if col not in display_columns:
            display_columns.append(col)


if display_columns:

    st.dataframe(
        display_data[display_columns],
        use_container_width=True,
        hide_index=True
    )

else:

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# LOGOUT
# ============================================================

st.sidebar.markdown("---")


if st.sidebar.button(
    "Logout",
    key="overdue_logout"
):

    st.session_state["authenticated"] = False
    st.session_state["logged_in_user"] = None
    st.session_state["user_role"] = None

    st.switch_page(
        "pages/home.py"
    )
