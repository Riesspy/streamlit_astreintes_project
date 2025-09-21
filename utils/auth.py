import json
import os

def load_users(filepath="data/users.json"):
    if not os.path.exists(filepath):
        # Valeurs par défaut
        return {
            "JULIE": "Julie",
            "LYNDA": "Lynda",
            "RIADH": "Riadh",
            "ESTELLE": "Estelle",
            "FLORIAN": "Florian",
            "MATHIAS": "Mathias"
        }
    with open(filepath, "r") as f:
        return json.load(f)

def check_user(code, users):
    if code in users:
        return users[code]
    return None
