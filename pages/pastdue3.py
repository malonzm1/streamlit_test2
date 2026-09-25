import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import hashlib
import secrets

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


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
        for x in data[fdo_col].unique()
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


# ============================================================
# SIDEBAR — GROUP BY
# ============================================================

if user_role == "branch_manager":

    group_by_options = [
        "Credit officer",
        "Branch name"
    ]
    
elif user_role == "credit_officer":

    group_by_options = [
        "Credit officer"
    ]
else:

    group_by_options = [
        "Credit officer",
        "Branch name",
        "Area"
    ]


# If the previously selected option is "Area"
# and the user has changed to Branch Manager,
# automatically switch to Credit officer.
if (
    st.session_state.get("group_label_choice")
    not in group_by_options
):

    st.session_state["group_label_choice"] = (
        group_by_options[0]
    )


group_label_choice = st.sidebar.radio(
    "Group by:",
    options=group_by_options,
    key="group_label_choice"
)


# ============================================================
# SIDEBAR — SORT BY
# ============================================================

sortby = st.sidebar.radio(
    "Sort by:",
    options=[
        "Loan value",
        "Loan overdue value",
        "Loan clients",
        "Loan overdue clients",
        "Alphabetical"
    ],
    key="combined_sortby"
)


# ============================================================
# DETERMINE GROUPING
# ============================================================

if group_label_choice == "Credit officer":

    # ========================================================
    # CREDIT OFFICER
    # ========================================================

    officer_options = sorted(
        working_data[
            fdo_col
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    officer_options = [
        x
        for x in officer_options
        if x and x != "Unknown"
    ]

    if not officer_options:

        st.error(
            "No Credit Officers are available "
            "for the current selection."
        )

        st.stop()

    selected_officer = st.sidebar.selectbox(
        "Select Credit Officer:",
        options=officer_options,
        key="selected_officer"
    )

    working_data = working_data[
        working_data[fdo_col]
        .astype(str)
        .str.strip()
        ==
        str(selected_officer).strip()
    ].copy()

    # --------------------------------------------------------
    # Group by Centre
    # --------------------------------------------------------

    if centre_col is None:

        st.error(
            "The Centre column could not be found "
            "in the data."
        )

        st.write(
            "Available columns:",
            list(data.columns)
        )

        st.stop()

    group_col = centre_col

    group_label = (
        f"Centre of Credit Officer: "
        f"{selected_officer}"
    )


# ============================================================
# BRANCH
# ============================================================

elif group_label_choice == "Branch name":

    branch_options = sorted(
        working_data[
            branch_col
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    branch_options = [
        x
        for x in branch_options
        if x and x != "Unknown"
    ]

    if not branch_options:

        st.error(
            "No Branches are available "
            "for the current selection."
        )

        st.stop()

    selected_branch = st.sidebar.selectbox(
        "Select Branch:",
        options=branch_options,
        key="selected_branch"
    )

    working_data = working_data[
        working_data[branch_col]
        .astype(str)
        .str.strip()
        ==
        str(selected_branch).strip()
    ].copy()

    group_col = fdo_col

    group_label = (
        f"Credit Officer in Branch: "
        f"{selected_branch}"
    )


# ============================================================
# AREA
# ============================================================

else:

    area_options = sorted(
        working_data[
            area_col
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    area_options = [
        x
        for x in area_options
        if x
    ]

    if not area_options:

        st.error(
            "No Areas are available "
            "for the current selection."
        )

        st.stop()

    # --------------------------------------------------------
    # AREA MANAGER
    # --------------------------------------------------------

    if user_role == "area_manager":

        selected_area = manager_area

        st.sidebar.info(
            "Selected Area: "
            + str(selected_area)
        )

    else:

        selected_area = st.sidebar.selectbox(
            "Select Area:",
            options=area_options,
            key="selected_area"
        )

    working_data = working_data[
        working_data[area_col]
        .astype(str)
        .str.strip()
        ==
        str(selected_area).strip()
    ].copy()

    group_col = branch_col

    group_label = (
        f"Branch in Area: "
        f"{selected_area}"
    )


# ============================================================
# CHECK DATA AFTER FILTERING
# ============================================================

if working_data.empty:

    st.warning(
        "No records are available for "
        "the selected filters."
    )

    st.stop()


# ============================================================
# CLEAN GROUP COLUMN
# ============================================================

working_data[group_col] = (
    working_data[group_col]
    .fillna("Unknown")
    .astype(str)
    .str.strip()
)

working_data = working_data[
    working_data[group_col] != ""
].copy()


if working_data.empty:

    st.warning(
        "No valid grouping values were found."
    )

    st.stop()


# ============================================================
# DASHBOARD SUBTITLE
# ============================================================

st.subheader(
    f"Loan Portfolio — {group_label}"
)

st.caption(
    "Click any bar in either chart to display "
    "the corresponding records in the table below."
)


# ============================================================
# CREATE COMMON SUMMARY
# ============================================================

# ============================================================
# LOAN VALUE SUMMARY
# ============================================================

value_summary = (

    working_data

    .groupby(
        group_col,
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
# CLIENT SUMMARY
# ============================================================

client_summary = (

    working_data

    .groupby(
        group_col,
        as_index=False
    )

    .agg(
        total_clients=(
            client_col,
            "nunique"
        )
    )

)


# ============================================================
# OVERDUE CLIENT SUMMARY
# ============================================================

overdue_client_data = working_data[
    working_data[
        overdue_col
    ] > 0
].copy()


overdue_client_summary = (

    overdue_client_data

    .groupby(
        group_col
    )[client_col]

    .nunique()

    .reset_index(
        name="overdue_clients"
    )

)


# ============================================================
# COMBINE SUMMARY
# ============================================================

summary = value_summary.merge(
    client_summary,
    on=group_col,
    how="outer"
)

summary = summary.merge(
    overdue_client_summary,
    on=group_col,
    how="left"
)


# ============================================================
# CLEAN SUMMARY
# ============================================================

summary["total_loan"] = (
    summary["total_loan"]
    .fillna(0)
)

summary["total_overdue"] = (
    summary["total_overdue"]
    .fillna(0)
)

summary["total_clients"] = (
    summary["total_clients"]
    .fillna(0)
    .astype(int)
)

summary["overdue_clients"] = (
    summary["overdue_clients"]
    .fillna(0)
    .astype(int)
)


# ============================================================
# TARGET SETTINGS
# ============================================================

# Branch view:
#   Loan target = ₱4,000,000
#   Client target = 400 per Credit Officer
#
# Area view:
#   Loan target = ₱16,000,000
#   Client target = 400 per Credit Officer
#
# Credit Officer/Centre view:
#   No target displayed.

if group_label_choice == "Branch name":

    summary["loan_target"] = 4_000_000

elif group_label_choice == "Area":

    summary["loan_target"] = 16_000_000

else:

    summary["loan_target"] = 0


# ============================================================
# CREDIT OFFICER COUNTS
# ============================================================

if group_label_choice == "Area":

    credit_officer_counts = (
        working_data
        .groupby(group_col)[fdo_col]
        .nunique()
        .reindex(summary[group_col])
        .fillna(0)
        .astype(int)
        .reset_index()
    )

    credit_officer_counts.columns = [
        group_col,
        "credit_officer_count"
    ]

    summary = summary.merge(
        credit_officer_counts,
        on=group_col,
        how="left"
    )

    summary["credit_officer_count"] = (
        summary["credit_officer_count"]
        .fillna(0)
        .astype(int)
    )

    summary["client_target"] = (
        summary["credit_officer_count"] * 400
    )


elif group_label_choice == "Branch name":

    summary["credit_officer_count"] = 1

    summary["client_target"] = 400


else:

    summary["credit_officer_count"] = 1

    summary["client_target"] = 0


# ============================================================
# TARGET DATA TYPES
# ============================================================

summary["loan_target"] = (
    summary["loan_target"]
    .fillna(0)
    .astype(int)
)

summary["client_target"] = (
    summary["client_target"]
    .fillna(0)
    .astype(int)
)


# ============================================================
# OVERDUE LOAN PERCENTAGE
# ============================================================

summary["overdue_percent"] = (

    summary["total_overdue"]

    .div(
        summary["total_loan"].replace(
            0,
            pd.NA
        )
    )

    .fillna(0)

    * 100

)


# ============================================================
# OVERDUE CLIENT PERCENTAGE
# ============================================================

summary["overdue_client_percent"] = (

    summary["overdue_clients"]

    .div(
        summary["total_clients"].replace(
            0,
            pd.NA
        )
    )

    .fillna(0)

    * 100

)


# ============================================================
# TARGET LOAN PERCENTAGE
# ============================================================

summary["target_percent"] = (

    summary["total_loan"]

    .div(
        summary["loan_target"].replace(
            0,
            pd.NA
        )
    )

    .fillna(0)

    * 100

)


# ============================================================
# TARGET CLIENT PERCENTAGE
# ============================================================

summary["target_client_percent"] = (

    summary["total_clients"]

    .div(
        summary["client_target"].replace(
            0,
            pd.NA
        )
    )

    .fillna(0)

    * 100

)


# ============================================================
# SORTING
# ============================================================

if sortby == "Loan value":

    summary = summary.sort_values(
        "total_loan",
        ascending=True
    )


elif sortby == "Loan overdue value":

    summary = summary.sort_values(
        "total_overdue",
        ascending=True
    )


elif sortby == "Loan clients":

    summary = summary.sort_values(
        "total_clients",
        ascending=True
    )


elif sortby == "Loan overdue clients":

    summary = summary.sort_values(
        "overdue_clients",
        ascending=True
    )


else:

    summary = summary.sort_values(
        group_col,
        ascending=True
    )


# ============================================================
# GROUP ORDER
# ============================================================

group_order = summary[
    group_col
].tolist()


# ============================================================
# TWO COLUMNS
# ============================================================

left_col, right_col = st.columns(
    2,
    gap="large"
)


# ============================================================
# SHARED SELECTION
# ============================================================

if "selected_name" not in st.session_state:

    st.session_state[
        "selected_name"
    ] = None


if "selected_type" not in st.session_state:

    st.session_state[
        "selected_type"
    ] = None


selected_name = (
    st.session_state[
        "selected_name"
    ]
)

selected_type = (
    st.session_state[
        "selected_type"
    ]
)


# ============================================================
# LEFT — LOAN CLIENTS
# ============================================================

with left_col:

    #st.markdown(
    #    "### Loan Clients"
    #)

    client_fig = go.Figure()


    # ========================================================
    # TOTAL CLIENTS
    # ========================================================

    client_fig.add_trace(

        go.Bar(

            x=summary[
                "total_clients"
            ],

            y=summary[
                group_col
            ],

            name="Loan Clients",

            orientation="h",

            offsetgroup="clients",

            marker=dict(
                color="green"
            ),

            text=[

                f"{value:,} "
                f"({percent:.1f}%)"

                for value, percent

                in zip(

                    summary[
                        "total_clients"
                    ],

                    summary[
                        "target_client_percent"
                    ]

                )

            ],

            textposition="outside",

            cliponaxis=False,

            customdata=summary[
                [
                    "total_clients",
                    "overdue_clients",
                    "target_client_percent"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Loan Clients: "
                "%{customdata[0]:,}<br>"

                "Overdue Clients: "
                "%{customdata[1]:,}<br>"

                "Target Achievement: "
                "%{customdata[2]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # TARGET CLIENTS
    # ========================================================

    if group_label_choice in {
        "Branch name",
        "Area"
    }:

        client_fig.add_trace(

            go.Bar(

                x=summary[
                    "client_target"
                ],

                y=summary[
                    group_col
                ],

                name="Target",

                orientation="h",

                offsetgroup="target",

                marker=dict(
                    color="blue"
                ),

                text=[

                    f"{value:,}"

                    for value

                    in summary[
                        "client_target"
                    ]

                ],

                textposition="outside",

                cliponaxis=False,

                customdata=summary[
                    [
                        "client_target",
                        "credit_officer_count"
                    ]
                ],

                hovertemplate=(

                    "<b>%{y}</b><br>"

                    "Client Target: "
                    "%{customdata[0]:,}<br>"

                    "Credit Officers: "
                    "%{customdata[1]:,}"

                    "<extra></extra>"

                )

            )

        )


    # ========================================================
    # OVERDUE CLIENTS
    # ========================================================

    client_fig.add_trace(

        go.Bar(

            x=summary[
                "overdue_clients"
            ],

            y=summary[
                group_col
            ],

            name="Loan Overdue Clients",

            orientation="h",

            offsetgroup="overdue",

            marker=dict(
                color="red"
            ),

            text=[

                f"{value:,} "
                f"({percent:.1f}%)"

                for value, percent

                in zip(

                    summary[
                        "overdue_clients"
                    ],

                    summary[
                        "overdue_client_percent"
                    ]

                )

            ],

            textposition="outside",

            cliponaxis=False,

            customdata=summary[
                [
                    "overdue_clients",
                    "total_clients",
                    "overdue_client_percent"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Loan Overdue Clients: "
                "%{customdata[0]:,}<br>"

                "Loan Clients: "
                "%{customdata[1]:,}<br>"

                "Overdue Clients: "
                "%{customdata[2]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # CLIENT AXIS
    # ========================================================

    max_clients = max(

        summary[
            "total_clients"
        ].max(),

        summary[
            "overdue_clients"
        ].max(),

        summary[
            "client_target"
        ].max(),

        1

    )


    client_fig.update_layout(

        title=dict(

            text="Loan Clients",

            x=0.5,

            xanchor="center"

        ),

        barmode="group",

        xaxis=dict(

            title="Number of Clients",

            range=[
                0,
                max_clients * 1.30
            ],

            tickformat=",",

            showgrid=True,

            zeroline=False

        ),

        yaxis=dict(

            title=group_label,

            categoryorder="array",

            categoryarray=group_order,

            autorange="reversed"

        ),

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.0,

            xanchor="center",

            x=0.5

        ),

        height=max(

            600,

            len(summary) * 35 + 150

        ),

        margin=dict(

            l=100,

            r=130,

            t=155,

            b=60

        )

    )


    # ========================================================
    # DISPLAY CLIENT CHART
    # ========================================================

    client_event = st.plotly_chart(

        client_fig,

        width="stretch",

        key="combined_loan_clients_chart",

        on_select="rerun"

    )


    # ========================================================
    # CLIENT CHART SELECTION
    # ========================================================

    if (
        client_event
        and client_event.selection.points
    ):

        point = (
            client_event
            .selection
            .points[0]
        )

        clicked_name = point.get(
            "y"
        )

        curve_number = point.get(
            "curve_number"
        )


        if curve_number == 0:

            st.session_state[
                "selected_name"
            ] = clicked_name

            st.session_state[
                "selected_type"
            ] = "total_clients"


        elif (
            curve_number == 1
            and group_label_choice in {
                "Branch name",
                "Area"
            }
        ):

            st.session_state[
                "selected_name"
            ] = clicked_name

            st.session_state[
                "selected_type"
            ] = "target_clients"


        elif (
            curve_number == 2
            and group_label_choice in {
                "Branch name",
                "Area"
            }
        ):

            st.session_state[
                "selected_name"
            ] = clicked_name

            st.session_state[
                "selected_type"
            ] = "overdue_clients"

        elif curve_number == 1:

            st.session_state[
                "selected_name"
            ] = clicked_name

            st.session_state[
                "selected_type"
            ] = "overdue_clients"


        selected_name = (
            st.session_state[
                "selected_name"
            ]
        )

        selected_type = (
            st.session_state[
                "selected_type"
            ]
        )


# ============================================================
# RIGHT — LOAN VALUE
# ============================================================

with right_col:

    #st.markdown(
    #    "### Loan Value"
    #)

    value_fig = go.Figure()


    # ========================================================
    # TOTAL LOAN
    # ========================================================

    value_fig.add_trace(

        go.Bar(

            x=summary[
                "total_loan"
            ],

            y=summary[
                group_col
            ],

            name="Loan Value",

            orientation="h",

            offsetgroup="loan",

            marker=dict(
                color="green"
            ),

            text=[

                f"₱{value:,.2f} "
                f"({percent:.1f}%)"

                for value, percent

                in zip(

                    summary[
                        "total_loan"
                    ],

                    summary[
                        "target_percent"
                    ]

                )

            ],

            textposition="outside",

            cliponaxis=False,

            customdata=summary[
                [
                    "total_loan",
                    "total_overdue",
                    "target_percent"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Loan Value: "
                "₱%{customdata[0]:,.2f}<br>"

                "Loan Overdue Value: "
                "₱%{customdata[1]:,.2f}<br>"

                "Target Achievement: "
                "%{customdata[2]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # TARGET LOAN
    # ========================================================

    if group_label_choice in {
        "Branch name",
        "Area"
    }:

        value_fig.add_trace(

            go.Bar(

                x=summary[
                    "loan_target"
                ],

                y=summary[
                    group_col
                ],

                name="Target",

                orientation="h",

                offsetgroup="target",

                marker=dict(
                    color="blue"
                ),

                text=[

                    f"₱{value:,.2f}"

                    for value

                    in summary[
                        "loan_target"
                    ]

                ],

                textposition="outside",

                cliponaxis=False,

                hovertemplate=(

                    "<b>%{y}</b><br>"

                    "Loan Target: "

                    + "₱%{x:,.2f}"

                    + "<extra></extra>"

                )

            )

        )


    # ========================================================
    # OVERDUE LOAN
    # ========================================================

    value_fig.add_trace(

        go.Bar(

            x=summary[
                "total_overdue"
            ],

            y=summary[
                group_col
            ],

            name="Loan Overdue Value",

            orientation="h",

            offsetgroup="overdue",

            marker=dict(
                color="red"
            ),

            text=[

                f"₱{value:,.2f} "
                f"({percent:.1f}%)"

                for value, percent

                in zip(

                    summary[
                        "total_overdue"
                    ],

                    summary[
                        "overdue_percent"
                    ]

                )

            ],

            textposition="outside",

            cliponaxis=False,

            customdata=summary[
                [
                    "total_overdue",
                    "total_loan",
                    "overdue_percent"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Loan Overdue Value: "
                "₱%{customdata[0]:,.2f}<br>"

                "Loan Value: "
                "₱%{customdata[1]:,.2f}<br>"

                "Overdue: "
                "%{customdata[2]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # ========================================================
    # VALUE AXIS
    # ========================================================

    max_value = max(

        summary[
            "total_loan"
        ].max(),

        summary[
            "total_overdue"
        ].max(),

        summary[
            "loan_target"
        ].max(),

        1

    )


    value_fig.update_layout(

        title=dict(

            text="Loan Value",

            x=0.5,

            xanchor="center"

        ),

        barmode="group",

        xaxis=dict(

            title="Amount",

            range=[
                0,
                max_value * 1.30
            ],

            tickformat=",.0f",

            showgrid=True,

            zeroline=False

        ),

        yaxis=dict(

            title=group_label,

            categoryorder="array",

            categoryarray=group_order,

            autorange="reversed"

        ),

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.0,

            xanchor="center",

            x=0.5

        ),

        height=max(

            600,

            len(summary) * 35 + 150

        ),

        margin=dict(

            l=100,

            r=150,

            t=155,

            b=60

        )

    )


    # ========================================================
    # DISPLAY VALUE CHART
    # ========================================================

    value_event = st.plotly_chart(

        value_fig,

        width="stretch",

        key="combined_loan_value_chart",

        on_select="rerun"

    )


    # ========================================================
    # VALUE CHART SELECTION
    # ========================================================

    if (
        value_event
        and value_event.selection.points
    ):

        point = (
            value_event
            .selection
            .points[0]
        )

        clicked_name = point.get(
            "y"
        )

        curve_number = point.get(
            "curve_number"
        )


        if curve_number == 0:

            st.session_state[
                "selected_name"
            ] = clicked_name

            st.session_state[
                "selected_type"
            ] = "total_loan"


        elif (
            curve_number == 1
            and group_label_choice in {
                "Branch name",
                "Area"
            }
        ):

            st.session_state[
                "selected_name"
            ] = clicked_name

            st.session_state[
                "selected_type"
            ] = "target_loan"


        elif (
            curve_number == 2
            and group_label_choice in {
                "Branch name",
                "Area"
            }
        ):

            st.session_state[
                "selected_name"
            ] = clicked_name

            st.session_state[
                "selected_type"
            ] = "overdue_loan"

        elif curve_number == 1:

            st.session_state[
                "selected_name"
            ] = clicked_name

            st.session_state[
                "selected_type"
            ] = "overdue_loan"


        selected_name = (
            st.session_state[
                "selected_name"
            ]
        )

        selected_type = (
            st.session_state[
                "selected_type"
            ]
        )


# ============================================================
# SELECTED RECORDS
# ============================================================

st.divider()

st.subheader(
    "Selected Records"
)


if selected_name is None:

    st.info(
        "Click a bar in either chart above "
        "to display the corresponding records here."
    )


else:

    selected_name = str(
        selected_name
    )


    # ========================================================
    # TOTAL CLIENTS
    # ========================================================

    if selected_type == "total_clients":

        selected_data = working_data[
            working_data[
                group_col
            ].astype(str)
            ==
            selected_name
        ].copy()

        table_title = (
            f"All Records — "
            f"{group_label}: "
            f"{selected_name}"
        )


    # ========================================================
    # OVERDUE CLIENTS
    # ========================================================

    elif selected_type == "overdue_clients":

        overdue_clients = (

            working_data.loc[

                (
                    working_data[
                        group_col
                    ].astype(str)
                    ==
                    selected_name
                )

                &

                (
                    working_data[
                        overdue_col
                    ] > 0
                ),

                client_col

            ]

            .dropna()

            .astype(str)

            .unique()

        )


        selected_data = working_data[

            (
                working_data[
                    group_col
                ].astype(str)
                ==
                selected_name
            )

            &

            (
                working_data[
                    client_col
                ].astype(str)
                .isin(
                    overdue_clients
                )
            )

        ].copy()


        table_title = (
            f"Clients with Overdue — "
            f"{group_label}: "
            f"{selected_name}"
        )


    # ========================================================
    # TOTAL LOAN
    # ========================================================

    elif selected_type == "total_loan":

        selected_data = working_data[
            working_data[
                group_col
            ].astype(str)
            ==
            selected_name
        ].copy()

        table_title = (
            f"All Loan Records — "
            f"{group_label}: "
            f"{selected_name}"
        )


    # ========================================================
    # TARGET CLIENTS
    # ========================================================

    elif selected_type == "target_clients":

        selected_data = working_data[
            working_data[
                group_col
            ].astype(str)
            ==
            selected_name
        ].copy()


        matching_summary = summary[
            summary[
                group_col
            ].astype(str)
            ==
            selected_name
        ]


        if not matching_summary.empty:

            target_value = int(
                matching_summary[
                    "client_target"
                ].iloc[0]
            )

        else:

            target_value = 0


        table_title = (
            f"Target — "
            f"{group_label}: "
            f"{selected_name} "
            f"(Target: "
            f"{target_value:,} clients)"
        )


    # ========================================================
    # TARGET LOAN
    # ========================================================

    elif selected_type == "target_loan":

        selected_data = working_data[
            working_data[
                group_col
            ].astype(str)
            ==
            selected_name
        ].copy()


        matching_summary = summary[
            summary[
                group_col
            ].astype(str)
            ==
            selected_name
        ]


        if not matching_summary.empty:

            target_value = int(
                matching_summary[
                    "loan_target"
                ].iloc[0]
            )

        else:

            target_value = 0


        table_title = (
            f"Target — "
            f"{group_label}: "
            f"{selected_name} "
            f"(Target: "
            f"₱{target_value:,.2f})"
        )


    # ========================================================
    # OVERDUE LOAN
    # ========================================================

    elif selected_type == "overdue_loan":

        selected_data = working_data[

            (
                working_data[
                    group_col
                ].astype(str)
                ==
                selected_name
            )

            &

            (
                working_data[
                    overdue_col
                ] > 0
            )

        ].copy()


        table_title = (
            f"Overdue Loan Records — "
            f"{group_label}: "
            f"{selected_name}"
        )


    # ========================================================
    # FALLBACK
    # ========================================================

    else:

        selected_data = pd.DataFrame()

        table_title = (
            "Selected Records"
        )


    # ========================================================
    # DISPLAY TABLE
    # ========================================================

    st.subheader(
        table_title
    )


    if not selected_data.empty:

        st.dataframe(

            selected_data,

            width="stretch",

            hide_index=True

        )

    else:

        st.info(
            "No records found for the selected bar."
        )
