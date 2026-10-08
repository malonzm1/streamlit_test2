import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np


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

    data = data[
        ~exclude_mask
    ].copy()
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
        list(data.columns)
    )

    st.stop()


# ============================================================
# CONVERT NUMERIC COLUMNS
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
# CREDIT OFFICERS
# ============================================================

#credit_officers = sorted(
#    [
#        x
#        for x in data[fdo_col].unique()
#        if x and x != "Unknown"
#    ]
#)


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
# HANDLE COLUMN NAMES
# ============================================================

def find_column(df, possible_names):

    for name in possible_names:

        if name in df.columns:
            return name

    return None


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
        "Client.name",
        "Client name"
    ]
)


cycle_col = find_column(
    working_data,
    [
        "Loan.Cycle",
        "Loan Cycle"
    ]
)


branch_col = find_column(
    working_data,
    [
        "Branch name",
        "Branch.name"
    ]
)


fdo_col = find_column(
    working_data,
    [
        "Credit.officer",
        "Credit officer"
    ]
)


required_columns = {

    "Loan amount": loan_col,

    "Overdue total": overdue_col,

    "Client": client_col,

    "Loan Cycle": cycle_col,

    "Branch name": branch_col,

    "Credit Officer": fdo_col,

}


missing = [

    name

    for name, column
    in required_columns.items()

    if column is None

]


if missing:

    st.error(
        "The following required columns are missing: "
        + ", ".join(missing)
    )

    st.write(
        "Available columns:",
        list(data.columns)
    )

    st.stop()


# ============================================================
# CONVERT NUMERIC COLUMNS
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
            "FDO",
            "Branch name",
            "Total loan",
            "Total overdue"
        ],
        index=2
    )

else:

    sortby2 = st.sidebar.selectbox(
        "Sort by:",
        options=[
            "FDO",
            "Branch name",
            "Total clients",
            "Overdue clients"
        ],
        index=2
    )


# ============================================================
# LOAN CYCLE
# ============================================================

cycles = sorted(
    working_data[cycle_col]
    .dropna()
    .astype(str)
    .unique()
)


cycle = st.sidebar.selectbox(
    "Loan cycle",
    options=[
        "All"
    ] + cycles,
    index=0
)


# ============================================================
# FILTER BY LOAN CYCLE
# ============================================================

if cycle != "All":

    working_data = working_data[
        working_data[cycle_col].astype(str) == cycle
    ].copy()


# ============================================================
# LOAN VALUE
# ============================================================

if selection == "loan value":

    # --------------------------------------------------------
    # SUMMARISE BY BRANCH + CREDIT OFFICER
    # --------------------------------------------------------

    officer_summary = (

        working_data

        .groupby(
            [branch_col, fdo_col],
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


    # --------------------------------------------------------
    # CALCULATE OVERDUE % OF TOTAL LOAN
    # --------------------------------------------------------

    officer_summary[
        "overdue_percent_of_loan"
    ] = (

        officer_summary[
            "total_overdue"
        ]

        .div(
            officer_summary[
                "total_loan"
            ].replace(
                0,
                np.nan
            )
        )

        .fillna(0)

        * 100

    )


    # --------------------------------------------------------
    # ORDER FDOs
    # --------------------------------------------------------

    if sortby1 == "Branch name":

        officer_order = (
            officer_summary
            .sort_values(
                [branch_col, "total_loan"],
                ascending=[True, False]
            )
        )


    elif sortby1 == "FDO":

        officer_order = (
            officer_summary
            .sort_values(
                fdo_col,
                ascending=True
            )
        )


    elif sortby1 == "Total loan":

        officer_order = (
            officer_summary
            .sort_values(
                "total_loan",
                ascending=True
            )
        )


    else:

        officer_order = (
            officer_summary
            .sort_values(
                "total_overdue",
                ascending=True
            )
        )


    # --------------------------------------------------------
    # ORDERED FDOs
    # --------------------------------------------------------

    officer_order_list = (
        officer_order[fdo_col]
        .drop_duplicates()
        .tolist()
    )


    officer_summary[fdo_col] = pd.Categorical(
        officer_summary[fdo_col],
        categories=officer_order_list,
        ordered=True
    )


    officer_summary = officer_summary.sort_values(
        fdo_col
    )


    # --------------------------------------------------------
    # SCALING FACTOR
    # --------------------------------------------------------

    max_loan = officer_summary[
        "total_loan"
    ].max()


    max_overdue = officer_summary[
        "total_overdue"
    ].max()


    if max_overdue > 0:

        scale_factor = (
            max_loan / max_overdue
        )

    else:

        scale_factor = 1


    # --------------------------------------------------------
    # PLOT DATA
    # --------------------------------------------------------

    officer_long = officer_summary.melt(
        id_vars=[
            branch_col,
            fdo_col,
            "overdue_percent_of_loan"
        ],

        value_vars=[
            "total_loan",
            "total_overdue"
        ],

        var_name="Metric",

        value_name="Amount"
    )


    officer_long["PlotAmount"] = officer_long.apply(

        lambda row:

            row["Amount"] * scale_factor

            if row["Metric"] == "total_overdue"

            else row["Amount"],

        axis=1

    )


    officer_long["Metric"] = officer_long[
        "Metric"
    ].map({

        "total_loan": "Loan Amount",

        "total_overdue": "Overdue Total"

    })


    # --------------------------------------------------------
    # CREATE CHART
    # --------------------------------------------------------

    fig = go.Figure()


    # --------------------------------------------------------
    # LOAN AMOUNT
    # --------------------------------------------------------

    loan_plot = officer_long[
        officer_long["Metric"] == "Loan Amount"
    ]


    fig.add_trace(

        go.Bar(

            x=loan_plot["PlotAmount"],

            y=loan_plot[fdo_col],

            name="Loan Amount",

            orientation="h",

            offsetgroup="loan",

            xaxis="x",

            customdata=loan_plot[
                [
                    branch_col,
                    "Amount",
                    "overdue_percent_of_loan"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Branch: %{customdata[0]}<br>"

                "Total Loan: "
                "₱%{customdata[1]:,.2f}<br>"

                "Overdue / Total Loan: "
                "%{customdata[2]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # --------------------------------------------------------
    # OVERDUE
    # --------------------------------------------------------

    overdue_plot = officer_long[
        officer_long["Metric"] == "Overdue Total"
    ]


    fig.add_trace(

        go.Bar(

            x=overdue_plot["PlotAmount"],

            y=overdue_plot[fdo_col],

            name="Overdue Total",

            orientation="h",

            offsetgroup="overdue",

            xaxis="x",

            customdata=overdue_plot[
                [
                    branch_col,
                    "Amount",
                    "overdue_percent_of_loan"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Branch: %{customdata[0]}<br>"

                "Total Overdue: "
                "₱%{customdata[1]:,.2f}<br>"

                "Overdue / Total Loan: "
                "%{customdata[2]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # --------------------------------------------------------
    # AXIS LIMITS
    # --------------------------------------------------------

    max_plot_amount = officer_long[
        "PlotAmount"
    ].max()


    label_x = max_plot_amount * 1.05

    plot_xmax = max_plot_amount * 1.25


    # --------------------------------------------------------
    # BRANCH LABELS
    # --------------------------------------------------------

    for _, row in officer_summary.iterrows():

        fig.add_annotation(

            x=label_x,

            y=row[fdo_col],

            text=str(row[branch_col]),

            showarrow=False,

            xanchor="left",

            font=dict(
                size=11
            )

        )


    # --------------------------------------------------------
    # LAYOUT
    # --------------------------------------------------------

    fig.update_layout(

        title=dict(

            text=(
                "Total Loan Amount and Total Overdue "
                "by Credit Officer"
            ),

            x=0.5,

            xanchor="center",

            y=0.98,

            yanchor="top"

        ),

        barmode="group",

        # ----------------------------------------------------
        # BOTTOM AXIS = LOAN AMOUNT
        # ----------------------------------------------------

        xaxis=dict(

            title="Total Loan Amount",

            range=[
                0,
                plot_xmax
            ],

            tickformat=".2e",

            showgrid=True,

            zeroline=False,

            showline=True,

            domain=[
                0,
                1
            ]

        ),

        # ----------------------------------------------------
        # TOP AXIS = ACTUAL OVERDUE VALUES
        # ----------------------------------------------------

        xaxis2=dict(

            title="Total Overdue",

            overlaying="x",

            side="top",

            range=[

                0,

                plot_xmax / scale_factor

            ],

            tickformat=".2e",

            showgrid=False,

            zeroline=False,

            showline=True,

            anchor="y"

        ),

        yaxis=dict(

            title="Credit Officer",

            categoryorder="array",

            categoryarray=officer_order_list,

            autorange="reversed"

        ),

        # ----------------------------------------------------
        # LEGEND
        # ----------------------------------------------------

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.08,

            xanchor="center",

            x=0.5

        ),

        # ----------------------------------------------------
        # SIZE / SPACING
        # ----------------------------------------------------

        height=max(

            600,

            len(officer_order_list) * 35 + 120

        ),

        margin=dict(

            l=80,

            r=180,

            t=125,

            b=60

        )

    )


    # --------------------------------------------------------
    # FORCE SECONDARY TOP AXIS
    # --------------------------------------------------------

    fig.add_trace(

        go.Scatter(

            x=[
                0,
                plot_xmax / scale_factor
            ],

            y=[
                None,
                None
            ],

            xaxis="x2",

            showlegend=False,

            hoverinfo="skip",

            mode="lines"

        )

    )


    st.plotly_chart(

        fig,

        width="stretch"

    )


# ============================================================
# LOAN CLIENTS
# ============================================================

else:

    # --------------------------------------------------------
    # SUMMARISE CLIENTS BY BRANCH + CREDIT OFFICER
    # --------------------------------------------------------

    officer_summary = (

        data

        .groupby(
            [branch_col, fdo_col],
            as_index=False
        )

        .agg(

            total_clients=(
                client_col,
                "nunique"
            ),

            overdue_clients=(
                client_col,
                lambda x: x[
                    data.loc[
                        x.index,
                        overdue_col
                    ] > 0
                ].nunique()
            )

        )

    )


    # --------------------------------------------------------
    # CALCULATE OVERDUE CLIENTS %
    # OF TOTAL CLIENTS
    # --------------------------------------------------------

    officer_summary[
        "overdue_client_percent"
    ] = (

        officer_summary[
            "overdue_clients"
        ]

        .div(

            officer_summary[
                "total_clients"
            ].replace(
                0,
                np.nan
            )

        )

        .fillna(0)

        * 100

    )


    # --------------------------------------------------------
    # ORDER FDOs
    # --------------------------------------------------------

    if sortby2 == "Branch name":

        officer_order = (
            officer_summary
            .sort_values(
                [branch_col, "total_clients"],
                ascending=[True, False]
            )
        )


    elif sortby2 == "FDO":

        officer_order = (
            officer_summary
            .sort_values(
                fdo_col,
                ascending=True
            )
        )


    elif sortby2 == "Total clients":

        officer_order = (
            officer_summary
            .sort_values(
                "total_clients",
                ascending=True
            )
        )


    else:

        officer_order = (
            officer_summary
            .sort_values(
                "overdue_clients",
                ascending=True
            )
        )


    # --------------------------------------------------------
    # ORDERED FDOs
    # --------------------------------------------------------

    officer_order_list = (
        officer_order[fdo_col]
        .drop_duplicates()
        .tolist()
    )


    officer_summary[fdo_col] = pd.Categorical(
        officer_summary[fdo_col],
        categories=officer_order_list,
        ordered=True
    )


    officer_summary = officer_summary.sort_values(
        fdo_col
    )


    # --------------------------------------------------------
    # PLOT
    # --------------------------------------------------------

    fig = go.Figure()


    # --------------------------------------------------------
    # TOTAL CLIENTS
    # --------------------------------------------------------

    clients_plot = officer_summary[
        [
            branch_col,
            fdo_col,
            "total_clients",
            "overdue_client_percent"
        ]
    ]


    fig.add_trace(

        go.Bar(

            x=clients_plot[
                "total_clients"
            ],

            y=clients_plot[
                fdo_col
            ],

            name="Total Clients",

            orientation="h",

            offsetgroup="clients",

            width=0.35,

            customdata=clients_plot[
                [
                    branch_col,
                    "total_clients",
                    "overdue_client_percent"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Branch: %{customdata[0]}<br>"

                "Total Clients: "
                "%{customdata[1]:,}<br>"

                "Overdue Clients / Total Clients: "
                "%{customdata[2]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # --------------------------------------------------------
    # CLIENTS WITH NON-ZERO OVERDUE
    # --------------------------------------------------------

    overdue_clients_plot = officer_summary[
        [
            branch_col,
            fdo_col,
            "total_clients",
            "overdue_clients",
            "overdue_client_percent"
        ]
    ]


    fig.add_trace(

        go.Bar(

            x=overdue_clients_plot[
                "overdue_clients"
            ],

            y=overdue_clients_plot[
                fdo_col
            ],

            name="Clients with Non-zero Overdue",

            orientation="h",

            offsetgroup="overdue",

            width=0.35,

            customdata=overdue_clients_plot[
                [
                    branch_col,
                    "overdue_clients",
                    "total_clients",
                    "overdue_client_percent"
                ]
            ],

            hovertemplate=(

                "<b>%{y}</b><br>"

                "Branch: %{customdata[0]}<br>"

                "Clients with Non-zero Overdue: "
                "%{customdata[1]:,}<br>"

                "Total Clients: "
                "%{customdata[2]:,}<br>"

                "Overdue Clients / Total Clients: "
                "%{customdata[3]:.1f}%"

                "<extra></extra>"

            )

        )

    )


    # --------------------------------------------------------
    # BRANCH LABELS
    # --------------------------------------------------------

    max_clients = max(

        officer_summary[
            "total_clients"
        ].max(),

        officer_summary[
            "overdue_clients"
        ].max(),

        1

    )


    # Small amount of space after longest bar

    plot_xmax = max_clients * 1.05

    label_x = max_clients * 1.01


    for _, row in officer_summary.iterrows():

        fig.add_annotation(

            x=label_x,

            y=row[fdo_col],

            text=str(row[branch_col]),

            showarrow=False,

            xanchor="left",

            font=dict(
                size=11
            )

        )


    # --------------------------------------------------------
    # LAYOUT
    # --------------------------------------------------------

    fig.update_layout(

        title=(

            "Total Clients and Clients with "
            "Non-zero Overdue by Credit Officer"

        ),

        # ONE SCALE ONLY

        xaxis=dict(

            title="Number of Clients",

            range=[
                0,
                plot_xmax
            ],

            tickformat=",",

            showgrid=True,

            zeroline=False

        ),

        yaxis=dict(

            title="Credit Officer",

            categoryorder="array",

            categoryarray=officer_order_list

        ),

        # NO SECONDARY AXIS

        barmode="group",

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.04,

            xanchor="left",

            x=0

        ),

        height=max(

            600,

            len(officer_order_list) * 35

        ),

        margin=dict(

            l=80,

            r=180,

            t=125,

            b=60

        )

    )


    st.plotly_chart(

        fig,

        width="stretch"

    )

