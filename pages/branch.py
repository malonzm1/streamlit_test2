#library(reticulate)
#py_install(c("streamlit"))
#py_install(c("plotly"))
#library(reticulate)

#py_require(c(
#    "google-api-python-client",
#    "google-auth"
#))

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


combined_data = st.session_state["data"]

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
    combined_data,
    [
        "Loan amount",
        "Loan.amount"
    ]
)


overdue_col = find_column(
    combined_data,
    [
        "Overdue total",
        "Overdue.total"
    ]
)


client_col = find_column(
    combined_data,
    [
        "Client name",
        "Client.name"
    ]
)


fdo_col = find_column(
    combined_data,
    [
        "Credit officer",
        "Credit.officer"
    ]
)


branch_col = find_column(
    combined_data,
    [
        "Branch name",
        "Branch.name"
    ]
)


area_col = find_column(
    combined_data,
    [
        "Area",
        "Area.name"
    ]
)


# ============================================================
# FIND CENTRE COLUMN
# ============================================================

centre_col = find_column(
    combined_data,
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
        list(data.columns)
    )

    st.stop()


# ============================================================
# CONVERT NUMERIC COLUMNS
# ============================================================



# ============================================================
# CREDIT OFFICERS
# ============================================================

credit_officers = sorted(
    [
        x
        for x in combined_data[fdo_col].unique()
        if x and x != "Unknown"
    ]
)





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



# ============================================================
# DASHBOARD TITLE
# ============================================================

#st.title(
#    "KCCDMFI Loan Dashboard"
#)


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


# Make sure numeric columns are numeric
combined_data["Loan amount"] = pd.to_numeric(
    combined_data["Loan amount"],
    errors="coerce"
)

combined_data["Overdue total"] = pd.to_numeric(
    combined_data["Overdue total"],
    errors="coerce"
)


# =========================================================
# Sidebar
# =========================================================

selection = st.sidebar.radio(
    "Choose an option:",
    options=["loan value", "loan clients"]
)


if selection == "loan value":

    sortby1 = st.sidebar.selectbox(
        "Sort by:",
        options=[
            "Branch",
            "Total loan",
            "Total overdue"
        ],
        index=1
    )

else:

    sortby2 = st.sidebar.selectbox(
        "Sort by:",
        options=[
            "Branch",
            "Total clients",
            "Overdue clients"
        ],
        index=1
    )


# =========================================================
# Loan cycle
# =========================================================

cycles = sorted(
    combined_data["Loan Cycle"]
    .dropna()
    .unique()
)

cycle = st.sidebar.selectbox(
    "Loan cycle",
    options=["All"] + list(cycles)
)


# =========================================================
# Filter by loan cycle
# =========================================================

if cycle != "All":

    combined_data = combined_data[
        combined_data["Loan Cycle"] == cycle
    ].copy()


# =========================================================
# LOAN VALUE
# =========================================================

if selection == "loan value":

    # -----------------------------------------------------
    # Equivalent of:
    #
    # group_by(Branch) %>%
    # summarise(...)
    # -----------------------------------------------------

    branch_totals = (
        combined_data
        .groupby("Branch name", dropna=False)
        .agg(
            total_loan=("Loan amount", "sum"),
            total_overdue=("Overdue total", "sum")
        )
        .reset_index()
    )


    # -----------------------------------------------------
    # Equivalent of fct_reorder()
    # -----------------------------------------------------

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

    elif sortby1 == "Branch":

        branch_totals = branch_totals.sort_values(
            "Branch name",
            ascending=True
        )


    # -----------------------------------------------------
    # Plot
    # -----------------------------------------------------

    fig = go.Figure()
    
    
    fig.add_trace(
        go.Bar(
            x=branch_totals["Branch name"],
            y=branch_totals["total_loan"],
            name="Total Loan",
            offsetgroup="loan"
        )
    )
    
    
    fig.add_trace(
        go.Bar(
            x=branch_totals["Branch name"],
            y=branch_totals["total_overdue"],
            name="Total Overdue",
            yaxis="y2",
            offsetgroup="overdue"
        )
    )
    
    
    fig.update_layout(
        title="Total Loan Amount and Total Loan Overdue by Branch",
    
        xaxis=dict(
            title="Branch",
            tickangle=45
        ),
    
        yaxis=dict(
            title="Total Loan Amount"
        ),
    
        yaxis2=dict(
            title="Total Loan Overdue",
            overlaying="y",
            side="right"
        ),
    
        barmode="group",
    
        height=600,
    
        margin=dict(
            l=60,
            r=80,
            t=80,
            b=120
        )
    )
    
    
    st.plotly_chart(
        fig,
        width="stretch"
    )
  

# =========================================================
# LOAN CLIENTS
# =========================================================

else:

    # -----------------------------------------------------
    # Equivalent of:
    #
    # group_by(Branch) %>%
    # summarise(
    #     total_clients = n(),
    #     overdue_clients = sum(Overdue.total > 0)
    # )
    # -----------------------------------------------------

    branch_totals = (
        combined_data
        .groupby("Branch name", dropna=False)
        .agg(
            total_clients=("Branch name", "size"),
            overdue_clients=(
                "Overdue total",
                lambda x: (x > 0).sum()
            )
        )
        .reset_index()
    )


    # -----------------------------------------------------
    # Sorting
    # -----------------------------------------------------

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

    elif sortby2 == "Branch name":

        branch_totals = branch_totals.sort_values(
            "Branch name",
            ascending=True
        )


    # -----------------------------------------------------
    # Plot
    # -----------------------------------------------------

    fig = go.Figure()


    fig.add_trace(
        go.Bar(
            x=branch_totals["Branch name"],
            y=branch_totals["total_clients"],
            name="Total Clients"
        )
    )


    fig.add_trace(
        go.Bar(
            x=branch_totals["Branch name"],
            y=branch_totals["overdue_clients"],
            name="Clients with Overdue"
        )
    )


    fig.update_layout(
        title="Total Clients and Clients with Overdue by Branch",

        xaxis=dict(
            title="Branch",
            tickangle=45
        ),

        yaxis=dict(
            title="Number of Clients"
        ),

        barmode="group",

        height=600,

        margin=dict(
            l=60,
            r=40,
            t=80,
            b=120
        )
    )


    st.plotly_chart(
        fig,
        use_container_width=True
    )
