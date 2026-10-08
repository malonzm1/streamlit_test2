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

if "working_data" not in st.session_state:

    st.warning(
        "Data has not been loaded yet. "
        "Please return to Home first."
    )

    st.stop()


data = st.session_state["data"]

working_data = st.session_state["working_data"]

# ============================================================
# SIDEBAR — LOAN PRODUCT FILTER
# ============================================================

product_filter = st.sidebar.radio(
    "Loan Product:",
    options=[
        "Keep all loan products",
        "Remove ACPC/restructured/Sagip/Pagbangon/recovery"
    ],
    key="loan_product_filter"
)

if product_filter == "Remove ACPC/restructured/Sagip/Pagbangon/recovery":

    excluded_product_words = [
        "ACPC",
        "restructured",
        "sagip",
        "pagbangon",
        "recovery"
    ]

    product_text = (
        working_data["Product name"]
        .fillna("")
        .astype(str)
    )

    exclude_mask = product_text.str.contains(
        "|".join(excluded_product_words),
        case=False,
        na=False,
        regex=True
    )

    working_data = working_data[
        ~exclude_mask
    ].copy()


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
    working_data,
    [
        "Loan amount",
        "Loan.amount"
    ]
)


overdue_col = find_column(
    working_data,
    [
        "Overdue total",
        "Overdue.total"
    ]
)


client_col = find_column(
    working_data,
    [
        "Client name",
        "Client.name"
    ]
)


fdo_col = find_column(
    working_data,
    [
        "Credit officer",
        "Credit.officer"
    ]
)


branch_col = find_column(
    working_data,
    [
        "Branch name",
        "Branch.name"
    ]
)


area_col = find_column(
    working_data,
    [
        "Area",
        "Area.name"
    ]
)


cycle_col = find_column(
    working_data,
    [
        "Loan Cycle"
    ]
)


product_col = find_column(
    working_data,
    [
        "Product name"
    ]
)


# ============================================================
# FIND CENTRE COLUMN
# ============================================================

centre_col = find_column(
    working_data,
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

logged_in_user = st.session_state.get(
    "logged_in_user"
)

user_role = st.session_state.get(
    "user_role"
)


# ============================================================
# GET ROLE MAPPINGS
# ============================================================

AREA_MANAGERS2 = st.session_state.get(
    "AREA_MANAGERS2",
    {}
)

BRANCH_MANAGERS2 = st.session_state.get(
    "BRANCH_MANAGERS2",
    {}
)


# ============================================================
# SIDEBAR USER INFORMATION
# ============================================================

st.sidebar.success(
    "Logged in as: "
    + str(logged_in_user)
)


# ============================================================
# DETERMINE USER'S AREA / BRANCH
# ============================================================

manager_area = None
manager_branch = None


if user_role == "credit_officer":

    st.sidebar.info(
        "Role: Credit Officer"
    )


elif user_role == "area_manager":

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


elif user_role == "branch_manager":

    manager_branch = BRANCH_MANAGERS2.get(
        logged_in_user
    )

    if manager_branch is None:

        st.error(
            "This Branch Manager is not assigned "
            "to a Branch."
        )

        st.stop()

    st.sidebar.info(
        "Role: Branch Manager"
    )

    st.sidebar.info(
        "Branch: "
        + str(manager_branch)
    )


elif user_role == "superuser":

    st.sidebar.info(
        "Role: Administrator"
    )


else:

    st.error(
        "Unknown user role: "
        + str(user_role)
    )

    st.stop()


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


elif user_role == "branch_manager":

    st.caption(
        "Branch Manager: "
        + str(logged_in_user)
        + " | Branch: "
        + str(manager_branch)
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
# CLEAN DATA VALUES
# ============================================================

data[area_col] = (
    data[area_col]
    .astype(str)
    .str.strip()
)

data[branch_col] = (
    data[branch_col]
    .astype(str)
    .str.strip()
)

data[fdo_col] = (
    data[fdo_col]
    .astype(str)
    .str.strip()
)


# ============================================================
# CREATE LIST OF AREA MANAGERS
# ============================================================

area_manager_names = sorted(
    [
        str(x).strip()
        for x in AREA_MANAGERS2.keys()
        if str(x).strip()
        and str(x).strip().lower() != "nan"
    ]
)


# ============================================================
# CREATE LIST OF BRANCH MANAGERS
# ============================================================

branch_manager_names = sorted(
    [
        str(x).strip()
        for x in BRANCH_MANAGERS2.keys()
        if str(x).strip()
        and str(x).strip().lower() != "nan"
    ]
)


# ============================================================
# CREATE LIST OF CREDIT OFFICERS
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


# ============================================================
# ROLE-BASED FILTER
# ============================================================

# This variable is used later in the filter summary.
selected_area_manager = "All Area Managers"
selected_branch_manager = "All Branch Managers"
selected_credit_officer = "All Credit Officers"

filter_type = "All data"


# ============================================================
# CREDIT OFFICER
# ============================================================
#
# Credit Officer:
#   - No radio buttons
#   - No dropdown
#   - Automatically sees own data
#
# ============================================================

if user_role == "credit_officer":

    selected_credit_officer = str(
        logged_in_user
    ).strip()

    data = data[
        data[fdo_col].astype(str).str.strip()
        == selected_credit_officer
    ].copy()


# ============================================================
# ADMIN
# ============================================================
#
# Admin radio buttons:
#
#   All data
#   Area managers
#   Branch managers
#   Credit officers
#
# ============================================================

elif user_role == "superuser":

    filter_type = st.sidebar.radio(
        "View:",
        options=[
            "All data",
            "Area managers",
            "Branch managers",
            "Credit officers"
        ],
        index=0,
        key="admin_view_filter"
    )


    # ========================================================
    # ALL DATA
    # ========================================================

    if filter_type == "All data":

        # No dropdown

        pass


    # ========================================================
    # AREA MANAGERS
    # ========================================================

    elif filter_type == "Area managers":

        selected_area_manager = st.sidebar.selectbox(
            "Area Manager:",
            options=[
                "All Area Managers"
            ] + area_manager_names,
            index=0,
            key="admin_area_manager_filter"
        )


        if (
            selected_area_manager
            != "All Area Managers"
        ):

            selected_area = AREA_MANAGERS2.get(
                selected_area_manager
            )

            if selected_area is None:

                st.error(
                    "The selected Area Manager "
                    "is not assigned to an Area."
                )

                st.stop()


            data = data[
                data[area_col].astype(str).str.strip()
                == str(selected_area).strip()
            ].copy()


    # ========================================================
    # BRANCH MANAGERS
    # ========================================================

    elif filter_type == "Branch managers":

        selected_branch_manager = st.sidebar.selectbox(
            "Branch Manager:",
            options=[
                "All Branch Managers"
            ] + branch_manager_names,
            index=0,
            key="admin_branch_manager_filter"
        )


        if (
            selected_branch_manager
            != "All Branch Managers"
        ):

            selected_branch = BRANCH_MANAGERS2.get(
                selected_branch_manager
            )

            if selected_branch is None:

                st.error(
                    "The selected Branch Manager "
                    "is not assigned to a Branch."
                )

                st.stop()


            data = data[
                data[branch_col].astype(str).str.strip()
                == str(selected_branch).strip()
            ].copy()


    # ========================================================
    # CREDIT OFFICERS
    # ========================================================

    elif filter_type == "Credit officers":

        selected_credit_officer = st.sidebar.selectbox(
            "Credit Officer:",
            options=[
                "All Credit Officers"
            ] + credit_officers,
            index=0,
            key="admin_credit_officer_filter"
        )


        if (
            selected_credit_officer
            != "All Credit Officers"
        ):

            data = data[
                data[fdo_col].astype(str).str.strip()
                == selected_credit_officer
            ].copy()


# ============================================================
# AREA MANAGER
# ============================================================
#
# Area Manager radio buttons:
#
#   All data
#   Branch managers
#   Credit officers
#
# The Area Manager can only see data belonging to
# his/her assigned Area.
#
# ============================================================

elif user_role == "area_manager":

    filter_type = st.sidebar.radio(
        "View:",
        options=[
            "All data",
            "Branch managers",
            "Credit officers"
        ],
        index=0,
        key="area_manager_view_filter"
    )


    # ========================================================
    # FIRST RESTRICT DATA TO AREA
    # ========================================================

    area_data = data[
        data[area_col].astype(str).str.strip()
        == str(manager_area).strip()
    ].copy()


    # ========================================================
    # ALL DATA
    # ========================================================

    if filter_type == "All data":

        data = area_data.copy()


    # ========================================================
    # BRANCH MANAGERS
    # ========================================================

    elif filter_type == "Branch managers":

        # ----------------------------------------------------
        # Find branches belonging to this Area
        # ----------------------------------------------------

        area_branches = sorted(
            area_data[branch_col]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )


        # ----------------------------------------------------
        # Find Branch Managers whose branch belongs to
        # this Area
        # ----------------------------------------------------

        available_branch_managers = []

        for (
            manager,
            branch
        ) in BRANCH_MANAGERS2.items():

            manager = str(
                manager
            ).strip()

            branch = str(
                branch
            ).strip()


            if branch in area_branches:

                available_branch_managers.append(
                    manager
                )


        available_branch_managers = sorted(
            set(
                available_branch_managers
            )
        )


        # ----------------------------------------------------
        # Branch Manager dropdown
        # ----------------------------------------------------

        selected_branch_manager = st.sidebar.selectbox(
            "Branch Manager:",
            options=[
                "All Branch Managers"
            ] + available_branch_managers,
            index=0,
            key="area_branch_manager_filter"
        )


        # ----------------------------------------------------
        # All Branch Managers in the Area
        # ----------------------------------------------------

        if (
            selected_branch_manager
            == "All Branch Managers"
        ):

            data = area_data.copy()


        # ----------------------------------------------------
        # One Branch Manager
        # ----------------------------------------------------

        else:

            selected_branch = BRANCH_MANAGERS2.get(
                selected_branch_manager
            )


            if selected_branch is None:

                st.error(
                    "The selected Branch Manager "
                    "is not assigned to a Branch."
                )

                st.stop()


            data = area_data[
                area_data[branch_col]
                .astype(str)
                .str.strip()
                == str(selected_branch).strip()
            ].copy()


    # ========================================================
    # CREDIT OFFICERS
    # ========================================================

    elif filter_type == "Credit officers":

        # ----------------------------------------------------
        # Credit officers belonging to this Area
        # ----------------------------------------------------

        available_credit_officers = sorted(
            [
                str(x).strip()
                for x in area_data[
                    fdo_col
                ].dropna().unique()
                if str(x).strip()
                and str(x).strip().lower()
                != "unknown"
                and str(x).strip().lower()
                != "nan"
            ]
        )


        # ----------------------------------------------------
        # Credit Officer dropdown
        # ----------------------------------------------------

        selected_credit_officer = st.sidebar.selectbox(
            "Credit Officer:",
            options=[
                "All Credit Officers"
            ] + available_credit_officers,
            index=0,
            key="area_credit_officer_filter"
        )


        # ----------------------------------------------------
        # All Credit Officers in Area
        # ----------------------------------------------------

        if (
            selected_credit_officer
            == "All Credit Officers"
        ):

            data = area_data.copy()


        # ----------------------------------------------------
        # One Credit Officer
        # ----------------------------------------------------

        else:

            data = area_data[
                area_data[fdo_col]
                .astype(str)
                .str.strip()
                == selected_credit_officer
            ].copy()


# ============================================================
# BRANCH MANAGER
# ============================================================
#
# Branch Manager radio buttons:
#
#   All data
#   Credit officers
#
# The Branch Manager can only see data belonging to
# his/her assigned Branch.
#
# ============================================================

elif user_role == "branch_manager":

    filter_type = st.sidebar.radio(
        "View:",
        options=[
            "All data",
            "Credit officers"
        ],
        index=0,
        key="branch_manager_view_filter"
    )


    # ========================================================
    # FIRST RESTRICT DATA TO BRANCH
    # ========================================================

    branch_data = data[
        data[branch_col].astype(str).str.strip()
        == str(manager_branch).strip()
    ].copy()


    # ========================================================
    # ALL DATA
    # ========================================================

    if filter_type == "All data":

        data = branch_data.copy()


    # ========================================================
    # CREDIT OFFICERS
    # ========================================================

    elif filter_type == "Credit officers":

        available_credit_officers = sorted(
            [
                str(x).strip()
                for x in branch_data[
                    fdo_col
                ].dropna().unique()
                if str(x).strip()
                and str(x).strip().lower()
                != "unknown"
                and str(x).strip().lower()
                != "nan"
            ]
        )


        # ----------------------------------------------------
        # Credit Officer dropdown
        # ----------------------------------------------------

        selected_credit_officer = st.sidebar.selectbox(
            "Credit Officer:",
            options=[
                "All Credit Officers"
            ] + available_credit_officers,
            index=0,
            key="branch_credit_officer_filter"
        )


        # ----------------------------------------------------
        # All Credit Officers in Branch
        # ----------------------------------------------------

        if (
            selected_credit_officer
            == "All Credit Officers"
        ):

            data = branch_data.copy()


        # ----------------------------------------------------
        # One Credit Officer
        # ----------------------------------------------------

        else:

            data = branch_data[
                branch_data[fdo_col]
                .astype(str)
                .str.strip()
                == selected_credit_officer
            ].copy()


# ============================================================
# CHECK DATA AFTER ROLE FILTER
# ============================================================

if data.empty:

    st.warning(
        "No data was found for the selected "
        "filter."
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
    options=[
        "All"
    ] + cycles,
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
    .groupby(
        product_col,
        as_index=False
    )
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
    .groupby(
        product_col
    )
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
    .groupby(
        product_col
    )[client_col]
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

client_summary[
    "overdue_clients"
] = (
    pd.to_numeric(
        client_summary[
            "overdue_clients"
        ],
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


sort_summary[
    "overdue_clients"
] = (
    sort_summary[
        "overdue_clients"
    ]
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
        sort_summary[
            "total_loan"
        ].max()
    )


    max_overdue = (
        sort_summary[
            "total_overdue"
        ].max()
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

    sort_summary[
        "scaled_overdue"
    ] = (
        sort_summary[
            "total_overdue"
        ]
        * scale_factor
    )


    sort_summary[
        "loan_plot"
    ] = (
        sort_summary[
            "total_loan"
        ]
        .clip(lower=1)
        .apply(
            lambda x: math.log10(x)
        )
    )


    sort_summary[
        "overdue_plot"
    ] = (
        sort_summary[
            "scaled_overdue"
        ]
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

            x=sort_summary[
                "loan_plot"
            ],

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

if user_role == "superuser":

    st.caption(
        "View: "
        + str(filter_type)
        + " | Area Manager: "
        + str(selected_area_manager)
        + " | Branch Manager: "
        + str(selected_branch_manager)
        + " | Credit Officer: "
        + str(selected_credit_officer)
        + " | Loan Cycle: "
        + str(cycle)
        + " | Sort by: "
        + str(sort_by)
    )


elif user_role == "area_manager":

    st.caption(
        "View: "
        + str(filter_type)
        + " | Area: "
        + str(manager_area)
        + " | Branch Manager: "
        + str(selected_branch_manager)
        + " | Credit Officer: "
        + str(selected_credit_officer)
        + " | Loan Cycle: "
        + str(cycle)
        + " | Sort by: "
        + str(sort_by)
    )


elif user_role == "branch_manager":

    st.caption(
        "View: "
        + str(filter_type)
        + " | Branch: "
        + str(manager_branch)
        + " | Credit Officer: "
        + str(selected_credit_officer)
        + " | Loan Cycle: "
        + str(cycle)
        + " | Sort by: "
        + str(sort_by)
    )


elif user_role == "credit_officer":

    st.caption(
        "Credit Officer: "
        + str(logged_in_user)
        + " | Loan Cycle: "
        + str(cycle)
        + " | Sort by: "
        + str(sort_by)
    )
