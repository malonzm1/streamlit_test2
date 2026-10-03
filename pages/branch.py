from google.oauth2 import service_account
from googleapiclient.discovery import build
import plotly.graph_objects as go
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
# CHECK DATA
# ============================================================

if "data" not in st.session_state:

    st.warning(
        "Data has not been loaded yet. "
        "Please return to Home first."
    )

    st.stop()


# ============================================================
# DATA
# ============================================================

combined_data = st.session_state["data"]

working_data = st.session_state["working_data"]


# ============================================================
# FIND COLUMN
# ============================================================

def find_column(df, possible_names):

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
        list(working_data.columns)
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

    AREA_MANAGERS2 = st.session_state[
        "AREA_MANAGERS2"
    ]

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

    BRANCH_MANAGERS2 = st.session_state.get(
        "BRANCH_MANAGERS2",
        {}
    )

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
# DASHBOARD CAPTION
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
# MAKE NUMERIC COLUMNS NUMERIC
# ============================================================

working_data[loan_col] = pd.to_numeric(
    working_data[loan_col],
    errors="coerce"
).fillna(0)


working_data[overdue_col] = pd.to_numeric(
    working_data[overdue_col],
    errors="coerce"
).fillna(0)


# ============================================================
# SIDEBAR
# ============================================================

selection = st.sidebar.radio(
    "Choose an option:",
    options=[
        "loan value",
        "loan clients"
    ]
)


# ============================================================
# SORT OPTIONS
# ============================================================

if selection == "loan value":

    sortby1 = st.sidebar.selectbox(
        "Sort by:",
        options=[
            "Branch",
            "Total loan",
            "Total overdue",
            "Overdue % of total loan"
        ],
        index=1
    )

else:

    sortby2 = st.sidebar.selectbox(
        "Sort by:",
        options=[
            "Branch",
            "Total clients",
            "Overdue clients",
            "Overdue % of total clients"
        ],
        index=1
    )


# ============================================================
# LOAN CYCLE
# ============================================================

cycles = sorted(
    working_data[
        "Loan Cycle"
    ]
    .dropna()
    .unique()
)


cycle = st.sidebar.selectbox(
    "Loan cycle",
    options=[
        "All"
    ] + list(cycles)
)


# ============================================================
# FILTER BY LOAN CYCLE
# ============================================================

if cycle != "All":

    working_data = working_data[
        working_data[
            "Loan Cycle"
        ]
        ==
        cycle
    ].copy()


# ============================================================
# LOAN VALUE
# ============================================================

if selection == "loan value":

    # ========================================================
    # GROUP BY BRANCH
    # ========================================================

    branch_totals = (

        working_data

        .groupby(
            branch_col,
            dropna=False
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


    # ========================================================
    # CALCULATE OVERDUE AS % OF TOTAL LOAN
    # ========================================================

    branch_totals[
        "overdue_percent_of_loan"
    ] = (

        branch_totals[
            "total_overdue"
        ]

        .div(

            branch_totals[
                "total_loan"
            ].replace(
                0,
                pd.NA
            )

        )

        .fillna(0)

        * 100

    )


    # ========================================================
    # SORTING
    # ========================================================

    if sortby1 == "Total loan":

        branch_totals = branch_totals.sort_values(
            "total_loan",
            ascending=False
        )


    elif sortby1 == "Total overdue":

        branch_totals = branch_totals.sort_values(
            "total_overdue",
            ascending=False
        )


    elif sortby1 == "Overdue % of total loan":

        branch_totals = branch_totals.sort_values(
            "overdue_percent_of_loan",
            ascending=False
        )


    elif sortby1 == "Branch":

        branch_totals = branch_totals.sort_values(
            branch_col,
            ascending=True
        )


    # ========================================================
    # PLOT
    # ========================================================

    fig = go.Figure()


    # ========================================================
    # TOTAL LOAN
    # ========================================================

    fig.add_trace(

        go.Bar(

            y=branch_totals[
                branch_col
            ],

            x=branch_totals[
                "total_loan"
            ],

            name="Total Loan",

            orientation="h",

            offsetgroup="loan",

            customdata=branch_totals[
                [
                    "total_loan"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Total Loan: "
                "₱%{customdata[0]:,.2f}"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # TOTAL OVERDUE
    # ========================================================

    fig.add_trace(

        go.Bar(

            y=branch_totals[
                branch_col
            ],

            x=branch_totals[
                "total_overdue"
            ],

            name="Total Overdue",

            orientation="h",

            offsetgroup="overdue",

            customdata=branch_totals[
                [
                    "total_overdue",
                    "overdue_percent_of_loan"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Total Overdue: "
                "₱%{customdata[0]:,.2f}<br>"

                "Overdue / Total Loan: "
                "%{customdata[1]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # OVERDUE % OF TOTAL LOAN
    # ========================================================

    fig.add_trace(

        go.Bar(

            y=branch_totals[
                branch_col
            ],

            x=branch_totals[
                "overdue_percent_of_loan"
            ],

            name="Overdue % of Total Loan",

            orientation="h",

            xaxis="x2",

            offsetgroup="percentage",

            customdata=branch_totals[
                [
                    "overdue_percent_of_loan",
                    "total_overdue",
                    "total_loan"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Overdue / Total Loan: "
                "%{customdata[0]:.1f}%<br>"

                "Total Overdue: "
                "₱%{customdata[1]:,.2f}<br>"

                "Total Loan: "
                "₱%{customdata[2]:,.2f}"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # LOAN CHART LAYOUT
    # ========================================================

    fig.update_layout(
    
        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------
        title=dict(
            text=(
                "Total Loan, Total Overdue and "
                "Overdue % of Total Loan by Branch"
            ),
            x=0.5,
            xanchor="center",
    
            # Move title closer to legend
            y=0.84,
            yanchor="top",
    
            font=dict(size=13)
        ),
    
        # ----------------------------------------------------
        # MAIN AMOUNT SCALE
        # ----------------------------------------------------
        xaxis=dict(
            title="Amount",
            tickformat=",.0f",
            rangemode="tozero"
        ),
    
        # ----------------------------------------------------
        # PERCENTAGE SCALE ON TOP
        # ----------------------------------------------------
        xaxis2=dict(
            title="Overdue / Total Loan (%)",
            overlaying="x",
            side="top",
    
            range=[
                0,
                max(
                    100,
                    float(
                        branch_totals[
                            "overdue_percent_of_loan"
                        ].max()
                    ) * 1.10
                )
            ],
    
            tickmode="linear",
            tick0=0,
            dtick=10,
            ticksuffix="%",
            showgrid=False,
            zeroline=False
        ),
    
        # ----------------------------------------------------
        # Y AXIS
        # ----------------------------------------------------
        yaxis=dict(
            title="Branch",
            type="category",
            categoryorder="array",
            categoryarray=(
                branch_totals[
                    branch_col
                ].tolist()
            ),
            automargin=True
        ),
    
        barmode="group",
    
        # ----------------------------------------------------
        # FIGURE HEIGHT
        # ----------------------------------------------------
        height=max(
            600,
            len(branch_totals) * 55
        ),
    
        # ----------------------------------------------------
        # TOP MARGIN
        # ----------------------------------------------------
        margin=dict(
            l=150,
            r=80,
    
            # Reserve space above the plot
            t=300,
    
            b=60
        ),
    
        # ----------------------------------------------------
        # LEGEND
        # ----------------------------------------------------
        legend=dict(
            orientation="h",
        
            x=0.5,
            xanchor="center",
        
            # Pull legend upward
            y=1.40,
            yanchor="bottom",
        
            font=dict(size=12),
        
            tracegroupgap=20
        )


    )






    # ========================================================
    # DISPLAY LOAN CHART
    # ========================================================

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# LOAN CLIENTS
# ============================================================

else:

    # ========================================================
    # GROUP BY BRANCH
    # ========================================================

    branch_totals = (

        working_data

        .groupby(
            branch_col,
            dropna=False
        )

        .agg(

            total_clients=(
                branch_col,
                "size"
            ),

            overdue_clients=(
                overdue_col,
                lambda x: (
                    x > 0
                ).sum()
            )

        )

        .reset_index()

    )


    # ========================================================
    # CALCULATE OVERDUE CLIENTS
    # AS % OF TOTAL CLIENTS
    # ========================================================

    branch_totals[
        "overdue_client_percent"
    ] = (

        branch_totals[
            "overdue_clients"
        ]

        .div(

            branch_totals[
                "total_clients"
            ].replace(
                0,
                pd.NA
            )

        )

        .fillna(0)

        * 100

    )


    # ========================================================
    # SORTING
    # ========================================================

    if sortby2 == "Total clients":

        branch_totals = branch_totals.sort_values(
            "total_clients",
            ascending=False
        )


    elif sortby2 == "Overdue clients":

        branch_totals = branch_totals.sort_values(
            "overdue_clients",
            ascending=False
        )


    elif sortby2 == "Overdue % of total clients":

        branch_totals = branch_totals.sort_values(
            "overdue_client_percent",
            ascending=False
        )


    elif sortby2 == "Branch":

        branch_totals = branch_totals.sort_values(
            branch_col,
            ascending=True
        )


    # ========================================================
    # PLOT
    # ========================================================

    fig = go.Figure()


    # ========================================================
    # TOTAL CLIENTS
    # ========================================================

    fig.add_trace(

        go.Bar(

            y=branch_totals[
                branch_col
            ],

            x=branch_totals[
                "total_clients"
            ],

            name="Total Clients",

            orientation="h",

            offsetgroup="clients",

            customdata=branch_totals[
                [
                    "total_clients"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Total Clients: "
                "%{customdata[0]:,}"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # CLIENTS WITH OVERDUE
    # ========================================================

    fig.add_trace(

        go.Bar(

            y=branch_totals[
                branch_col
            ],

            x=branch_totals[
                "overdue_clients"
            ],

            name="Clients with Overdue",

            orientation="h",

            offsetgroup="overdue_clients",

            customdata=branch_totals[
                [
                    "overdue_clients",
                    "overdue_client_percent"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Clients with Overdue: "
                "%{customdata[0]:,}<br>"

                "Overdue Clients / Total Clients: "
                "%{customdata[1]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # OVERDUE CLIENTS % OF TOTAL CLIENTS
    # ========================================================

    fig.add_trace(

        go.Bar(

            y=branch_totals[
                branch_col
            ],

            x=branch_totals[
                "overdue_client_percent"
            ],

            name="Overdue Clients % of Total",

            orientation="h",

            xaxis="x2",

            offsetgroup="percentage",

            customdata=branch_totals[
                [
                    "overdue_client_percent",
                    "overdue_clients",
                    "total_clients"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Overdue Clients / Total Clients: "
                "%{customdata[0]:.1f}%<br>"

                "Clients with Overdue: "
                "%{customdata[1]:,}<br>"

                "Total Clients: "
                "%{customdata[2]:,}"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # CLIENT CHART LAYOUT
    # ========================================================

    fig.update_layout(

        title=(
            "Total Clients, Clients with Overdue and "
            "Overdue Client % by Branch"
        ),

        # ----------------------------------------------------
        # MAIN CLIENT COUNT SCALE
        # ----------------------------------------------------

        xaxis=dict(

            title="Number of Clients",

            tickformat=",",

            rangemode="tozero"

        ),

        # ----------------------------------------------------
        # PERCENTAGE SCALE ON TOP
        # ----------------------------------------------------

        xaxis2=dict(

            title="Overdue Clients / Total Clients (%)",

            overlaying="x",

            side="top",

            range=[
                0,
                max(
                    100,
                    float(
                        branch_totals[
                            "overdue_client_percent"
                        ].max()
                    ) * 1.10
                )
            ],

            tickmode="linear",

            tick0=0,

            dtick=10,

            ticksuffix="%",

            showgrid=False,

            zeroline=False

        ),

        yaxis=dict(

            title="Branch",

            type="category",

            categoryorder="array",

            categoryarray=(
                branch_totals[
                    branch_col
                ].tolist()
            ),

            automargin=True

        ),

        barmode="group",

        height=max(
            600,
            len(branch_totals) * 55
        ),

        margin=dict(

            l=150,

            r=80,

            t=140,

            b=60

        ),

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.08,

            xanchor="left",

            x=0

        )

    )


    # ========================================================
    # DISPLAY CLIENT CHART
    # ========================================================

    st.plotly_chart(
        fig,
        use_container_width=True
    )
