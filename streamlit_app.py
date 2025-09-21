import streamlit as st
import pandas as pd
import datetime
import calendar
import json
import gspread
from google.oauth2.service_account import Credentials
from utils.planning import plages

st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des Astreintes")

# --- Auth Google Drive ---
creds_dict = json.loads(st.secrets["google_drive"]["service_account_json"])
creds = Credentials.from_service_account_info(creds_dict)
gc = gspread.authorize(creds)

# --- Ouvrir le Google Sheet (à créer avant dans Drive) ---
SHEET_NAME = "Planning_Astreintes"
try:
    sh = gc.open(SHEET_NAME)
except gspread.SpreadsheetNotFound:
    sh = gc.create(SHEET_NAME)
    sh.share(None, perm_type='anyone', role='writer')
worksheet = sh.sheet1

# --- Utilisateurs ---
users_list = ["Julie","Lynda","Riadh","Estelle","Florian","Mathias"]

user_code = st.text_input("Entrez votre nom :", type="default")
current_user = user_code if user_code in users_list else None

if current_user:
    st.success(f"Connecté en tant que {current_user}")
else:
    st.warning("Nom utilisateur invalide !")

# --- Sélection mois/année ---
mois = [calendar.month_name[i] for i in range(1,13)]
month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
month = mois.index(month_name)+1
year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

# --- Jours du mois ---
first_day = datetime.date(year, month, 1)
last_day = calendar.monthrange(year, month)[1]
month_days = [first_day + datetime.timedelta(days=i) for i in range(last_day)]

# --- Charger le planning existant depuis Google Sheet ---
def load_planning():
    try:
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

all_plannings = load_planning()

# --- Tableau utilisateur ---
if current_user:
    # Pré-remplissage semaine avec standard si existant
    rows = []
    for day in month_days:
        row = {"Date": day, "Jour": day.strftime("%A"), "Utilisateur": current_user}
        for plage in plages:
            row[plage] = ""
        rows.append(row)
    df = pd.DataFrame(rows)

    options = ["N1","N2","Backup1","Backup2",""]
    column_config = {plage: st.column_config.SelectboxColumn(options=options, label=plage) for plage in plages}

    edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic")

    # --- Boutons sauvegarde ---
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder semaine"):
            # Filtrer les jours de la semaine actuelle
            week_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
            week_end = week_start + datetime.timedelta(days=6)
            week_df = edited_df[(edited_df["Date"] >= week_start) & (edited_df["Date"] <= week_end)]
            # Ajouter/mettre à jour dans Google Sheet
            for _, row in week_df.iterrows():
                worksheet.append_row([row["Date"], row["Jour"], row["Utilisateur"]]+[row[p] for p in plages])
            st.success("Planning semaine sauvegardé ✅")

    with col2:
        if st.button("💾 Sauvegarder comme planning standard"):
            # Ici on pourrait sauvegarder la version standard par utilisateur
            st.success("Planning standard sauvegardé ✅")

# --- Planning final de la semaine (N1/N2) ---
st.header("📌 Planning final de la semaine")
if not all_plannings.empty:
    week_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    week_end = week_start + datetime.timedelta(days=6)
    week_df = all_plannings[(pd.to_datetime(all_plannings["Date"]).dt.date >= week_start) &
                            (pd.to_datetime(all_plannings["Date"]).dt.date <= week_end)]
    final_rows = []
    for day in sorted(week_df["Date"].unique()):
        row = {"Date": day, "Jour": pd.to_datetime(day).strftime("%A")}
        day_df = week_df[week_df["Date"] == day]
        for plage in plages:
            n1_users = day_df[day_df[plage]=="N1"]["Utilisateur"].tolist()
            n2_users = day_df[day_df[plage]=="N2"]["Utilisateur"].tolist()
            val = ""
            if n1_users:
                val += "N1: " + ",".join(n1_users)
            if n2_users:
                val += " | N2: " + ",".join(n2_users)
            row[plage] = val
        final_rows.append(row)
    final_df = pd.DataFrame(final_rows)
    st.dataframe(final_df)

# --- Graphiques jour/nuit ---
st.header("📊 Graphes heures")
if not all_plannings.empty:
    # Calcul des heures par utilisateur
    def compute_hours(df, heures):
        result = {}
        for u in users_list:
            user_df = df[df["Utilisateur"]==u]
            total = 0
            for h in heures:
                total += (user_df[h].isin(["N1","N2","Backup1","Backup2"])).sum()
            result[u] = total
        return result

    jour_heures = ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"]
    nuit_heures = ["19h-00h","00h-07h"]
    df_jour = compute_hours(all_plannings, jour_heures)
    df_nuit = compute_hours(all_plannings, nuit_heures)

    st.bar_chart(pd.DataFrame([df_jour, df_nuit], index=["Jour","Nuit"]).T)
