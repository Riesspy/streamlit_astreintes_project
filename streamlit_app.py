import streamlit as st
import pandas as pd
import os
import calendar
from datetime import datetime, timedelta

# 📌 Fichier standard
STANDARD_FILE = "utils/standard_planning.csv"

# 📌 Configuration Streamlit
st.set_page_config(page_title="Planning Astreintes", layout="wide")

st.title("📅 Planning des Astreintes - Vue par semaine")

# ---- UPLOAD / CHARGEMENT PLANNING STANDARD ----
st.sidebar.header("⚙️ Configuration du planning standard")

uploaded_file = st.sidebar.file_uploader("Uploader un planning standard (CSV)", type="csv")

if uploaded_file is not None:
    df_standard = pd.read_csv(uploaded_file)
    os.makedirs("utils", exist_ok=True)
    df_standard.to_csv(STANDARD_FILE, index=False)
    st.sidebar.success("✅ Nouveau planning standard chargé et sauvegardé.")
elif os.path.exists(STANDARD_FILE):
    df_standard = pd.read_csv(STANDARD_FILE)
    st.sidebar.info("📂 Planning standard chargé automatiquement.")
else:
    st.sidebar.warning("⚠️ Aucun planning standard trouvé. Veuillez uploader un fichier CSV.")
    st.stop()

# ---- GESTION DES SEMAINES ----
today = datetime.today()
current_week = today.isocalendar()[1]  # Numéro de semaine courante
year = today.year

selected_week = st.sidebar.number_input(
    "📌 Choisir une semaine",
    min_value=1,
    max_value=52,
    value=current_week
)

# Déterminer les dates de la semaine sélectionnée
first_day_of_year = datetime(year, 1, 1)
first_day_of_week = first_day_of_year + timedelta(weeks=selected_week - 1)
week_dates = [first_day_of_week + timedelta(days=i) for i in range(7)]

# ---- CONSTRUCTION DU PLANNING FINAL ----
# On récupère uniquement les jours de la semaine sélectionnée depuis le standard
df_week = df_standard[df_standard["Date"].isin([d.strftime("%Y-%m-%d") for d in week_dates])]

if df_week.empty:
    st.warning("⚠️ Aucun planning trouvé pour cette semaine. Complétez le standard.")
else:
    # Édition du planning
    st.subheader(f"📆 Planning de la semaine {selected_week} - {year}")
    edited_df = st.data_editor(
        df_week,
        num_rows="fixed",
        use_container_width=True
    )

    # Sauvegarde après modification
    if st.button("💾 Sauvegarder les modifications"):
        # Mise à jour du fichier standard
        df_standard.update(edited_df)
        df_standard.to_csv(STANDARD_FILE, index=False)
        st.success("✅ Modifications sauvegardées dans le planning standard.")

# ---- AFFICHAGE DU PLANNING MENSUEL (optionnel) ----
if st.sidebar.checkbox("📊 Voir le planning du mois"):
    month = st.sidebar.selectbox("Sélectionner un mois", range(1, 13), index=today.month - 1)
    month_days = calendar.monthrange(year, month)[1]
    month_dates = [datetime(year, month, d).strftime("%Y-%m-%d") for d in range(1, month_days + 1)]

    df_month = df_standard[df_standard["Date"].isin(month_dates)]
    st.subheader(f"📅 Planning du mois {calendar.month_name[month]} {year}")
    st.dataframe(df_month, use_container_width=True)
