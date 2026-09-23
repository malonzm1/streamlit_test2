from google.oauth2 import service_account
from googleapiclient.discovery import build
import plotly.graph_objects as go
import math

from googleapiclient.http import MediaIoBaseDownload

import pandas as pd
import streamlit as st
import os


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="KMFI Loan Dashboard",
    layout="wide"
)


# ============================================================
# CHECK LOGIN
# ============================================================

if st.session_state.get("logged_in_user") is None:
    st.switch_page("pages/home.py")


# ============================================================
# DATA
# ============================================================

if "data" not in st.session_state:

    st.warning(
        "Data has not been loaded yet. "
        "Please return to Home first."
    )

    st.stop()


data = st.session_state["data"]

working_data = st.session_state["working_data"]


# ============================================================
# FIND COLUMN
# ============================================================

def find_column(
    df,
    possible_names
):

    for name in possible_names:

        if name in df.columns:

            return name

    return None


# ============================================================
# FIND REQUIRED COLUMNS
# ============================================================

loan_col = find_column(
    data,
    [
        "Loan amount",
        "Loan.amount"
    ]
)


overdue_col = find_column(
    data,
    [
        "Overdue total",
        "Overdue.total"
    ]
)


client_col = find_column(
    data,
    [
        "Client name",
        "Client.name"
    ]
)


fdo_col = find_column(
    data,
    [
        "Credit officer",
        "Credit.officer"
    ]
)


branch_col = find_column(
    data,
    [
        "Branch name",
        "Branch.name"
    ]
)


area_col = find_column(
    data,
    [
        "Area",
        "Area.name"
    ]
)


cycle_col = find_column(
    data,
    [
        "Loan Cycle"
    ]
)


product_col = find_column(
    data,
    [
        "Product name"
    ]
)


# ============================================================
# FIND CENTRE COLUMN
# ============================================================

centre_col = find_column(
    data,
    [
        "Centre",
        "Center",
        "Centre name",
        "Center name",
        "Centre.name",
        "Center.name"
    ]
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

    "Area": area_col,

    "Loan Cycle": cycle_col,

    "Product name": product_col,

}


missing_columns = [

    name

    for name, column
    in required_columns.items()

    if column is None

]


if missing_columns:

    st.error(
        "The following required columns "
        "could not be found:"
    )

    st.write(
        missing_columns
    )

    st.write(
        "Available columns:"
    )

    st.write(
        list(data.columns)
    )

    st.stop()


# ============================================================
# CURRENT USER
# ============================================================

logged_in_user = (
    st.session_state[
        "logged_in_user"
    ]
)


user_role = (
    st.session_state[
        "user_role"
    ]
)


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

    AREA_MANAGERS2 = (
        st.session_state["AREA_MANAGERS2"]
    )

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


# ============================================================
# DASHBOARD TITLE / USER CAPTION
# ============================================================

if user_role == "area_manager":

    st.caption(
        "Area Manager: "
        + str(logged_in_user)
        + " | Area: "
        + str(manager_area)
    )

elif user_role == "credit_officer":

    st.caption(
        "Credit Officer: "
        + str(logged_in_user)
    )


# ============================================================
# WORKING DATA
# ============================================================

data = working_data.copy()


# ============================================================
# CONVERT NUMERIC COLUMNS
# ============================================================

data[loan_col] = pd.to_numeric(
    data[loan_col],
    errors="coerce"
).fillna(0)


data[overdue_col] = pd.to_numeric(
    data[overdue_col],
    errors="coerce"
).fillna(0)


# ============================================================
# CREDIT OFFICER DROPDOWN
# ============================================================

credit_officers = sorted(
    [
        str(x).strip()
        for x in data[fdo_col].dropna().unique()
        if str(x).strip()
        and str(x).strip().lower() != "unknown"
        and str(x).strip().lower() != "nan"
    ]
)


if user_role == "credit_officer":

    credit_officers = [
        str(logged_in_user)
    ]


if user_role == "credit_officer":

    selected_credit_officer = st.sidebar.selectbox(
        "Credit Officer:",
        credit_officers,
        index=0,
        key="product_summary_credit_officer"
    )

else:

    selected_credit_officer = st.sidebar.selectbox(
        "Credit Officer:",
        ["All Credit Officers"] + credit_officers,
        index=0,
        key="product_summary_credit_officer"
    )


# ============================================================
# FILTER BY CREDIT OFFICER
# ============================================================

if selected_credit_officer != "All Credit Officers":

    data = data[
        data[fdo_col].astype(str).str.strip()
        == selected_credit_officer
    ].copy()


# ============================================================
# CHECK DATA AFTER CREDIT OFFICER FILTER
# ============================================================

if data.empty:

    st.warning(
        "No data was found for the selected "
        "Credit Officer."
    )

    st.stop()


# ============================================================
# LOAN CYCLE DROPDOWN
# ============================================================

cycles = sorted(
    data[cycle_col]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)


cycle = st.sidebar.selectbox(
    "Loan cycle:",
    options=["All"] + cycles,
    index=0,
    key="product_summary_loan_cycle"
)


# ============================================================
# FILTER BY LOAN CYCLE
# ============================================================

if cycle != "All":

    data = data[
        data[cycle_col].astype(str).str.strip()
        == cycle
    ].copy()


# ============================================================
# CHECK DATA AFTER LOAN CYCLE FILTER
# ============================================================

if data.empty:

    st.warning(
        "No data was found for the selected "
        "Loan Cycle."
    )

    st.stop()


# ============================================================
# SINGLE SORT DROPDOWN
# ============================================================

sort_by = st.sidebar.selectbox(
    "Sort by:",
    options=[
        "Loan Product",
        "Total Loan",
        "Total Overdue",
        "Total Clients",
        "Overdue Clients"
    ],
    index=0,
    key="loan_product_sort"
)


# ============================================================
# CREATE TWO COLUMNS
# ============================================================

col1, col2 = st.columns(2)


# ============================================================
# CREATE LOAN VALUE SUMMARY
# ============================================================

product_summary = (
    data
    .groupby(product_col, as_index=False)
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
)


# ============================================================
# CREATE CLIENT SUMMARY
# ============================================================

client_summary = (
    data
    .groupby(product_col)
    .agg(
        total_clients=(
            client_col,
            "nunique"
        )
    )
    .reset_index()
)


# ============================================================
# CREATE OVERDUE CLIENT SUMMARY
# ============================================================

overdue_client_data = (
    data.loc[
        data[overdue_col] > 0
    ]
    .groupby(product_col)[client_col]
    .nunique()
    .rename(
        "overdue_clients"
    )
    .reset_index()
)


# ============================================================
# MERGE OVERDUE CLIENT COUNTS
# ============================================================

client_summary = client_summary.merge(
    overdue_client_data,
    on=product_col,
    how="left"
)


# ============================================================
# FILL PRODUCTS WITH NO OVERDUE CLIENTS
# ============================================================

client_summary["overdue_clients"] = (
    pd.to_numeric(
        client_summary["overdue_clients"],
        errors="coerce"
    )
    .fillna(0)
    .astype(int)
)


# ============================================================
# COMBINE SUMMARY DATA FOR SORTING
# ============================================================

sort_summary = product_summary.merge(
    client_summary,
    on=product_col,
    how="left"
)


sort_summary["overdue_clients"] = (
    sort_summary["overdue_clients"]
    .fillna(0)
    .astype(int)
)


# ============================================================
# SORT BOTH CHARTS USING ONE SORT OPTION
# ============================================================

if sort_by == "Total Loan":

    sort_summary = sort_summary.sort_values(
        "total_loan",
        ascending=False
    )

elif sort_by == "Total Overdue":

    sort_summary = sort_summary.sort_values(
        "total_overdue",
        ascending=False
    )

elif sort_by == "Total Clients":

    sort_summary = sort_summary.sort_values(
        "total_clients",
        ascending=False
    )

elif sort_by == "Overdue Clients":

    sort_summary = sort_summary.sort_values(
        "overdue_clients",
        ascending=False
    )

else:

    sort_summary = sort_summary.sort_values(
        product_col,
        ascending=False
    )


# ============================================================
# APPLY SAME PRODUCT ORDER TO BOTH CHARTS
# ============================================================

product_order = (
    sort_summary[
        product_col
    ]
    .tolist()
)


# ============================================================
# LEFT SIDE
# LOAN VALUE
# ============================================================

with col1:

    # ========================================================
    # SCALING FACTOR
    # ========================================================

    max_loan = (
        sort_summary["total_loan"].max()
    )


    max_overdue = (
        sort_summary["total_overdue"].max()
    )


    if max_overdue > 0:

        scale_factor = (
            max_loan
            / max_overdue
        )

    else:

        scale_factor = 1


    # ========================================================
    # CREATE SCALED VALUES
    # ========================================================

    sort_summary["scaled_overdue"] = (
        sort_summary["total_overdue"]
        * scale_factor
    )


    sort_summary["loan_plot"] = (
        sort_summary["total_loan"]
        .clip(lower=1)
        .apply(
            lambda x: math.log10(x)
        )
    )


    sort_summary["overdue_plot"] = (
        sort_summary["scaled_overdue"]
        .clip(lower=1)
        .apply(
            lambda x: math.log10(x)
        )
    )


    # ========================================================
    # FIGURE
    # ========================================================

    fig_loan = go.Figure()


    # ========================================================
    # TOTAL LOAN
    # ========================================================

    fig_loan.add_trace(
        go.Bar(
            x=sort_summary["loan_plot"],

            y=sort_summary[
                product_col
            ],

            name="Total Loan",

            orientation="h",

            offsetgroup="loan",

            width=0.35,

            xaxis="x",

            customdata=sort_summary[
                "total_loan"
            ],

            hovertemplate=(
                "<b>%{y}</b><br>"
                "Total Loan: "
                "₱%{customdata:,.2f}"
                "<extra></extra>"
            )
        )
    )


    # ========================================================
    # TOTAL OVERDUE
    # ========================================================

    fig_loan.add_trace(
        go.Bar(
            x=sort_summary[
                "overdue_plot"
            ],

            y=sort_summary[
                product_col
            ],

            name="Total Overdue",

            orientation="h",

            offsetgroup="overdue",

            width=0.35,

            xaxis="x2",

            customdata=sort_summary[
                "total_overdue"
            ],

            hovertemplate=(
                "<b>%{y}</b><br>"
                "Total Overdue: "
                "₱%{customdata:,.2f}"
                "<extra></extra>"
            )
        )
    )


    # ========================================================
    # BOTTOM SCALE — TOTAL LOAN
    # ========================================================

    loan_tick_values = [

        1,
        10,
        100,
        1_000,
        10_000,
        100_000,
        1_000_000,
        10_000_000,
        100_000_000,
        1_000_000_000

    ]


    loan_tick_positions = [

        math.log10(x)

        for x in loan_tick_values

    ]


    loan_tick_labels = [

        "1",
        "10",
        "100",
        "1K",
        "10K",
        "100K",
        "1M",
        "10M",
        "100M",
        "1B"

    ]


    # ========================================================
    # TOP SCALE — TOTAL OVERDUE
    # ========================================================

    overdue_tick_values = [

        1,
        10,
        100,
        1_000,
        10_000,
        100_000,
        1_000_000,
        10_000_000,
        100_000_000

    ]


    overdue_tick_positions = [

        math.log10(
            value * scale_factor
        )

        for value in overdue_tick_values

    ]


    overdue_tick_labels = [

        "1",
        "10",
        "100",
        "1K",
        "10K",
        "100K",
        "1M",
        "10M",
        "100M"

    ]


    # ========================================================
    # RANGE
    # ========================================================

    max_plot = max(

        sort_summary[
            "loan_plot"
        ].max(),

        sort_summary[
            "overdue_plot"
        ].max()

    )


    plot_xmax = (
        max_plot + 0.30
    )


    # ========================================================
    # LAYOUT
    # ========================================================

    fig_loan.update_layout(

        barmode="group",

        xaxis=dict(

            title=dict(
                text="Total Loan Amount",
                standoff=10
            ),

            tickmode="array",

            tickvals=loan_tick_positions,

            ticktext=loan_tick_labels,

            range=[
                0,
                plot_xmax
            ],

            showgrid=True,

            showline=True,

            zeroline=False,

            side="bottom",

            ticks="outside"
        ),


        xaxis2=dict(

            title=dict(
                text="Total Overdue",
                standoff=10
            ),

            overlaying="x",

            side="top",

            anchor="y",

            range=[
                0,
                plot_xmax
            ],

            tickmode="array",

            tickvals=overdue_tick_positions,

            ticktext=overdue_tick_labels,

            showticklabels=True,

            showline=True,

            ticks="outside",

            ticklen=6,

            showgrid=False,

            zeroline=False,

            layer="above traces"
        ),


        yaxis=dict(

            title="Product Name",

            categoryorder="array",

            categoryarray=product_order,

            autorange="reversed",

            showgrid=False

        ),


        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.18,

            xanchor="center",

            x=0.5

        ),


        height=max(
            650,
            len(product_order) * 40 + 220
        ),


        margin=dict(

            l=100,

            r=50,

            t=180,

            b=80

        )

    )


    # ========================================================
    # TITLE
    # ========================================================

    st.subheader(
        "Total Loan Amount and Total Overdue by Product"
    )


    st.plotly_chart(
        fig_loan,
        width="stretch",
        key="loan_value_product_chart"
    )


# ============================================================
# RIGHT SIDE
# LOAN CLIENTS
# ============================================================

with col2:

    # ========================================================
    # LOG TRANSFORMATION
    # ========================================================

    sort_summary[
        "total_clients_plot"
    ] = (

        sort_summary[
            "total_clients"
        ]
        .clip(lower=1)
        .apply(math.log10)

    )


    sort_summary[
        "overdue_clients_plot"
    ] = (

        sort_summary[
            "overdue_clients"
        ]
        .clip(lower=1)
        .apply(math.log10)

    )


    # ========================================================
    # FIGURE
    # ========================================================

    fig_clients = go.Figure()


    # ========================================================
    # TOTAL CLIENTS
    # ========================================================

    fig_clients.add_trace(
        go.Bar(

            y=sort_summary[
                product_col
            ],

            x=sort_summary[
                "total_clients_plot"
            ],

            orientation="h",

            name="Total Clients",

            customdata=sort_summary[
                "total_clients"
            ],

            hovertemplate=(
                "<b>%{y}</b><br>"
                "Total Clients: "
                "%{customdata:,}"
                "<extra></extra>"
            )

        )
    )


    # ========================================================
    # OVERDUE CLIENTS
    # ========================================================

    fig_clients.add_trace(
        go.Bar(

            y=sort_summary[
                product_col
            ],

            x=sort_summary[
                "overdue_clients_plot"
            ],

            orientation="h",

            name="Clients with Non-Zero Overdue",

            customdata=sort_summary[
                "overdue_clients"
            ],

            hovertemplate=(
                "<b>%{y}</b><br>"
                "Clients with Non-Zero Overdue: "
                "%{customdata:,}"
                "<extra></extra>"
            )

        )
    )


    # ========================================================
    # CLIENT AXIS
    # ========================================================

    max_clients = max(

        sort_summary[
            "total_clients"
        ].max(),

        sort_summary[
            "overdue_clients"
        ].max(),

        1

    )


    log_max = math.ceil(
        math.log10(
            max_clients
        )
    )


    tick_values = []

    tick_labels = []


    for power in range(
        log_max + 1
    ):

        value = 10 ** power

        if value <= max_clients:

            tick_values.append(
                math.log10(value)
            )

            tick_labels.append(
                f"{value:,}"
            )


    if not tick_values:

        tick_values = [0]

        tick_labels = ["1"]


    # ========================================================
    # LAYOUT
    # ========================================================

    fig_clients.update_layout(

        barmode="group",

        xaxis=dict(

            title="Number of Clients",

            type="linear",

            tickmode="array",

            tickvals=tick_values,

            ticktext=tick_labels,

            range=[
                0,
                max(
                    log_max,
                    1
                )
            ],

            showgrid=True,

            zeroline=False

        ),


        yaxis=dict(

            title="Loan Product",

            categoryorder="array",

            categoryarray=product_order,

            autorange="reversed"

        ),


        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.02,

            xanchor="center",

            x=0.5

        ),


        height=max(
            500,
            len(product_order) * 45
        ),


        margin=dict(

            l=150,

            r=40,

            t=80,

            b=70

        )

    )


    # ========================================================
    # TITLE
    # ========================================================

    st.subheader(
        "Total Clients and Clients with Non-zero Overdue by Product"
    )


    st.plotly_chart(
        fig_clients,
        width="stretch",
        key="loan_client_product_chart"
    )


# ============================================================
# CURRENT FILTER SUMMARY
# ============================================================

st.caption(
    "Credit Officer: "
    + str(selected_credit_officer)
    + " | Loan Cycle: "
    + str(cycle)
    + " | Sort by: "
    + str(sort_by)
)
