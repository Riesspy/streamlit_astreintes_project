import streamlit as st
import datetime
import calendar
import pandas as pd
from utils.auth import load_users, check_user
from utils.planning import init_dataframe, save_user_planning, load_all_plannings, plages
from utils.charts import plot_hours

st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des astreintes")

# --- Login ---
users = load_users()
user_code = st.text_input("Entrez votre code personnel :", type="password")
current_user = check_user(user_code, users)

users_list = list(users.values())

# --- Sélection du mois et année ---
mois = [calendar.month_name[i] for i in range(1, 13)]
month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
month = mois.index(month_name) + 1
year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

# --- Jours du mois (global) ---
first_day = datetime.date(year, month, 1)
last_day = calendar.monthrange(year, month)[1]
month_days = [first_day + datetime.timedelta(days=i) for i in range(last_day)]

# --- Charger tous les plannings existants ---
all_plannings = load_all_plannings()
if not all_plannings.empty:
    all_plannings["Date"] = pd.to_datetime(all_plannings["Date"]).dt.date

# --- Fonction heures cumulées ---
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
    return "Absent"

# --- Sélecteur de semaine avec boutons ---
if "week_start" not in st.session_state:
    st.session_state.week_start = first_day

col1, col2, col3 = st.columns([1,2,1])
with col1:
    if st.button("⬅️ Semaine précédente"):
        st.session_state.week_start -= datetime.timedelta(days=7)
        if st.session_state.week_start < first_day:
            st.session_state.week_start = first_day
with col3:
    if st.button("Semaine suivante ➡️"):
        st.session_state.week_start += datetime.timedelta(days=7)
        last_month_day = datetime.date(year, month, last_day)
        if st.session_state.week_start > last_month_day:
            st.session_state.week_start = last_month_day

st.subheader(f"Semaine du {st.session_state.week_start.strftime('%d/%m/%Y')}")

week_days = [st.session_state.week_start + datetime.timedelta(days=i) for i in range(7)
             if (st.session_state.week_start + datetime.timedelta(days=i)).month == month]

# --- Tableau utilisateur pour la semaine ---
if current_user:
    # Charger le planning existant
    if not all_plannings.empty:
        user_week_df = all_plannings[
            (all_plannings["Utilisateur"] == current_user) &
            (all_plannings["Date"].isin(week_days))
        ]
        df = user_week_df.copy() if not user_week_df.empty else init_dataframe(st.session_state.week_start)
    else:
        df = init_dataframe(st.session_state.week_start)

    options = ["N1", "N2", "Backup1", "Backup2", "Absent"]
    column_config = {plage: st.column_config.SelectboxColumn(options=options, label=plage) for plage in plages}

    edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic")
    for col in edited_df.columns:
        if col in plages:
            edited_df[col] = edited_df[col].fillna("Absent")

    if st.button("💾 Sauvegarder la semaine"):
        save_user_planning(current_user, edited_df)
        st.success("Planning sauvegardé ✅")

# --- Planning final de la semaine (tableau large) ---
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
            row[plage] = assign_plage_balanced(day_df, plage, user_hours, is_night=is_night)
        week_table_rows.append(row)

    week_table_df = pd.DataFrame(week_table_rows)
    st.dataframe(week_table_df)

    # Graphes
    fig_jour = plot_hours(all_plannings, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures journée (07h-19h)")
    fig_nuit = plot_hours(all_plannings, ["19h-00h","00h-07h"], "Heures nuit (19h-07h)")

    col1, col2 = st.columns(2)
    with col1:
        if fig_jour: st.plotly_chart(fig_jour, use_container_width=True)
    with col2:
        if fig_nuit: st.plotly_chart(fig_nuit, use_container_width=True)
