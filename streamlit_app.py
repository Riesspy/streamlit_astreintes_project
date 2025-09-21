import streamlit as st
import datetime
import calendar
import pandas as pd
from utils.auth import load_users, check_user
from utils.planning import (
    init_dataframe, save_user_planning, load_all_plannings,
    get_weeks_of_month, plages, generate_final_week_planning
)
from utils.charts import plot_hours

st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des astreintes")

# --- Login ---
users = load_users()
user_code = st.text_input("Entrez votre code personnel :", type="password")
current_user = check_user(user_code, users)

if current_user:
    st.success(f"Bonjour {current_user}, vous pouvez remplir vos plages")

    # Sélection du mois et de l'année
    mois = [calendar.month_name[i] for i in range(1, 13)]
    month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
    month = mois.index(month_name) + 1
    year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

    weeks = get_weeks_of_month(month, year)
    all_plannings = load_all_plannings()

    for start, end in weeks:
        st.subheader(f"Semaine du {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}")

        # Charger le planning sauvegardé de l'utilisateur pour cette semaine
        if not all_plannings.empty:
            all_plannings["Date"] = pd.to_datetime(all_plannings["Date"]).dt.date
            user_week_df = all_plannings[
                (all_plannings["Utilisateur"] == current_user) &
                (all_plannings["Date"] >= start) &
                (all_plannings["Date"] <= end)
            ]
            if not user_week_df.empty:
                df = user_week_df.copy()
            else:
                df = init_dataframe(start)
        else:
            df = init_dataframe(start)

        # Options pour chaque plage
        options = ["N1", "N2", "Backup1", "Backup2", "Absent"]
        column_config = {plage: st.column_config.SelectboxColumn(options=options, label=plage) for plage in plages}

        # Tableau interactif
        edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic")

        # Remplacer vides par "Absent"
        for col in edited_df.columns:
            if col in plages:
                edited_df[col] = edited_df[col].fillna("Absent")

        # Bouton sauvegarde
        if st.button(f"💾 Sauvegarder Planning ({start.strftime('%d/%m/%Y')})"):
            save_user_planning(current_user, edited_df)
            st.success("Planning sauvegardé ✅")

else:
    st.warning("Veuillez entrer un code valide pour continuer.")

# --- Affichage global ---
st.header("📊 Planning global")
all_df = load_all_plannings()
if not all_df.empty:
    all_df["Date"] = pd.to_datetime(all_df["Date"]).dt._
