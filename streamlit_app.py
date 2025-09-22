import streamlit as st
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io

# ---------------- GOOGLE DRIVE AUTH ----------------
def connect_drive():
    creds_dict = json.loads(st.secrets["google_drive"]["service_account_json"])
    creds = Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

# ---------------- GOOGLE DRIVE FUNCTIONS ----------------
FOLDER_NAME = "Astreintes_Planning"

def get_or_create_folder(service):
    """Get or create a folder on Google Drive for storing plannings."""
    results = service.files().list(
        q=f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'",
        spaces="drive",
        fields="files(id, name)"
    ).execute()
    items = results.get("files", [])
    if items:
        return items[0]["id"]
    file_metadata = {
        "name": FOLDER_NAME,
        "mimeType": "application/vnd.google-apps.folder"
    }
    folder = service.files().create(body=file_metadata, fields="id").execute()
    return folder.get("id")

def upload_file(service, folder_id, filename, dataframe):
    """Upload or update a CSV file to Google Drive."""
    file_metadata = {"name": filename, "parents": [folder_id]}
    buffer = io.BytesIO()
    dataframe.to_csv(buffer, index=False)
    buffer.seek(0)

    # Check if file already exists
    results = service.files().list(
        q=f"name='{filename}' and '{folder_id}' in parents",
        spaces="drive",
        fields="files(id, name)"
    ).execute()
    items = results.get("files", [])

    media = MediaIoBaseUpload(buffer, mimetype="text/csv", resumable=True)

    if items:
        file_id = items[0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(body=file_metadata, media_body=media).execute()

def download_file(service, folder_id, filename):
    """Download CSV file from Google Drive."""
    results = service.files().list(
        q=f"name='{filename}' and '{folder_id}' in parents",
        spaces="drive",
        fields="files(id, name)"
    ).execute()
    items = results.get("files", [])
    if not items:
        return None
    file_id = items[0]["id"]

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh)

# ---------------- PLANNING FUNCTIONS ----------------
plages = ["Nuit", "Jour"]

def init_dataframe():
    return pd.DataFrame(columns=["Nom", "Jour", "Plage", "Rôle"])

def save_user_planning(df, username):
    service = connect_drive()
    folder_id = get_or_create_folder(service)
    upload_file(service, folder_id, f"{username}_planning.csv", df)

def load_user_planning(username):
    service = connect_drive()
    folder_id = get_or_create_folder(service)
    return download_file(service, folder_id, f"{username}_planning.csv")

def load_all_plannings():
    service = connect_drive()
    folder_id = get_or_create_folder(service)
    results = service.files().list(
        q=f"'{folder_id}' in parents",
        spaces="drive",
        fields="files(id, name)"
    ).execute()
    files = results.get("files", [])
    all_plans = []
    for f in files:
        if f["name"].endswith("_planning.csv"):
            df = download_file(service, folder_id, f["name"])
            if df is not None:
                all_plans.append(df)
    if all_plans:
        return pd.concat(all_plans, ignore_index=True)
    return init_dataframe()

# ---------------- STREAMLIT APP ----------------
st.title("📅 Gestion des Astreintes")

menu = st.sidebar.radio("Menu", ["Mon Planning", "Planning Global"])

if menu == "Mon Planning":
    username = st.text_input("Entrez votre nom :")
    if username:
        df_user = load_user_planning(username)
        if df_user is None:
            df_user = init_dataframe()

        st.subheader(f"Planning de {username}")
        with st.form("planning_form"):
            jour = st.date_input("Jour")
            plage = st.selectbox("Plage", plages)
            role = st.selectbox("Rôle", ["N1", "N2"])
            submitted = st.form_submit_button("Ajouter")
            if submitted:
                new_row = pd.DataFrame([{"Nom": username, "Jour": jour, "Plage": plage, "Rôle": role}])
                df_user = pd.concat([df_user, new_row], ignore_index=True)
                save_user_planning(df_user, username)
                st.success("✅ Planning sauvegardé sur Google Drive !")

        st.dataframe(df_user)

elif menu == "Planning Global":
    st.subheader("🌍 Vue Globale des Plannings")
    df_all = load_all_plannings()
    if not df_all.empty:
        st.dataframe(df_all)
    else:
        st.info("Aucun planning trouvé.")
