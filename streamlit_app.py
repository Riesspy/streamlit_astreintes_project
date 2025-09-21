import streamlit as st
import datetime
import calendar
import pandas as pd
from utils.auth import load_users, check_user
from utils.planning import (
    init_dataframe, save_user_planning, load_all_plannings,
    get_weeks_of_month, plages
)
from utils.charts import plot_hours

st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des astreintes")

# --- Login ---
users = load_users()
user_code = st.text_input("Entrez votre code personnel :", type="password")
current_user = check_user(user_code, users)

# Liste des noms de tous les utilisateurs
users_list = list(users.values())

if current_user:
    st.success(f"Bonjour {current_user}, vous pouvez remplir vos plages")

    # Sélection du mois et de l'année
    mois = [calendar.month_name[i] for i in range(1, 13)]
    month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
    month = mois.index(month_name) + 1
    year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

    weeks = get_weeks_of_month(month, year)
    all_plannings = load_all_plannings()

    # Conversion dates si CSV existant
    if not all_plannings.empty:
        all_plannings["Date"] = pd.to_datetime(all_plannings["Date"]).dt.date

    for start, end in weeks:
        st.subheader(f"Semaine du {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}")

        # Charger le planning sauvegardé de l'utilisateur pour cette semaine
        if not all_plannings.empty:
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

# --- Fonction pour choisir la personne pour chaque plage selon priorité ---
def assign_plage(day_df, plage):
    """
    Choisit la personne pour la plage selon N1 > N2 > Backup1 > Backup2 > Absent
    """
    for priority in ["N1", "N2", "Backup1", "Backup2"]:
        users_priority = day_df[day_df[plage] == priority]
        if not users_priority.empty:
            return users_priority.iloc[0]["Utilisateur"]
    return "Absent"

# --- Fonction pour générer le planning final complet ---
def generate_final_week_planning_complete(all_df, start_date, users_list):
    # Créer un DataFrame complet avec tous les utilisateurs
    complete_df = pd.DataFrame()
    for user in users_list:
        user_df = all_df[all_df["Utilisateur"] == user].copy()
        # Ajouter les jours manquants
        for i in range(7):
            day = start_date + datetime.timedelta(days=i)
            if user_df[user_df["Date"] == day].empty:
                row = {"Date": day, "Jour": day.strftime("%A"), "Utilisateur": user}
                for plage in plages:
                    row[plage] = "Absent"
                user_df = pd.concat([user_df, pd.DataFrame([row])], ignore_index=True)
        complete_df = pd.concat([complete_df, user_df], ignore_index=True)

    # Générer le planning final
    final = pd.DataFrame()
    final["Date"] = sorted(complete_df["Date"].unique())
    final["Jour"] = final["Date"].apply(lambda d: pd.to_datetime(d).strftime("%A"))
    
    for plage in plages:
        final[plage] = final["Date"].apply(lambda d: assign_plage(complete_df[complete_df["Date"]==d], plage))
    
    return final

# --- Affichage global ---
st.header("📊 Planning global")
all_df = load_all_plannings()
if not all_df.empty:
    all_df["Date"] = pd.to_datetime(all_df["Date"]).dt.date
    st.dataframe(all_df)

    # Graphes d'heures
    fig_jour = plot_hours(all_df, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures journée (07h-19h)")
    fig_nuit = plot_hours(all_df, ["19h-00h","00h-07h"], "Heures nuit (19h-07h)")

    col1, col2 = st.columns(2)
    with col1:
        if fig_jour: st.plotly_chart(fig_jour, use_container_width=True)
    with col2:
        if fig_nuit: st.plotly_chart(fig_nuit, use_container_width=True)

# --- Planning final de la semaine (toujours généré) ---
st.header("📌 Planning final de la semaine")
today = datetime.date.today()
start_week = today - datetime.timedelta(days=today.weekday())
final_week_df = generate_final_week_planning_complete(all_df, start_week, users_list)
st.dataframe(final_week_df)
