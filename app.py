import re
import json
import os
import logging
import requests
from flask import Flask, request, make_response

app = Flask(__name__)
YEMOT_API_URL = "https://www.call2all.co.il/ym/api/"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------- קובץ לשמירת פרטי משתמשים ----------
CREDENTIALS_FILE = "credentials.json"

def load_credentials():
    """טוען את כל הפרטים מקובץ JSON"""
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_credentials_to_file(data):
    """שומר את כל הפרטים לקובץ JSON"""
    with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_credentials(cli):
    """מחזיר פרטי מערכת (system, password) לפי cli, או None"""
    data = load_credentials()
    if cli and cli in data:
        return data[cli].get('system'), data[cli].get('password')
    return None, None

def save_user_credentials(cli, system, password):
    """שומר פרטי מערכת לפי cli (או כ-default אם אין cli)"""
    data = load_credentials()
    key = cli if cli else 'default'
    data[key] = {'system': system, 'password': password}
    save_credentials_to_file(data)
    logging.info(f"פרטים נשמרו תחת '{key}'")

# ---------- פונקציות בסיסיות ----------
def ym_response(content: str):
    res = make_response(content)
    res.headers["Content-Type"] = "text/plain; charset=utf-8"
    return res

def ym_read(var_name: str, prompt: str, max_digits=1):
    return ym_response(f"read={prompt}={var_name},{max_digits},12,1,Digits")

def ym_say_and_go_back(text: str):
    """משמיע הודעה וחוזר לתפריט הקודם (ללא לופ)"""
    return ym_response(f"id_list_message={text}")

# ---------- שלוחה 1: שמירת פרטי מערכת ----------
@app.route('/save-credentials', methods=['GET', 'POST'])
def save_credentials():
    cli = request.values.get('cli')
    system = request.values.get('system')
    password = request.values.get('password')

    if not system:
        return ym_read("system", "t-ברוכים הבאים למגדיר פון, קו ההגדרות המתקדמות מבית פון קול אנא הקישו את מספר המערכת בסיום הקישו סולמית", 10)
    if not password:
        return ym_read("password", "t-אנא הקש את סיסמת המערכת ובסיומה סולמית", 10)

    save_user_credentials(cli, system.strip(), password.strip())

    if cli:
        msg = f"t-הפרטים נשמרו בהצלחה למספר {cli}"
    else:
        msg = "t-הפרטים נשמרו בהצלחה (ברירת מחדל)"
    return ym_say_and_go_back(msg)

# ---------- שלוחה 2: יצירת תפריט ----------
@app.route('/create-menu', methods=['GET', 'POST'])
def create_menu():
    cli = request.values.get('cli')
    system = request.values.get('system')
    password = request.values.get('password')
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

    # ---------- שלב 0: שליפת פרטים מהזיכרון (אם קיימים) ----------
    if not system or not password:
        saved_system, saved_password = get_user_credentials(cli)
        if saved_system and saved_password:
            system = saved_system
            password = saved_password
            logging.info(f"נשלפו פרטים שמורים ל-CLI {cli}")

    # ---------- שלב 1: מספר מערכת ----------
    if not system:
        return ym_read("system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10)

    # ---------- שלב 2: סיסמה ----------
    if not password:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10)

    # ---------- שמירה (אם הגיעו מה-read) ----------
    if cli:
        save_user_credentials(cli, system.strip(), password.strip())

    # ---------- שלב 3: מספר שלוחה ----------
    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה ובסיום הקישו סולמית, לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה", 10)

    # ---------- שלב 4: שינוי ברירת מחדל של הקשות ----------
    if not change_default:
        return ym_read("change_default", "t-ברירת מחדל לכל שלוחה יש סיפרה אחת בלבד וכשמקישים 1 אז נכנסים לשלוחה 1 ואם מקישים 2 אז נכנסים לשלוחה 2, לשינוי הקישו 1 וסולמית להמשך ללא שינוי הקישו 0", 1)
    if change_default == "1" and not num_digits:
        return ym_read("num_digits", "t-אנא הקישו את מספר ההקשות בסיום הקישו סולמית", 1)

    # ---------- שלב 5: בחירת קול ----------
    if not change_voice:
        return ym_read("change_voice", "t-האם ברצונך להגדיר את הקול הרובוטי בשלוחה, להגדרה הקישו 1 וסולמית להמשך ללא שינוי הקישו 0 וסולמית", 1)
    if change_voice == "1" and not voice_choice:
        return ym_read("voice_choice", "t-בחר קול:  לאליק הקישו 1 וסולמית ליעקב הקישו 2 וסולמית לסיוון הקישו 3 וסולמית לאסנת הקישו 4 וסולמית", 1)

    # ---------- שלב 6: מהירות הקריאה ----------
    if not change_speed:
        return ym_read("change_speed", "t-האם ברצונך לשנות את מהירות הקול הרובוטי? לשינוי הקישו 1 וסולמית להמשך ללא שינוי הקישו 0 וסולמית", 1)
    if change_speed == "1" and not speed_choice:
        return ym_read("speed_choice", "t-בחר מהירות: לקול קצת איטי הקש 1, לקול קצת מהיר הקש 2, לקול איטי הקש 3, לקול מהיר הקש 4, לקול איטי מאוד הקש 5, לקול מהיר מאוד הקש 6, לקול איטי במיוחד הקש 7, לקול מהיר במיוחד הקש 8", 1)

    # ---------- שלב 7: ספירת העומר ----------
    if omer_choice is None:
        return ym_read("omer_choice", "t-האם להפעיל בתפריט תזכורת ספירת העומר? להפעלה הקישו 1 וסולמית לביטול הקישו 0 וסולמית", 1)

    # ---------- שלב 8: הודעת ועידה פעילה ----------
    if conf_bridge is None:
        return ym_read("conf_bridge", "t-האם ברצונך להפעיל הודעה שמודיעה אם קיימת ועידה פעילה? להפעלה הקישו 1 וסולמית לביטול הקישו 0 וסולמית", 1)
    if conf_bridge == "1" and not conf_extension:
        return ym_read("conf_extension", "t-אנא הקישו את מספר השלוחה של חדר הועידה ובסיום הקישו סולמית לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה", 10)

    # ---------- שלב 9: מקש סולמית # ----------
    if not hash_setting:
        return ym_read("hash_setting", "t-ברירת המחדל מקש סולמית משמש לחזרה לתפריט הקודם, אם ברצונך ששלוחה סולמית תיהיה שלוחה בפני עצמה הקישו 1 וסולמית להמשך ללא שינוי הקישו 0 וסולמית", 1)

    # ---------- שלב 10: מקש כוכבית * ----------
    if star_setting is None:
        return ym_read("star_setting", "t-ברירת המחדל מקש כוכבית משמש כמקש חזרה לתפריט הראשי, אם ברצונך ששלוחת כוכבית תיהיה שלוחה בפני עצמה הקישו 1 וסולמית להמשך ללא שינוי הקישו 0 וסולמית", 1)

    # ===================== יצירת השלוחה =====================
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
            conf_lines = f"menu_say_conf_bridge=yes\nmenu_say_conf_bridge_1={conf_extension.strip()}"
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
            speed_labels = {
                "-2": "קצת איטי",
                "2": "קצת מהיר",
                "-4": "איטי",
                "4": "מהיר",
                "-7": "איטי מאוד",
                "7": "מהיר מאוד",
                "-10": "איטי במיוחד",
                "10": "מהיר במיוחד"
            }
            speed_label = speed_labels.get(selected_speed, "רגיל")
            omer_status = "פעיל" if omer_choice == "1" else "כבוי"
            conf_status = f"פעיל (שלוחה {conf_extension})" if conf_bridge == "1" else "כבוי"
            hash_status = "שלוחה נפרדת" if hash_setting == "1" else "ברירת מחדל (חזרה)"
            star_status = "שלוחה נפרדת" if star_setting == "1" else "ברירת מחדל (הפרדה)"
            msg = f"t-השלוחה {clean_ext} הוגדרה בהצלחה על ידי מגדיר פון שלום ולהתראות. מהירות: {speed_label}. ספירת העומר: {omer_status}. ועידה: {conf_status}. סולמית: {hash_status}. כוכבית: {star_status}"
            return ym_say_and_go_back(msg)
        else:
            return ym_say_and_go_back("t-השלוחה נוצרה אך התפריט לא נטען")

    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה טכנית")

# ---------- שלוחה 3: יצירת שלוחת השמעה ----------
@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    cli = request.values.get('cli')
    system = request.values.get('system')
    password = request.values.get('password')
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

    # ---------- שלב 0: שליפת פרטים מהזיכרון ----------
    if not system or not password:
        saved_system, saved_password = get_user_credentials(cli)
        if saved_system and saved_password:
            system = saved_system
            password = saved_password
            logging.info(f"נשלפו פרטים שמורים ל-CLI {cli}")

    # --- שלב 1: system ---
    if not system:
        return ym_read("system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10)

    # --- שלב 2: password ---
    if not password:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10)

    # ---------- שמירה ----------
    if cli:
        save_user_credentials(cli, system.strip(), password.strip())

    # --- שלב 3: extension ---
    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה שברצונכם להגדיר לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה בסיום הקישו סולמית", 10)

    # --- שלב 4: אורך הקובץ ---
    if say_length is None:
        return ym_read("say_length", "t- אם ברצונך להגדיר שישמיע את אורך הקובץ לפני שמשמיע את הקובץ? להגדרה כברירת מחדל הקש 0 אם ברצונך שישמיע את אורך הקובץ הקש 1 אם ברצונך שישמיע את אורך הקובץ רק אם הקובץ ארוך מחמש דקות הקש 2", 1)

    # --- שלב 5: ביפ ---
    if play_beep is None:
        return ym_read("play_beep", "t-ברירת המחדל של המערכת משמיע בין קובץ לקובץ ציפצוף להמשך ללא שינוי הקש 0 להגדרה שלא ישמיע ציפצוף בין הודעה להודעה הקש 1", 1)

    # --- שלב 6: סדר השמעה ---
    if play_order is None:
        return ym_read("play_order", "t-ברירת מחדל של המערכת משמיע את הקבצים מהחדש לישן להמשך ללא שינוי הקש 0 לשינוי והגדרה שישמיע את הקבצים מהישן לחדש הקש 1", 1)

    # --- שלב 7: כמות הודעות ---
    if say_files_amount is None:
        return ym_read("say_files_amount", "t-האם ברצונך שישמיע בכניסה לשלוחה את כמות הקבצים שנמצאים בשלוחה? להגדרה כברירת מחדל הקש 0 להגדרה שישמיע את כמות הקבצים הקש 1", 1)

    # --- שלב 8: מקור ---
    if source_extension is None:
        return ym_read("source_extension", "t-ברירת המחדל של המערכת משמיע את הקבצים מהשלוחה עצמה להמשך ללא שינוי הקש 0 לשינוי והגדרה שישמיע את הקבצים משלוחה אחרת הקש 1", 1)

    if source_extension == "1" and not source_extension_path:
        return ym_read("source_extension_path", "t-הקש את השלוחה שברצונך ממנה שישמיע את הקבצים כאשר בין שלוחה לשלוחה הקש כוכבית", 10)

    # --- שלב 9: סיום ---
    if end_action is None:
        return ym_read("end_action", "t-ברירת מחדל של המערכת בסיום השמעת ההודעות חוזר לתפריט הקודם, להמשך ללא שינוי הקש 0 לשינוי והגדרה שיעבור בסיום ההשמעה לשלוחה אחרת הקש 1", 1)

    if end_action == "1" and not end_extension:
        return ym_read("end_extension", "t-אנא הקש את מספר השלוחה אליה יעבור בסיום כאשר בין שלוחה לשלוחה הקש כוכבית", 10)

    # --- שלב 10: שמירת מיקום ---
    if last_play_action is None:
        return ym_read("last_play_action", "t-ברירת המחדל של המערכת משמיע את השלוחה מחדש כל פעם להמשך ללא שינוי הקש 0 לשינוי והגדרה שיכנס לשלוחה ישאל את המאזין האם לחזור למקום האחרון אליו האזין בשלוחה הקש 1 לשינוי והגדרה שמייד יחזור למיקום האחרון אליו האזין הקש שתיים", 1)

    # --- יצירת השלוחה ---
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
            return ym_say_and_go_back(f"t- השלוחה הוגדרה בהצלחה במיקום  {clean_ext} נוצרה בהצלחה ")
        else:
            return ym_say_and_go_back("t-שגיאה בהעלאת התפריט")

    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה טכנית")

# ---------- הרצת השרת ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
