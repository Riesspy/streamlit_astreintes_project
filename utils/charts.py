import plotly.express as px

def plot_hours(df, plages_jour, title):
    if df.empty:
        return None
    heures_par_plage = {
        "07h-09h": 2, "09h-12h": 3, "12h-14h": 2, "15h-18h": 3, "18h-19h": 1,
        "19h-07h (nuit)": 12, "Vendredi 19h-00h": 5, "Samedi 00h-24h": 24, "Dimanche 00h-07h": 7
    }
    # Calcul des heures par utilisateur
    heures = {}
    for _, row in df.iterrows():
        user = row["Utilisateur"]
        heures[user] = heures.get(user, 0)
        for plage in plages_jour:
            if row.get(plage) in ["N1", "N2", "Backup1", "Backup2"]:
                heures[user] += heures_par_plage[plage]
    data = [{"Utilisateur": u, "Heures": h} for u, h in heures.items()]
    fig = px.bar(data, x="Utilisateur", y="Heures", title=title, text="Heures")
    return fig
