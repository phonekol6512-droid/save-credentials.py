import re
import logging
import requests
from flask import Flask, request, make_response

app = Flask(__name__)
YEMOT_API_URL = "https://www.call2all.co.il/ym/api/"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------- זיכרון פרטי משתמשים לפי CLI ----------
user_sessions = {}

def get_user_credentials(cli):
    """מחזיר פרטי מערכת (system, password) לפי מספר טלפון"""
    if cli and cli in user_sessions:
        return user_sessions[cli].get('system'), user_sessions[cli].get('password')
    return None, None

def save_user_credentials(cli, system, password):
    """שומר פרטי מערכת לפי מספר טלפון"""
    if cli:
        user_sessions[cli] = {'system': system, 'password': password}
        logging.info(f"פרטים נשמרו עבור CLI {cli}")
    else:
        # fallback – שומר גלובלי (כל המשתמשים ישתמשו באותו פרט)
        user_sessions['default'] = {'system': system, 'password': password}
        logging.info("פרטים נשמרו ברירת מחדל (ללא CLI)")

def ym_response(content: str):
    res = make_response(content)
    res.headers["Content-Type"] = "text/plain; charset=utf-8"
    return res

def ym_read(var_name: str, prompt: str, max_digits=10):
    return ym_response(f"read={prompt}={var_name},{max_digits},12,1,Digits")

def ym_say_and_go_back(text: str):
    return ym_response(f"id_list_message={text}")

# ---------- שלוחה 1: שמירת פרטי מערכת ----------
@app.route('/save-credentials', methods=['GET', 'POST'])
def save_credentials():
    cli = request.values.get('cli')
    system = request.values.get('system')
    password = request.values.get('password')

    # שלב 1: שאלת מספר מערכת
    if not system:
        return ym_read("system", "t-אנא הקש את מספר המערכת ובסיומה סולמית", 10)

    # שלב 2: שאלת סיסמה
    if not password:
        return ym_read("password", "t-אנא הקש את סיסמת המערכת ובסיומה סולמית", 10)

    # שלב 3: שמירה בזיכרון
    save_user_credentials(cli, system.strip(), password.strip())

    # הודעה למשתמש
    if cli:
        msg = f"t-הפרטים נשמרו בהצלחה עבור מספר {cli}"
    else:
        msg = "t-הפרטים נשמרו בהצלחה (ברירת מחדל)"
    return ym_say_and_go_back(msg)

# ---------- שלוחה 2: יצירת שלוחת השמעה ----------
@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    cli = request.values.get('cli')

    # ---------- ניסיון לשלוף פרטים מהזיכרון ----------
    system, password = get_user_credentials(cli)

    # אם אין פרטים – שואל
    if not system:
        system = request.values.get('system')
        if not system:
            return ym_read("system", "t-אנא הקש את מספר המערכת ובסיומה סולמית", 10)

    if not password:
        password = request.values.get('password')
        if not password:
            return ym_read("password", "t-אנא הקש את סיסמת המערכת ובסיומה סולמית", 10)

    # שומר פרטים אם הגיעו מה-read (למקרה שזה המשתמש הראשון)
    if cli:
        save_user_credentials(cli, system.strip(), password.strip())

    # ---------- שאר השאלות ----------
    extension = request.values.get('extension')
    say_length = request.values.get('say_length')
    play_beep = request.values.get('play_beep')
    play_order = request.values.get('play_order')
    say_files_amount = request.values.get('say_files_amount')
    source_extension = request.values.get('source_extension')
    source_extension_path = request.values.get('source_extension_path')
    end_action = request.values.get('end_action')
    end_extension = request.values.get('end_extension')
    last_play_action = request.values.get('last_play_action')

    if not extension:
        return ym_read("extension", "t-אנא הקש את מספר השלוחה (לפנימית הקש כוכבית) ובסיום סולמית", 10)

    if say_length is None:
        return ym_read("say_length", "t-אורך הקובץ? 1-כן תמיד 2-רק מעל 5 דקות 0-לא", 1)

    if play_beep is None:
        return ym_read("play_beep", "t-להסיר ביפ? 1-כן 0-לא", 1)

    if play_order is None:
        return ym_read("play_order", "t-סדר: 1-ישן לחדש 0-ברירת מחדל", 1)

    if say_files_amount is None:
        return ym_read("say_files_amount", "t-להשמיע כמות? 1-כן 0-לא", 1)

    if source_extension is None:
        return ym_read("source_extension", "t-משלוחה אחרת? 1-כן 0-לא", 1)

    if source_extension == "1" and not source_extension_path:
        return ym_read("source_extension_path", "t-הקש את השלוחה המקור (לפנימית הקש כוכבית)", 10)

    if end_action is None:
        return ym_read("end_action", "t-לעבור לשלוחה בסיום? 1-כן 0-לא", 1)

    if end_action == "1" and not end_extension:
        return ym_read("end_extension", "t-הקש את שלוחת היעד (לפנימית הקש כוכבית)", 10)

    if last_play_action is None:
        return ym_read("last_play_action", "t-שמירת מיקום: 1-תפריט 2-אוטומטי 0-לא", 1)

    # ---------- יצירת השלוחה ----------
    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_go_back("t-שגיאה: השלוחה ריקה")

        token = f"{system.strip()}:{password.strip()}"

        say_length_value = "say_length=yes" if say_length == "1" else "playfile_say_length_if=5" if say_length == "2" else "say_length=no"
        beep_line = "play_beep=no" if play_beep == "1" else ""
        order_line = "start=min" if play_order == "1" else ""
        files_amount_line = "say_files_amount=yes" if say_files_amount == "1" else ""

        if source_extension == "1" and source_extension_path:
            clean_source = source_extension_path.strip().replace('*', '/').replace('-', '/').strip('/')
            source_line = f"folder_to_play={clean_source}"
        else:
            source_line = ""

        if end_action == "1" and end_extension:
            clean_end = end_extension.strip().replace('*', '/').replace('-', '/').strip('/')
            end_line = f"playfile_end_goto=/{clean_end}"
        else:
            end_line = ""

        if last_play_action == "1":
            last_play_lines = "save_last_play=yes\nlast_play_tfr=yes"
        elif last_play_action == "2":
            last_play_lines = "save_last_play=yes\nlast_play_auto=yes"
        else:
            last_play_lines = ""

        ext_ini = f"""type=playfile
after_play=return
{say_length_value}
{beep_line}
{order_line}
{files_amount_line}
{source_line}
{end_line}
{last_play_lines}
"""
        ext_ini = "\n".join([line for line in ext_ini.splitlines() if line.strip()])

        r1 = requests.get(
            f"{YEMOT_API_URL}UpdateExtension",
            params={
                "token": token,
                "path": f"ivr2:{clean_ext}",
                "type": "playfile"
            },
            timeout=15
        )
        logging.info(f"UpdateExtension: {r1.status_code} - {r1.text}")

        if not (r1.status_code == 200 and '"responseStatus":"OK"' in r1.text):
            return ym_say_and_go_back("t-שגיאה ביצירת השלוחה")

        r2 = requests.post(
            f"{YEMOT_API_URL}UploadTextFile",
            params={
                "token": token,
                "what": f"ivr2:/{clean_ext}/ext.ini",
                "contents": ext_ini
            },
            timeout=15
        )
        logging.info(f"UploadTextFile: {r2.status_code} - {r2.text}")

        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            return ym_say_and_go_back(f"t-שלוחת ההשמעה {clean_ext} נוצרה בהצלחה")
        else:
            return ym_say_and_go_back("t-השלוחה נוצרה אך התפריט לא נטען")

    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה טכנית")

# ---------- שלוחה 3: יצירת תפריט ----------
@app.route('/create-menu', methods=['GET', 'POST'])
def create_menu():
    cli = request.values.get('cli')

    # ---------- ניסיון לשלוף פרטים מהזיכרון ----------
    system, password = get_user_credentials(cli)

    # אם אין פרטים – שואל
    if not system:
        system = request.values.get('system')
        if not system:
            return ym_read("system", "t-אנא הקש את מספר המערכת ובסיומה סולמית", 10)

    if not password:
        password = request.values.get('password')
        if not password:
            return ym_read("password", "t-אנא הקש את סיסמת המערכת ובסיומה סולמית", 10)

    # שומר פרטים אם הגיעו מה-read
    if cli:
        save_user_credentials(cli, system.strip(), password.strip())

    # ---------- שאר השאלות ----------
    extension = request.values.get('extension')
    change_default = request.values.get('change_default')
    num_digits = request.values.get('num_digits')
    change_voice = request.values.get('change_voice')
    voice_choice = request.values.get('voice_choice')
    change_speed = request.values.get('change_speed')
    speed_choice = request.values.get('speed_choice')
    omer_choice = request.values.get('omer_choice')
    conf_bridge = request.values.get('conf_bridge')
    conf_extension = request.values.get('conf_extension')
    hash_setting = request.values.get('hash_setting')
    star_setting = request.values.get('star_setting')

    if not extension:
        return ym_read("extension", "t-אנא הקש את מספר השלוחה (לפנימית הקש כוכבית) ובסיום סולמית", 10)

    if not change_default:
        return ym_read("change_default", "t-לשנות כמות הקשות? 1-כן 0-לא", 1)
    if change_default == "1" and not num_digits:
        return ym_read("num_digits", "t-כמה הקשות? (1-9)", 1)

    if not change_voice:
        return ym_read("change_voice", "t-להגדיר קול רובוטי? 1-כן 0-לא", 1)
    if change_voice == "1" and not voice_choice:
        return ym_read("voice_choice", "t-בחר קול: 1-אליק 2-יעקב 3-סיוון 4-אסנת", 1)

    if not change_speed:
        return ym_read("change_speed", "t-לשנות מהירות קול? 1-כן 0-לא", 1)
    if change_speed == "1" and not speed_choice:
        return ym_read("speed_choice", "t-מהירות: 1-קצת איטי 2-קצת מהיר 3-איטי 4-מהיר 5-איטי מאוד 6-מהיר מאוד 7-איטי במיוחד 8-מהיר במיוחד", 1)

    if omer_choice is None:
        return ym_read("omer_choice", "t-ספירת העומר? 1-כן 0-לא", 1)

    if conf_bridge is None:
        return ym_read("conf_bridge", "t-הודעת ועידה? 1-כן 0-לא", 1)
    if conf_bridge == "1" and not conf_extension:
        return ym_read("conf_extension", "t-הקש את שלוחת הועידה (לפנימית הקש כוכבית)", 10)

    if not hash_setting:
        return ym_read("hash_setting", "t-סולמית כשלוחה נפרדת? 1-כן 0-לא", 1)

    if star_setting is None:
        return ym_read("star_setting", "t-כוכבית כשלוחה נפרדת? 1-כן 0-לא", 1)

    # ---------- יצירת התפריט ----------
    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_go_back("t-שגיאה: השלוחה ריקה")

        token = f"{system.strip()}:{password.strip()}"
        digits = int(num_digits) if (num_digits and num_digits.isdigit()) else 1

        voice_map = {
            "1": "Elik_2100",
            "2": "Jacob",
            "3": "Sivan",
            "4": "Osnat"
        }
        selected_voice = voice_map.get(voice_choice, "he-il-1") if change_voice == "1" else "he-il-1"

        speed_map = {
            "1": "-2", "2": "2", "3": "-4", "4": "4",
            "5": "-7", "6": "7", "7": "-10", "8": "10"
        }
        selected_speed = speed_map.get(speed_choice, "0") if change_speed == "1" else "0"

        omer_line = "omer_today_play=yes" if omer_choice == "1" else ""
        conf_lines = ""
        if conf_bridge == "1" and conf_extension:
            clean_conf = conf_extension.strip().replace('*', '/').replace('-', '/').strip('/')
            conf_lines = f"menu_say_conf_bridge=yes\nmenu_say_conf_bridge_1={clean_conf}"
        hash_line = "hash_extension=yes" if hash_setting == "1" else ""
        star_line = "star_extension=yes" if star_setting == "1" else ""

        ext_ini = f"""type=menu
title=שלוחת תפריט נבנה באמצעות מגדיר פון 
max_digits={digits}
{hash_line}
{star_line}
menu_voice={selected_voice}
rate={selected_speed}
{omer_line}
{conf_lines}
"""

        r1 = requests.get(
            f"{YEMOT_API_URL}UpdateExtension",
            params={
                "token": token,
                "path": f"ivr2:{clean_ext}",
                "type": "menu",
                "max_digits": digits
            },
            timeout=15
        )
        logging.info(f"UpdateExtension: {r1.status_code} - {r1.text}")

        if not (r1.status_code == 200 and '"responseStatus":"OK"' in r1.text):
            return ym_say_and_go_back("t-שגיאה ביצירת השלוחה")

        r2 = requests.post(
            f"{YEMOT_API_URL}UploadTextFile",
            params={
                "token": token,
                "what": f"ivr2:/{clean_ext}/ext.ini",
                "contents": ext_ini
            },
            timeout=15
        )
        logging.info(f"UploadTextFile: {r2.status_code} - {r2.text}")

        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            return ym_say_and_go_back(f"t-התפריט {clean_ext} נוצר בהצלחה")
        else:
            return ym_say_and_go_back("t-השלוחה נוצרה אך התפריט לא נטען")

    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה טכנית")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
