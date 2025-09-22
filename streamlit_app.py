import streamlit as st
import pandas as pd
import datetime
import calendar
from utils.planning import init_dataframe, save_user_planning, load_all_plannings, load_standard_planning, plages
from utils.charts import plot_hours

# --- Login ---
def load_users():
    # Exemple, tu peux remplacer par la vraie fonction
    return ["Riadh", "Mathias", "Florian", "Lynda", "Julie", "Estelle"]

def check_user(user_code, users):
    return user_code if user_code in users else None

users = load_users()
user_code = st.text_input("Entrez votre code personnel :", type="password")
current_user = check_user(user_code, users)

if current_user:
    st.success(f"Connecté en tant que : {current_user}")
else:
    st.warning("Veuillez entrer votre code pour vous connecter.")

# --- Sélection du mois et année ---
mois = [calendar.month_name[i] for i in range(1, 13)]
month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
month = mois.index(month_name) + 1
year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

# --- Jours du mois ---
first_day = datetime.date(year, month, 1)
last_day = calendar.monthrange(year, month)[1]
month_days = [first_day + datetime.timedelta(days=i) for i in range(last_day)]

# --- Charger tous les plannings existants ---
all_plannings = load_all_plannings()
if not all_plannings.empty:
    all_plannings["Date"] = pd.to_datetime(all_plannings["Date"]).dt.date
    all_plannings["Jour"] = all_plannings["Date"].apply(lambda d: d.strftime("%A"))

# --- Semaine actuelle ---
if "week_start" not in st.session_state:
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    st.session_state.week_start = week_start

col1, col2, col3 = st.columns([1,2,1])
with col1:
    if st.button("⬅️ Semaine précédente"):
        st.session_state.week_start -= datetime.timedelta(days=7)
with col3:
    if st.button("Semaine suivante ➡️"):
        st.session_state.week_start += datetime.timedelta(days=7)

st.subheader(f"Semaine du {st.session_state.week_start.strftime('%d/%m/%Y')}")
week_days = [st.session_state.week_start + datetime.timedelta(days=i) for i in range(7)]

# --- Tableau utilisateur ---
if current_user:
    # Charger standard ou semaine existante
    user_week_df = all_plannings[
        (all_plannings["Utilisateur"] == current_user) &
        (all_plannings["Date"].isin(week_days))
    ]
    if not user_week_df.empty:
        df = user_week_df.copy()
    else:
        standard = load_standard_planning(current_user)
        rows = []
        for day in week_days:
            row = {"Date": day, "Jour": day.strftime("%A"), "Utilisateur": current_user}
            row.update(standard)
            rows.append(row)
        df = pd.DataFrame(rows)

    options = ["", "N1", "N2", "Backup1", "Backup2"]
    column_config = {plage: st.column_config.SelectboxColumn(options=options, label=plage) for plage in plages}
    edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder la semaine"):
            save_user_planning(current_user, edited_df)
            st.success("Planning de la semaine sauvegardé ✅")
    with col2:
        if st.button("💾 Sauvegarder comme standard"):
            edited_df_standard = edited_df.copy()
            edited_df_standard = edited_df_standard.drop(columns=["Date", "Jour"])
            edited_df_standard.to_csv("data/standard_planning.csv", index=False, mode="w", header=True)
            st.success("Planning standard mis à jour ✅")

# --- Planning final semaine ---
st.header("📌 Planning global de la semaine")
if not all_plannings.empty:
    # Construire planning final avec N1 et N2 côte à côte
    week_df = all_plannings[all_plannings["Date"].isin(week_days)].copy()
    week_table_rows = []
    for day in week_days:
        row = {"Date": day, "Jour": day.strftime("%A")}
        day_df = week_df[week_df["Date"] == day]
        for plage in plages:
            n1_users = day_df[day_df[plage] == "N1"]["Utilisateur"].tolist()
            n2_users = day_df[day_df[plage] == "N2"]["Utilisateur"].tolist()
            row[plage] = f"N1: {', '.join(n1_users)} | N2: {', '.join(n2_users)}"
        week_table_rows.append(row)
    week_table_df = pd.DataFrame(week_table_rows)
    st.dataframe(week_table_df)

    # --- Graphiques ---
    jour_plages = ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"]
    nuit_plages = ["19h-00h","00h-07h"]

    fig_jour = plot_hours(all_plannings, jour_plages, "Heures journée (07h-19h)")
    fig_nuit = plot_hours(all_plannings, nuit_plages, "Heures nuit (19h-07h, inclu weekend)")

    col1, col2 = st.columns(2)
    with col1:
        if fig_jour: st.plotly_chart(fig_jour, use_container_width=True)
    with col2:
        if fig_nuit: st.plotly_chart(fig_nuit, use_container_width=True)
