from google.oauth2 import service_account
from googleapiclient.discovery import build
import plotly.graph_objects as go
import math

from googleapiclient.http import MediaIoBaseDownload

import pandas as pd
import streamlit as st
import os

if st.session_state.get("logged_in_user") is None:
    st.switch_page("pages/home.py")
    
# =========================================================
# CHECK DATA
# =========================================================

if "data" not in st.session_state:

    st.warning(
        "Data has not been loaded yet. "
        "Please return to Home first."
    )

    st.stop()


# Original complete data
data = st.session_state["data"]


# Role-filtered data
combined_data = st.session_state["working_data"]

# ============================================================
# CURRENT USER
# ============================================================

logged_in_user = st.session_state.get("logged_in_user")
user_role = st.session_state.get("user_role")


# ============================================================
# SIDEBAR USER INFORMATION
# ============================================================

st.sidebar.success(
    "Logged in as: "
    + str(logged_in_user)
)


if user_role == "credit_officer":

    st.sidebar.info(
        "Role: Credit Officer"
    )


elif user_role == "area_manager":

    AREA_MANAGERS2 = st.session_state["AREA_MANAGERS2"]
    manager_area = AREA_MANAGERS2.get(
        logged_in_user
    )

    if manager_area is None:

        st.error(
            "This Area Manager is not assigned "
            "to an Area."
        )

        st.stop()

    st.sidebar.info(
        "Role: Area Manager"
    )

    st.sidebar.info(
        "Area: "
        + str(manager_area)
    )


elif user_role == "superuser":

    st.sidebar.info(
        "Role: Administrator"
    )


# ============================================================
# LOGOUT
# ============================================================

if st.sidebar.button(
    "Logout",
    key="logout_button"
):

    st.session_state["authenticated"] = False
    st.session_state["logged_in_user"] = None
    st.session_state["user_role"] = None

    st.switch_page("pages/home.py")



# =========================================================
# FIND COLUMN
# =========================================================

def find_column(df, candidates):

    for col in candidates:

        if col in df.columns:
            return col

    return None


# =========================================================
# FIND REQUIRED COLUMNS
# =========================================================

cycle_col = find_column(
    combined_data,
    ["Loan Cycle"]
)

loan_col = find_column(
    combined_data,
    ["Loan amount"]
)

overdue_col = find_column(
    combined_data,
    ["Overdue total"]
)

client_col = find_column(
    combined_data,
    ["Client name"]
)

fdo_col = find_column(
    combined_data,
    [
        "Credit officer",
        "Credit.officer"
    ]
)


required_columns = {

    "Loan Cycle": cycle_col,

    "Loan amount": loan_col,

    "Overdue total": overdue_col,

    "Client": client_col,

    "Credit officer": fdo_col
}


missing = [

    name

    for name, col in required_columns.items()

    if col is None
]


if missing:

    st.error(
        "The following required columns were not found: "
        + ", ".join(missing)
    )

    st.stop()


# =========================================================
# WORKING COPY
# =========================================================

working_data = combined_data.copy()


# =========================================================
# CONVERT NUMERIC COLUMNS
# =========================================================

working_data[loan_col] = pd.to_numeric(
    working_data[loan_col],
    errors="coerce"
).fillna(0)


working_data[overdue_col] = pd.to_numeric(
    working_data[overdue_col],
    errors="coerce"
).fillna(0)


# =========================================================
# CLEAN COLUMNS
# =========================================================

working_data[cycle_col] = (
    working_data[cycle_col]
    .astype(str)
    .str.strip()
)


working_data[fdo_col] = (
    working_data[fdo_col]
    .astype(str)
    .str.strip()
)


working_data["_client_clean"] = (
    working_data[client_col]
    .astype(str)
    .str.strip()
)


# =========================================================
# REMOVE EMPTY / NAN LOAN CYCLES
# =========================================================

working_data = working_data[
    (working_data[cycle_col] != "")
    &
    (working_data[cycle_col].str.lower() != "nan")
].copy()


# =========================================================
# CREDIT OFFICER DROPDOWN — SIDEBAR
# =========================================================

credit_officers = sorted(
    [
        officer
        for officer in working_data[fdo_col].unique()
        if officer
        and officer.lower() != "nan"
        and officer.lower() != "unknown"
    ]
)

if user_role != "credit_officer":
  
  selected_credit_officer = st.sidebar.selectbox(
  
      "Credit Officer:",
  
      ["All Credit Officers"] + credit_officers,
  
      index=0,
  
      key="loan_cycle_credit_officer"
  )
  
else:
  
  selected_credit_officer = st.sidebar.selectbox(
  
      "Credit Officer:",
  
      credit_officers,
  
      index=0,
  
      key="loan_cycle_credit_officer"
  )

# =========================================================
# FILTER BY CREDIT OFFICER
# =========================================================

if selected_credit_officer != "All Credit Officers":

    working_data = working_data[
        working_data[fdo_col]
        == selected_credit_officer
    ].copy()


# =========================================================
# CHECK FILTERED DATA
# =========================================================

if working_data.empty:

    st.warning(
        "No data was found for the selected "
        "Credit Officer."
    )

    st.stop()


# =========================================================
# CLIENT CLEANING AFTER FILTER
# =========================================================

working_data = working_data[
    (working_data["_client_clean"] != "")
    &
    (working_data["_client_clean"].str.lower() != "nan")
].copy()


# =========================================================
# OVERALL TOTALS
# =========================================================

overall_total_loan = (
    working_data[loan_col].sum()
)


overall_total_overdue = (
    working_data[overdue_col].sum()
)


# =========================================================
# CLIENT TOTALS
# =========================================================

# Total unique clients
overall_total_clients = (
    working_data["_client_clean"]
    .nunique()
)


# Total unique overdue clients
overall_overdue_clients = (
    working_data.loc[
        working_data[overdue_col] > 0,
        "_client_clean"
    ]
    .nunique()
)


# =========================================================
# LOAN VALUE BY LOAN CYCLE
# =========================================================

loan_cycle_totals = (

    working_data

    .groupby(cycle_col)

    .agg(

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


# =========================================================
# CLIENTS BY LOAN CYCLE
# =========================================================

total_clients_by_cycle = (

    working_data

    .groupby(cycle_col)

    .agg(

        total_clients=(
            "_client_clean",
            "nunique"
        )

    )

    .reset_index()
)


# =========================================================
# OVERDUE CLIENTS BY LOAN CYCLE
# =========================================================

overdue_clients_by_cycle = (

    working_data[
        working_data[overdue_col] > 0
    ]

    .groupby(cycle_col)

    .agg(

        overdue_clients=(
            "_client_clean",
            "nunique"
        )

    )

    .reset_index()
)


# =========================================================
# COMBINE CLIENT COUNTS
# =========================================================

client_cycle_totals = (

    total_clients_by_cycle

    .merge(
        overdue_clients_by_cycle,
        on=cycle_col,
        how="left"
    )

)


client_cycle_totals["overdue_clients"] = (

    client_cycle_totals["overdue_clients"]
    .fillna(0)
    .astype(int)

)


# =========================================================
# CREATE PERCENTAGES
# =========================================================

# ---------------------------------------------------------
# Loan percentage
# ---------------------------------------------------------

if overall_total_loan > 0:

    loan_cycle_totals["loan_percent"] = (

        loan_cycle_totals["total_loan"]
        / overall_total_loan
        * 100

    )

else:

    loan_cycle_totals["loan_percent"] = 0


# ---------------------------------------------------------
# Overdue percentage
# ---------------------------------------------------------

if overall_total_overdue > 0:

    loan_cycle_totals["overdue_percent"] = (

        loan_cycle_totals["total_overdue"]
        / overall_total_overdue
        * 100

    )

else:

    loan_cycle_totals["overdue_percent"] = 0


# ---------------------------------------------------------
# Client percentage
# ---------------------------------------------------------

if overall_total_clients > 0:

    client_cycle_totals["client_percent"] = (

        client_cycle_totals["total_clients"]
        / overall_total_clients
        * 100

    )

else:

    client_cycle_totals["client_percent"] = 0


# ---------------------------------------------------------
# Overdue client percentage
# ---------------------------------------------------------

if overall_overdue_clients > 0:

    client_cycle_totals["overdue_client_percent"] = (

        client_cycle_totals["overdue_clients"]
        / overall_overdue_clients
        * 100

    )

else:

    client_cycle_totals["overdue_client_percent"] = 0


# =========================================================
# SORT LOAN CYCLES NUMERICALLY
# =========================================================

try:

    loan_cycle_totals["_cycle_numeric"] = pd.to_numeric(
        loan_cycle_totals[cycle_col],
        errors="raise"
    )

    loan_cycle_totals = (
        loan_cycle_totals
        .sort_values(
            "_cycle_numeric"
        )
        .drop(
            columns="_cycle_numeric"
        )
    )

except:

    pass


# =========================================================
# KEEP SAME LOAN CYCLE ORDER
# =========================================================

cycle_order = (
    loan_cycle_totals[cycle_col]
    .tolist()
)


client_cycle_totals[cycle_col] = (
    client_cycle_totals[cycle_col]
    .astype(str)
)


client_cycle_totals = (
    client_cycle_totals
    .set_index(cycle_col)
    .reindex(cycle_order)
    .reset_index()
)


# =========================================================
# TWO CHARTS SIDE-BY-SIDE
# =========================================================

col1, col2 = st.columns(2)


# =========================================================
# LEFT CHART
# LOAN VALUE
# =========================================================

with col1:

    fig_loan = go.Figure()


    # -----------------------------------------------------
    # TOTAL LOAN
    # -----------------------------------------------------

    fig_loan.add_trace(

        go.Bar(

            x=loan_cycle_totals[cycle_col],

            y=loan_cycle_totals["total_loan"],

            name="Total Loan",

            customdata=loan_cycle_totals[
                [
                    "total_loan",
                    "loan_percent"
                ]
            ],

            hovertemplate=(

                "<b>Loan Cycle %{x}</b><br>"

                "Total Loan: "
                "₱%{customdata[0]:,.2f}<br>"

                "Percent of Total Loan: "
                "%{customdata[1]:.1f}%"

                "<extra></extra>"
            )

        )

    )


    # -----------------------------------------------------
    # TOTAL OVERDUE
    # -----------------------------------------------------

    fig_loan.add_trace(

        go.Bar(

            x=loan_cycle_totals[cycle_col],

            y=loan_cycle_totals["total_overdue"],

            name="Total Overdue",

            customdata=loan_cycle_totals[
                [
                    "total_overdue",
                    "overdue_percent"
                ]
            ],

            hovertemplate=(

                "<b>Loan Cycle %{x}</b><br>"

                "Total Overdue: "
                "₱%{customdata[0]:,.2f}<br>"

                "Percent of Total Overdue: "
                "%{customdata[1]:.1f}%"

                "<extra></extra>"
            )

        )

    )


    # -----------------------------------------------------
    # LOAN CHART LAYOUT
    # -----------------------------------------------------

    fig_loan.update_layout(

        title=dict(

            text="Loan Value by Loan Cycle",

            x=0.5,

            xanchor="center"

        ),

        barmode="group",

        xaxis=dict(

            title="Loan Cycle",

            categoryorder="array",

            categoryarray=cycle_order

        ),

        yaxis=dict(

            title="Amount",

            tickformat=",.0f"

        ),

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.02,

            xanchor="center",

            x=0.5

        ),

        height=600,

        margin=dict(

            l=70,

            r=40,

            t=100,

            b=70

        )

    )


    st.plotly_chart(

        fig_loan,

        width="stretch",

        key="loan_cycle_chart"

    )


# =========================================================
# RIGHT CHART
# CLIENTS
# =========================================================

with col2:

    fig_clients = go.Figure()


    # -----------------------------------------------------
    # TOTAL CLIENTS
    # -----------------------------------------------------

    fig_clients.add_trace(

        go.Bar(

            x=client_cycle_totals[cycle_col],

            y=client_cycle_totals[
                "total_clients"
            ],

            name="Total Clients",

            customdata=client_cycle_totals[
                [
                    "total_clients",
                    "client_percent"
                ]
            ],

            hovertemplate=(

                "<b>Loan Cycle %{x}</b><br>"

                "Total Clients: "
                "%{customdata[0]:,}<br>"

                "Percent of Total Clients: "
                "%{customdata[1]:.1f}%"

                "<extra></extra>"
            )

        )

    )


    # -----------------------------------------------------
    # OVERDUE CLIENTS
    # -----------------------------------------------------

    fig_clients.add_trace(

        go.Bar(

            x=client_cycle_totals[cycle_col],

            y=client_cycle_totals[
                "overdue_clients"
            ],

            name="Overdue Clients",

            customdata=client_cycle_totals[
                [
                    "overdue_clients",
                    "overdue_client_percent"
                ]
            ],

            hovertemplate=(

                "<b>Loan Cycle %{x}</b><br>"

                "Total Overdue Clients: "
                "%{customdata[0]:,}<br>"

                "Percent of Total Overdue Clients: "
                "%{customdata[1]:.1f}%"

                "<extra></extra>"
            )

        )

    )


    # -----------------------------------------------------
    # CLIENT CHART LAYOUT
    # -----------------------------------------------------

    fig_clients.update_layout(

        title=dict(

            text="Clients by Loan Cycle",

            x=0.5,

            xanchor="center"

        ),

        barmode="group",

        xaxis=dict(

            title="Loan Cycle",

            categoryorder="array",

            categoryarray=cycle_order

        ),

        yaxis=dict(

            title="Number of Clients",

            tickformat=","

        ),

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.02,

            xanchor="center",

            x=0.5

        ),

        height=600,

        margin=dict(

            l=70,

            r=40,

            t=100,

            b=70

        )

    )


    st.plotly_chart(

        fig_clients,

        width="stretch",

        key="client_cycle_chart"

    )


# =========================================================
# SUMMARY
# =========================================================

st.caption(

    f"Credit Officer: {selected_credit_officer}"
    f" | Total Loan: ₱{overall_total_loan:,.2f}"
    f" | Total Overdue: ₱{overall_total_overdue:,.2f}"
    f" | Total Clients: {overall_total_clients:,}"
    f" | Total Overdue Clients: "
    f"{overall_overdue_clients:,}"

)
