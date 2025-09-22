# streamlit_app.py
import streamlit as st
import datetime
import calendar
import pandas as pd
import io
import json

# Google Drive libs
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# Utils locaux
from utils.auth import load_users, check_user
from utils.planning import init_dataframe, save_user_planning, load_all_plannings, load_standard_planning, plages
from utils.charts import plot_hours

st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des astreintes")

# ---------------- Google Drive helpers ----------------
def get_drive_service():
    creds_dict = {
        "type": st.secrets["google_drive"]["type"],
        "project_id": st.secrets["google_drive"]["project_id"],
        "private_key_id": st.secrets["google_drive"]["private_key_id"],
        "private_key": st.secrets["google_drive"]["private_key"],
        "client_email": st.secrets["google_drive"]["client_email"],
        "client_id": st.secrets["google_drive"]["client_id"],
        "auth_uri": st.secrets["google_drive"]["auth_uri"],
        "token_uri": st.secrets["google_drive"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["google_drive"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["google_drive"]["client_x509_cert_url"],
    }
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds)
    return service

FOLDER_NAME = "Astreintes_Planning"

def get_or_create_folder(service):
    q = f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'"
    res = service.files().list(q=q, spaces="drive", fields="files(id, name)").execute()
    items = res.get("files", [])
    if items:
        return items[0]["id"]
    metadata = {"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder.get("id")

def upload_df_to_drive(service, folder_id, filename, df):
    buffer = io.BytesIO()
    buffer.write(df.to_csv(index=False).encode("utf-8"))
    buffer.seek(0)
    media = MediaIoBaseUpload(buffer, mimetype="text/csv", resumable=True)

    q = f"name='{filename}' and '{folder_id}' in parents"
    res = service.files().list(q=q, spaces="drive", fields="files(id, name)").execute()
    items = res.get("files", [])
    if items:
        file_id = items[0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        metadata = {"name": filename, "parents": [folder_id]}
        service.files().create(body=metadata, media_body=media, fields="id").execute()

def download_csv_from_drive(service, folder_id, filename):
    q = f"name='{filename}' and '{folder_id}' in parents"
    res = service.files().list(q=q, spaces="drive", fields="files(id, name)").execute()
    items = res.get("files", [])
    if not items:
        return None
    file_id = items[0]["id"]
    req = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    try:
        df = pd.read_csv(fh)
        return df
    except Exception:
        return None
    
    # ---------------- Sidebar et connexion ----------------
st.sidebar.header("Connexion utilisateur")
raw_user = st.sidebar.text_input("Entrez votre nom", key="login_user")
current_user = raw_user.strip().capitalize() if raw_user else None
if current_user:
    st.sidebar.success(f"Connecté en tant que : {current_user}")
else:
    st.sidebar.info("Veuillez entrer votre nom pour accéder au planning.")

# Menu planning
st.sidebar.header("Affichage Planning")
planning_type = st.sidebar.radio(
    "Choisir le type de planning",
    ("Planning personnel", "Planning général")
)



# ---------------- Choix mois/année ----------------
mois = [calendar.month_name[i] for i in range(1, 13)]
month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month - 1)
month = mois.index(month_name) + 1
year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

first_day = datetime.date(year, month, 1)
last_day = calendar.monthrange(year, month)[1]
month_days = [first_day + datetime.timedelta(days=i) for i in range(last_day)]

# ---------------- Charger plannings existants ----------------
try:
    drive = get_drive_service()
    folder_id = get_or_create_folder(drive)
    df_all_drive = download_csv_from_drive(drive, folder_id, "all_plannings.csv")
    df_std_drive = download_csv_from_drive(drive, folder_id, "standard_planning.csv")
    if df_all_drive is not None:
        df_all_drive.to_csv("data/all_plannings.csv", index=False)
    if df_std_drive is not None:
        df_std_drive.to_csv("utils/standard_planning.csv", index=False)
except Exception as e:
    drive = None
    folder_id = None

all_plannings = load_all_plannings()
if not all_plannings.empty and "Date" in all_plannings.columns:
    # convert to datetime safely
    all_plannings["Date"] = pd.to_datetime(all_plannings["Date"], errors="coerce").dt.date
    # créer la colonne Jour en évitant les NaT
    all_plannings["Jour"] = all_plannings["Date"].apply(lambda d: d.strftime("%A") if pd.notnull(d) else "")

STANDARD_FILE = "utils/standard_planning.csv"

def load_standard(user):
    try:
        df_standard = pd.read_csv(STANDARD_FILE)
        if df_standard.empty:
            # fichier vide -> retourner dict vide
            return {plage: "" for plage in plages}
        user_df = df_standard[df_standard["Utilisateur"] == user]
        if not user_df.empty:
            return user_df.iloc[0][plages].to_dict()
    except FileNotFoundError:
        # fichier non trouvé -> retourner dict vide
        return {plage: "" for plage in plages}
    except pd.errors.EmptyDataError:
        # fichier vide -> retourner dict vide
        return {plage: "" for plage in plages}
    return {plage: "" for plage in plages}

def save_standard_local_and_drive(user, df_user):
    try:
        # Vérifier si le fichier existe et s'il contient des données
        try:
            df_standard = pd.read_csv(STANDARD_FILE)
            if df_standard.empty:
                df_standard = pd.DataFrame(columns=["Utilisateur"] + plages)
            else:
                df_standard = df_standard[df_standard["Utilisateur"] != user]
        except (FileNotFoundError, pd.errors.EmptyDataError):
            # Si fichier manquant ou vide -> créer DataFrame vide avec colonnes
            df_standard = pd.DataFrame(columns=["Utilisateur"] + plages)

        # Ajouter ou remplacer la ligne de l'utilisateur
        new_row = {"Utilisateur": user}
        new_row.update(df_user.iloc[0][plages].to_dict())
        df_standard = pd.concat([df_standard, pd.DataFrame([new_row])], ignore_index=True)

        # Sauvegarde locale
        df_standard.to_csv(STANDARD_FILE, index=False)

        # Upload sur Drive si configuré
        if drive and folder_id:
            upload_df_to_drive(drive, folder_id, "standard_planning.csv", df_standard)

        st.success("Planning standard mis à jour ✅")

    except Exception as e:
        st.error(f"Erreur en sauvegardant le standard: {e}")

def compute_user_hours(all_df):
    user_hours = {}
    jour_plages = ["07h-09h", "09h-12h", "12h-14h", "15h-18h", "18h-19h"]
    nuit_plages = ["19h-00h", "00h-07h"]
    if all_df.empty:
        return {u: {"jour": 0, "nuit": 0} for u in users.values()}
    for user in all_df["Utilisateur"].unique():
        df_user = all_df[all_df["Utilisateur"] == user]
        day_hours = 0
        night_hours = 0
        for p in jour_plages:
            if p in df_user.columns:
                day_hours += df_user[p].isin(["N1", "N2", "Backup1", "Backup2"]).sum()
        for p in nuit_plages:
            if p in df_user.columns:
                night_hours += df_user[p].isin(["N1", "N2", "Backup1", "Backup2"]).sum()
        user_hours[user] = {"jour": int(day_hours), "nuit": int(night_hours)}
    return user_hours

def assign_plage_final(day_df, plage, user_hours, is_night=False):
    result = {"N1": "", "N2": ""}
    for priority in ["N1", "N2"]:
        users_priority = day_df[day_df[plage] == priority]
        if not users_priority.empty:
            if is_night:
                users_priority = users_priority.assign(total_hours=users_priority["Utilisateur"].map(lambda u: user_hours.get(u, {"nuit":0})["nuit"]))
            else:
                users_priority = users_priority.assign(total_hours=users_priority["Utilisateur"].map(lambda u: user_hours.get(u, {"jour":0})["jour"]))
            selected_user = users_priority.sort_values("total_hours").iloc[0]["Utilisateur"]
            result[priority] = selected_user
    return result

# ---------------- Navigation semaine ----------------
if "week_start" not in st.session_state:
    today = datetime.date.today()
    st.session_state.week_start = today - datetime.timedelta(days=today.weekday())

col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("⬅️ Semaine précédente"):
        st.session_state.week_start -= datetime.timedelta(days=7)
with col3:
    if st.button("Semaine suivante ➡️"):
        st.session_state.week_start += datetime.timedelta(days=7)

st.subheader(f"Semaine du {st.session_state.week_start.strftime('%d/%m/%Y')}")
week_days = [st.session_state.week_start + datetime.timedelta(days=i) for i in range(7)
             if (st.session_state.week_start + datetime.timedelta(days=i)).month == month]

# ---------------- Mon Planning ----------------
if current_user:
    # Nettoyer le nom de l'utilisateur pour éviter les problèmes d'espaces
    current_user = current_user.strip()

    # Convertir Date en datetime.date pour correspondre à week_days
    if not all_plannings.empty and "Date" in all_plannings.columns:
        all_plannings["Date"] = pd.to_datetime(all_plannings["Date"], errors="coerce").dt.date

    # Nettoyer les noms d'utilisateur dans all_plannings
    all_plannings["Utilisateur"] = all_plannings["Utilisateur"].astype(str).str.strip()

    # Filtrer les données de la semaine pour l'utilisateur courant
    user_week_df = all_plannings[
        (all_plannings["Utilisateur"] == current_user) &
        (all_plannings["Date"].isin(week_days))
    ] if not all_plannings.empty else pd.DataFrame()

    # Si aucune donnée existante, utiliser le planning standard
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

    # Configurer le data_editor Streamlit
    options = ["N1", "N2", "Backup1", "Backup2", ""]
    column_config = {plage: st.column_config.SelectboxColumn(options=options, label=plage) for plage in plages}
    edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic")

    # ---------------- Sauvegarder la semaine ----------------
def save_week(current_user, edited_df):
    if edited_df.empty or "Date" not in edited_df.columns:
        st.error("Impossible de sauvegarder : le planning est vide.")
        return

    # Normaliser le nom dans le DataFrame
    edited_df["Utilisateur"] = current_user

    try:
        # Charger tous les plannings existants
        try:
            all_plannings_local = pd.read_csv("data/all_plannings.csv")
            all_plannings_local["Date"] = pd.to_datetime(all_plannings_local["Date"]).dt.date
        except (FileNotFoundError, pd.errors.EmptyDataError):
            all_plannings_local = pd.DataFrame(columns=edited_df.columns)

        # Supprimer l'ancien planning de l'utilisateur pour ces dates
        mask = (all_plannings_local["Utilisateur"] == current_user) & (all_plannings_local["Date"].isin(edited_df["Date"]))
        all_plannings_local = all_plannings_local[~mask]

        # Ajouter le nouveau planning
        all_plannings_local = pd.concat([all_plannings_local, edited_df], ignore_index=True)

        # Sauvegarde locale
        all_plannings_local.to_csv("data/all_plannings.csv", index=False)

        # Upload Drive
        if drive and folder_id:
            upload_df_to_drive(drive, folder_id, "all_plannings.csv", all_plannings_local)

        st.success("Planning de la semaine sauvegardé ✅")

    except Exception as e:
        st.error(f"Erreur sauvegarde: {e}")


# ---------------- Sauvegarder comme standard ----------------





def save_standard(current_user, edited_df):
    if edited_df.empty or "Date" not in edited_df.columns:
        st.error("Impossible de sauvegarder le standard : le planning est vide.")
        return

    edited_df["Utilisateur"] = current_user

    try:
        try:
            df_standard = pd.read_csv(STANDARD_FILE)
            if df_standard.empty:
                df_standard = pd.DataFrame(columns=["Utilisateur"] + plages)
            else:
                df_standard = df_standard[df_standard["Utilisateur"] != current_user]
        except (FileNotFoundError, pd.errors.EmptyDataError):
            df_standard = pd.DataFrame(columns=["Utilisateur"] + plages)

        new_row = {"Utilisateur": current_user}
        new_row.update(edited_df.iloc[0][plages].to_dict())
        df_standard = pd.concat([df_standard, pd.DataFrame([new_row])], ignore_index=True)

        df_standard.to_csv(STANDARD_FILE, index=False)

        if drive and folder_id:
            upload_df_to_drive(drive, folder_id, "standard_planning.csv", df_standard)

        st.success("Planning standard mis à jour ✅")

    except Exception as e:
        st.error(f"Erreur en sauvegardant le standard: {e}")

# ---------------- sidebar pour Sauvegarder  ----------------
col1, col2 = st.columns(2)

with col1:
    if st.button("💾 Sauvegarder la semaine"):
        save_week(current_user, edited_df)  # Appelle la fonction corrigée

with col2:
    if st.button("💾 Sauvegarder comme standard"):
        save_standard(current_user, edited_df)  # Appelle la fonction corrigée



# ---------------- Planning final semaine ----------------
if planning_type == "Planning général":
    st.header("📌 Planning final de la semaine")
    if not all_plannings.empty:
        # Calcul des heures
        user_hours = compute_user_hours(all_plannings)
        week_table_rows = []
        conflicts = []

        # Filtrer seulement les jours du mois sélectionné
        week_df = all_plannings[all_plannings["Date"].isin(month_days)].copy()

        for day in month_days:
            row = {"Date": day.strftime("%Y-%m-%d"), "Jour": day.strftime("%A")}
            day_df = week_df[week_df["Date"] == day]
            for plage in plages:
                is_night = plage in ["19h-00h", "00h-07h"]
                assigned = assign_plage_final(day_df, plage, user_hours, is_night=is_night)

                # Détection des conflits
                n1_list = day_df[day_df[plage] == "N1"]["Utilisateur"].tolist()
                n2_list = day_df[day_df[plage] == "N2"]["Utilisateur"].tolist()
                if len(n1_list) > 1:
                    conflicts.append({"Date": day.strftime("%Y-%m-%d"), "Plage": plage, "Role": "N1", "Users": ", ".join(n1_list)})
                if len(n2_list) > 1:
                    conflicts.append({"Date": day.strftime("%Y-%m-%d"), "Plage": plage, "Role": "N2", "Users": ", ".join(n2_list)})

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
        st.dataframe(week_table_df, use_container_width=True)

        # Affichage des conflits
        if conflicts:
            st.markdown("### ⚠️ Conflits détectés")
            df_conflicts = pd.DataFrame(conflicts)
            st.dataframe(df_conflicts, use_container_width=True)
        else:
            st.success("Aucun conflit détecté pour cette période ✅")

        # ---------------- Graphes ----------------
    jour_plages = ["07h-09h", "09h-12h", "12h-14h", "15h-18h", "18h-19h"]
    nuit_plages = ["19h-00h", "00h-07h"]

    # S'assurer que toutes les colonnes existent dans all_plannings
    for plage in jour_plages + nuit_plages:
        if plage not in all_plannings.columns:
            all_plannings[plage] = ""

    # --- Graphiques sécurisés ---
    def safe_plot(title, plages, filter_role=None):
        try:
            return plot_hours(all_plannings, plages, title, filter_role=filter_role)
        except Exception as e:
            st.error(f"Erreur graphique {title}: {e}")
            return None

    fig_jour = safe_plot("Heures journée (07h-19h)", jour_plages)
    fig_nuit = safe_plot("Heures nuit (19h-07h)", nuit_plages)
    fig_n1 = safe_plot("Heures N1 (total)", jour_plages + nuit_plages, filter_role="N1")
    fig_n2 = safe_plot("Heures N2 (total)", jour_plages + nuit_plages, filter_role="N2")

    # --- Affichage ---
    cols = st.columns(2)
    with cols[0]:
        if fig_jour: st.plotly_chart(fig_jour, use_container_width=True)
        if fig_n1: st.plotly_chart(fig_n1, use_container_width=True)
    with cols[1]:
        if fig_nuit: st.plotly_chart(fig_nuit, use_container_width=True)
        if fig_n2: st.plotly_chart(fig_n2, use_container_width=True)
        

else:
    st.info("Aucun planning disponible. Demandez à chaque personne de sauvegarder sa semaine.")
