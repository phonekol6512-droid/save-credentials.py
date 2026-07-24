import logging
import requests
from flask import Flask, request, make_response

app = Flask(__name__)
YEMOT_API_URL = "https://www.call2all.co.il/ym/api/"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------- מילון לשמירת פרטים לפי מספר טלפון ----------
user_sessions = {}

def ym_response(content: str):
    res = make_response(content)
    res.headers["Content-Type"] = "text/plain; charset=utf-8"
    return res

def ym_read(var_name: str, prompt: str, max_digits=10):
    return ym_response(f"read={prompt}={var_name},{max_digits},12,1,Digits")

def ym_say_and_go_back(text: str):
    return ym_response(f"id_list_message={text}")

@app.route('/save-credentials', methods=['GET', 'POST'])
def save_credentials():
    # ---------- שלב 1: שליפת המספר של המתקשר ----------
    cli = request.values.get('cli')
    system = request.values.get('system')
    password = request.values.get('password')

    # ---------- שלב 2: שאלת מספר מערכת ----------
    if not system:
        return ym_read("system", "t-אנא הקש את מספר המערכת ובסיומה סולמית", 10)

    # ---------- שלב 3: שאלת סיסמה ----------
    if not password:
        return ym_read("password", "t-אנא הקש את סיסמת המערכת ובסיומה סולמית", 10)

    # ---------- שלב 4: שמירה לפי מספר טלפון ----------
    if cli:
        user_sessions[cli] = {
            "system": system.strip(),
            "password": password.strip()
        }
        logging.info(f"פרטים נשמרו למספר {cli}")
        return ym_say_and_go_back(f"t-הפרטים נשמרו בהצלחה למספר {cli}")
    else:
        # אם אין CLI (לא סביר, אבל למקרה הצורך)
        return ym_say_and_go_back("t-לא זוהה מספר מתקשר. נסה שוב")

# ---------- פונקציה לשימוש במודולים אחרים ----------
def get_user_credentials(cli):
    """מחזירה את פרטי המשתמש לפי מספר טלפון, או None אם לא נמצא"""
    return user_sessions.get(cli)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
