import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import hashlib
import secrets

from streamlit_plotly_events import plotly_events

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

def find_column(df, possible_names):

    for name in possible_names:

        if name in df.columns:

            return name

    return None


# ============================================================
# NORMALIZE VALUES FOR COMPARISON
# ============================================================

def normalize_value(value):

    return str(value).strip().casefold()


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

branch_col = find_column(
    data,
    [
        "Branch name",
        "Branch.name",
        "Branch"
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

if branch_col is None:
    missing_columns.append("Branch name")

if loan_col is None:
    missing_columns.append("Loan amount")

if overdue_col is None:
    missing_columns.append("Overdue total")

if client_col is None:
    missing_columns.append("Client name")


if missing_columns:

    st.error(
        "The following required columns could not "
        "be found in the data:"
    )

    st.write(missing_columns)

    st.write("Available columns:")

    st.write(list(data.columns))

    st.stop()


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password, salt=None):

    if salt is None:

        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000
    ).hex()

    return salt, password_hash


def verify_password(password, salt, stored_hash):

    generated_salt, password_hash = hash_password(
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
# BRANCH MANAGERS
# ============================================================

BRANCH_MANAGER_FILE = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "Branch_managers.tsv"
)


def load_branch_managers():

    if not os.path.exists(
        BRANCH_MANAGER_FILE
    ):

        st.error(
            "Branch_managers.tsv was not found."
        )

        st.write(
            "Expected location:"
        )

        st.code(
            BRANCH_MANAGER_FILE
        )

        st.stop()

    branch_managers = {}

    try:

        with open(
            BRANCH_MANAGER_FILE,
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
                        "Invalid Branch_managers.tsv format "
                        f"on line {line_number}."
                    )

                    st.code(line)

                    st.stop()

                branch = parts[0].strip()

                manager = parts[1].strip()

                if not branch or not manager:

                    st.error(
                        "Empty Branch or Manager on "
                        f"line {line_number}."
                    )

                    st.stop()

                branch_managers[manager] = branch

    except Exception as e:

        st.error(
            "Could not read Branch_managers.tsv."
        )

        st.exception(e)

        st.stop()

    return branch_managers


BRANCH_MANAGERS2 = load_branch_managers()

BRANCH_MANAGER_NAMES = sorted(
    BRANCH_MANAGERS2.keys()
)


# ============================================================
# LOAD USERS
# ============================================================

users = load_users()


# ============================================================
# CREDIT OFFICERS
# ============================================================

credit_officers = sorted(
    [
        str(x).strip()
        for x in data[fdo_col].dropna().unique()
        if (
            str(x).strip()
            and
            str(x).strip().lower()
            not in [
                "unknown",
                "nan",
                "none"
            ]
        )
    ]
)


# ============================================================
# SESSION STATE
# ============================================================

if "authenticated" not in st.session_state:

    st.session_state["authenticated"] = False


if "logged_in_user" not in st.session_state:

    st.session_state["logged_in_user"] = None


if "user_role" not in st.session_state:

    st.session_state["user_role"] = None


if "selected_pie_breakdown" not in st.session_state:

    st.session_state["selected_pie_breakdown"] = None


if "last_loan_pie_event" not in st.session_state:

    st.session_state["last_loan_pie_event"] = None


if "last_client_pie_event" not in st.session_state:

    st.session_state["last_client_pie_event"] = None


if "last_arrears_pie_event" not in st.session_state:

    st.session_state["last_arrears_pie_event"] = None


if "filter_signature" not in st.session_state:

    st.session_state["filter_signature"] = None


# ============================================================
# LOGIN / REGISTRATION
# ============================================================

if not st.session_state["authenticated"]:

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
                "Branch Manager",
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

                        user_info = users[username]

                        if user_info.get("role") != "credit_officer":

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

                        user_info = users[username]

                        if user_info.get("role") != "area_manager":

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
        # BRANCH MANAGER LOGIN
        # ====================================================

        elif login_type == "Branch Manager":

            if not BRANCH_MANAGER_NAMES:

                st.error(
                    "No Branch Managers were found "
                    "in Branch_managers.tsv."
                )

            else:

                username = st.selectbox(
                    "Branch Manager:",
                    BRANCH_MANAGER_NAMES,
                    key="login_branch_manager"
                )

                st.info(
                    "Assigned Branch: "
                    + BRANCH_MANAGERS2[username]
                )

                password = st.text_input(
                    "Password:",
                    type="password",
                    key="branch_manager_password"
                )

                if st.button(
                    "Login",
                    type="primary",
                    key="branch_manager_login"
                ):

                    if username not in users:

                        st.error(
                            "This Branch Manager has not "
                            "registered a password yet. "
                            "Please use Register."
                        )

                    else:

                        user_info = users[username]

                        if user_info.get("role") != "branch_manager":

                            st.error(
                                "Invalid Branch Manager account."
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
                            ] = "branch_manager"

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

                if os.path.exists(LOCAL_CREDENTIALS):

                    try:

                        with open(
                            LOCAL_CREDENTIALS,
                            "r",
                            encoding="utf-8"
                        ) as f:

                            credential_data = json.load(f)

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

                if admin_password == stored_admin_password:

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
                "Area Manager",
                "Branch Manager"
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

            registration_role = "credit_officer"


        # ====================================================
        # AREA MANAGER REGISTRATION
        # ====================================================

        elif registration_type == "Area Manager":

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

            registration_role = "area_manager"

            st.info(
                "Assigned Area: "
                + AREA_MANAGERS2[
                    registration_name
                ]
            )


        # ====================================================
        # BRANCH MANAGER REGISTRATION
        # ====================================================

        else:

            if not BRANCH_MANAGER_NAMES:

                st.error(
                    "No Branch Managers were found "
                    "in Branch_managers.tsv."
                )

                st.stop()

            registration_name = st.selectbox(
                "Branch Manager:",
                BRANCH_MANAGER_NAMES,
                key="registration_branch_manager"
            )

            registration_role = "branch_manager"

            st.info(
                "Assigned Branch: "
                + BRANCH_MANAGERS2[
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

        registration_password_confirm = st.text_input(
            "Confirm Password:",
            type="password",
            key="registration_password_confirm"
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

            elif len(registration_password) < 8:

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

                salt, password_hash = hash_password(
                    registration_password
                )

                users[registration_name] = {
                    "role": registration_role,
                    "salt": salt,
                    "password_hash": password_hash
                }

                save_users(users)

                st.success(
                    "Registration successful for "
                    + registration_name
                    + ". You can now log in."
                )


    st.stop()


# ============================================================
# CURRENT USER
# ============================================================

logged_in_user = st.session_state["logged_in_user"]

user_role = st.session_state["user_role"]


# ============================================================
# SIDEBAR USER INFORMATION
# ============================================================

st.sidebar.success(
    "Logged in as: "
    + str(logged_in_user)
)


if user_role == "credit_officer":

    st.sidebar.info("Role: Credit Officer")


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

    st.sidebar.info("Role: Area Manager")

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

    st.sidebar.info("Role: Branch Manager")

    st.sidebar.info(
        "Branch: "
        + str(manager_branch)
    )


elif user_role == "superuser":

    st.sidebar.info("Role: Administrator")


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

    st.session_state["selected_pie_breakdown"] = None

    st.session_state["last_loan_pie_event"] = None

    st.session_state["last_client_pie_event"] = None

    st.session_state["last_arrears_pie_event"] = None

    st.session_state["filter_signature"] = None

    st.rerun()


# ============================================================
# DEFAULT SELECTION VARIABLES
# ============================================================

selected_area_manager = None

selected_branch_manager = None

selected_credit_officer = None

selected_manager_area = None

selected_manager_branch = None

admin_selection_type = None

admin_area_view_type = None

area_manager_view_type = None


# ============================================================
# DATA ACCESS CONTROL
# ============================================================

if user_role == "superuser":

    st.sidebar.markdown(
        "### Dashboard Selection"
    )

    admin_selection_type = st.sidebar.radio(
        "View data as:",
        [
            "All Data",
            "Area Manager",
            "Branch Manager",
            "Credit Officer"
        ],
        key="admin_selection_type"
    )


    # ========================================================
    # ADMIN -> ALL DATA
    # ========================================================

    if admin_selection_type == "All Data":

        working_data = data.copy()


    # ========================================================
    # ADMIN -> AREA MANAGER
    # ========================================================

    elif admin_selection_type == "Area Manager":

        selected_area_manager = st.sidebar.selectbox(
            "Select Area Manager:",
            AREA_MANAGER_NAMES,
            key="admin_area_manager"
        )

        selected_manager_area = (
            AREA_MANAGERS2.get(
                selected_area_manager
            )
        )

        working_data = data[
            data[area_col]
            .astype(str)
            .str.strip()
            .str.casefold()
            ==
            normalize_value(
                selected_manager_area
            )
        ].copy()


        st.sidebar.markdown(
            "### Area Manager Filters"
        )

        admin_area_view_type = st.sidebar.radio(
            "View data as:",
            [
                "All Credit Officers",
                "Credit Officer"
            ],
            key="admin_area_view_type"
        )


        if admin_area_view_type == "Credit Officer":

            area_credit_officers = sorted(
                [
                    str(x).strip()
                    for x in working_data[
                        fdo_col
                    ].dropna().unique()
                    if (
                        str(x).strip()
                        and
                        str(x).strip().lower()
                        not in [
                            "unknown",
                            "nan",
                            "none"
                        ]
                    )
                ]
            )

            if not area_credit_officers:

                st.error(
                    "No Credit Officers were found "
                    "in the selected Area."
                )

                st.stop()

            selected_credit_officer = (
                st.sidebar.selectbox(
                    "Select Credit Officer:",
                    area_credit_officers,
                    key="admin_area_credit_officer"
                )
            )

            working_data = working_data[
                working_data[fdo_col]
                .astype(str)
                .str.strip()
                .str.casefold()
                ==
                normalize_value(
                    selected_credit_officer
                )
            ].copy()

        else:

            selected_credit_officer = (
                "All Credit Officers"
            )


    # ========================================================
    # ADMIN -> BRANCH MANAGER
    # ========================================================

    elif admin_selection_type == "Branch Manager":

        selected_branch_manager = (
            st.sidebar.selectbox(
                "Select Branch Manager:",
                BRANCH_MANAGER_NAMES,
                key="admin_branch_manager"
            )
        )

        selected_manager_branch = (
            BRANCH_MANAGERS2.get(
                selected_branch_manager
            )
        )

        working_data = data[
            data[branch_col]
            .astype(str)
            .str.strip()
            .str.casefold()
            ==
            normalize_value(
                selected_manager_branch
            )
        ].copy()

        selected_area_manager = None

        selected_credit_officer = None


    # ========================================================
    # ADMIN -> CREDIT OFFICER
    # ========================================================

    else:

        admin_credit_officers = sorted(
            [
                str(x).strip()
                for x in data[
                    fdo_col
                ].dropna().unique()
                if (
                    str(x).strip()
                    and
                    str(x).strip().lower()
                    not in [
                        "unknown",
                        "nan",
                        "none"
                    ]
                )
            ]
        )

        if not admin_credit_officers:

            st.error(
                "No Credit Officers were found "
                "in the data."
            )

            st.stop()

        selected_credit_officer = (
            st.sidebar.selectbox(
                "Select Credit Officer:",
                admin_credit_officers,
                key="admin_credit_officer"
            )
        )

        working_data = data[
            data[fdo_col]
            .astype(str)
            .str.strip()
            .str.casefold()
            ==
            normalize_value(
                selected_credit_officer
            )
        ].copy()


# ============================================================
# CREDIT OFFICER
# ============================================================

elif user_role == "credit_officer":

    selected_credit_officer = logged_in_user

    working_data = data[
        data[fdo_col]
        .astype(str)
        .str.strip()
        .str.casefold()
        ==
        normalize_value(logged_in_user)
    ].copy()


# ============================================================
# AREA MANAGER
# ============================================================

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

    selected_area_manager = logged_in_user

    working_data = data[
        data[area_col]
        .astype(str)
        .str.strip()
        .str.casefold()
        ==
        normalize_value(manager_area)
    ].copy()


    # ========================================================
    # AREA MANAGER VIEW TYPE
    # ========================================================

    st.sidebar.markdown(
        "### Dashboard Selection"
    )

    area_manager_view_type = st.sidebar.radio(
        "View data as:",
        [
            "All Credit Officers",
            "Branch Manager",
            "Credit Officer"
        ],
        key="area_manager_view_type"
    )


    # ========================================================
    # AREA MANAGER -> ALL CREDIT OFFICERS
    # ========================================================

    if area_manager_view_type == "All Credit Officers":

        selected_credit_officer = (
            "All Credit Officers"
        )

        selected_branch_manager = None


    # ========================================================
    # AREA MANAGER -> BRANCH MANAGER
    # ========================================================

    elif area_manager_view_type == "Branch Manager":

        selected_credit_officer = None

        area_branches = set(
            normalize_value(x)
            for x in working_data[
                branch_col
            ].dropna().unique()
            if normalize_value(x)
            not in [
                "",
                "nan",
                "none"
            ]
        )

        area_branch_managers = sorted(
            [
                manager
                for manager, branch
                in BRANCH_MANAGERS2.items()
                if normalize_value(branch)
                in area_branches
            ]
        )

        if not area_branch_managers:

            st.error(
                "No Branch Managers were found "
                "for the selected Area."
            )

            st.stop()

        selected_branch_manager = (
            st.sidebar.selectbox(
                "Select Branch Manager:",
                area_branch_managers,
                key="area_manager_branch_manager"
            )
        )

        selected_manager_branch = (
            BRANCH_MANAGERS2.get(
                selected_branch_manager
            )
        )

        if selected_manager_branch is None:

            st.error(
                "The selected Branch Manager is not "
                "assigned to a Branch."
            )

            st.stop()

        st.sidebar.info(
            "Assigned Branch: "
            + str(selected_manager_branch)
        )

        working_data = working_data[
            working_data[branch_col]
            .astype(str)
            .str.strip()
            .str.casefold()
            ==
            normalize_value(
                selected_manager_branch
            )
        ].copy()


    # ========================================================
    # AREA MANAGER -> CREDIT OFFICER
    # ========================================================

    else:

        selected_branch_manager = None

        area_credit_officers = sorted(
            [
                str(x).strip()
                for x in working_data[
                    fdo_col
                ].dropna().unique()
                if (
                    str(x).strip()
                    and
                    str(x).strip().lower()
                    not in [
                        "unknown",
                        "nan",
                        "none"
                    ]
                )
            ]
        )

        if not area_credit_officers:

            st.error(
                "No Credit Officers were found "
                "in your Area."
            )

            st.stop()

        selected_credit_officer = (
            st.sidebar.selectbox(
                "Select Credit Officer:",
                area_credit_officers,
                key="area_manager_credit_officer"
            )
        )

        working_data = working_data[
            working_data[fdo_col]
            .astype(str)
            .str.strip()
            .str.casefold()
            ==
            normalize_value(
                selected_credit_officer
            )
        ].copy()


# ============================================================
# BRANCH MANAGER
# ============================================================

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

    selected_area_manager = None

    selected_branch_manager = logged_in_user

    selected_manager_branch = manager_branch


    # ========================================================
    # FIRST FILTER TO THE BRANCH
    # ========================================================

    branch_data = data[
        data[branch_col]
        .astype(str)
        .str.strip()
        .str.casefold()
        ==
        normalize_value(manager_branch)
    ].copy()


    # ========================================================
    # FIND CREDIT OFFICERS IN THIS BRANCH
    # ========================================================

    branch_credit_officers = sorted(
        [
            str(x).strip()
            for x in branch_data[
                fdo_col
            ].dropna().unique()
            if (
                str(x).strip()
                and
                str(x).strip().lower()
                not in [
                    "unknown",
                    "nan",
                    "none"
                ]
            )
        ]
    )


    # ========================================================
    # BRANCH MANAGER CREDIT OFFICER DROPDOWN
    # ========================================================

    st.sidebar.markdown(
        "### Dashboard Selection"
    )

    if not branch_credit_officers:

        st.error(
            "No Credit Officers were found "
            "in your Branch."
        )

        st.stop()


    selected_credit_officer = (
        st.sidebar.selectbox(
            "Select Credit Officer:",
            [
                "All Credit Officers"
            ]
            +
            branch_credit_officers,
            key="branch_manager_credit_officer"
        )
    )


    # ========================================================
    # FILTER BRANCH DATA BY CREDIT OFFICER
    # ========================================================

    if selected_credit_officer == "All Credit Officers":

        working_data = branch_data.copy()

    else:

        working_data = branch_data[
            branch_data[fdo_col]
            .astype(str)
            .str.strip()
            .str.casefold()
            ==
            normalize_value(
                selected_credit_officer
            )
        ].copy()


# ============================================================
# INVALID ROLE
# ============================================================

else:

    st.error("Invalid user role.")

    st.stop()


# ============================================================
# CHECK DATA ACCESS
# ============================================================

if working_data.empty:

    st.error(
        "There are no records available "
        "for the selected filters."
    )

    st.stop()


# ============================================================
# SAVE SHARED SESSION DATA
# ============================================================

st.session_state["working_data"] = working_data

st.session_state["AREA_MANAGERS2"] = AREA_MANAGERS2

st.session_state["BRANCH_MANAGERS2"] = BRANCH_MANAGERS2


# ============================================================
# CURRENT SELECTION
# ============================================================

if user_role == "superuser":

    if admin_selection_type == "All Data":

        st.caption(
            "Administrator | Viewing: All Data"
        )

    elif admin_selection_type == "Area Manager":

        if selected_credit_officer == "All Credit Officers":

            st.caption(
                "Administrator"
                + " | Area Manager: "
                + str(selected_area_manager)
                + " | Area: "
                + str(selected_manager_area)
                + " | Credit Officer: All"
            )

        else:

            st.caption(
                "Administrator"
                + " | Area Manager: "
                + str(selected_area_manager)
                + " | Area: "
                + str(selected_manager_area)
                + " | Credit Officer: "
                + str(selected_credit_officer)
            )

    elif admin_selection_type == "Branch Manager":

        st.caption(
            "Administrator"
            + " | Branch Manager: "
            + str(selected_branch_manager)
            + " | Branch: "
            + str(selected_manager_branch)
        )

    else:

        st.caption(
            "Administrator"
            + " | Credit Officer: "
            + str(selected_credit_officer)
        )


elif user_role == "area_manager":

    if area_manager_view_type == "All Credit Officers":

        st.caption(
            "Area Manager: "
            + str(logged_in_user)
            + " | Area: "
            + str(manager_area)
            + " | Credit Officer: All"
        )

    elif area_manager_view_type == "Branch Manager":

        st.caption(
            "Area Manager: "
            + str(logged_in_user)
            + " | Area: "
            + str(manager_area)
            + " | Branch Manager: "
            + str(selected_branch_manager)
            + " | Branch: "
            + str(selected_manager_branch)
        )

    else:

        st.caption(
            "Area Manager: "
            + str(logged_in_user)
            + " | Area: "
            + str(manager_area)
            + " | Credit Officer: "
            + str(selected_credit_officer)
        )


elif user_role == "branch_manager":

    if selected_credit_officer == "All Credit Officers":

        st.caption(
            "Branch Manager: "
            + str(logged_in_user)
            + " | Branch: "
            + str(manager_branch)
            + " | Credit Officer: All"
        )

    else:

        st.caption(
            "Branch Manager: "
            + str(logged_in_user)
            + " | Branch: "
            + str(manager_branch)
            + " | Credit Officer: "
            + str(selected_credit_officer)
        )


elif user_role == "credit_officer":

    st.caption(
        "Credit Officer: "
        + str(logged_in_user)
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

    # Remove those records
    working_data = working_data[
        ~exclude_mask
    ].copy()
    
# ============================================================
# SUMMARY CALCULATIONS
# ============================================================

numeric_loan = (
    pd.to_numeric(
        working_data[loan_col],
        errors="coerce"
    )
    .fillna(0)
)

numeric_overdue = (
    pd.to_numeric(
        working_data[overdue_col],
        errors="coerce"
    )
    .fillna(0)
)


total_loan = numeric_loan.sum()

total_overdue = numeric_overdue.sum()

total_overdue = max(
    total_overdue,
    0
)

total_overdue = min(
    total_overdue,
    max(total_loan, 0)
)

non_overdue = (
    total_loan
    -
    total_overdue
)

if total_loan > 0:

    overdue_percent = (
        total_overdue
        /
        total_loan
        *
        100
    )

else:

    overdue_percent = 0


# ============================================================
# CLIENT COUNTS
# ============================================================

total_clients = (
    working_data
    .dropna(
        subset=[client_col]
    )[client_col]
    .astype(str)
    .str.strip()
    .replace(
        "",
        pd.NA
    )
    .dropna()
    .nunique()
)


overdue_client_names = (
    working_data.loc[
        numeric_overdue > 0,
        client_col
    ]
    .dropna()
    .astype(str)
    .str.strip()
)

overdue_client_names = (
    overdue_client_names[
        overdue_client_names != ""
    ].unique()
)

overdue_clients = len(
    overdue_client_names
)

non_overdue_clients = max(
    total_clients
    -
    overdue_clients,
    0
)

if total_clients > 0:

    overdue_client_percent = (
        overdue_clients
        /
        total_clients
        *
        100
    )

else:

    overdue_client_percent = 0


# ============================================================
# FIND DAYS IN ARREARS COLUMN
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
        "days_in_arrears"
    ]
)


# ============================================================
# ARREARS CATEGORY FUNCTION
# ============================================================

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


# ============================================================
# PIE CLICK HANDLING
# ============================================================

def get_clicked_slice(events):

    if not events:

        return None

    try:

        event = events[0]

        if isinstance(event, dict):

            if "pointNumber" in event:

                return int(
                    event["pointNumber"]
                )

            if "pointIndex" in event:

                return int(
                    event["pointIndex"]
                )

        return None

    except Exception:

        return None


# ============================================================
# CREATE A STABLE SIGNATURE FOR A CLICK EVENT
# ============================================================

def get_event_signature(events):

    if not events:

        return None

    try:

        event = events[0]

        if isinstance(event, dict):

            return json.dumps(
                event,
                sort_keys=True,
                default=str
            )

        return str(event)

    except Exception:

        return str(events)


# ============================================================
# UPDATE PIE BREAKDOWN
# ============================================================

def update_pie_breakdown(
    new_breakdown
):

    if (
        st.session_state.get(
            "selected_pie_breakdown"
        )
        !=
        new_breakdown
    ):

        st.session_state[
            "selected_pie_breakdown"
        ] = new_breakdown

        st.rerun()


# ============================================================
# DETERMINE WHETHER PIES ARE CLICKABLE
# ============================================================

can_click_pies = False


# ============================================================
# ADMIN
# ============================================================

if user_role == "superuser":

    # Admin -> All Data
    if admin_selection_type == "All Data":

        can_click_pies = True

    # Admin -> Area Manager -> All Credit Officers
    elif (
        admin_selection_type == "Area Manager"
        and
        selected_credit_officer == "All Credit Officers"
    ):

        can_click_pies = True

    # Admin -> Branch Manager -> All Credit Officers
    #
    # This is only relevant if you later add an
    # All Credit Officers option to the Admin Branch
    # Manager view.
    elif (
        admin_selection_type == "Branch Manager"
        and
        selected_credit_officer == "All Credit Officers"
    ):

        can_click_pies = True


# ============================================================
# AREA MANAGER
# ============================================================

elif user_role == "area_manager":

    if area_manager_view_type == "All Credit Officers":

        can_click_pies = True


# ============================================================
# BRANCH MANAGER
# ============================================================

elif user_role == "branch_manager":

    # Branch Manager -> All Credit Officers
    #
    # The Branch Manager sees the complete branch,
    # so the pie charts can be clicked and will
    # generate the Credit Officer breakdown.
    if selected_credit_officer == "All Credit Officers":

        can_click_pies = True


# ============================================================
# RESET BREAKDOWN WHEN FILTER SELECTION CHANGES
# ============================================================

current_filter_signature = (
    user_role,

    admin_selection_type
    if user_role == "superuser"
    else None,

    area_manager_view_type
    if user_role == "area_manager"
    else None,

    selected_area_manager,

    selected_branch_manager,

    selected_credit_officer
)


if (
    st.session_state.get(
        "filter_signature"
    )
    !=
    current_filter_signature
):

    st.session_state[
        "filter_signature"
    ] = current_filter_signature

    st.session_state[
        "selected_pie_breakdown"
    ] = None

    st.session_state[
        "last_loan_pie_event"
    ] = None

    st.session_state[
        "last_client_pie_event"
    ] = None

    st.session_state[
        "last_arrears_pie_event"
    ] = None


# ============================================================
# CREATE THREE PIE CHARTS
# ============================================================

col1, col2, col3 = st.columns(3)


# ============================================================
# PIE CHART 1 — LOAN PORTFOLIO
# ============================================================

with col1:

    pie_fig_loan = go.Figure(
        data=[
            go.Pie(
                labels=[
                    "Active Loan Portfolio",
                    "Overdue Loan"
                ],
                values=[
                    non_overdue,
                    total_overdue
                ],
                marker=dict(
                    colors=[
                        "#2E86DE",
                        "#E74C3C"
                    ]
                ),
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
                font=dict(size=15),
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

        paper_bgcolor="white",

        plot_bgcolor="white",

        font=dict(
            color="#222222"
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


    if can_click_pies:

        loan_events = plotly_events(
            pie_fig_loan,
            click_event=True,
            select_event=False,
            hover_event=False,
            override_height=450,
            override_width="100%",
            key="loan_portfolio_pie_events"
        )

        loan_event_signature = (
            get_event_signature(
                loan_events
            )
        )

        if (
            loan_event_signature is not None
            and
            loan_event_signature
            !=
            st.session_state[
                "last_loan_pie_event"
            ]
        ):

            st.session_state[
                "last_loan_pie_event"
            ] = loan_event_signature

            clicked = get_clicked_slice(
                loan_events
            )

            if clicked == 0:

                update_pie_breakdown(
                    "Active Loan Portfolio"
                )

            elif clicked == 1:

                update_pie_breakdown(
                    "Overdue Loan"
                )

    else:

        st.plotly_chart(
            pie_fig_loan,
            width="stretch",
            key="loan_portfolio_pie"
        )


# ============================================================
# PIE CHART 2 — CLIENT PORTFOLIO
# ============================================================

with col2:

    pie_fig_clients = go.Figure(
        data=[
            go.Pie(
                labels=[
                    "Active Clients",
                    "Pastdue Clients"
                ],
                values=[
                    non_overdue_clients,
                    overdue_clients
                ],
                marker=dict(
                    colors=[
                        "#2E86DE",
                        "#E74C3C"
                    ]
                ),
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
                font=dict(size=15),
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

        paper_bgcolor="white",

        plot_bgcolor="white",

        font=dict(
            color="#222222"
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


    if can_click_pies:

        client_events = plotly_events(
            pie_fig_clients,
            click_event=True,
            select_event=False,
            hover_event=False,
            override_height=450,
            override_width="100%",
            key="client_portfolio_pie_events"
        )

        client_event_signature = (
            get_event_signature(
                client_events
            )
        )

        if (
            client_event_signature is not None
            and
            client_event_signature
            !=
            st.session_state[
                "last_client_pie_event"
            ]
        ):

            st.session_state[
                "last_client_pie_event"
            ] = client_event_signature

            clicked = get_clicked_slice(
                client_events
            )

            if clicked == 0:

                update_pie_breakdown(
                    "Active Clients"
                )

            elif clicked == 1:

                update_pie_breakdown(
                    "Pastdue Clients"
                )

    else:

        st.plotly_chart(
            pie_fig_clients,
            width="stretch",
            key="client_portfolio_pie"
        )


# ============================================================
# PIE CHART 3 — OVERDUE BY DAYS IN ARREARS
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

        arrears_data = working_data.copy()

        arrears_data[
            "_days_in_arrears"
        ] = (
            pd.to_numeric(
                arrears_data[
                    days_arrears_col
                ],
                errors="coerce"
            )
            .fillna(0)
        )

        arrears_data[
            "_overdue_value"
        ] = (
            pd.to_numeric(
                arrears_data[
                    overdue_col
                ],
                errors="coerce"
            )
            .fillna(0)
        )

        arrears_data = arrears_data[
            arrears_data[
                "_overdue_value"
            ] > 0
        ].copy()

        arrears_data[
            "_arrears_category"
        ] = (
            arrears_data[
                "_days_in_arrears"
            ]
            .apply(
                arrears_category
            )
        )

        arrears_order = [
            "1–30",
            "31–60",
            "61–90",
            "91–180",
            "181–365",
            ">365"
        ]

        arrears_summary = (
            arrears_data
            .groupby(
                "_arrears_category"
            )["_overdue_value"]
            .sum()
            .reindex(
                arrears_order,
                fill_value=0
            )
        )

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
                        labels=arrears_summary.index.tolist(),

                        values=arrears_summary.values.tolist(),

                        domain=dict(
                            x=[
                                0.12,
                                0.92
                            ],
                            y=[
                                0.28,
                                0.92
                            ]
                        ),

                        marker=dict(
                            colors=[
                                "#2E86DE",
                                "#F39C12",
                                "#E67E22",
                                "#D35400",
                                "#C0392B",
                                "#8E44AD"
                            ][:len(arrears_summary)]
                        ),

                        hole=0.55,

                        textinfo="label+percent",

                        textposition="outside",

                        sort=False,

                        direction="clockwise",

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
                    x=0.52,
                    xanchor="center",
                    y=0.98
                ),

                annotations=[
                    dict(
                        text=(
                            "<b>Total Overdue</b><br>"
                            f"₱{total_overdue:,.2f}"
                        ),

                        x=0.52,

                        y=0.60,

                        font=dict(
                            size=13
                        ),

                        showarrow=False
                    )
                ],

                height=500,

                margin=dict(
                    l=10,
                    r=10,
                    t=65,
                    b=145
                ),

                paper_bgcolor="white",

                plot_bgcolor="white",

                font=dict(
                    color="#222222"
                ),

                showlegend=True,

                legend=dict(
                    orientation="h",

                    yanchor="top",

                    y=0.18,

                    xanchor="center",

                    x=0.5,

                    font=dict(
                        size=10
                    ),

                    bgcolor="rgba(255,255,255,0)"
                )
            )


            if can_click_pies:

                arrears_events = plotly_events(
                    pie_fig_arrears,

                    click_event=True,

                    select_event=False,

                    hover_event=False,

                    override_height=500,

                    override_width="100%",

                    key="overdue_days_pie_events"
                )

                arrears_event_signature = (
                    get_event_signature(
                        arrears_events
                    )
                )

                if (
                    arrears_event_signature is not None
                    and
                    arrears_event_signature
                    !=
                    st.session_state[
                        "last_arrears_pie_event"
                    ]
                ):

                    st.session_state[
                        "last_arrears_pie_event"
                    ] = arrears_event_signature

                    clicked = get_clicked_slice(
                        arrears_events
                    )

                    if (
                        clicked is not None
                        and
                        0 <= clicked
                        <
                        len(arrears_summary)
                    ):

                        clicked_category = (
                            arrears_summary.index[
                                clicked
                            ]
                        )

                        update_pie_breakdown(
                            "Arrears: "
                            + str(clicked_category)
                        )

            else:

                st.plotly_chart(
                    pie_fig_arrears,
                    width="stretch",
                    key="overdue_days_pie"
                )


# ============================================================
# CREDIT OFFICER BREAKDOWN
# ============================================================

selected_breakdown = (
    st.session_state.get(
        "selected_pie_breakdown"
    )
)


if (
    can_click_pies
    and
    selected_breakdown is not None
):

    st.markdown("---")

    st.subheader(
        selected_breakdown
        + " by Credit Officer"
    )

    breakdown_data = working_data.copy()

    breakdown_data[
        "_credit_officer"
    ] = (
        breakdown_data[
            fdo_col
        ]
        .astype(str)
        .str.strip()
    )

    breakdown_data = (
        breakdown_data[
            ~breakdown_data[
                "_credit_officer"
            ]
            .str.lower()
            .isin(
                [
                    "",
                    "nan",
                    "none",
                    "unknown"
                ]
            )
        ].copy()
    )


    # ========================================================
    # LOAN VALUE BREAKDOWNS
    # ========================================================

    if selected_breakdown in [
        "Active Loan Portfolio",
        "Overdue Loan"
    ]:

        breakdown_data[
            "_loan"
        ] = (
            pd.to_numeric(
                breakdown_data[
                    loan_col
                ],
                errors="coerce"
            )
            .fillna(0)
        )

        breakdown_data[
            "_overdue"
        ] = (
            pd.to_numeric(
                breakdown_data[
                    overdue_col
                ],
                errors="coerce"
            )
            .fillna(0)
        )

        breakdown_data[
            "_overdue"
        ] = (
            breakdown_data[
                "_overdue"
            ]
            .clip(
                lower=0
            )
        )

        breakdown_data[
            "_overdue"
        ] = (
            breakdown_data[
                "_overdue"
            ]
            .clip(
                upper=breakdown_data[
                    "_loan"
                ].clip(
                    lower=0
                )
            )
        )

        if (
            selected_breakdown
            ==
            "Active Loan Portfolio"
        ):

            breakdown_data[
                "_value"
            ] = (
                breakdown_data[
                    "_loan"
                ]
                -
                breakdown_data[
                    "_overdue"
                ]
            ).clip(
                lower=0
            )

        else:

            breakdown_data[
                "_value"
            ] = breakdown_data[
                "_overdue"
            ]

        co_summary = (
            breakdown_data
            .groupby(
                "_credit_officer"
            )["_value"]
            .sum()
            .sort_values(
                ascending=True
            )
        )

        total_value = co_summary.sum()

        if total_value > 0:

            percentages = (
                co_summary
                /
                total_value
                *
                100
            )

        else:

            percentages = co_summary * 0

        text_values = [

            (
                f"₱{value:,.2f} "
                f"({percentages.loc[co]:.1f}%)"
            )

            for co, value in co_summary.items()

        ]

        bar_fig = go.Figure(
            data=[
                go.Bar(
                    x=co_summary.values,
                    y=co_summary.index,
                    orientation="h",
                    text=text_values,
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Value: ₱%{x:,.2f}"
                        "<extra></extra>"
                    )
                )
            ]
        )

        bar_fig.update_layout(

            title=dict(
                text=(
                    selected_breakdown
                    + " by Credit Officer"
                ),
                x=0.5,
                xanchor="center"
            ),

            xaxis=dict(
                title="Loan Value"
            ),

            yaxis=dict(
                title="Credit Officer"
            ),

            height=max(
                400,
                70 * len(co_summary)
            ),

            margin=dict(
                l=180,
                r=220,
                t=80,
                b=70
            ),

            showlegend=False
        )

        st.plotly_chart(
            bar_fig,
            width="stretch",
            key=(
                "breakdown_"
                + selected_breakdown
            )
        )


    # ========================================================
    # CLIENT BREAKDOWNS
    # ========================================================

    elif selected_breakdown in [
        "Active Clients",
        "Pastdue Clients"
    ]:

        client_data = working_data.copy()

        client_data[
            "_client"
        ] = (
            client_data[
                client_col
            ]
            .astype(str)
            .str.strip()
        )

        client_data[
            "_credit_officer"
        ] = (
            client_data[
                fdo_col
            ]
            .astype(str)
            .str.strip()
        )

        client_data[
            "_overdue"
        ] = (
            pd.to_numeric(
                client_data[
                    overdue_col
                ],
                errors="coerce"
            )
            .fillna(0)
        )

        client_data = (
            client_data[
                (
                    client_data[
                        "_client"
                    ] != ""
                )
                &
                (
                    client_data[
                        "_client"
                    ].str.lower()
                    != "nan"
                )
            ].copy()
        )

        client_data = (
            client_data[
                ~client_data[
                    "_credit_officer"
                ]
                .str.lower()
                .isin(
                    [
                        "",
                        "nan",
                        "none",
                        "unknown"
                    ]
                )
            ].copy()
        )

        client_status = (
            client_data
            .groupby(
                [
                    "_credit_officer",
                    "_client"
                ]
            )["_overdue"]
            .max()
            .reset_index()
        )

        if selected_breakdown == "Pastdue Clients":

            client_status = client_status[
                client_status[
                    "_overdue"
                ] > 0
            ].copy()

        else:

            client_status = client_status[
                client_status[
                    "_overdue"
                ] <= 0
            ].copy()

        co_summary = (
            client_status
            .groupby(
                "_credit_officer"
            )["_client"]
            .nunique()
            .sort_values(
                ascending=True
            )
        )

        total_clients_breakdown = co_summary.sum()

        if total_clients_breakdown > 0:

            percentages = (
                co_summary
                /
                total_clients_breakdown
                *
                100
            )

        else:

            percentages = co_summary * 0

        text_values = [

            (
                f"{int(value):,} "
                f"({percentages.loc[co]:.1f}%)"
            )

            for co, value in co_summary.items()

        ]

        bar_fig = go.Figure(
            data=[
                go.Bar(
                    x=co_summary.values,
                    y=co_summary.index,
                    orientation="h",
                    text=text_values,
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Clients: %{x:,}"
                        "<extra></extra>"
                    )
                )
            ]
        )

        bar_fig.update_layout(

            title=dict(
                text=(
                    selected_breakdown
                    + " by Credit Officer"
                ),
                x=0.5,
                xanchor="center"
            ),

            xaxis=dict(
                title="Number of Clients"
            ),

            yaxis=dict(
                title="Credit Officer"
            ),

            height=max(
                400,
                70 * len(co_summary)
            ),

            margin=dict(
                l=180,
                r=180,
                t=80,
                b=70
            ),

            showlegend=False
        )

        st.plotly_chart(
            bar_fig,
            width="stretch",
            key=(
                "breakdown_"
                + selected_breakdown
            )
        )


    # ========================================================
    # ARREARS BREAKDOWN
    # ========================================================

    elif selected_breakdown.startswith("Arrears:"):

        selected_category = (
            selected_breakdown
            .replace(
                "Arrears:",
                ""
            )
            .strip()
        )

        if days_arrears_col is None:

            st.warning(
                "Days in arrears column was not found."
            )

        else:

            arrears_breakdown = working_data.copy()

            arrears_breakdown[
                "_credit_officer"
            ] = (
                arrears_breakdown[
                    fdo_col
                ]
                .astype(str)
                .str.strip()
            )

            arrears_breakdown[
                "_days_in_arrears"
            ] = (
                pd.to_numeric(
                    arrears_breakdown[
                        days_arrears_col
                    ],
                    errors="coerce"
                )
                .fillna(0)
            )

            arrears_breakdown[
                "_overdue_value"
            ] = (
                pd.to_numeric(
                    arrears_breakdown[
                        overdue_col
                    ],
                    errors="coerce"
                )
                .fillna(0)
            )

            arrears_breakdown = (
                arrears_breakdown[
                    arrears_breakdown[
                        "_overdue_value"
                    ] > 0
                ].copy()
            )

            arrears_breakdown[
                "_category"
            ] = (
                arrears_breakdown[
                    "_days_in_arrears"
                ]
                .apply(
                    arrears_category
                )
            )

            arrears_breakdown = (
                arrears_breakdown[
                    arrears_breakdown[
                        "_category"
                    ]
                    ==
                    selected_category
                ].copy()
            )

            arrears_breakdown = (
                arrears_breakdown[
                    ~arrears_breakdown[
                        "_credit_officer"
                    ]
                    .str.lower()
                    .isin(
                        [
                            "",
                            "nan",
                            "none",
                            "unknown"
                        ]
                    )
                ].copy()
            )

            co_summary = (
                arrears_breakdown
                .groupby(
                    "_credit_officer"
                )["_overdue_value"]
                .sum()
                .sort_values(
                    ascending=True
                )
            )

            total_value = co_summary.sum()

            if total_value > 0:

                percentages = (
                    co_summary
                    /
                    total_value
                    *
                    100
                )

            else:

                percentages = co_summary * 0

            text_values = [

                (
                    f"₱{value:,.2f} "
                    f"({percentages.loc[co]:.1f}%)"
                )

                for co, value in co_summary.items()

            ]

            bar_fig = go.Figure(
                data=[
                    go.Bar(
                        x=co_summary.values,
                        y=co_summary.index,
                        orientation="h",
                        text=text_values,
                        textposition="outside",
                        cliponaxis=False,
                        hovertemplate=(
                            "<b>%{y}</b><br>"
                            "Overdue: ₱%{x:,.2f}"
                            "<extra></extra>"
                        )
                    )
                ]
            )

            bar_fig.update_layout(

                title=dict(
                    text=(
                        "Overdue Loan "
                        + selected_category
                        + " by Credit Officer"
                    ),
                    x=0.5,
                    xanchor="center"
                ),

                xaxis=dict(
                    title="Overdue Loan Value"
                ),

                yaxis=dict(
                    title="Credit Officer"
                ),

                height=max(
                    400,
                    70 * len(co_summary)
                ),

                margin=dict(
                    l=180,
                    r=220,
                    t=80,
                    b=70
                ),

                showlegend=False
            )

            st.plotly_chart(
                bar_fig,
                width="stretch",
                key=(
                    "breakdown_"
                    + selected_breakdown
                )
            )


# ============================================================
# OVERDUE SUMMARY
# ============================================================

st.caption(
    f"Total Loan Value: ₱{total_loan:,.2f}"
    f" | Total Overdue: ₱{total_overdue:,.2f}"
    f" | Overdue Rate: {overdue_percent:.1f}%"
    f" | Total Clients: {total_clients:,}"
    f" | Pastdue Clients: {overdue_clients:,}"
    f" | Overdue Client Rate: "
    f"{overdue_client_percent:.1f}%"
)
