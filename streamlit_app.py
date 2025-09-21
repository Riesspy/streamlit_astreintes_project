import streamlit as st
import pandas as pd
from utils.auth import load_users, check_user
from utils.planning import init_dataframe, save_user_planning, load_all_plannings, plages
from utils.charts import plot_hours

st.set_page_config(page_title="Planning Astreintes", layout="wide")

users = load_users()

st.title("📅 Planning des astreintes")

# --- Login ---
user_code = st.text_input("Entrez votre code personnel :", type="password")

current_user = check_user(user_code, users)
if current_user:
    st.success(f"Bonjour {current_user}, vous pouvez remplir vos plages")

    df = init_dataframe()

    # Remplissage du tableau
    for i, row in df.iterrows():
        jour = row["Jour"]
        for plage in plages:
            df.at[i, plage] = st.selectbox(
                f"{jour} - {plage}", 
                ["", "N1", "N2", "Backup1", "Backup2", "Absent"], 
                key=f"{jour}-{plage}-{current_user}"
            )

    if st.button("💾 Sauvegarder mon planning"):
        save_user_planning(current_user, df)
        st.success("Planning sauvegardé avec succès ✅")

else:
    st.warning("Veuillez entrer un code valide pour continuer.")

# --- Vue globale ---
st.header("📊 Planning global")
all_df = load_all_plannings()
if not all_df.empty:
    st.dataframe(all_df)

    # Graphes
    fig1 = plot_hours(all_df, ["07h-09h","09h-12h","12h-14h","15h-18h","18h-19h"], "Heures semaine (Lun-Ven)")
    fig2 = plot_hours(all_df, ["19h-07h (nuit)", "Vendredi 19h-00h", "Samedi 00h-24h", "Dimanche 00h-07h"], "Heures nuits & week-end")

    col1, col2 = st.columns(2)
    with col1:
        if fig1: st.plotly_chart(fig1, use_container_width=True)
    with col2:
        if fig2: st.plotly_chart(fig2, use_container_width=True)
