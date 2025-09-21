# utils/charts.py
import plotly.express as px
import pandas as pd

def plot_hours(df, plages, title="Heures"):
    if df.empty:
        return None
    df_copy = df.copy()
    # On remplace les valeurs N1, N2, Backup1, Backup2 par 1 et tout le reste par 0
    for col in plages:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(lambda x: 1 if x in ["N1","N2","Backup1","Backup2"] else 0)
    df_copy["total"] = df_copy[plages].sum(axis=1)
    summary = df_copy.groupby("Utilisateur")["total"].sum().reset_index()
    fig = px.bar(summary, x="Utilisateur", y="total", title=title)
    return fig
