import re
import json
import os
import logging
import requests
from flask import Flask, request, make_response

app = Flask(__name__)
YEMOT_API_URL = "https://www.call2all.co.il/ym/api/"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------- שמירה בימות ----------
CREDENTIALS_PATH = "ivr2:1/credentials.json"

def load_credentials():
    token = os.environ.get('MASTER_TOKEN')
    if not token:
        return {}
    try:
        r = requests.get(f"{YEMOT_API_URL}GetTextFile", params={"token": token, "what": CREDENTIALS_PATH}, timeout=10)
        if r.status_code == 200 and r.text.strip():
            outer = json.loads(r.text)
            if outer.get("responseStatus") == "OK":
                contents = outer.get("contents", "")
                if contents and contents.strip():
                    return json.loads(contents)
        return {}
    except Exception as e:
        logging.error(f"שגיאה בטעינה מימות: {e}")
        return {}

def save_credentials_to_file(data):
    token = os.environ.get('MASTER_TOKEN')
    if not token:
        return False
    try:
        r = requests.post(f"{YEMOT_API_URL}UploadTextFile", params={"token": token, "what": CREDENTIALS_PATH, "contents": json.dumps(data, ensure_ascii=False, indent=2)}, timeout=15)
        return r.status_code == 200 and '"responseStatus":"OK"' in r.text
    except:
        return False

def get_user_credentials(cli):
    data = load_credentials()
    if cli and cli in data:
        return data[cli].get('system'), data[cli].get('password')
    return None, None

def save_field(cli, field, value):
    data = load_credentials()
    key = cli if cli else 'default'
    if key not in data:
        data[key] = {}
    data[key][field] = value
    save_credentials_to_file(data)

def delete_user_credentials(cli):
    data = load_credentials()
    key = cli if cli else 'default'
    if key in data:
        del data[key]
        save_credentials_to_file(data)

# ---------- פונקציות בסיסיות ----------
def ym_response(content: str):
    res = make_response(content)
    res.headers["Content-Type"] = "text/plain; charset=utf-8"
    return res

def ym_read(var_name: str, prompt: str, max_digits=1, input_type="Digits"):
    return ym_response(f"read={prompt}={var_name},{max_digits},12,1,{input_type}")

def ym_say_and_go_back(text: str):
    return ym_response(f"id_list_message={text}")

# ---------- שלוחה 1: ניהול מערכת ----------
@app.route('/manage-credentials', methods=['GET', 'POST'])
def manage_credentials():
    cli = request.values.get('ApiPhone')
    user_system = request.values.get('user_system')
    password = request.values.get('password')
    manage_action = request.values.get('manage_action')

    saved_system, saved_password = get_user_credentials(cli)

    if saved_system and saved_password and manage_action is None:
        return ym_read("manage_action", f"t-מספר מערכת {saved_system} שמור בתור המערכת הקבועה שלכם לעדכון המספר של המערכת או להחלפת המערכת  הקש 1 למחיקת מספר המערכת שלכם והסיסמה הקש 2 ליציאה הקש 0", 1)

    if manage_action == "2":
        delete_user_credentials(cli)
        return ym_say_and_go_back("t-מספר המערכת שלכם והסיסמה נמחק בהצלחה")

    if manage_action == "0":
        return ym_say_and_go_back("t-הנכם מועברים לתפריט הקודם")

    if not user_system:
        return ym_read("user_system", "t-הגדרת המערכת הקבועה שלכם, שימו לב מספר המערכת והסיסמה שלכם נשמרים בשרת מאובטח בכל זאת תמיד תוכלו למחוק את הפרטים ולעדכן אותם, הנכם מועברים להגדרת המערכת הקבועה שלכם, אנא הקישו את מספר המערכת שלכם ובסיום הקישו סולמית", 10, "Any")
    if not password:
        return ym_read("password", "t-אנא הקישו את סיסמת המערכת שלכם ובסיום הקישו סולמית", 10, "Any")

    if 'user_system' in request.values and user_system:
        save_field(cli, 'system', user_system.strip())
    if 'password' in request.values and password:
        save_field(cli, 'password', password.strip())

    return ym_say_and_go_back("t-הפרטים נשמרו בהצלחה מעתה בכל פעם שתגדירו מודול תועברו ישירות רק להקשת מספר השלוחה")

# ---------- שלוחה 2: יצירת תפריט ----------
@app.route('/create-menu', methods=['GET', 'POST'])
def create_menu():
    cli = request.values.get('ApiPhone')
    user_system = request.values.get('user_system')
    password = request.values.get('password')
    
    saved_system, saved_password = get_user_credentials(cli)

    if saved_system and saved_password:
        user_system = saved_system
        password = saved_password
    else:
        if not user_system:
            return ym_read("user_system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10, "Any")
        if not password:
            return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10, "Any")

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
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה ובסיום הקישו סולמית לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה", 10)

    if not change_default:
        return ym_read("change_default", "t-ברירת מחדל לכל שלוחה יש סיפרה אחת בלבד וכשמקישים 1 אז נכנסים לשלוחה 1 ואם מקישים 2 אז נכנסים לשלוחה 2 לשינוי הקישו 1 וסולמית להמשך ללא שינוי הקישו 0", 1)
    if change_default == "1" and not num_digits:
        return ym_read("num_digits", "t-אנא הקישו את מספר ההקשות בסיום הקישו סולמית", 1)

    if not change_voice:
        return ym_read("change_voice", "t-האם ברצונך להגדיר את הקול הרובוטי בשלוחה להגדרה הקישו 1 וסולמית להמשך ללא שינוי הקישו 0 וסולמית", 1)
    if change_voice == "1" and not voice_choice:
        return ym_read("voice_choice", "t-בחר קול  לאליק הקישו 1 וסולמית ליעקב הקישו 2 וסולמית לסיוון הקישו 3 וסולמית לאסנת הקישו 4 וסולמית", 1)

    if not change_speed:
        return ym_read("change_speed", "t-האם ברצונך לשנות את מהירות הקול הרובוטי? לשינוי הקישו 1 וסולמית להמשך ללא שינוי הקישו 0 וסולמית", 1)
    if change_speed == "1" and not speed_choice:
        return ym_read("speed_choice", "t-בחר מהירות לקול קצת איטי הקש 1 לקול קצת מהיר הקש 2 לקול איטי הקש 3 לקול מהיר הקש 4 לקול איטי מאוד הקש 5 לקול מהיר מאוד הקש 6 לקול איטי במיוחד הקש 7 לקול מהיר במיוחד הקש 8", 1)

    if omer_choice is None:
        return ym_read("omer_choice", "t-האם להפעיל בתפריט תזכורת ספירת העומר? להפעלה הקישו 1 וסולמית לביטול הקישו 0 וסולמית", 1)

    if conf_bridge is None:
        return ym_read("conf_bridge", "t-האם ברצונך להפעיל הודעה שמודיעה אם קיימת ועידה פעילה? להפעלה הקישו 1 וסולמית לביטול הקישו 0 וסולמית", 1)
    if conf_bridge == "1" and not conf_extension:
        return ym_read("conf_extension", "t-אנא הקישו את מספר השלוחה של חדר הועידה ובסיום הקישו סולמית לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה", 10)

    if not hash_setting:
        return ym_read("hash_setting", "t-ברירת המחדל מקש סולמית משמש לחזרה לתפריט הקודם אם ברצונך ששלוחה סולמית תיהיה שלוחה בפני עצמה הקישו 1 וסולמית להמשך ללא שינוי הקישו 0 וסולמית", 1)

    if star_setting is None:
        return ym_read("star_setting", "t-ברירת המחדל מקש כוכבית משמש כמקש חזרה לתפריט הראשי אם ברצונך ששלוחת כוכבית תיהיה שלוחה בפני עצמה הקישו 1 וסולמית להמשך ללא שינוי הקישו 0 וסולמית", 1)

    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_go_back("t-שגיאה השלוחה ריקה")

        token = f"{user_system.strip()}:{password.strip()}"
        digits = int(num_digits) if (num_digits and num_digits.isdigit()) else 1

        voice_map = {"1": "Elik_2100", "2": "Jacob", "3": "Sivan", "4": "Osnat"}
        selected_voice = voice_map.get(voice_choice, "he-il-1") if change_voice == "1" else "he-il-1"

        speed_map = {"1": "-2", "2": "2", "3": "-4", "4": "4", "5": "-7", "6": "7", "7": "-10", "8": "10"}
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

        r1 = requests.get(f"{YEMOT_API_URL}UpdateExtension", params={"token": token, "path": f"ivr2:{clean_ext}", "type": "menu", "max_digits": digits}, timeout=15)
        if not (r1.status_code == 200 and '"responseStatus":"OK"' in r1.text):
            return ym_say_and_go_back("t-שגיאה ביצירת השלוחה")

        r2 = requests.post(f"{YEMOT_API_URL}UploadTextFile", params={"token": token, "what": f"ivr2:/{clean_ext}/ext.ini", "contents": ext_ini}, timeout=15)
        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            return ym_say_and_go_back(f"t-השלוחה {clean_ext} הוגדרה בהצלחה")
        else:
            return ym_say_and_go_back("t-השלוחה נוצרה אך התפריט לא נטען")
    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה טכנית")

# ---------- שלוחה 3: יצירת שלוחת השמעה ----------
@app.route('/create-playfile', methods=['GET', 'POST'])
def create_playfile():
    cli = request.values.get('ApiPhone')
    user_system = request.values.get('user_system')
    password = request.values.get('password')
    
    saved_system, saved_password = get_user_credentials(cli)
    if saved_system and saved_password:
        user_system, password = saved_system, saved_password
    else:
        if not user_system:
            return ym_read("user_system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10, "Any")
        if not password:
            return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10, "Any")

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
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה שברצונכם להגדיר לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה בסיום הקישו סולמית", 10)

    if say_length is None:
        return ym_read("say_length", "t- אם ברצונך להגדיר שישמיע את אורך הקובץ לפני שמשמיע את הקובץ? להגדרה כברירת מחדל הקש 0 אם ברצונך שישמיע את אורך הקובץ הקש 1 אם ברצונך שישמיע את אורך הקובץ רק אם הקובץ ארוך מחמש דקות הקש 2", 1)

    if play_beep is None:
        return ym_read("play_beep", "t-ברירת המחדל של המערכת משמיע בין קובץ לקובץ ציפצוף להמשך ללא שינוי הקש 0 להגדרה שלא ישמיע ציפצוף בין הודעה להודעה הקש 1", 1)

    if play_order is None:
        return ym_read("play_order", "t-ברירת מחדל של המערכת משמיע את הקבצים מהחדש לישן להמשך ללא שינוי הקש 0 לשינוי והגדרה שישמיע את הקבצים מהישן לחדש הקש 1", 1)

    if say_files_amount is None:
        return ym_read("say_files_amount", "t-האם ברצונך שישמיע בכניסה לשלוחה את כמות הקבצים שנמצאים בשלוחה? להגדרה כברירת מחדל הקש 0 להגדרה שישמיע את כמות הקבצים הקש 1", 1)

    if source_extension is None:
        return ym_read("source_extension", "t-ברירת המחדל של המערכת משמיע את הקבצים מהשלוחה עצמה להמשך ללא שינוי הקש 0 לשינוי והגדרה שישמיע את הקבצים משלוחה אחרת הקש 1", 1)

    if source_extension == "1" and not source_extension_path:
        return ym_read("source_extension_path", "t-הקש את השלוחה שברצונך ממנה שישמיע את הקבצים כאשר בין שלוחה לשלוחה הקש כוכבית", 10)

    if end_action is None:
        return ym_read("end_action", "t-ברירת מחדל של המערכת בסיום השמעת ההודעות חוזר לתפריט הקודם להמשך ללא שינוי הקש 0 לשינוי והגדרה שיעבור בסיום ההשמעה לשלוחה אחרת הקש 1", 1)

    if end_action == "1" and not end_extension:
        return ym_read("end_extension", "t-אנא הקש את מספר השלוחה אליה יעבור בסיום כאשר בין שלוחה לשלוחה הקש כוכבית", 10)

    if last_play_action is None:
        return ym_read("last_play_action", "t-ברירת המחדל של המערכת משמיע את השלוחה מחדש כל פעם להמשך ללא שינוי הקש 0 לשינוי והגדרה שיכנס לשלוחה ישאל את המאזין האם לחזור למקום האחרון אליו האזין בשלוחה הקש 1 לשינוי והגדרה שמייד יחזור למיקום האחרון אליו האזין הקש שתיים", 1)

    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_go_back("t-שגיאה השלוחה ריקה")

        token = f"{user_system.strip()}:{password.strip()}"
        
        say_length_value = "say_length=yes" if say_length == "1" else "playfile_say_length_if=5" if say_length == "2" else ""
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
title=שלוחת השמעת קבצים נבנה באמצעות מגדיר פון 
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

        r1 = requests.get(f"{YEMOT_API_URL}UpdateExtension", params={"token": token, "path": f"ivr2:{clean_ext}", "type": "playfile"}, timeout=15)
        if not (r1.status_code == 200 and '"responseStatus":"OK"' in r1.text):
            return ym_say_and_go_back("t-שגיאה ביצירת השלוחה")

        r2 = requests.post(f"{YEMOT_API_URL}UploadTextFile", params={"token": token, "what": f"ivr2:/{clean_ext}/ext.ini", "contents": ext_ini}, timeout=15)
        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            return ym_say_and_go_back(f"t-השלוחה הוגדרה בהצלחה במיקום {clean_ext}")
        else:
            return ym_say_and_go_back("t-שגיאה בהעלאת התפריט")
    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה טכנית")

# ---------- שלוחה 4: יצירת שלוחת הקלטה ----------
@app.route('/create-record', methods=['GET', 'POST'])
def create_record():
    cli = request.values.get('ApiPhone')
    user_system = request.values.get('user_system')
    password = request.values.get('password')
    
    saved_system, saved_password = get_user_credentials(cli)
    if saved_system and saved_password:
        user_system, password = saved_system, saved_password
    else:
        if not user_system:
            return ym_read("user_system", "t-אנא הקישו את מספר המערכת ובסיום הקישו סולמית", 10, "Any")
        if not password:
            return ym_read("password", "t-אנא הקישו את סיסמת המערכת ובסיום הקישו סולמית", 10, "Any")

    extension = request.values.get('extension')
    folder_move_choice = request.values.get('folder_move_choice')
    folder_move_path = request.values.get('folder_move_path')
    record_end_goto = request.values.get('record_end_goto')
    record_cancel_goto = request.values.get('record_cancel_goto')
    say_record_menu = request.values.get('say_record_menu')
    say_record_number = request.values.get('say_record_number')
    
    list_tzintuk = request.values.get('list_tzintuk')
    hangup_insert_file = request.values.get('hangup_insert_file')
    set_record_name = request.values.get('set_record_name')
    record_title = request.values.get('record_title')
    record_stop_any_key = request.values.get('record_stop_any_key')
    enter_id = request.values.get('enter_id')
    hard_link = request.values.get('hard_link')
    copy_record_link = request.values.get('copy_record_link')

    if not extension:
        return ym_read("extension", "t-אנא הקישו את מספר השלוחה החדשה ובסיום הקישו סולמית לשלוחה פנימית הקישו כוכבית בין שלוחה לשלוחה", 10)

    if folder_move_choice is None:
        return ym_read("folder_move_choice", "t-ברירת המחדל של המערכת ההקלטות נשמרות בשלוחה עצמה להמשך כברירת מחדל הקישו 0 להעברת ההקלטה לשלוחה אחרת הקישו 1 לתיבה אישית הקישו 2 לבחירה בזמן הקלטה הקישו 3", 1)

    folder_move_value = ""
    if folder_move_choice == "1":
        if not folder_move_path:
            return ym_read("folder_move_path", "t-הקישו את מספר שלוחת היעד ובסיום סולמית", 10)
        folder_move_value = f"/{folder_move_path.strip().replace('*', '/')}"
    elif folder_move_choice == "2":
        folder_move_value = "id"
    elif folder_move_choice == "3":
        folder_move_value = "tfr"

    if record_end_goto is None:
        return ym_read("record_end_goto", "t-ברירת המחדל של המערכת בסיום ההקלטה חוזרת לתפריט הקודם להמשך כברירת מחדל הקישו 0 להעברה לשלוחה אחרת בסיום ההקלטה הקישו 1", 1)
    
    end_goto_value = ""
    if record_end_goto == "1":
        if not request.values.get('record_end_goto_path'):
            return ym_read("record_end_goto_path", "t-הקישו את שלוחת היעד בסיום ובסיום סולמית", 10)
        end_goto_value = f"/{request.values.get('record_end_goto_path').strip().replace('*', '/')}"

    if record_cancel_goto is None:
        return ym_read("record_cancel_goto", "t-ברירת המחדל של המערכת בביטול ההקלטה חוזרת לתפריט הקודם להמשך כברירת מחדל הקישו 0 להעברה לשלוחה אחרת בביטול הקישו 1", 1)
    
    cancel_goto_value = ""
    if record_cancel_goto == "1":
        if not request.values.get('record_cancel_goto_path'):
            return ym_read("record_cancel_goto_path", "t-הקישו את שלוחת הביטול ובסיום סולמית", 10)
        cancel_goto_value = f"/{request.values.get('record_cancel_goto_path').strip().replace('*', '/')}"

    if say_record_menu is None:
        return ym_read("say_record_menu", "t-ברירת המחדל של המערכת משמיעה תפריט אישור ביטול והקלטה מחדש בסיום ההקלטה להמשך כברירת מחדל הקישו 0 לביטול התפריט הקישו 1", 1)
    
    say_record_menu_value = ""
    if say_record_menu == "1":
        say_record_menu_value = "no"

    if say_record_number is None:
        return ym_read("say_record_number", "t-ברירת המחדל של המערכת משמיעה את מספר ההקלטה לפני ההשמעה להמשך כברירת מחדל הקישו 0 לביטול השמעת המספר הקישו 1", 1)
    
    say_record_number_value = ""
    if say_record_number == "1":
        say_record_number_value = "no"

    if list_tzintuk is None:
        return ym_read("list_tzintuk", "t-האם ברצונך לשלוח צינתוק על הקלטה חדשה? להגדרה הקישו 1 אחרת הקישו 0", 1)
    
    tzintuk_value = ""
    if list_tzintuk == "1":
        if not request.values.get('list_tzintuk_name'):
            return ym_read("list_tzintuk_name", "t-הקישו את שם רשימת הצינתוקים ובסיום סולמית", 20, "Any")
        tzintuk_value = request.values.get('list_tzintuk_name').strip()

    if hangup_insert_file is None:
        return ym_read("hangup_insert_file", "t-האם ברצונך לשמור את ההקלטה גם אם המשתמש מנתק? להגדרה הקישו 1 אחרת הקישו 0", 1)
    
    hangup_insert_value = ""
    if hangup_insert_file == "1":
        hangup_insert_value = "yes"

    if set_record_name is None:
        return ym_read("set_record_name", "t-האם ברצונך לאפשר למקליט לבחור שם קובץ? להגדרה הקישו 1 אחרת הקישו 0", 1)
    
    set_record_name_value = ""
    if set_record_name == "1":
        set_record_name_value = "yes"

    if record_title is None:
        return ym_read("record_title", "t-האם ברצונך להקליט כותרת לפני ההקלטה? תמיד הקישו 1 עם תפריט הקישו 2 אחרת הקישו 0", 1)
    
    record_title_value = ""
    if record_title == "1":
        record_title_value = "yes"
    elif record_title == "2":
        record_title_value = "tfr"

    if record_stop_any_key is None:
        return ym_read("record_stop_any_key", "t-האם ברצונך לעצור את ההקלטה בכל מקש? להגדרה הקישו 1 אחרת הקישו 0", 1)
    
    stop_any_key_value = ""
    if record_stop_any_key == "1":
        stop_any_key_value = "yes"

    if enter_id is None:
        return ym_read("enter_id", "t-האם ברצונך להפעיל זיהוי משתמש לפי טלפון? להגדרה הקישו 1 אחרת הקישו 0", 1)
    
    enter_id_value = ""
    if enter_id == "1":
        enter_id_value = "yes"

    if hard_link is None:
        return ym_read("hard_link", "t-האם ברצונך ליצור קישור קשיח להקלטה? להגדרה הקישו 1 אחרת הקישו 0", 1)
    
    hard_link_value = ""
    if hard_link == "1":
        hard_link_value = "yes"

    if copy_record_link is None:
        return ym_read("copy_record_link", "t-האם ברצונך להעתיק את ההקלטה לשלוחה נוספת? להגדרה הקישו 1 אחרת הקישו 0", 1)
    
    copy_link_value = ""
    if copy_record_link == "1":
        if not request.values.get('copy_record_link_path'):
            return ym_read("copy_record_link_path", "t-הקישו את שלוחת ההעתקה ובסיום סולמית", 10)
        copy_link_value = f"/{request.values.get('copy_record_link_path').strip().replace('*', '/')}"

    try:
        clean_ext = extension.strip().replace('*', '/').replace('-', '/').strip('/')
        if not clean_ext:
            return ym_say_and_go_back("t-שגיאה השלוחה ריקה")

        token = f"{user_system.strip()}:{password.strip()}"
        
        lines = ["type=record", "title=שלוחת הקלטה נבנה באמצעות מגדיר פון"]
        
        if folder_move_value:
            lines.append(f"folder_move={folder_move_value}")
            
        if end_goto_value:
            lines.append(f"record_end_goto={end_goto_value}")
            
        if cancel_goto_value: 
            lines.append(f"record_cancel_goto={cancel_goto_value}")
        
        if say_record_menu_value == "no":
            lines.append("say_record_menu=no")
            
        if say_record_number_value == "no":
            lines.append("say_record_number=no")
        
        if tzintuk_value:
            lines.append(f"list_tzintuk={tzintuk_value}")
            lines.append("record_end_run_tzintuk=yes")
        if hangup_insert_value: 
            lines.append(f"hangup_insert_file={hangup_insert_value}")
        if set_record_name_value: 
            lines.append(f"set_record_name={set_record_name_value}")
        if record_title_value: 
            lines.append(f"record_title={record_title_value}")
        if stop_any_key_value: 
            lines.append(f"record_stop_any_key={stop_any_key_value}")
        if enter_id_value:
            lines.append(f"enter_id={enter_id_value}")
            lines.append("enter_id_type=phone")
        if hard_link_value: 
            lines.append(f"hard_link={hard_link_value}")
        if copy_link_value: 
            lines.append(f"copy_record_link={copy_link_value}")

        ext_ini = "\n".join(lines)

        r1 = requests.get(f"{YEMOT_API_URL}UpdateExtension", params={"token": token, "path": f"ivr2:{clean_ext}", "type": "record"}, timeout=15)
        if not (r1.status_code == 200 and '"responseStatus":"OK"' in r1.text):
            return ym_say_and_go_back("t-שגיאה ביצירת השלוחה")

        r2 = requests.post(f"{YEMOT_API_URL}UploadTextFile", params={"token": token, "what": f"ivr2:/{clean_ext}/ext.ini", "contents": ext_ini}, timeout=15)
        if r2.status_code == 200 and '"responseStatus":"OK"' in r2.text:
            return ym_say_and_go_back(f"t-שלוחת ההקלטה {clean_ext} נוצרה בהצלחה")
        else:
            return ym_say_and_go_back("t-השלוחה נוצרה אך התפריט לא נטען")
    except Exception as e:
        logging.exception("שגיאה")
        return ym_say_and_go_back("t-שגיאה טכנית")

# ---------- שלוחה 5: ניהול שיחות פעילות ----------
# מילון לניהול מצב השיחה (האם אנחנו בתפריט הראשי או בתת-תפריט, ומה ה-ID של השיחה המוצגת)
call_states = {}
just_disconnected = set()

@app.route('/active-calls', methods=['GET', 'POST'], strict_slashes=False)
def active_calls():
    if request.values.get('hangup') == 'yes':
        return ""

    cli = request.values.get('ApiPhone')
    
    # שליפת ההקשה האחרונה
    actions = request.values.getlist('action')
    action = actions[-1] if actions else None

    if cli not in call_states:
        call_states[cli] = {'mode': 'main', 'current_call_id': None}
    
    state = call_states[cli]

    saved_system, saved_password = get_user_credentials(cli)
    if not saved_system or not saved_password:
        call_states[cli] = {'mode': 'main', 'current_call_id': None}
        return ym_say_and_go_back("t-לא נמצאו פרטי מערכת שמורים אנא הגדירו את המערכת בשלוחת הניהול")

    token = f"{saved_system}:{saved_password}"

    try:
        r = requests.get(f"{YEMOT_API_URL}GetIncomingCalls", params={"token": token}, timeout=10)
        data = r.json()
        calls = data.get('calls', [])
    except Exception as e:
        logging.exception("שגיאה ב-GetIncomingCalls")
        call_states[cli] = {'mode': 'main', 'current_call_id': None}
        return ym_say_and_go_back("t-שגיאה טכנית בשליפת השיחות")

    # סינון השיחה של המשתמש עצמו והשיחות שזה עתה נותקו (כדי למנוע קפיצות ברשימה)
    other_calls = [c for c in calls if c.get('callerIdNum') != cli and c.get('id') not in just_disconnected]
    total_count = len(calls)

    # ================= תפריט ראשי =================
    if state['mode'] == 'main':
        just_disconnected.clear()  # איפוס הניתוקים בכל כניסה לתפריט הראשי
        
        if action is None:
            state['current_call_id'] = None
            if total_count == 0:
                call_states[cli] = {'mode': 'main', 'current_call_id': None}
                return ym_response(f"id_list_message=t-המספר שלך הוא {cli} אין כרגע אף מספר מחובר למערכת\nend=true")
            
            msg = f"t-המספר שלך הוא {cli} מחוברים כרגע למערכת {total_count} מספרים שונים לשמיעת המספרים האחרים הקש 1 לניתוק כל המספרים הקש 3 ליציאה הקש 0"
            return ym_read("action", msg, 1)

        if action == "3":
            call_states[cli] = {'mode': 'main', 'current_call_id': None}
            if total_count == 0:
                return ym_response("id_list_message=t-אין מספרים לנתק\nend=true")
            for call in calls:
                call_id = call.get('id')
                if call_id:
                    requests.get(f"{YEMOT_API_URL}CallAction", params={"token": token, "ids": call_id, "action": "hangup"}, timeout=5)
            return ym_response(f"id_list_message=t-נותקו {total_count} מספרים בהצלחה\nend=true")

        if action == "0":
            call_states[cli] = {'mode': 'main', 'current_call_id': None}
            return ym_response("id_list_message=t-להתראות\nend=true")

        if action == "1":
            state['mode'] = 'sub'
            action = "2" # מפעיל את הצגת השיחה הראשונה

    # ================= תת תפריט =================
    if state['mode'] == 'sub':
        if action == "0":
            call_states[cli] = {'mode': 'main', 'current_call_id': None}
            return ym_response("id_list_message=t-חזרת לתפריט הראשי\nend=true")

        if action == "1":
            # ניתוק השיחה הנוכחית
            call_id_to_disconnect = state.get('current_call_id')
            if call_id_to_disconnect:
                res = requests.get(f"{YEMOT_API_URL}CallAction", params={"token": token, "ids": call_id_to_disconnect, "action": "hangup"}, timeout=5)
                logging.info(f"Disconnect {call_id_to_disconnect}: {res.text}")
                just_disconnected.add(call_id_to_disconnect)
                # הסרת השיחה מהרשימה המקומית כדי שנוכל לעבור לבאה בתור
                other_calls = [c for c in other_calls if c.get('id') != call_id_to_disconnect]
            
            action = "2" # מפעיל את הצגת השיחה הבאה בתור

        if action == "2":
            # מציאת השיחה הבאה בתור
            current_id = state.get('current_call_id')
            next_call = None
            
            if current_id:
                for i, c in enumerate(other_calls):
                    if c.get('id') == current_id:
                        if i + 1 < len(other_calls):
                            next_call = other_calls[i+1]
                        break
            
            if not next_call and other_calls:
                next_call = other_calls[0]

            if not next_call:
                call_states[cli] = {'mode': 'main', 'current_call_id': None}
                return ym_response("id_list_message=t-אין עוד מספרים ברשימה להתראות\nend=true")

            state['current_call_id'] = next_call.get('id')
            phone = next_call.get('callerIdNum', 'לא ידוע')
            duration = next_call.get('duration', 0)
            path = next_call.get('path') or "לא ידועה"

            msg = f"t-המספר {phone} מחובר {duration} שניות ונמצא בשלוחה {path} לניתוק הקש 1 לשמיעת המספר הבא הקש 2 ליציאה הקש 0"
            return ym_read("action", msg, 1)

    call_states[cli] = {'mode': 'main', 'current_call_id': None}
    return ym_say_and_go_back("t-שגיאה לא ידועה")

# ---------- הרצת השרת ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
