import plotly.express as px
import pandas as pd

def plot_hours(df, plages, title, filter_role=None):
    """
    df : DataFrame contenant les plannings
    plages : liste des colonnes à inclure
    title : titre du graphique
    filter_role : 'N1', 'N2', 'Backup1', 'Backup2' ou None
    """
    df_plot = df.copy()

    # Vérifier que toutes les colonnes existent
    for plage in plages:
        if plage not in df_plot.columns:
            df_plot[plage] = ""

    if filter_role:
        # compter uniquement les cellules correspondant au rôle
        df_plot['heures'] = df_plot.apply(lambda row: sum(row[plage] == filter_role for plage in plages), axis=1)
    else:
        # compter toutes les assignations N1/N2/Backup
        df_plot['heures'] = df_plot.apply(lambda row: sum(row[plage] in ["N1", "N2", "Backup1", "Backup2"] for plage in plages), axis=1)

    # Groupement par utilisateur
    df_grouped = df_plot.groupby('Utilisateur')['heures'].sum().reset_index()

    # Création du graphique bar
    fig = px.bar(df_grouped, x='Utilisateur', y='heures', title=title, text='heures')
    fig.update_traces(textposition='outside')
    fig.update_layout(yaxis=dict(title='Heures'), xaxis=dict(title='Utilisateur'))
    return fig
