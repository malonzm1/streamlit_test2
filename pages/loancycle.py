from google.oauth2 import service_account
from googleapiclient.discovery import build
import plotly.graph_objects as go
import math

from googleapiclient.http import MediaIoBaseDownload

import pandas as pd
import streamlit as st
import os


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="KMFI Loan Cycle",
    layout="wide"
)


# =========================================================
# CHECK LOGIN
# =========================================================

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


# =========================================================
# ORIGINAL COMPLETE DATA
# =========================================================

data = st.session_state["data"]


# =========================================================
# ROLE-FILTERED DATA
# =========================================================

combined_data = st.session_state.get(
    "working_data",
    data.copy()
)

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

    # Words to search for in Product name
    excluded_product_words = [
        "ACPC",
        "restructured",
        "sagip",
        "pagbangon",
        "recovery"
    ]

    # Create a mask identifying products containing any
    # of the excluded words, case-insensitively
    product_text = (
        combined_data["Product name"]
        .fillna("")
        .astype(str)
    )

    exclude_mask = product_text.str.contains(
        "|".join(excluded_product_words),
        case=False,
        na=False,
        regex=True
    )

    # Remove those records
    combined_data = combined_data[
        ~exclude_mask
    ].copy()
    
    product_text = (
        data["Product name"]
        .fillna("")
        .astype(str)
    )

    exclude_mask = product_text.str.contains(
        "|".join(excluded_product_words),
        case=False,
        na=False,
        regex=True
    )

    # Remove those records
    data = data[
        ~exclude_mask
    ].copy()

# =========================================================
# CURRENT USER
# =========================================================

logged_in_user = st.session_state.get(
    "logged_in_user"
)

user_role = st.session_state.get(
    "user_role"
)


# =========================================================
# ROLE MAPPINGS
# =========================================================

AREA_MANAGERS2 = st.session_state.get(
    "AREA_MANAGERS2",
    {}
)


BRANCH_MANAGERS2 = st.session_state.get(
    "BRANCH_MANAGERS2",
    {}
)


# =========================================================
# SIDEBAR USER INFORMATION
# =========================================================

st.sidebar.success(
    "Logged in as: "
    + str(logged_in_user)
)


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


# =========================================================
# LOGOUT
# =========================================================

if st.sidebar.button(
    "Logout",
    key="logout_button"
):

    st.session_state["authenticated"] = False

    st.session_state["logged_in_user"] = None

    st.session_state["user_role"] = None

    st.switch_page(
        "pages/home.py"
    )


# =========================================================
# FIND COLUMN
# =========================================================

def find_column(
    df,
    candidates
):

    for col in candidates:

        if col in df.columns:

            return col

    return None


# =========================================================
# FIND REQUIRED COLUMNS
#
# Use the ORIGINAL COMPLETE DATA so that Admin can
# access Area, Branch, and Credit Officer filters.
# =========================================================

cycle_col = find_column(
    data,
    [
        "Loan Cycle"
    ]
)


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


required_columns = {

    "Loan Cycle": cycle_col,

    "Loan amount": loan_col,

    "Overdue total": overdue_col,

    "Client": client_col,

    "Credit officer": fdo_col,

    "Branch name": branch_col,

    "Area": area_col

}


missing = [

    name

    for name, col
    in required_columns.items()

    if col is None

]


if missing:

    st.error(
        "The following required columns were not found: "
        + ", ".join(missing)
    )

    st.stop()


# =========================================================
# CREATE BASE DATA
#
# This is cleaned BEFORE role filtering.
# =========================================================

base_data = data.copy()


# =========================================================
# CONVERT NUMERIC COLUMNS
# =========================================================

base_data[loan_col] = pd.to_numeric(
    base_data[loan_col],
    errors="coerce"
).fillna(0)


base_data[overdue_col] = pd.to_numeric(
    base_data[overdue_col],
    errors="coerce"
).fillna(0)


# =========================================================
# CLEAN LOAN CYCLE
# =========================================================

base_data[cycle_col] = (
    base_data[cycle_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# CLEAN CREDIT OFFICER
# =========================================================

base_data[fdo_col] = (
    base_data[fdo_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# CLEAN BRANCH
# =========================================================

base_data[branch_col] = (
    base_data[branch_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# CLEAN AREA
# =========================================================

base_data[area_col] = (
    base_data[area_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# CLEAN CLIENT
# =========================================================

base_data["_client_clean"] = (
    base_data[client_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# REMOVE EMPTY / NAN LOAN CYCLES
# =========================================================

base_data = base_data[
    (base_data[cycle_col] != "")
    &
    (
        base_data[
            cycle_col
        ].str.lower()
        != "nan"
    )
].copy()


# =========================================================
# VARIABLES USED BY FILTER MENUS
# =========================================================

selected_area_manager = None

selected_branch_manager = None

selected_credit_officer = None


# =========================================================
# ADMINISTRATOR FILTER
#
# Admin:
#   All data
#   Area managers
#   Branch managers
#   Credit officers
# =========================================================

if user_role == "superuser":

    admin_view = st.sidebar.radio(

        "View data as:",

        [
            "All data",
            "Area managers",
            "Branch managers",
            "Credit officers"
        ],

        key="loan_cycle_admin_view"

    )


    # =====================================================
    # ADMIN -> ALL DATA
    # =====================================================

    if admin_view == "All data":

        working_data = base_data.copy()


    # =====================================================
    # ADMIN -> AREA MANAGERS
    # =====================================================

    elif admin_view == "Area managers":

        area_manager_options = sorted(

            [

                str(manager)

                for manager
                in AREA_MANAGERS2.keys()

                if str(manager).strip() != ""

            ]

        )


        if not area_manager_options:

            st.sidebar.warning(
                "No Area Managers are available."
            )

            working_data = (
                base_data.iloc[0:0].copy()
            )

        else:

            selected_area_manager = (
                st.sidebar.selectbox(

                    "Select Area Manager:",

                    area_manager_options,

                    key=(
                        "loan_cycle_admin_"
                        "area_manager"
                    )

                )
            )


            selected_area = (
                AREA_MANAGERS2.get(
                    selected_area_manager
                )
            )


            working_data = base_data[
                base_data[area_col]
                .astype(str)
                .str.strip()
                ==
                str(selected_area)
                .strip()
            ].copy()


    # =====================================================
    # ADMIN -> BRANCH MANAGERS
    # =====================================================

    elif admin_view == "Branch managers":

        branch_manager_options = sorted(

            [

                str(manager)

                for manager
                in BRANCH_MANAGERS2.keys()

                if str(manager).strip() != ""

            ]

        )


        if not branch_manager_options:

            st.sidebar.warning(
                "No Branch Managers are available."
            )

            working_data = (
                base_data.iloc[0:0].copy()
            )

        else:

            selected_branch_manager = (
                st.sidebar.selectbox(

                    "Select Branch Manager:",

                    branch_manager_options,

                    key=(
                        "loan_cycle_admin_"
                        "branch_manager"
                    )

                )
            )


            selected_branch = (
                BRANCH_MANAGERS2.get(
                    selected_branch_manager
                )
            )


            working_data = base_data[
                base_data[branch_col]
                .astype(str)
                .str.strip()
                ==
                str(selected_branch)
                .strip()
            ].copy()


    # =====================================================
    # ADMIN -> CREDIT OFFICERS
    # =====================================================

    else:

        credit_officer_options = sorted(

            [

                officer

                for officer
                in base_data[fdo_col].unique()

                if officer

                and officer.lower() != "nan"

                and officer.lower() != "unknown"

            ]

        )


        if not credit_officer_options:

            st.sidebar.warning(
                "No Credit Officers are available."
            )

            working_data = (
                base_data.iloc[0:0].copy()
            )

        else:

            selected_credit_officer = (
                st.sidebar.selectbox(

                    "Select Credit Officer:",

                    credit_officer_options,

                    key=(
                        "loan_cycle_admin_"
                        "credit_officer"
                    )

                )
            )


            working_data = base_data[
                base_data[fdo_col]
                ==
                selected_credit_officer
            ].copy()


# =========================================================
# AREA MANAGER FILTER
#
# Area Manager:
#   All data
#   Branch managers
#   Credit officers
# =========================================================

elif user_role == "area_manager":

    area_manager_view = st.sidebar.radio(

        "View data as:",

        [
            "All data",
            "Branch managers",
            "Credit officers"
        ],

        key="loan_cycle_area_manager_view"

    )


    # =====================================================
    # AREA MANAGER'S DATA
    #
    # Start from combined_data because Home has already
    # restricted this user to their own Area.
    # =====================================================

    area_data = combined_data.copy()


    # -----------------------------------------------------
    # Re-clean numeric columns
    # -----------------------------------------------------

    area_data[loan_col] = pd.to_numeric(
        area_data[loan_col],
        errors="coerce"
    ).fillna(0)


    area_data[overdue_col] = pd.to_numeric(
        area_data[overdue_col],
        errors="coerce"
    ).fillna(0)


    # -----------------------------------------------------
    # Re-clean text columns
    # -----------------------------------------------------

    area_data[cycle_col] = (
        area_data[cycle_col]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    area_data[fdo_col] = (
        area_data[fdo_col]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    area_data[branch_col] = (
        area_data[branch_col]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    area_data[area_col] = (
        area_data[area_col]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    area_data["_client_clean"] = (
        area_data[client_col]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    # =====================================================
    # AREA MANAGER -> ALL DATA
    # =====================================================

    if area_manager_view == "All data":

        working_data = area_data.copy()


    # =====================================================
    # AREA MANAGER -> BRANCH MANAGERS
    # =====================================================

    elif area_manager_view == "Branch managers":

        # Branches actually available to this Area Manager

        area_branches = set(

            area_data[
                branch_col
            ]

            .dropna()

            .astype(str)

            .str.strip()

            .loc[
                lambda x: x != ""
            ]

            .unique()

        )


        # Only show Branch Managers whose branch
        # belongs to this Area Manager

        branch_manager_options = sorted(

            [

                str(manager)

                for manager, branch
                in BRANCH_MANAGERS2.items()

                if str(branch).strip()
                in area_branches

            ]

        )


        if not branch_manager_options:

            st.sidebar.warning(
                "No Branch Managers were found "
                "in your Area."
            )

            working_data = (
                area_data.iloc[0:0].copy()
            )

        else:

            selected_branch_manager = (
                st.sidebar.selectbox(

                    "Select Branch Manager:",

                    branch_manager_options,

                    key=(
                        "loan_cycle_area_"
                        "branch_manager"
                    )

                )
            )


            selected_branch = (
                BRANCH_MANAGERS2.get(
                    selected_branch_manager
                )
            )


            working_data = area_data[
                area_data[branch_col]
                .astype(str)
                .str.strip()
                ==
                str(selected_branch)
                .strip()
            ].copy()


    # =====================================================
    # AREA MANAGER -> CREDIT OFFICERS
    # =====================================================

    else:

        credit_officer_options = sorted(

            [

                officer

                for officer
                in area_data[fdo_col].unique()

                if officer

                and officer.lower() != "nan"

                and officer.lower() != "unknown"

            ]

        )


        if not credit_officer_options:

            st.sidebar.warning(
                "No Credit Officers were found "
                "in your Area."
            )

            working_data = (
                area_data.iloc[0:0].copy()
            )

        else:

            selected_credit_officer = (
                st.sidebar.selectbox(

                    "Select Credit Officer:",

                    credit_officer_options,

                    key=(
                        "loan_cycle_area_"
                        "credit_officer"
                    )

                )
            )


            working_data = area_data[
                area_data[fdo_col]
                ==
                selected_credit_officer
            ].copy()


# =========================================================
# BRANCH MANAGER
#
# Home has already restricted this user to their branch.
# =========================================================

elif user_role == "branch_manager":

    working_data = combined_data.copy()


# =========================================================
# CREDIT OFFICER
#
# Home has already restricted this user to their data.
# =========================================================

elif user_role == "credit_officer":

    working_data = combined_data.copy()


# =========================================================
# FALLBACK
# =========================================================

else:

    working_data = combined_data.copy()


# =========================================================
# FINAL CLEANING
#
# IMPORTANT:
# Recreate _client_clean AFTER role filtering.
#
# This prevents:
# KeyError: '_client_clean'
# =========================================================

working_data[loan_col] = pd.to_numeric(
    working_data[loan_col],
    errors="coerce"
).fillna(0)


working_data[overdue_col] = pd.to_numeric(
    working_data[overdue_col],
    errors="coerce"
).fillna(0)


working_data[cycle_col] = (
    working_data[cycle_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


working_data[fdo_col] = (
    working_data[fdo_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


working_data[branch_col] = (
    working_data[branch_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


working_data[area_col] = (
    working_data[area_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


working_data["_client_clean"] = (
    working_data[client_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# REMOVE EMPTY / NAN CLIENTS
# =========================================================

working_data = working_data[
    (
        working_data[
            "_client_clean"
        ]
        != ""
    )
    &
    (
        working_data[
            "_client_clean"
        ]
        .str.lower()
        != "nan"
    )
].copy()


# =========================================================
# CHECK FILTERED DATA
# =========================================================

if working_data.empty:

    st.warning(
        "No data was found for the selected filters."
    )

    st.stop()


# =========================================================
# CREDIT OFFICER DROPDOWN
#
# Only show this dropdown when the selected view has
# not already selected a specific Credit Officer.
#
# Therefore:
#
# Admin -> All data:
#     Credit Officer dropdown
#
# Admin -> Area Manager:
#     Credit Officer dropdown
#
# Admin -> Branch Manager:
#     Credit Officer dropdown
#
# Admin -> Credit Officer:
#     already selected, so no second dropdown
#
# Area Manager -> All data:
#     Credit Officer dropdown
#
# Area Manager -> Branch Manager:
#     Credit Officer dropdown
#
# Area Manager -> Credit Officer:
#     already selected
#
# Branch Manager / Credit Officer:
#     existing behavior
# =========================================================

if selected_credit_officer is None:

    credit_officers = sorted(

        [

            officer

            for officer
            in working_data[fdo_col].unique()

            if officer

            and officer.lower() != "nan"

            and officer.lower() != "unknown"

        ]

    )


    if user_role == "credit_officer":

        if credit_officers:

            selected_credit_officer = (
                credit_officers[0]
            )

            working_data = working_data[
                working_data[fdo_col]
                ==
                selected_credit_officer
            ].copy()

    else:

        if credit_officers:

            selected_credit_officer = (
                st.sidebar.selectbox(

                    "Credit Officer:",

                    [
                        "All Credit Officers"
                    ]
                    +
                    credit_officers,

                    index=0,

                    key=(
                        "loan_cycle_credit_officer"
                    )

                )
            )


            # ---------------------------------------------
            # Filter only when a specific officer is chosen
            # ---------------------------------------------

            if (
                selected_credit_officer
                != "All Credit Officers"
            ):

                working_data = working_data[
                    working_data[fdo_col]
                    ==
                    selected_credit_officer
                ].copy()

        else:

            selected_credit_officer = (
                "All Credit Officers"
            )


# =========================================================
# FINAL CHECK AFTER CREDIT OFFICER FILTER
# =========================================================

if working_data.empty:

    st.warning(
        "No data was found for the selected "
        "Credit Officer."
    )

    st.stop()


# =========================================================
# RECREATE CLIENT COLUMN AFTER FINAL FILTER
# =========================================================

working_data["_client_clean"] = (
    working_data[client_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


working_data = working_data[
    (
        working_data[
            "_client_clean"
        ]
        != ""
    )
    &
    (
        working_data[
            "_client_clean"
        ]
        .str.lower()
        != "nan"
    )
].copy()


# =========================================================
# OVERALL TOTALS
# =========================================================

overall_total_loan = (
    working_data[
        loan_col
    ].sum()
)


overall_total_overdue = (
    working_data[
        overdue_col
    ].sum()
)


# =========================================================
# CLIENT TOTALS
# =========================================================

overall_total_clients = (
    working_data[
        "_client_clean"
    ]
    .nunique()
)


overall_overdue_clients = (
    working_data.loc[
        working_data[
            overdue_col
        ] > 0,

        "_client_clean"
    ]
    .nunique()
)


# =========================================================
# LOAN VALUE BY LOAN CYCLE
# =========================================================

loan_cycle_totals = (

    working_data

    .groupby(
        cycle_col
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

    .reset_index()

)


# =========================================================
# CLIENTS BY LOAN CYCLE
# =========================================================

total_clients_by_cycle = (

    working_data

    .groupby(
        cycle_col
    )

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
        working_data[
            overdue_col
        ] > 0
    ]

    .groupby(
        cycle_col
    )

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


client_cycle_totals[
    "overdue_clients"
] = (

    client_cycle_totals[
        "overdue_clients"
    ]

    .fillna(0)

    .astype(int)

)


# =========================================================
# CREATE PERCENTAGES
# =========================================================


# ---------------------------------------------------------
# LOAN PERCENTAGE
# ---------------------------------------------------------

if overall_total_loan > 0:

    loan_cycle_totals[
        "loan_percent"
    ] = (

        loan_cycle_totals[
            "total_loan"
        ]

        / overall_total_loan

        * 100

    )

else:

    loan_cycle_totals[
        "loan_percent"
    ] = 0


# ---------------------------------------------------------
# OVERDUE PERCENTAGE OF TOTAL OVERDUE
# ---------------------------------------------------------

if overall_total_overdue > 0:

    loan_cycle_totals[
        "overdue_percent"
    ] = (

        loan_cycle_totals[
            "total_overdue"
        ]

        / overall_total_overdue

        * 100

    )

else:

    loan_cycle_totals[
        "overdue_percent"
    ] = 0


# ---------------------------------------------------------
# CLIENT PERCENTAGE
# ---------------------------------------------------------

if overall_total_clients > 0:

    client_cycle_totals[
        "client_percent"
    ] = (

        client_cycle_totals[
            "total_clients"
        ]

        / overall_total_clients

        * 100

    )

else:

    client_cycle_totals[
        "client_percent"
    ] = 0


# ---------------------------------------------------------
# OVERDUE CLIENT PERCENTAGE OF TOTAL OVERDUE CLIENTS
# ---------------------------------------------------------

if overall_overdue_clients > 0:

    client_cycle_totals[
        "overdue_client_percent"
    ] = (

        client_cycle_totals[
            "overdue_clients"
        ]

        / overall_overdue_clients

        * 100

    )

else:

    client_cycle_totals[
        "overdue_client_percent"
    ] = 0


# =========================================================
# SORT LOAN CYCLES NUMERICALLY
# =========================================================

try:

    loan_cycle_totals[
        "_cycle_numeric"
    ] = pd.to_numeric(

        loan_cycle_totals[
            cycle_col
        ],

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
    loan_cycle_totals[
        cycle_col
    ].tolist()
)


client_cycle_totals[
    cycle_col
] = (

    client_cycle_totals[
        cycle_col
    ]

    .astype(str)

)


client_cycle_totals = (

    client_cycle_totals

    .set_index(
        cycle_col
    )

    .reindex(
        cycle_order
    )

    .reset_index()

)


# =========================================================
# ADD RATIO PERCENTAGES FOR HOVER
# =========================================================


# ---------------------------------------------------------
# OVERDUE LOAN AS % OF TOTAL LOAN
# ---------------------------------------------------------

loan_cycle_totals[
    "overdue_of_loan_percent"
] = (

    loan_cycle_totals[
        "total_overdue"
    ]

    .div(

        loan_cycle_totals[
            "total_loan"
        ].replace(
            0,
            pd.NA
        )

    )

    .fillna(0)

    * 100

)


# ---------------------------------------------------------
# OVERDUE CLIENTS AS % OF TOTAL CLIENTS
# ---------------------------------------------------------

client_cycle_totals[
    "overdue_of_clients_percent"
] = (

    client_cycle_totals[
        "overdue_clients"
    ]

    .div(

        client_cycle_totals[
            "total_clients"
        ].replace(
            0,
            pd.NA
        )

    )

    .fillna(0)

    * 100

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

            x=loan_cycle_totals[
                cycle_col
            ],

            y=loan_cycle_totals[
                "total_loan"
            ],

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

            x=loan_cycle_totals[
                cycle_col
            ],

            y=loan_cycle_totals[
                "total_overdue"
            ],

            name="Total Overdue",

            customdata=loan_cycle_totals[
                [
                    "total_overdue",
                    "overdue_percent",
                    "overdue_of_loan_percent"
                ]
            ],

            hovertemplate=(

                "<b>Loan Cycle %{x}</b><br>"

                "Total Overdue: "
                "₱%{customdata[0]:,.2f}<br>"

                "Percent of Total Overdue: "
                "%{customdata[1]:.1f}%<br>"

                "Overdue / Total Loan: "
                "%{customdata[2]:.1f}%"

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

            x=client_cycle_totals[
                cycle_col
            ],

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

            x=client_cycle_totals[
                cycle_col
            ],

            y=client_cycle_totals[
                "overdue_clients"
            ],

            name="Overdue Clients",

            customdata=client_cycle_totals[
                [
                    "overdue_clients",
                    "overdue_client_percent",
                    "overdue_of_clients_percent"
                ]
            ],

            hovertemplate=(

                "<b>Loan Cycle %{x}</b><br>"

                "Total Overdue Clients: "
                "%{customdata[0]:,}<br>"

                "Percent of Total Overdue Clients: "
                "%{customdata[1]:.1f}%<br>"

                "Overdue Clients / Total Clients: "
                "%{customdata[2]:.1f}%"

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

if user_role == "superuser":

    if selected_area_manager is not None:

        view_label = (
            "Area Manager: "
            + str(selected_area_manager)
        )

    elif selected_branch_manager is not None:

        view_label = (
            "Branch Manager: "
            + str(selected_branch_manager)
        )

    elif (
        selected_credit_officer is not None
        and
        selected_credit_officer
        != "All Credit Officers"
    ):

        view_label = (
            "Credit Officer: "
            + str(selected_credit_officer)
        )

    else:

        view_label = "All data"


elif user_role == "area_manager":

    if selected_branch_manager is not None:

        view_label = (
            "Branch Manager: "
            + str(selected_branch_manager)
        )

    elif (
        selected_credit_officer is not None
        and
        selected_credit_officer
        != "All Credit Officers"
    ):

        view_label = (
            "Credit Officer: "
            + str(selected_credit_officer)
        )

    else:

        view_label = (
            "Area: "
            + str(manager_area)
        )


elif user_role == "branch_manager":

    view_label = (
        "Branch: "
        + str(manager_branch)
    )


elif user_role == "credit_officer":

    view_label = (
        "Credit Officer: "
        + str(logged_in_user)
    )


else:

    view_label = "All data"


st.caption(

    f"{view_label}"

    f" | Total Loan: "
    f"₱{overall_total_loan:,.2f}"

    f" | Total Overdue: "
    f"₱{overall_total_overdue:,.2f}"

    f" | Total Clients: "
    f"{overall_total_clients:,}"

    f" | Total Overdue Clients: "
    f"{overall_overdue_clients:,}"

)

