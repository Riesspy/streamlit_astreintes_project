import streamlit as st
import datetime
import calendar
import pandas as pd
from utils.auth import load_users, check_user
from utils.planning import (
    init_dataframe, save_user_planning, load_all_plannings,
    plages
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

# --- Sélection du mois et de l'année ---
mois = [calendar.month_name[i] for i in range(1, 13)]
month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
month = mois.index(month_name) + 1
year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

# --- Calculer les jours du mois --- 🔹 global pour éviter NameError
first_day = datetime.date(year, month, 1)
last_day = calendar.monthrange(year, month)[1]
month_days = [first_day + datetime.timedelta(days=i) for i in range(last_day)]

# --- Charger tous les plannings existants ---
all_plannings = load_all_plannings()
if not all_plannings.empty:
    all_plannings["Date"] = pd.to_datetime(all_plannings["Date"]).dt.date

# --- Tableau interactif utilisateur ---
if current_user:
    st.success(f"Bonjour {current_user}, vous pouvez remplir vos plages")

    # Générer tableau interactif pour chaque semaine du mois
    for week_start in [first_day + datetime.timedelta(days=i) for i in range(0, last_day, 7)]:
        st.subheader(f"Semaine du {week_start.strftime('%d/%m/%Y')}")
        week_days = [week_start + datetime.timedelta(days=i) for i in range(7) if (week_start + datetime.timedelta(days=i)).month == month]

        # Charger le planning sauvegardé de l'utilisateur pour cette semaine
        if not all_plannings.empty:
            user_week_df = all_plannings[
                (all_plannings["Utilisateur"] == current_user) &
                (all_plannings["Date"].isin(week_days))
            ]
            if not user_week_df.empty:
                df = user_week_df.copy()
            else:
                df = init_dataframe(week_start)
        else:
            df = init_dataframe(week_start)

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
        if st.button(f"💾 Sauvegarder Planning ({week_start.strftime('%d/%m/%Y')})"):
            save_user_planning(current_user, edited_df)
            st.success("Planning sauvegardé ✅")

else:
    st.warning("Veuillez entrer un code valide pour continuer.")

# --- Calcul des heures cumulées ---
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

# --- Attribution par priorité et heures cumulées ---
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
    return "Absent"

# --- Pré-remplissage de la semaine suivante ---
def prefill_next_week(all_df, last_week_start, users_list):
    next_week_start = last_week_start + datetime.timedelta(days=7)
    next_week_days = [next_week_start + datetime.timedelta(days=i) for i in range(7)]
    user_hours = compute_user_hours(all_df)

    rows = []
    for day in next_week_days:
        for user in users_list:
            row = {"Date": day, "Jour": day.strftime("%A"), "Utilisateur": user}
            for plage in plages:
                is_night = plage in ["19h-00h","00h-07h"]
                prev_day = day - datetime.timedelta(days=7)
                prev_choice = all_df[(all_df["Date"] == prev_day) & (all_df["Utilisateur"] == user)]
                if not prev_choice.empty:
                    row[plage] = prev_choice.iloc[0][plage]
                else:
                    row[plage] = "Absent"
                row[plage] = assign_plage_balanced(all_df, plage, user_hours, is_night=is_night)
            rows.append(row)
    return pd.DataFrame(rows)

# --- Planning final du mois ---
st.header("📌 Planning final du mois")
if not all_plannings.empty:
    all_df = all_plannings.copy()
    all_df["Date"] = pd.to_datetime(all_df["Date"]).dt.date
    final_month_rows = []
    user_hours = compute_user_hours(all_df)

    for day in month_days:
        day_df = all_df[all_df["Date"] == day]
        for plage in plages:
            is_night = plage in ["19h-00h","00h-07h"]
            selected_user = assign_plage_balanced(day_df, plage, user_hours, is_night=is_night)
            final_month_rows.append({
                "Date": day,
                "Jour": day.strftime("%A"),
                "Plage": plage,
                "Utilisateur": selected_user
            })

    final_month_df = pd.DataFrame(final_month_rows)
    st.dataframe(final_month_df)

    # Graphes
    fig_jour = plot_hours(all_df, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures journée (07h-19h)")
    fig_nuit = plot_hours(all_df, ["19h-00h","00h-07h"], "Heures nuit (19h-07h)")

    col1, col2 = st.columns(2)
    with col1:
        if fig_jour: st.plotly_chart(fig_jour, use_container_width=True)
    with col2:
        if fig_nuit: st.plotly_chart(fig_nuit, use_container_width=True)
