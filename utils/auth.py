users_dict = {
    "julie": "Julie",
    "lynda": "Lynda",
    "riadh": "Riadh",
    "estelle": "Estelle",
    "florian": "Florian",
    "mathias": "Mathias"
}

def load_users():
    return users_dict

def check_user(code, users):
    return users.get(code, None)
