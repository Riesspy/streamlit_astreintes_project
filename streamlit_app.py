import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from collections import defaultdict

st.set_page_config(page_title="Planning Astreintes", layout="wide")

# --- Exemple de données ---
personnes = ["Alice", "Bob", "Claire", "David", "Emma", "Farid"]

jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
jours_nuits = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Plages horaires
plages_jour = {
    "plage1": (7, 9),
    "plage2": (9, 12),
    "plage3": (12, 14),
    "plage4": (15, 18)
}

plages_nuit = {
    "plage5": (19, 7),  # nuit : 19h -> 7h lendemain
    "vendredi_soir": (19, 24),
    "samedi": (0, 24),
    "dimanche_nuit": (0, 7)
}

# --- Stockage des préférences et absences ---
st.sidebar.title("Mes Préférences & Absences")
prefs = {}
absences = {}

for p in personnes:
    st.sidebar.subheader(p)
    prefs[p] = {}
    absences[p] = {}
    for jour in jours_semaine:
        for plage in plages_jour:
            prefs[p][(jour, plage)] = st.sidebar.selectbox(
                f"{jour} {plage} - {p}", ["N1", "N2", "BackupN1", "BackupN2", "Aucun"], key=f"{p}_{jour}_{plage}"
            )
            absences[p][(jour, plage)] = st.sidebar.checkbox(
                f"Absent {jour} {plage} - {p}", key=f"abs_{p}_{jour}_{plage}"
            )
    for jour in jours_nuits:
        for plage in plages_nuit:
            prefs[p][(jour, plage)] = st.sidebar.selectbox(
                f"{jour} {plage} (nuit/week-end) - {p}", ["N1", "N2", "BackupN1", "BackupN2", "Aucun"], key=f"{p}_{jour}_{plage}_nuit"
            )
            absences[p][(jour, plage)] = st.sidebar.checkbox(
                f"Absent {jour} {plage} - {p}", key=f"abs_{p}_{jour}_{plage}_nuit"
            )

# --- Calcul planning ---
planning = {}
heures_cumulees = defaultdict(float)

def duree(plage):
    h_start, h_end = plage
    return (h_end - h_start) % 24  # pour gérer les nuits

# Assignation simple selon règles
def assigner(jour, plage, candidats):
    if not candidats:
        return None
    # Priorité N1 > N2 > BackupN1 > BackupN2
    niveaux = ["N1", "N2", "BackupN1", "BackupN2"]
    for niveau in niveaux:
        candidats_niveau = [p for p in candidats if prefs[p].get((jour, plage), "Aucun") == niveau]
        if candidats_niveau:
            # Choisir la personne avec moins d'heures cumulées
            p_min = min(candidats_niveau, key=lambda x: heures_cumulees[x])
            heures_cumulees[p_min] += duree(plages_jour.get(plage, plages_nuit.get(plage)))
            return p_min
    # Si aucun, choisir au hasard parmi candidats restants
    p_min = min(candidats, key=lambda x: heures_cumulees[x])
    heures_cumulees[p_min] += duree(plages_jour.get(plage, plages_nuit.get(plage)))
    return p_min

# Planning semaine
for jour in jours_semaine:
    planning[jour] = {}
    for plage in plages_jour:
        candidats = [p for p in personnes if not absences[p].get((jour, plage), False)]
        planning[jour][plage] = assigner(jour, plage, candidats)

# Planning nuits/week-end
planning_nuits = {}
for jour in jours_nuits:
    planning_nuits[jour] = {}
    for plage in plages_nuit:
        candidats = [p for p in personnes if not absences[p].get((jour, plage), False)]
        planning_nuits[jour][plage] = assigner(jour, plage, candidats)

# --- Affichage planning ---
st.header("📅 Planning Semaine (7h-19h)")
for jour, pl in planning.items():
    st.subheader(jour)
    st.table(pd.DataFrame.from_dict(pl, orient="index", columns=["Personne assignée"]))

st.header("🌙 Planning Nuits & Week-end")
for jour, pl in planning_nuits.items():
    st.subheader(jour)
    st.table(pd.DataFrame.from_dict(pl, orient="index", columns=["Personne assignée"]))

# --- Graphique heures cumulées ---
heures_df = pd.DataFrame.from_dict(heures_cumulees, orient="index", columns=["Heures"])
st.header("📊 Répartition des heures par personne (Total)")
fig_total = px.bar(heures_df, x=heures_df.index, y="Heures", text="Heures")
st.plotly_chart(fig_total)

# Séparer graphique semaine vs nuits/week-end
heures_semaine = {p:0 for p in personnes}
heures_nuits = {p:0 for p in personnes}

for p in personnes:
    for jour, pl in planning.items():
        for plage, perso in pl.items():
            if perso == p:
                heures_semaine[p] += duree(plages_jour[plage])
    for jour, pl in planning_nuits.items():
        for plage, perso in pl.items():
            if perso == p:
                heures_nuits[p] += duree(plages_nuit[plage])

st.header("📊 Heures Semaine (7h-19h)")
fig_semaine = px.bar(pd.DataFrame.from_dict(heures_semaine, orient='index', columns=["Heures"]),
                     x=lambda df: df.index, y="Heures", text="Heures")
st.plotly_chart(fig_semaine)

st.header("📊 Heures Nuits & Week-end")
fig_nuits = px.bar(pd.DataFrame.from_dict(heures_nuits, orient='index', columns=["Heures"]),
                   x=lambda df: df.index, y="Heures", text="Heures")
st.plotly_chart(fig_nuits)
