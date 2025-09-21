import json
import os

def load_users(filepath="data/users.json"):
    if not os.path.exists(filepath):
        # Valeurs par défaut
        return {
            "JULIE123": "Julie",
            "LYNDA456": "Lynda",
            "RIADH789": "Riadh",
            "ESTELLE000": "Estelle",
            "FLORIAN321": "Florian",
            "MATHIAS654": "Mathias"
        }
    with open(filepath, "r") as f:
        return json.load(f)

def check_user(code, users):
    if code in users:
        return users[code]
    return None
