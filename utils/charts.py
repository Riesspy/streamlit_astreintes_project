import plotly.express as px
from utils.planning import heures_par_plage

def plot_hours(df, plages, title):
    if df.empty:
        return None
    heures = {}
    for _, row in df.iterrows():
        user = row["Utilisateur"]
        heures[user] = heures.get(user, 0)
        for plage in plages:
            if row.get(plage) not in ["", "Absent"]:
                heures[user] += heures_par_plage[plage]
    data = [{"Utilisateur": u, "Heures": h} for u,h in heures.items()]
    fig = px.bar(data, x="Utilisateur", y="Heures", title=title, text="Heures")
    return fig
