import pandas as pd
import datetime

# Plages horaires
plages = ["07h-09h", "09h-12h", "12h-14h", "15h-18h", "18h-19h", "19h-00h", "00h-07h"]

# Durées
heures_par_plage = {
    "07h-09h": 2,
    "09h-12h": 3,
    "12h-14h": 2,
    "15h-18h": 3,
    "18h-19h": 1,
    "19h-00h": 5,
    "00h-07h": 7
}

jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

def init_dataframe(start_date):
    """ Initialise un dataframe pour une semaine pour les priorités N1/N2/Backup1/Backup2 """
    data = []
    for i in range(7):
        jour_date = start_date + datetime.timedelta(days=i)
        row = {"Date": jour_date, "Jour": jour_date.strftime("%A")}
        for plage in plages:
            for priority in ["N1","N2","Backup1","Backup2"]:
                row[f"{plage}_{priority}"] = ""
        data.append(row)
    return pd.DataFrame(data)

def save_user_planning(user, df, filepath="data/plannings.csv"):
    df["Utilisateur"] = user
    try:
        old = pd.read_csv(filepath)
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

def get_weeks_of_month(month, year):
    first_day = datetime.date(year, month, 1)
    last_day = datetime.date(year, month+1, 1) - datetime.timedelta(days=1) if month < 12 else datetime.date(year, 12, 31)
    start = first_day
    if start.weekday() != 0:
        start += datetime.timedelta(days=(7 - start.weekday()))
    weeks = []
    while start <= last_day:
        end = start + datetime.timedelta(days=6)
        if end > last_day:
            end = last_day
        weeks.append((start, end))
        start += datetime.timedelta(days=7)
    return weeks

def assign_plage(sub_df, plage):
    """Assigner une personne pour une plage selon les priorités"""
    for priority in ["N1","N2","Backup1","Backup2"]:
        candidates = sub_df[sub_df[f"{plage}_{priority}"].notna() & (sub_df[f"{plage}_{priority}"] != "")]
        if not candidates.empty:
            return candidates.iloc[0]["Utilisateur"]
    return "Absent"

def generate_final_week_planning(all_df, start_date):
    week_mask = (pd.to_datetime(all_df["Date"]) >= pd.Timestamp(start_date)) & \
                (pd.to_datetime(all_df["Date"]) <= pd.Timestamp(start_date + datetime.timedelta(days=6)))
    week_df = all_df[week_mask].copy()
    if week_df.empty:
        return pd.DataFrame()
    
    final = pd.DataFrame()
    final["Date"] = sorted(week_df["Date"].unique())
    final["Jour"] = final["Date"].apply(lambda d: pd.to_datetime(d).strftime("%A"))
    
    for plage in plages:
        final[plage] = final["Date"].apply(lambda d: assign_plage(week_df[week_df["Date"]==d], plage))
    
    return final
