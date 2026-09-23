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


# ============================================================
# GOOGLE DRIVE
# ============================================================

LOCAL_CREDENTIALS = (
    ".secrets/client_secret_kccdmfi-instafin.json"
)

if "data" not in st.session_state:

    st.warning(
        "Data has not been loaded yet. "
        "Please return to Home first."
    )

    st.stop()


data = st.session_state["data"]


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

area_col = find_column(
    data,
    [
        "Area",
        "Area.name"
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


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

missing_columns = []

if fdo_col is None:
    missing_columns.append("Credit officer")

if area_col is None:
    missing_columns.append("Area")

if loan_col is None:
    missing_columns.append("Loan amount")

if overdue_col is None:
    missing_columns.append("Overdue total")

if missing_columns:

    st.error(
        "The following required columns could not "
        "be found in the data:"
    )

    st.write(missing_columns)

    st.write(
        "Available columns:"
    )

    st.write(
        list(data.columns)
    )

    st.stop()


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(
    password,
    salt=None
):

    if salt is None:

        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000
    ).hex()

    return salt, password_hash


def verify_password(
    password,
    salt,
    stored_hash
):

    _, password_hash = hash_password(
        password,
        salt
    )

    return secrets.compare_digest(
        password_hash,
        stored_hash
    )


# ============================================================
# AUTHENTICATION FILE
# ============================================================

AUTH_FILENAME = (
    "kccdmfi_dashboard_users.json"
)


def find_auth_file():

    local_path = os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        AUTH_FILENAME
    )

    if os.path.exists(local_path):

        return local_path

    return None


def load_users():

    file_path = find_auth_file()

    if file_path is None:

        return {}

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        st.error(
            f"Could not read {AUTH_FILENAME}: {e}"
        )

        st.stop()


def save_users(users):

    file_path = find_auth_file()

    if file_path is None:

        file_path = os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
            ),
            AUTH_FILENAME
        )

    try:

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                users,
                f,
                indent=4
            )

    except Exception as e:

        raise RuntimeError(
            f"Could not save {AUTH_FILENAME}: {e}"
        )


# ============================================================
# AREA MANAGERS
# ============================================================

AREA_MANAGER_FILE = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "Area_managers.tsv"
)


def load_area_managers():

    if not os.path.exists(
        AREA_MANAGER_FILE
    ):

        st.error(
            "Area_managers.tsv was not found."
        )

        st.write(
            "Expected location:"
        )

        st.code(
            AREA_MANAGER_FILE
        )

        st.stop()

    area_managers = {}

    try:

        with open(
            AREA_MANAGER_FILE,
            "r",
            encoding="utf-8-sig"
        ) as f:

            for line_number, line in enumerate(
                f,
                start=1
            ):

                line = line.strip()

                if not line:
                    continue

                parts = line.split("\t")

                if len(parts) != 2:

                    st.error(
                        "Invalid Area_managers.tsv format "
                        f"on line {line_number}."
                    )

                    st.code(line)

                    st.stop()

                area = parts[0].strip()
                manager = parts[1].strip()

                if not area or not manager:

                    st.error(
                        "Empty Area or Manager on "
                        f"line {line_number}."
                    )

                    st.stop()

                # Manager -> Area
                area_managers[manager] = area

    except Exception as e:

        st.error(
            "Could not read Area_managers.tsv."
        )

        st.exception(e)

        st.stop()

    return area_managers


AREA_MANAGERS2 = load_area_managers()

AREA_MANAGER_NAMES = sorted(
    AREA_MANAGERS2.keys()
)


# ============================================================
# LOAD USERS
# ============================================================

users = load_users()

credit_officers = sorted(
    [
        x
        for x in data[fdo_col].unique()
        if x and x != "Unknown"
    ]
)


# ============================================================
# SESSION STATE
# ============================================================

if "authenticated" not in st.session_state:

    st.session_state[
        "authenticated"
    ] = False


if "logged_in_user" not in st.session_state:

    st.session_state[
        "logged_in_user"
    ] = None


if "user_role" not in st.session_state:

    st.session_state[
        "user_role"
    ] = None


# ============================================================
# LOGIN / REGISTRATION
# ============================================================

if not st.session_state[
    "authenticated"
]:

    #st.title(
    #    "KMFI Loan Dashboard"
    #)

    auth_action = st.radio(
        "Choose an option:",
        [
            "Login",
            "Register"
        ],
        horizontal=True,
        key="auth_action"
    )


    # ========================================================
    # LOGIN
    # ========================================================

    if auth_action == "Login":

        login_type = st.radio(
            "Login as:",
            [
                "Credit Officer",
                "Area Manager",
                "Admin"
            ],
            key="login_type"
        )


        # ====================================================
        # CREDIT OFFICER LOGIN
        # ====================================================

        if login_type == "Credit Officer":

            if not credit_officers:

                st.error(
                    "No Credit Officers were found "
                    "in the data."
                )

            else:

                username = st.selectbox(
                    "Credit Officer:",
                    credit_officers,
                    key="login_credit_officer"
                )

                password = st.text_input(
                    "Password:",
                    type="password",
                    key="credit_officer_password"
                )

                if st.button(
                    "Login",
                    type="primary",
                    key="credit_officer_login"
                ):

                    if username not in users:

                        st.error(
                            "This Credit Officer has not "
                            "registered a password yet. "
                            "Please use Register."
                        )

                    else:

                        user_info = users[
                            username
                        ]

                        if user_info.get(
                            "role"
                        ) != "credit_officer":

                            st.error(
                                "Invalid account configuration."
                            )

                        elif verify_password(
                            password,
                            user_info["salt"],
                            user_info["password_hash"]
                        ):

                            st.session_state[
                                "authenticated"
                            ] = True

                            st.session_state[
                                "logged_in_user"
                            ] = username

                            st.session_state[
                                "user_role"
                            ] = "credit_officer"

                            st.rerun()

                        else:

                            st.error(
                                "Incorrect password."
                            )


        # ====================================================
        # AREA MANAGER LOGIN
        # ====================================================

        elif login_type == "Area Manager":

            if not AREA_MANAGER_NAMES:

                st.error(
                    "No Area Managers were found "
                    "in Area_managers.tsv."
                )

            else:

                username = st.selectbox(
                    "Area Manager:",
                    AREA_MANAGER_NAMES,
                    key="login_area_manager"
                )

                st.info(
                    "Assigned Area: "
                    + AREA_MANAGERS2[username]
                )

                password = st.text_input(
                    "Password:",
                    type="password",
                    key="area_manager_password"
                )

                if st.button(
                    "Login",
                    type="primary",
                    key="area_manager_login"
                ):

                    if username not in users:

                        st.error(
                            "This Area Manager has not "
                            "registered a password yet. "
                            "Please use Register."
                        )

                    else:

                        user_info = users[
                            username
                        ]

                        if user_info.get(
                            "role"
                        ) != "area_manager":

                            st.error(
                                "Invalid Area Manager account."
                            )

                        elif verify_password(
                            password,
                            user_info["salt"],
                            user_info["password_hash"]
                        ):

                            st.session_state[
                                "authenticated"
                            ] = True

                            st.session_state[
                                "logged_in_user"
                            ] = username

                            st.session_state[
                                "user_role"
                            ] = "area_manager"

                            st.rerun()

                        else:

                            st.error(
                                "Incorrect password."
                            )


        # ====================================================
        # ADMIN LOGIN
        # ====================================================

        else:

            admin_password = st.text_input(
                "Admin Password:",
                type="password",
                key="admin_password"
            )

            if st.button(
                "Login",
                type="primary",
                key="admin_login"
            ):

                # ------------------------------------------------
                # LOCAL COMPUTER
                # ------------------------------------------------

                if os.path.exists(
                    LOCAL_CREDENTIALS
                ):

                    try:

                        with open(
                            LOCAL_CREDENTIALS,
                            "r",
                            encoding="utf-8"
                        ) as f:

                            credential_data = json.load(
                                f
                            )

                        stored_admin_password = (
                            credential_data.get(
                                "superuser_password"
                            )
                        )

                    except Exception as e:

                        st.error(
                            "Could not read the local "
                            "credentials file."
                        )

                        st.exception(e)

                        st.stop()

                # ------------------------------------------------
                # STREAMLIT CLOUD
                # ------------------------------------------------

                else:

                    try:

                        stored_admin_password = (
                            st.secrets[
                                "superuser"
                            ][
                                "password"
                            ]
                        )

                    except Exception:

                        st.error(
                            "Superuser password has not "
                            "been configured in "
                            "Streamlit Secrets."
                        )

                        st.stop()


                # ------------------------------------------------
                # CHECK PASSWORD
                # ------------------------------------------------

                if (
                    admin_password
                    == stored_admin_password
                ):

                    st.session_state[
                        "authenticated"
                    ] = True

                    st.session_state[
                        "logged_in_user"
                    ] = "Admin"

                    st.session_state[
                        "user_role"
                    ] = "superuser"

                    st.rerun()

                else:

                    st.error(
                        "Incorrect admin password."
                    )


    # ========================================================
    # REGISTRATION
    # ========================================================

    else:

        st.subheader(
            "Register Password"
        )

        registration_type = st.radio(
            "Register as:",
            [
                "Credit Officer",
                "Area Manager"
            ],
            horizontal=True,
            key="registration_type"
        )


        # ====================================================
        # CREDIT OFFICER REGISTRATION
        # ====================================================

        if registration_type == "Credit Officer":

            if not credit_officers:

                st.error(
                    "No Credit Officers were found "
                    "in the data."
                )

                st.stop()

            registration_name = st.selectbox(
                "Credit Officer:",
                credit_officers,
                key="registration_credit_officer"
            )

            registration_role = (
                "credit_officer"
            )


        # ====================================================
        # AREA MANAGER REGISTRATION
        # ====================================================

        else:

            if not AREA_MANAGER_NAMES:

                st.error(
                    "No Area Managers were found "
                    "in Area_managers.tsv."
                )

                st.stop()

            registration_name = st.selectbox(
                "Area Manager:",
                AREA_MANAGER_NAMES,
                key="registration_area_manager"
            )

            registration_role = (
                "area_manager"
            )

            st.info(
                "Assigned Area: "
                + AREA_MANAGERS2[
                    registration_name
                ]
            )


        # ====================================================
        # PASSWORD
        # ====================================================

        registration_password = st.text_input(
            "Create Password:",
            type="password",
            key="registration_password"
        )

        registration_password_confirm = (
            st.text_input(
                "Confirm Password:",
                type="password",
                key="registration_password_confirm"
            )
        )


        # ====================================================
        # REGISTER BUTTON
        # ====================================================

        if st.button(
            "Register",
            type="primary",
            key="register_user"
        ):

            if registration_name in users:

                st.error(
                    "This user already has a "
                    "registered password. "
                    "Please use Login."
                )

            elif not registration_password:

                st.error(
                    "Please enter a password."
                )

            elif len(
                registration_password
            ) < 8:

                st.error(
                    "Password must contain at least "
                    "8 characters."
                )

            elif (
                registration_password
                != registration_password_confirm
            ):

                st.error(
                    "Passwords do not match."
                )

            else:

                salt, password_hash = (
                    hash_password(
                        registration_password
                    )
                )

                users[
                    registration_name
                ] = {

                    "role":
                        registration_role,

                    "salt":
                        salt,

                    "password_hash":
                        password_hash

                }

                save_users(
                    users
                )

                st.success(
                    "Registration successful for "
                    + registration_name
                    + ". You can now log in."
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

    st.session_state[
        "authenticated"
    ] = False

    st.session_state[
        "logged_in_user"
    ] = None

    st.session_state[
        "user_role"
    ] = None

    st.rerun()


# ============================================================
# DATA ACCESS CONTROL
# ============================================================

if user_role == "superuser":

    working_data = data.copy()


elif user_role == "credit_officer":

    working_data = data[
        data[fdo_col]
        .astype(str)
        .str.strip()
        ==
        str(logged_in_user).strip()
    ].copy()


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

    working_data = data[
        data[area_col]
        .astype(str)
        .str.strip()
        ==
        str(manager_area).strip()
    ].copy()


else:

    st.error(
        "Invalid user role."
    )

    st.stop()


# ============================================================
# CHECK DATA ACCESS
# ============================================================

if working_data.empty:

    if user_role == "area_manager":

        st.error(
            "There are no records available "
            "for Area Manager "
            + str(logged_in_user)
            + " in Area "
            + str(manager_area)
            + "."
        )

    elif user_role == "credit_officer":

        st.error(
            "There are no records available "
            "for Credit Officer "
            + str(logged_in_user)
            + "."
        )

    else:

        st.error(
            "There are no records available."
        )

    st.stop()


# ============================================================
# SAVE SHARED SESSION DATA
# ============================================================

st.session_state[
    "working_data"
] = working_data

st.session_state[
    "AREA_MANAGERS2"
] = AREA_MANAGERS2


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
# SUMMARY PIE CHARTS
# ============================================================


# ============================================================
# 1. LOAN PORTFOLIO
# ============================================================

total_loan = (
    working_data[loan_col]
    .sum()
)

total_overdue = (
    working_data[overdue_col]
    .sum()
)

# Prevent negative overdue values
total_overdue = max(
    total_overdue,
    0
)

# Prevent overdue from exceeding total loan
total_overdue = min(
    total_overdue,
    max(total_loan, 0)
)

non_overdue = (
    total_loan
    - total_overdue
)

if total_loan > 0:

    overdue_percent = (
        total_overdue
        / total_loan
        * 100
    )

else:

    overdue_percent = 0


# ============================================================
# 2. CLIENT COUNTS
# ============================================================

# Total unique clients
total_clients = (
    working_data
    .dropna(subset=[client_col])
    [client_col]
    .astype(str)
    .str.strip()
    .replace("", pd.NA)
    .dropna()
    .nunique()
)


# Clients having at least one overdue record
overdue_client_names = (
    working_data.loc[
        working_data[overdue_col] > 0,
        client_col
    ]
    .dropna()
    .astype(str)
    .str.strip()
)

overdue_client_names = (
    overdue_client_names[
        overdue_client_names != ""
    ]
    .unique()
)

overdue_clients = len(
    overdue_client_names
)


# Non-overdue clients
non_overdue_clients = max(
    total_clients - overdue_clients,
    0
)


if total_clients > 0:

    overdue_client_percent = (
        overdue_clients
        / total_clients
        * 100
    )

else:

    overdue_client_percent = 0


# ============================================================
# 3. FIND DAYS IN ARREARS COLUMN
# ============================================================

days_arrears_col = find_column(
    data,
    [
        "Days in arrears",
        "Days.in.arrears",
        "Days in Arrears",
        "Days.in.Arrears",
        "Days arrears",
        "Days.arrears",
        "Days in arrear",
        "Days.in.arrear",
        "Days",
        "days_in_arrears",
        "days_in_arrears"
    ]
)


# ============================================================
# 4. CREATE THE THREE PIE CHARTS
# ============================================================

col1, col2, col3 = st.columns(3)


# ============================================================
# PIE CHART 1
# LOAN PORTFOLIO
# ============================================================

with col1:

    pie_fig_loan = go.Figure(
        data=[
            go.Pie(
                labels=[
                    "Non-overdue Loan",
                    "Overdue Loan"
                ],

                values=[
                    non_overdue,
                    total_overdue
                ],

                hole=0.55,

                textinfo="label+percent",

                textposition="outside",

                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Loan Value: "
                    "₱%{value:,.2f}<br>"
                    "Percentage: "
                    "%{percent}<br>"
                    "<extra></extra>"
                )
            )
        ]
    )


    pie_fig_loan.update_layout(

        title=dict(
            text="Loan Portfolio",
            x=0.5,
            xanchor="center"
        ),

        annotations=[
            dict(
                text=(
                    "<b>Total Loan</b><br>"
                    f"₱{total_loan:,.2f}"
                ),

                x=0.5,
                y=0.5,

                font=dict(
                    size=15
                ),

                showarrow=False
            )
        ],

        height=450,

        margin=dict(
            l=20,
            r=20,
            t=80,
            b=80
        ),

        showlegend=True,

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.08,
            xanchor="center",
            x=0.5
        )
    )


    st.plotly_chart(
        pie_fig_loan,
        width="stretch",
        key="loan_portfolio_pie"
    )


# ============================================================
# PIE CHART 2
# CLIENTS
# ============================================================

with col2:

    pie_fig_clients = go.Figure(
        data=[
            go.Pie(
                labels=[
                    "Non-overdue Clients",
                    "Overdue Clients"
                ],

                values=[
                    non_overdue_clients,
                    overdue_clients
                ],

                hole=0.55,

                textinfo="label+percent",

                textposition="outside",

                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Clients: %{value:,}<br>"
                    "Percentage: %{percent}<br>"
                    "<extra></extra>"
                )
            )
        ]
    )


    pie_fig_clients.update_layout(

        title=dict(
            text="Client Portfolio",
            x=0.5,
            xanchor="center"
        ),

        annotations=[
            dict(
                text=(
                    "<b>Total Clients</b><br>"
                    f"{total_clients:,}"
                ),

                x=0.5,
                y=0.5,

                font=dict(
                    size=15
                ),

                showarrow=False
            )
        ],

        height=450,

        margin=dict(
            l=20,
            r=20,
            t=80,
            b=80
        ),

        showlegend=True,

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.08,
            xanchor="center",
            x=0.5
        )
    )


    st.plotly_chart(
        pie_fig_clients,
        width="stretch",
        key="client_portfolio_pie"
    )


# ============================================================
# PIE CHART 3
# OVERDUE BY DAYS IN ARREARS
# ============================================================

with col3:

    if days_arrears_col is None:

        st.warning(
            "Days in arrears column was not found."
        )

        st.caption(
            "Expected a column such as "
            "'Days in arrears' or "
            "'Days.in.arrears'."
        )

    else:

        # ----------------------------------------------------
        # Convert Days in Arrears to numeric
        # ----------------------------------------------------

        arrears_data = working_data.copy()

        arrears_data["_days_in_arrears"] = (
            pd.to_numeric(
                arrears_data[
                    days_arrears_col
                ],
                errors="coerce"
            )
            .fillna(0)
        )


        # ----------------------------------------------------
        # Only overdue records
        # ----------------------------------------------------

        arrears_data = arrears_data[
            arrears_data[overdue_col] > 0
        ].copy()


        # ----------------------------------------------------
        # Create arrears categories
        # ----------------------------------------------------

        def arrears_category(days):

            if days <= 30:

                return "1–30"

            elif days <= 60:

                return "31–60"

            elif days <= 90:

                return "61–90"

            elif days <= 180:

                return "91–180"

            elif days <= 365:

                return "181–365"

            else:

                return ">365"


        arrears_data[
            "_arrears_category"
        ] = (
            arrears_data[
                "_days_in_arrears"
            ]
            .apply(arrears_category)
        )


        # ----------------------------------------------------
        # Sum overdue value by arrears category
        # ----------------------------------------------------

        arrears_summary = (
            arrears_data
            .groupby(
                "_arrears_category"
            )[overdue_col]
            .sum()
            .reindex(
                [
                    "1–30",
                    "31–60",
                    "61–90",
                    "91–180",
                    "181–365",
                    ">365"
                ],
                fill_value=0
            )
        )


        # ----------------------------------------------------
        # Remove zero categories from the pie
        # ----------------------------------------------------

        arrears_summary = (
            arrears_summary[
                arrears_summary > 0
            ]
        )


        if arrears_summary.empty:

            st.info(
                "No overdue records with "
                "Days in Arrears were found."
            )

        else:

            pie_fig_arrears = go.Figure(
                data=[
                    go.Pie(
                        labels=arrears_summary.index,

                        values=arrears_summary.values,

                        hole=0.55,

                        textinfo="label+percent",

                        textposition="outside",

                        hovertemplate=(
                            "<b>%{label} days</b><br>"
                            "Overdue Loan Value: "
                            "₱%{value:,.2f}<br>"
                            "Percentage: %{percent}"
                            "<extra></extra>"
                        )
                    )
                ]
            )


            pie_fig_arrears.update_layout(

                title=dict(
                    text="Overdue by Days in Arrears",
                    x=0.5,
                    xanchor="center"
                ),

                annotations=[
                    dict(
                        text=(
                            "<b>Total Overdue</b><br>"
                            f"₱{total_overdue:,.2f}"
                        ),

                        x=0.5,
                        y=0.5,

                        font=dict(
                            size=15
                        ),

                        showarrow=False
                    )
                ],

                height=450,

                margin=dict(
                    l=20,
                    r=20,
                    t=80,
                    b=80
                ),

                showlegend=True,

                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.08,
                    xanchor="center",
                    x=0.5
                )
            )


            st.plotly_chart(
                pie_fig_arrears,
                width="stretch",
                key="overdue_days_pie"
            )


# ============================================================
# OVERDUE SUMMARY
# ============================================================

st.caption(
    f"Total Loan Value: ₱{total_loan:,.2f}"
    f" | Total Overdue: ₱{total_overdue:,.2f}"
    f" | Overdue Rate: {overdue_percent:.1f}%"
    f" | Total Clients: {total_clients:,}"
    f" | Overdue Clients: {overdue_clients:,}"
    f" | Overdue Client Rate: "
    f"{overdue_client_percent:.1f}%"
)
