import streamlit as st
import datetime
import calendar
from utils.auth import load_users, check_user
from utils.planning import init_dataframe, save_user_planning, load_all_plannings, get_weeks_of_month, plages, generate_final_week_planning
from utils.charts import plot_hours

st.set_page_config(page_title="Planning Astreintes", layout="wide")
st.title("📅 Planning des astreintes")

# --- Login ---
users = load_users()
user_code = st.text_input("Entrez votre code personnel :", type="password")
current_user = check_user(user_code, users)

if current_user:
    st.success(f"Bonjour {current_user}, vous pouvez remplir vos plages")

    # Mois par nom
    mois = [calendar.month_name[i] for i in range(1, 13)]
    month_name = st.selectbox("Sélectionner le mois :", mois, index=datetime.datetime.now().month-1)
    month = mois.index(month_name) + 1
    year = st.number_input("Année :", value=datetime.datetime.now().year, min_value=2020, max_value=2030)

    weeks = get_weeks_of_month(month, year)
    for start, end in weeks:
        st.subheader(f"Semaine du {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}")
        df = init_dataframe(start)

        # Options pour chaque plage
        options = ["N1", "N2", "Backup1", "Backup2", "Absent"]
        column_config = {plage: st.column_config.SelectboxColumn(options=options, label=plage) for plage in plages}

        # Tableau interactif
        edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic")

        # Remplacer vides par "Absent" pour les colonnes existantes dans le DataFrame
        for col in edited_df.columns:
            if col in plages:
                edited_df[col] = edited_df[col].fillna("Absent")

        if st.button(f"💾 Sauvegarder Planning ({start.strftime('%d/%m/%Y')})"):
            save_user_planning(current_user, edited_df)
            st.success("Planning sauvegardé ✅")

else:
    st.warning("Veuillez entrer un code valide pour continuer.")

# --- Affichage global ---
st.header("📊 Planning global")
all_df = load_all_plannings()
if not all_df.empty:
    st.dataframe(all_df)

    # Graphes d'heures
    fig_jour = plot_hours(all_df, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures journée (07h-19h)")
    fig_nuit = plot_hours(all_df, ["19h-00h","00h-07h"], "Heures nuit (19h-07h)")

    col1, col2 = st.columns(2)
    with col1:
        if fig_jour: st.plotly_chart(fig_jour, use_container_width=True)
    with col2:
        if fig_nuit: st.plotly_chart(fig_nuit, use_container_width=True)

    # Planning final de la semaine
    st.header("📌 Planning final de la semaine")
    today = datetime.date.today()
    start_week = today - datetime.timedelta(days=today.weekday())
    final_week_df = generate_final_week_planning(all_df, start_week)
    if not final_week_df.empty:
        st.dataframe(final_week_df)
