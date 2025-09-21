import pandas as pd

jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
plages = [
    "07h-09h", "09h-12h", "12h-14h", "15h-18h", "18h-19h",
    "19h-07h (nuit)", "Vendredi 19h-00h", "Samedi 00h-24h", "Dimanche 00h-07h"
]

def init_dataframe():
    data = []
    for jour in jours:
        row = {"Jour": jour}
        for plage in plages:
            row[plage] = ""
        data.append(row)
    return pd.DataFrame(data)

def save_user_planning(user, df, filepath="data/plannings.csv"):
    df["Utilisateur"] = user
    try:
        old = pd.read_csv(filepath)
        # Supprime les anciennes lignes de cet utilisateur
        old = old[old["Utilisateur"] != user]
        new = pd.concat([old, df], ignore_index=True)
    except FileNotFoundError:
        new = df
    new.to_csv(filepath, index=False)

def load_all_plannings(filepath="data/plannings.csv"):
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError:
        return pd.DataFrame()
