import re
import logging
import requests
from flask import Flask, request, make_response

app = Flask(__name__)
YEMOT_API_URL = "https://www.call2all.co.il/ym/api/"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------- זיכרון פרטי משתמשים ----------
user_sessions = {}

def get_user_data(cli):
    return user_sessions.get(cli)

def save_user_data(cli, system, password):
    if cli:
        user_sessions[cli] = {'system': system, 'password': password}
        logging.info(f"נשמרו פרטים ל-CLI {cli}")

def clear_user_data(cli):
    if cli and cli in user_sessions:
        del user_sessions[cli]
        logging.info(f"נמחקו פרטים ל-CLI {cli}")

def ym_response(content: str):
    res = make_response(content)
    res.headers["Content-Type"] = "text/plain; charset=utf-8"
    return res

def ym_read(var_name: str, prompt: str, max_digits=10):
    return ym_response(f"read={prompt}={var_name},{max_digits},12,1,Digits")

def ym_say_and_go_back(text: str):
    return ym_response(f"id_list_message={text}")

# ---------- השלוחה לשמירת פרטי מערכת ----------
@app.route('/save-credentials', methods=['GET', 'POST'])
def save_credentials():
    cli = request.values.get('cli')
    system = request.values.get('system')
    password = request.values.get('password')
    reset = request.values.get('reset')

    # ---------- שלב 1: אם רוצים לאפס ----------
    if reset == "*":
        clear_user_data(cli)
        return ym_say_and_go_back("t-הפרטים נמחקו. הקש שוב לכניסה חדשה")

    # ---------- שלב 2: שאלת מספר מערכת ----------
    if not system:
        return ym_read("system", "t-אנא הקש את מספר המערכת ובסיומה סולמית (או * לאיפוס)", 10)

    # ---------- שלב 3: שאלת סיסמה ----------
    if not password:
        return ym_read("password", "t-אנא הקש את סיסמת המערכת ובסיומה סולמית", 10)

    # ---------- שלב 4: שמירה בזיכרון ----------
    if cli:
        save_user_data(cli, system, password)
        msg = f"t-הפרטים נשמרו בהצלחה עבור מספר {cli}"
        return ym_say_and_go_back(msg)
    else:
        return ym_say_and_go_back("t-לא זוהה מספר מתקשר. נסה שוב")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
