import json

def load_users(filepath="data/users.json"):
    with open(filepath, "r") as f:
        return json.load(f)

def check_user(code, users):
    if code in users:
        return users[code]
    return None