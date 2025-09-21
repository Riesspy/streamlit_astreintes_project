# utils/planning.py
import pandas as pd
import os
from datetime import date

# --- Plages horaires ---
plages = ["07h-09h", "09h-12h", "12h-14h", "15h-18h", "18h-19h", "19h-00h", "00h-07h"]

# --- Initialiser un DataFrame vide pour un utilisateur ---
def init_dataframe():
    columns = ["Date", "Jour", "Utilisateur"] + plages
    return pd.DataFrame(columns=columns)

# --- Sauvegarder le planning d'un utilisateur ---
def save_user_planning(user, df):
    os.makedirs("data", exist_ok=True)
    df.to_csv(f"data/{user}_planning.csv", index=False)

# --- Charger tous les plannings utilisateurs ---
def load_all_plannings():
    import glob
    all_files = glob.glob("data/*_planning.csv")
    if not all_files:
        return pd.DataFrame(columns=["Date", "Jour", "Utilisateur"] + plages)
    df_list = [pd.read_csv(f) for f in all_files]
    return pd.concat(df_list, ignore_index=True)

# --- Charger le planning standard pour un utilisateur ---
def load_standard_planning(user):
    try:
        df_standard = pd.read_csv("data/standard_planning.csv")
        user_df = df_standard[df_standard["Utilisateur"] == user]
        if not user_df.empty:
            return user_df.iloc[0][plages].to_dict()
    except FileNotFoundError:
        pass
    # Si pas de standard, retourner vide
    return {plage: "" for plage in plages}
