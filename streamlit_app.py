import streamlit as st
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- IMPORTS LOCAUX ---
from utils.planning import init_dataframe, save_user_planning, load_all_plannings, plages

st.set_page_config(page_title="Planning Astreintes", layout="wide")

# --- GOOGLE DRIVE AUTH ---
st.subheader("🔑 Connexion Google Drive")

try:
    creds_dict = json.loads(st.secrets["google_drive"]["service_account_json"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/drive"])
    drive_service = build("drive", "v3", credentials=creds)

    # Test : Lister les 5 derniers fichiers
    results = drive_service.files().list(pageSize=5, fields="files(id, name)").execute()
    items = results.get("files", [])

    if not items:
        st.warning("Aucun fichier trouvé dans Google Drive.")
    else:
        st.success("✅ Connexion réussie à Google Drive")
        for item in items:
            st.write(f"- {item['name']} ({item['id']})")

except Exception as e:
    st.error(f"❌ Erreur de connexion Google Drive : {e}")
    st.stop()

# --- PLANNING ---
st.title("📅 Gestion des Astreintes")

# Liste des personnes
personnes = ["Julie", "Riadh", "Florian", "Nassim"]

# Initialisation du planning général
planning_general = init_dataframe()

# Sélection utilisateur
user = st.selectbox("👤 Sélectionnez votre nom", personnes)

# Création planning perso
planning_user = init_dataframe()

st.write("### Remplissez vos disponibilités")
for plage in plages:
    dispo = st.checkbox(f"{plage} - Disponible ?", key=f"{user}_{plage}")
    if dispo:
        planning_user.loc[plage, "N1"] = user

# Sauvegarde
if st.button("💾 Sauvegarder mon planning"):
    save_user_planning(user, planning_user)
    st.success("Planning sauvegardé avec succès ✅")

# Chargement du planning global
if st.button("📊 Charger le planning global"):
    planning_general = load_all_plannings()
    st.write("### Planning global")
    st.dataframe(planning_general)
