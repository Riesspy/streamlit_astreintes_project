import streamlit as st
import pandas as pd
import os
import calendar
from datetime import datetime, timedelta

# 📂 Fichier du planning standard
STANDARD_FILE = "utils/standard_planning.csv"

# ---- UPLOAD / CHARGEMENT PLANNING STANDARD ----
st.sidebar.header("⚙️ Configuration du planning standard")

uploaded_file = st.sidebar.file_uploader("Uploader un planning standard (CSV)", type="csv")

if uploaded_file is not None:
    df_standard = pd.read_csv(uploaded_file)
    os.makedirs("utils", exist_ok=True)
    df_standard.to_csv(STANDARD_FILE, index=False)
    st.sidebar.success("✅ Nouveau planning standard chargé et sauvegardé.")
else:
    try:
        if os.path.exists(STANDARD_FILE) and os.path.getsize(STANDARD_FILE) > 0:
            df_standard = pd.read_csv(STANDARD_FILE)
            st.sidebar.info("📂 Planning standard chargé automatiquement.")
        else:
            raise FileNotFoundError
    except (FileNotFoundError, pd.errors.EmptyDataError):
        st.sidebar.warning("⚠️ Aucun planning standard trouvé. Initialisation d’un modèle vide...")

        # Création d’un planning vide pour le mois courant
        plages = ["07h-09h", "09h-12h", "12h-14h", "15h-18h", "18h-19h", "19h-00h", "00h-07h"]
        today = datetime.today()
        year, month = today.year, today.month
        days_in_month = calendar.monthrange(year, month)[1]

        rows = []
        for d in range(1, days_in_month + 1):
            date = datetime(year, month, d)
            row = {"Date": date.strftime("%Y-%m-%d"), "Jour": calendar.day_name[date.weekday()]}
            for plage in plages:
                row[plage] = ""
            rows.append(row)

        df_standard = pd.DataFrame(rows)
        os.makedirs("utils", exist_ok=True)
        df_standard.to_csv(STANDARD_FILE, index=False)
        st.sidebar.success("✅ Planning standard vide créé automatiquement.")

# ---- AFFICHAGE DU PLANNING ----
st.title("📅 Planning des Astreintes")

# Choix de la semaine à afficher
df_standard["Date"] = pd.to_datetime(df_standard["Date"])
df_standard["Semaine"] = df_standard["Date"].dt.isocalendar().week

semaines_dispo = sorted(df_standard["Semaine"].unique())
semaine_sel = st.selectbox("Sélectionner une semaine :", semaines_dispo)

df_semaine = df_standard[df_standard["Semaine"] == semaine_sel]

st.subheader(f"Planning de la semaine {semaine_sel}")
st.dataframe(df_semaine, use_container_width=True)

# ---- PLANNING FINAL ----
st.subheader("📊 Planning Final du Mois")
st.dataframe(df_standard, use_container_width=True)
