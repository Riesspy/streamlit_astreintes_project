import streamlit as st
import pandas as pd
import datetime
import calendar
from utils.auth import load_users, check_user
from utils.planning import init_dataframe, save_user_planning, load_all_plannings, plages
from utils.charts import plot_hours
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import io

st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des astreintes")

# --- Login ---
users = load_users()
user_code = st.text_input("Entrez votre code personnel :", type="password")
current_user = check_user(user_code, users)
if current_user:
    st.success(f"Connecté en tant que {current_user}")
users_list = list(users.values())

# --- Mois et année ---
mois = [calendar.month_name[i] for i in range(1, 13)]
month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
month = mois.index(month_name) + 1
year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

# --- Jours du mois ---
first_day = datetime.date(year, month, 1)
last_day = calendar.monthrange(year, month)[1]
month_days = [first_day + datetime.timedelta(days=i) for i in range(last_day)]

# --- Google Drive Credentials ---
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
    "client_x509_cert_url": st.secrets["google_drive"]["client_x509_cert_url"]
}
creds = Credentials.from_service_account_info(creds_dict)
drive_service = build('drive', 'v3', credentials=creds)
FOLDER_ID = st.secrets["google_drive"]["folder_id"]  # dossier où stocker les CSV

# --- Fonction Google Drive ---
def upload_csv_to_drive(file_name, df):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    media_body = csv_buffer.getvalue().encode()
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]
    }
    # Vérifie si le fichier existe
    results = drive_service.files().list(q=f"name='{file_name}' and '{FOLDER_ID}' in parents", spaces='drive').execute()
    items = results.get('files', [])
    if items:
        file_id = items[0]['id']
        drive_service.files().update(fileId=file_id, media_body=media_body).execute()
    else:
        drive_service.files().create(body=file_metadata, media_body=media_body).execute()

# --- Charger tous les plannings existants ---
all_plannings = load_all_plannings()
if not all_plannings.empty:
    all_plannings["Date"] = pd.to_datetime(all_plannings["Date"]).dt.date

# --- Charger standard ---
def load_standard_planning(user):
    try:
        df_standard = pd.read_csv("utils/standard_planning.csv")
        user_df = df_standard[df_standard["Utilisateur"] == user]
        if not user_df.empty:
            return user_df.iloc[0][plages].to_dict()
    except FileNotFoundError:
        st.warning("Fichier de planning standard non trouvé.")
    return {plage: "" for plage in plages}

# --- Calcul des heures cumulées ---
def compute_user_hours(all_df):
    user_hours = {}
    jour_plages = ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"]
    nuit_plages = ["19h-00h","00h-07h","18h-19h"]
    for user in all_df["Utilisateur"].unique():
        df_user = all_df[all_df["Utilisateur"] == user]
        day_hours = df_user[jour_plages].applymap(lambda x: 1 if x in ["N1","N2","Backup1","Backup2"] else 0).sum().sum()
        night_hours = df_user[nuit_plages].applymap(lambda x: 1 if x in ["N1","N2","Backup1","Backup2"] else 0).sum().sum()
        user_hours[user] = {"jour": day_hours, "nuit": night_hours}
    return user_hours

# --- Attribution par priorité ---
def assign_plage_balanced(day_df, plage, user_hours, is_night=False):
    for priority in ["N1","N2","Backup1","Backup2"]:
        users_priority = day_df[day_df[plage] == priority]
        if not users_priority.empty:
            if is_night:
                users_priority = users_priority.assign(total_hours=users_priority["Utilisateur"].map(lambda u: user_hours[u]["nuit"]))
            else:
                users_priority = users_priority.assign(total_hours=users_priority["Utilisateur"].map(lambda u: user_hours[u]["jour"]))
            selected_user = users_priority.sort_values("total_hours").iloc[0]["Utilisateur"]
            return selected_user
    return ""

# --- Semaine actuelle ---
today = datetime.date.today()
week_start = today - datetime.timedelta(days=today.weekday())
week_days = [week_start + datetime.timedelta(days=i) for i in range(7)]

# --- Tableau utilisateur pour la semaine ---
if current_user:
    st.subheader(f"Votre planning pour la semaine du {week_start.strftime('%d/%m/%Y')}")
    # Pré-remplissage avec planning standard
    standard = load_standard_planning(current_user)
    rows = []
    for day in week_days:
        row = {"Date": day, "Jour": day.strftime("%A"), "Utilisateur": current_user}
        row.update(standard)
        rows.append(row)
    df = pd.DataFrame(rows)

    options = ["N1", "N2", "Backup1", "Backup2", ""]
    column_config = {plage: st.column_config.SelectboxColumn(options=options, label=plage) for plage in plages}
    edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic")
    for col in edited_df.columns:
        if col in plages:
            edited_df[col] = edited_df[col].fillna("")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder la semaine"):
            save_user_planning(current_user, edited_df)
            upload_csv_to_drive(f"{current_user}_week_{week_start}.csv", edited_df)
            st.success("Planning sauvegardé ✅")
    with col2:
        if st.button("💾 Sauvegarder comme standard"):
            edited_df_standard = edited_df.copy()
            edited_df_standard = edited_df_standard[["Utilisateur"] + plages]
            edited_df_standard.to_csv("utils/standard_planning.csv", index=False)
            upload_csv_to_drive("standard_planning.csv", edited_df_standard)
            st.success("Planning standard sauvegardé ✅")

# --- Planning final de la semaine ---
st.header("📌 Planning final de la semaine")
if not all_plannings.empty:
    user_hours = compute_user_hours(all_plannings)
    week_table_rows = []
    week_df = all_plannings[all_plannings["Date"].isin(week_days)].copy()
    for day in week_days:
        row = {"Date": day, "Jour": day.strftime("%A")}
        day_df = week_df[week_df["Date"] == day]
        for plage in plages:
            is_night = plage in ["19h-00h","00h-07h"]
            row[plage] = assign_plage_balanced(day_df, plage, user_hours, is_night=is_night)
        week_table_rows.append(row)
    week_table_df = pd.DataFrame(week_table_rows)
    st.dataframe(week_table_df)

    # Graphes
    fig_jour = plot_hours(all_plannings, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures journée")
    fig_nuit = plot_hours(all_plannings, ["19h-00h","00h-07h"], "Heures nuit")
    fig_n2 = plot_hours(all_plannings, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures jour N2", filter_priority="N2")

    col1, col2, col3 = st.columns(3)
    with col1:
        if fig_jour: st.plotly_chart(fig_jour, use_container_width=True)
    with col2:
        if fig_nuit: st.plotly_chart(fig_nuit, use_container_width=True)
    with col3:
        if fig_n2: st.plotly_chart(fig_n2, use_container_width=True)
