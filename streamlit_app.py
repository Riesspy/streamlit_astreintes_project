import streamlit as st
import datetime
import calendar
import pandas as pd
import plotly.express as px
from google.oauth2.service_account import Credentials
import gspread

# --- Configuration Streamlit ---
st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des astreintes")

# --- Google Drive / Sheets ---
creds_dict = st.secrets["google_drive"]  # Assurez-vous que st.secrets.toml est bien configuré
creds = Credentials.from_service_account_info(creds_dict)
gc = gspread.authorize(creds)

# --- Paramètres de planning ---
plages = ["07h-09h", "09h-12h", "12h-14h", "15h-18h", "18h-19h", "19h-00h", "00h-07h"]
users_list = ["Julie", "Lynda", "Riadh", "Estelle", "Florian", "Mathias"]
options = ["N1", "N2", "Backup1", "Backup2", ""]

# --- Fonction pour créer le planning standard initial ---
def create_standard_df():
    rows = []
    for user in users_list:
        row = {"Utilisateur": user}
        for plage in plages:
            row[plage] = ""
        rows.append(row)
    return pd.DataFrame(rows)

# --- Fonction pour sauvegarder planning dans Google Sheets ---
def save_to_drive(df, sheet_name):
    try:
        sh = gc.open("Planning_Astreintes")
    except gspread.SpreadsheetNotFound:
        sh = gc.create("Planning_Astreintes")
    try:
        worksheet = sh.worksheet(sheet_name)
        sh.del_worksheet(worksheet)
    except gspread.WorksheetNotFound:
        pass
    worksheet = sh.add_worksheet(title=sheet_name, rows=str(len(df)+10), cols=str(len(df.columns)+5))
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- Fonction pour charger planning depuis Google Sheets ---
def load_from_drive(sheet_name):
    try:
        sh = gc.open("Planning_Astreintes")
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

# --- Sélection de l’utilisateur ---
user_code = st.text_input("Entrez votre nom :", "")
current_user = user_code if user_code in users_list else None
if current_user:
    st.success(f"Connecté en tant que {current_user}")

# --- Semaine actuelle ---
today = datetime.date.today()
start_of_week = today - datetime.timedelta(days=today.weekday())
week_days = [start_of_week + datetime.timedelta(days=i) for i in range(7)]

st.subheader(f"Semaine du {start_of_week.strftime('%d/%m/%Y')}")

# --- Charger planning standard ou créer si inexistant ---
standard_df = load_from_drive("Standard")
if standard_df.empty:
    standard_df = create_standard_df()

user_standard = standard_df[standard_df["Utilisateur"]==current_user] if current_user else pd.DataFrame()

# --- Tableau interactif pour l’utilisateur ---
if current_user:
    st.markdown("### Remplissez votre planning standard / semaine")
    df_user = user_standard.copy() if not user_standard.empty else pd.DataFrame([{"Utilisateur": current_user, **{p:"" for p in plages}}])
    edited_df = st.data_editor(df_user, column_config={p: st.column_config.SelectboxColumn(options=options, label=p) for p in plages}, num_rows="dynamic")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder planning standard"):
            save_to_drive(edited_df, "Standard")
            st.success("Planning standard sauvegardé ✅")
    with col2:
        if st.button("💾 Sauvegarder planning semaine"):
            week_df = edited_df.copy()
            week_df = pd.concat([pd.DataFrame({"Date": [d], "Jour": [d.strftime('%A')], "Utilisateur": current_user, **edited_df.iloc[0][plages].to_dict()}, index=[0]) for d in week_days])
            save_to_drive(week_df, "Semaine")
            st.success("Planning semaine sauvegardé ✅")

# --- Planning final de la semaine ---
st.header("📌 Planning final de la semaine")
all_week_df = load_from_drive("Semaine")
if not all_week_df.empty:
    # Tableau final combinant N1/N2 pour chaque plage
    final_rows = []
    for d in week_days:
        day_df = all_week_df[all_week_df["Date"]==d.strftime("%Y-%m-%d")]
        row = {"Date": d, "Jour": d.strftime("%A")}
        for p in plages:
            n1_users = day_df[day_df[p]=="N1"]["Utilisateur"].tolist()
            n2_users = day_df[day_df[p]=="N2"]["Utilisateur"].tolist()
            cell = ""
            if n1_users:
                cell += "N1: " + ", ".join(n1_users)
            if n2_users:
                if cell: cell += " | "
                cell += "N2: " + ", ".join(n2_users)
            row[p] = cell
        final_rows.append(row)
    final_df = pd.DataFrame(final_rows)
    st.dataframe(final_df, use_container_width=True)

    # --- Graphiques ---
    def plot_hours(df, plages_filter, title):
        df_hours = {}
        for user in users_list:
            df_user = df[df["Utilisateur"]==user]
            count = df_user[plages_filter].applymap(lambda x: 1 if x in ["N1","N2"] else 0).sum().sum()
            df_hours[user] = count
        fig = px.bar(x=list(df_hours.keys()), y=list(df_hours.values()), labels={"x":"Utilisateur","y":"Heures"}, title=title)
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(plot_hours(all_week_df, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures journée N1/N2"))
    with col2:
        st.plotly_chart(plot_hours(all_week_df, ["19h-00h","00h-07h"], "Heures nuit N1/N2"))
