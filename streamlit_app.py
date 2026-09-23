#library(reticulate)
#py_install(c("streamlit"))
#py_install(c("plotly"))
#library(reticulate)

#py_require(c(
#    "google-api-python-client",
#    "google-auth"
#))

import streamlit as st
import pandas as pd
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


st.set_page_config(
    page_title="KCCDMFI Dashboard",
    layout="wide"
)


SCOPES = [
    "https://www.googleapis.com/auth/drive"
]

LOCAL_CREDENTIALS = (
    ".secrets/client_secret_kccdmfi-instafin.json"
)

DRIVE_FILE_ID = (
    "1kP_etSNeIq8LgWQNKec-L3IFVDmitLdx"
)

@st.cache_resource
def get_drive_service():

    if os.path.exists(LOCAL_CREDENTIALS):

        credentials = (
            service_account.Credentials
            .from_service_account_file(
                LOCAL_CREDENTIALS,
                scopes=SCOPES
            )
        )

    else:

        gcp_secrets = st.secrets[
            "gcp_service_account"
        ]

        credentials = (
            service_account.Credentials
            .from_service_account_info(
                dict(gcp_secrets),
                scopes=SCOPES
            )
        )

    return build(
        "drive",
        "v3",
        credentials=credentials
    )


@st.cache_data(ttl=300)
def load_data_from_drive():

    drive_service = get_drive_service()

    file_metadata = (
        drive_service
        .files()
        .get(
            fileId=DRIVE_FILE_ID,
            fields="id,name"
        )
        .execute()
    )

    filename = file_metadata["name"]

    local_directory = os.path.dirname(
        os.path.abspath(__file__)
    )

    local_file = os.path.join(
        local_directory,
        filename
    )

    request = (
        drive_service
        .files()
        .get_media(
            fileId=DRIVE_FILE_ID
        )
    )

    with open(local_file, "wb") as f:

        downloader = MediaIoBaseDownload(
            f,
            request
        )

        done = False

        while not done:

            status, done = (
                downloader.next_chunk()
            )

    return pd.read_csv(
        local_file,
        sep=";"
    )


# Load the data
if "data" not in st.session_state:

    with st.spinner(
        "Loading data from Google Drive..."
    ):

        st.session_state["data"] = (
            load_data_from_drive()
        )


data = st.session_state["data"]


st.title("KMFI Loan Dashboard")

st.success(
    f"Loaded {len(data):,} records."
)

pg = st.navigation(
    {
        "Dashboard": [
            st.Page(
                "pages/home.py",
                title="Home",
                icon="🏠"
            ),
            st.Page(
                "pages/pastdue3.py",
                title="Pastdue3",
                icon="⏰"
            ),
            st.Page(
                "pages/pastdue4.py",
                title="Pastdue4",
                icon="⏰"
            ),
            st.Page(
                "pages/loancycle.py",
                title="Loan Cycle",
                icon="🔄"
            ),
            st.Page(
                "pages/overdue.py",
                title="Overdue",
                icon="⚠️"
            ),
            st.Page(
                "pages/loanprod.py",
                title="Loan Product",
                icon="💰"
            ),
            st.Page(
                "pages/fdo.py",
                title="FDO",
                icon="👤"
            ),
            st.Page(
                "pages/branch.py",
                title="Branch",
                icon="🏢"
            ),
        ]
    }
)


# ---------------------------------------------------------
# Run selected page
# ---------------------------------------------------------

pg.run()
