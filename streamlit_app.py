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
st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des astreintes")

# --- Login ---
users = load_users()
user_code = st.text_input("Entrez votre code personnel :", type="password")
current_user = check_user(user_code, users)

if current_user:
    st.success(f"Connecté en tant que : {current_user}")
else:
    st.warning("Veuillez entrer votre code pour vous connecter.")

# --- Sélection du mois et année ---
mois = [calendar.month_name[i] for i in range(1, 13)]
month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
month = mois.index(month_name) + 1
year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

# --- Jours du mois ---
first_day = datetime.date(year, month, 1)
last_day = calendar.monthrange(year, month)[1]
month_days = [first_day + datetime.timedelta(days=i) for i in range(last_day)]

# --- Charger tous les plannings existants ---
all_plannings = load_all_plannings()
if not all_plannings.empty:
    all_plannings["Date"] = pd.to_datetime(all_plannings["Date"]).dt.date
    all_plannings["Jour"] = all_plannings["Date"].apply(lambda d: d.strftime("%A"))

# --- Standard planning ---
STANDARD_FILE = "utils/standard_planning.csv"

def load_standard(user):
    try:
        df_standard = pd.read_csv(STANDARD_FILE)
        user_df = df_standard[df_standard["Utilisateur"] == user]
        if not user_df.empty:
            return user_df.iloc[0][plages].to_dict()
    except FileNotFoundError:
        st.warning("Fichier de planning standard non trouvé.")
    return {plage: "" for plage in plages}

def save_standard(user, df_user):
    import os
    if not os.path.exists(STANDARD_FILE):
        df_standard = pd.DataFrame(columns=["Utilisateur"] + plages)
    else:
        df_standard = pd.read_csv(STANDARD_FILE)
        df_standard = df_standard[df_standard["Utilisateur"] != user]
    new_row = {"Utilisateur": user}
    new_row.update(df_user.iloc[0][plages].to_dict())
    df_standard = pd.concat([df_standard, pd.DataFrame([new_row])], ignore_index=True)
    df_standard.to_csv(STANDARD_FILE, index=False)

# --- Calcul heures cumulées ---
def compute_user_hours(all_df):
    user_hours = {}
    jour_plages = ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"]
    nuit_plages = ["19h-00h","00h-07h"]
    for user in all_df["Utilisateur"].unique():
        df_user = all_df[all_df["Utilisateur"] == user]
        day_hours = df_user[jour_plages].applymap(lambda x: 1 if x in ["N1","N2","Backup1","Backup2"] else 0).sum().sum()
        night_hours = df_user[nuit_plages].applymap(lambda x: 1 if x in ["N1","N2","Backup1","Backup2"] else 0).sum().sum()
        user_hours[user] = {"jour": day_hours, "nuit": night_hours}
    return user_hours

# --- Attribution équilibrée N1/N2 ---
def assign_plage_final(day_df, plage, user_hours, is_night=False):
    result = {"N1": "", "N2": ""}
    for priority in ["N1", "N2"]:
        users_priority = day_df[day_df[plage] == priority]
        if not users_priority.empty:
            if is_night:
                users_priority = users_priority.assign(total_hours=users_priority["Utilisateur"].map(lambda u: user_hours[u]["nuit"]))
            else:
                users_priority = users_priority.assign(total_hours=users_priority["Utilisateur"].map(lambda u: user_hours[u]["jour"]))
            selected_user = users_priority.sort_values("total_hours").iloc[0]["Utilisateur"]
            result[priority] = selected_user
    return result

# --- Semaine actuelle ---
if "week_start" not in st.session_state:
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    st.session_state.week_start = week_start

col1, col2, col3 = st.columns([1,2,1])
with col1:
    if st.button("⬅️ Semaine précédente"):
        st.session_state.week_start -= datetime.timedelta(days=7)
with col3:
    if st.button("Semaine suivante ➡️"):
        st.session_state.week_start += datetime.timedelta(days=7)

st.subheader(f"Semaine du {st.session_state.week_start.strftime('%d/%m/%Y')}")
week_days = [st.session_state.week_start + datetime.timedelta(days=i) for i in range(7)
             if (st.session_state.week_start + datetime.timedelta(days=i)).month == month]

# --- Tableau utilisateur ---
if current_user:
    user_week_df = all_plannings[
        (all_plannings["Utilisateur"] == current_user) &
        (all_plannings["Date"].isin(week_days))
    ]
    if not user_week_df.empty:
        df = user_week_df.copy()
    else:
        standard = load_standard(current_user)
        rows = []
        for day in week_days:
            row = {"Date": day, "Jour": day.strftime("%A"), "Utilisateur": current_user}
            row.update(standard)
            rows.append(row)
        df = pd.DataFrame(rows)

    options = ["N1", "N2", "Backup1", "Backup2", ""]
    column_config = {plage: st.column_config.SelectboxColumn(options=options, label=plage) for plage in plages}
    edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder la semaine"):
            save_user_planning(current_user, edited_df)
            st.success("Planning de la semaine sauvegardé ✅")
    with col2:
        if st.button("💾 Sauvegarder comme standard"):
            save_standard(current_user, edited_df)
            st.success("Planning standard mis à jour ✅")

# --- Planning final semaine (N1 et N2 affichés) ---
st.header("📌 Planning final de la semaine")
if not all_plannings.empty:
    user_hours = compute_user_hours(all_plannings)
    week_table_rows = []
    week_df = all_plannings[all_plannings["Date"].isin(week_days)].copy()

    for day in week_days:
        row = {"Date": day, "Jour": day.strftime("%A")}
        day_df = week_df[week_df["Date"] == day]
        for plage in plages:
            is_night = plage in ["19h-00h", "00h-07h"]
            assigned = assign_plage_final(day_df, plage, user_hours, is_night=is_night)
            if assigned["N1"] and assigned["N2"]:
                row[plage] = f"N1 {assigned['N1']} | N2 {assigned['N2']}"
            elif assigned["N1"]:
                row[plage] = f"N1 {assigned['N1']}"
            elif assigned["N2"]:
                row[plage] = f"N2 {assigned['N2']}"
            else:
                row[plage] = ""
        week_table_rows.append(row)

    week_table_df = pd.DataFrame(week_table_rows)
    st.dataframe(week_table_df)

    # --- Graphiques ---
    jour_plages = ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"]
    nuit_plages = ["19h-00h","00h-07h"]

    fig_jour = plot_hours(all_plannings, jour_plages, "Heures journée (07h-19h)")
    fig_nuit = plot_hours(all_plannings, nuit_plages, "Heures nuit (19h-07h)")

    col1, col2 = st.columns(2)
    with col1:
        if fig_jour: st.plotly_chart(fig_jour, use_container_width=True)
    with col2:
        if fig_nuit: st.plotly_chart(fig_nuit, use_container_width=True)

