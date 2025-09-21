import streamlit as st
import datetime
import calendar
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from utils.auth import load_users, check_user
from utils.planning import plages
from utils.charts import plot_hours

st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des astreintes")

# --- Google Drive Setup ---
creds_json = st.secrets["google_drive"]["service_account_json"]
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=[
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
)
gc = gspread.authorize(creds)

# --- Login ---
users = load_users()
user_code = st.text_input("Entrez votre code personnel :", type="password")
current_user = check_user(user_code, users)
if current_user:
    st.success(f"Connecté en tant que {current_user}")

# --- Sélection du mois ---
mois = [calendar.month_name[i] for i in range(1, 13)]
month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
month = mois.index(month_name) + 1
year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

# --- Jours du mois ---
first_day = datetime.date(year, month, 1)
last_day = calendar.monthrange(year, month)[1]
month_days = [first_day + datetime.timedelta(days=i) for i in range(last_day)]

# --- Semaine actuelle ---
def get_monday(d):
    return d - datetime.timedelta(days=d.weekday())
st.session_state.week_start = get_monday(datetime.date.today())
week_days = [st.session_state.week_start + datetime.timedelta(days=i) for i in range(7)
             if (st.session_state.week_start + datetime.timedelta(days=i)).month == month]

# --- Google Sheets utils ---
def load_sheet(sheet_name):
    try:
        sh = gc.open(sheet_name)
        ws = sh.sheet1
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(sheet_name)
        ws = sh.sheet1
        ws.append_row(["Date","Jour","Utilisateur"] + plages)
        return pd.DataFrame()

def save_sheet(df, sheet_name):
    sh = gc.open(sheet_name)
    ws = sh.sheet1
    ws.clear()
    ws.append_row(df.columns.tolist())
    for r in df.values.tolist():
        ws.append_row(r)

# --- Charger les plannings ---
all_plannings = load_sheet("astreintes_planning")
all_standard = load_sheet("astreintes_standard")

# --- Pré-remplissage planning utilisateur ---
def get_user_week_df(user):
    df_user = all_plannings[(all_plannings["Utilisateur"]==user) & (all_plannings["Date"].isin([d.strftime("%Y-%m-%d") for d in week_days]))]
    if not df_user.empty:
        return df_user
    # Sinon, pré-remplissage standard
    user_std = all_standard[all_standard["Utilisateur"]==user]
    rows=[]
    for day in week_days:
        row={"Date": day.strftime("%Y-%m-%d"), "Jour": day.strftime("%A"), "Utilisateur": user}
        if not user_std.empty:
            row.update(user_std.iloc[0][plages].to_dict())
        else:
            for p in plages: row[p]=""
        rows.append(row)
    return pd.DataFrame(rows)

# --- Tableau utilisateur ---
if current_user:
    df = get_user_week_df(current_user)
    options = ["N1","N2","Backup1","Backup2",""]
    column_config = {p: st.column_config.SelectboxColumn(options=options, label=p) for p in plages}
    edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic")
    
    col1,col2=st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder la semaine"):
            all_plannings = all_plannings[all_plannings["Utilisateur"]!=current_user]
            all_plannings = pd.concat([all_plannings, edited_df], ignore_index=True)
            save_sheet(all_plannings, "astreintes_planning")
            st.success("Semaine sauvegardée ✅")
    with col2:
        if st.button("💾 Sauvegarder le planning standard"):
            all_standard = all_standard[all_standard["Utilisateur"]!=current_user]
            std_df = edited_df.copy()
            std_df = std_df[["Utilisateur"] + plages]
            all_standard = pd.concat([all_standard, std_df], ignore_index=True)
            save_sheet(all_standard, "astreintes_standard")
            st.success("Planning standard sauvegardé ✅")

# --- Planning final semaine ---
st.header("📌 Planning final de la semaine")
week_table_rows=[]
if not all_plannings.empty:
    for day in week_days:
        row={"Date": day.strftime("%Y-%m-%d"), "Jour": day.strftime("%A")}
        day_df = all_plannings[all_plannings["Date"]==day.strftime("%Y-%m-%d")]
        for p in plages:
            n1_users = day_df[day_df[p]=="N1"]["Utilisateur"].tolist()
            n2_users = day_df[day_df[p]=="N2"]["Utilisateur"].tolist()
            row[p] = f"N1: {', '.join(n1_users)}; N2: {', '.join(n2_users)}"
        week_table_rows.append(row)
    week_table_df = pd.DataFrame(week_table_rows)
    st.dataframe(week_table_df)

    # --- Graphes ---
    fig_jour = plot_hours(all_plannings, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures journée")
    fig_nuit = plot_hours(all_plannings, ["19h-00h","00h-07h"], "Heures nuit")
    fig_n2 = plot_hours(all_plannings, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures journée N2", filter_role="N2")

    col1,col2,col3=st.columns(3)
    with col1: st.plotly_chart(fig_jour, use_container_width=True)
    with col2: st.plotly_chart(fig_nuit, use_container_width=True)
    with col3: st.plotly_chart(fig_n2, use_container_width=True)
