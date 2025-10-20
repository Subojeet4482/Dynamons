# === DYNAMONS WORLD - CELESTIAL BOT (SERVER v6.0) ===
# FEATURE: FULL API CONTROL + 24/7 UPTIME PING
# Saari settings (pets, strategy, templates) ab API se control hongi.
# Naye endpoints: /config (GET, POST), /history (GET, DELETE), /ping (GET)

import subprocess
import time
import cv2
import numpy as np
import os
import urllib.request
from flask import Flask, jsonify, request
import threading
from functools import wraps
import sqlite3
import datetime
import json

# ==============================================================================
# === Global Bot Configuration (API se change ho sakti hai) ===
# ==============================================================================

# 1. MY PETS IN SLOTS (Yeh default hai, API se badal sakte hain)
MY_PETS_IN_SLOTS = {
    "slot_1": "plant", "slot_2": "fire", "slot_3": "water", 
    "slot_4": "shadow", "slot_5": "electric"
}

# 2. PET PRIORITY
PET_PRIORITY = {
    "slot_1": 3, "slot_2": 2, "slot_3": 1, 
    "slot_4": 4, "slot_5": 5
}

# 3. ATTACK STRATEGY
ATTACK_STRATEGY = {
    "plant": "slot_2", "fire": "slot_3", "water": "slot_1", "electric": "slot_4",
    "shadow": "slot_1", "diamond": "slot_4", "gold": "slot_3", "ghost": "slot_4", "default": "slot_1"
}

# 4. ELEMENT ADVANTAGE
ELEMENT_ADVANTAGE = {
    "fire": "plant", "water": "fire", "plant": "water", "electric": "shadow",
    "shadow": ["electric", "diamond", "ghost"], "ghost": "shadow",
    "gold": "electric", "diamond": "shadow"
}

# 5. TEMPLATES (Default links, API se badal sakte hain)
TEMPLATES = {
    "arena_button": "https://i.imgur.com/gKDAiX1.png",
    "event_battle_button": "https://i.imgur.com/A6j4L7k.png",
    "normal_world_button": "YAHAN-NORMAL-WORLD-BUTTON-KA-LINK-DAALEIN",
    "normal_world_enemy": "YAHAN-NORMAL-WORLD-ENEMY-KA-LINK-DAALEIN", 
    "switch_pet_prompt": "YAHAN-SPECIFIC-PET-MAANGNE-WALI-SCREEN-KA-LINK-DAALEIN",
    "your_turn_indicator": "https://i.imgur.com/UfS1u3M.png",
    "switch_button": "https://i.imgur.com/Tq9PM5D.png",
    "ok_button": "https://i.imgur.com/N7bVd5L.png",
    "reward_button": "https://i.imgur.com/b9tV4k6.png",
    "you_win_banner": "https://i.imgur.com/Y3JtVb1.png",
    "you_lose_banner": "YAHAN-YOU-LOSE-BANNER-KA-LINK-DAALEIN",
    "enemy_element_plant": "https://i.imgur.com/v5g8Ohr.png",
    "enemy_element_fire": "https://i.imgur.com/sS4t2g1.png",
    "enemy_element_water": "https://i.imgur.com/2mGv9bX.png",
    "enemy_element_electric": "https://i.imgur.com/gK9pW2O.png",
    "enemy_element_shadow": "https://i.imgur.com/Uo2w9b7.png",
    "enemy_element_gold": "https://i.imgur.com/nRhXm44.png",
    "enemy_element_diamond": "https://i.imgur.com/Y8bB2iK.png",
    "enemy_element_ghost": "https://i.imgur.com/4g3d8aQ.png",
    "anchor_pet_plant": "https://i.imgur.com/dDQ1T1J.png",
    "anchor_pet_fire": "https://i.imgur.com/f9O2k5P.png",
    "anchor_pet_water": "https://i.imgur.com/jW4s7hQ.png",
    "anchor_pet_electric": "https://i.imgur.com/O6g3j3b.png",
    "anchor_pet_shadow": "https://i.imgur.com/dZ1j3jK.png",
    "anchor_pet_gold": "YAHAN-APNE-GOLD-PET-KA-IMGUR-LINK-DAALEIN",
    "anchor_pet_diamond": "YAHAN-APNE-DIAMOND-PET-KA-IMGUR-LINK-DAALEIN",
    "anchor_pet_ghost": "YAHAN-APNE-GHOST-PET-KA-IMGUR-LINK-DAALEIN",
    "anchor_attack_slot_1": "https://i.imgur.com/J3T5U7r.png",
    "anchor_attack_slot_2": "https://i.imgur.com/Cbnds3G.png",
    "anchor_attack_slot_3": "https://i.imgur.com/9v4Yo6H.png",
    "anchor_attack_slot_4": "https://i.imgur.com/eW2b1jK.png",
    "popup_daily_reward": "YAHAN-DAILY-REWARD-POPUP-KA-LINK-DAALEIN",
    "popup_special_offer": "YAHAN-SPECIAL-OFFER-POPUP-KA-LINK-DAALEIN",
    "button_close_popup": "YAHAN-POPUP-CLOSE-BUTTON-KA-LINK-DAALEIN",
    "popup_connection_lost": "YAHAN-CONNECTION-LOST-POPUP-KA-LINK-DAALEIN",
    "button_switch_cancel": "YAHAN-SWITCH-CANCEL-BUTTON-KA-LINK-DAALEIN"
}

# ==============================================================================
# === Global App State ===
# ==============================================================================

app = Flask(__name__)
DYNAMIC_COORDS = {}
BOT_RUNNING = False
bot_thread = None
API_KEY = "mandal4482"
BOT_MODE = "idle" # idle, arena, normal

# ==============================================================================
# === Database Functions ===
# ==============================================================================
def setup_database():
    conn = sqlite3.connect('match_history.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, result TEXT,
            my_pet TEXT, enemy_pet TEXT, moves_taken INTEGER, mode TEXT
        )''')
    conn.commit()
    conn.close()
    print("Database 'match_history.db' setup ho gaya hai.")

def log_match_result(result, my_pet="unknown", enemy_pet="unknown", moves=0):
    global BOT_MODE
    try:
        conn = sqlite3.connect('match_history.db')
        c = conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        c.execute("INSERT INTO matches (timestamp, result, my_pet, enemy_pet, moves_taken, mode) VALUES (?, ?, ?, ?, ?, ?)",
                  (timestamp, result, my_pet, enemy_pet, moves, BOT_MODE))
        conn.commit()
        conn.close()
        print(f"Match Logged: Result={result}, Mode={BOT_MODE}")
    except Exception as e:
        print(f"Database log error: {e}")

# ==============================================================================
# === API Key Checker ===
# ==============================================================================
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'X-API-Key' not in request.headers or request.headers['X-API-Key'] != API_KEY:
            return jsonify({"status": "error", "message": "Invalid or missing API key."}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==============================================================================
# === Bot ke Core Functions ===
# ==============================================================================

def setup_templates_folder():
    """ Saare template images ko URLs se download karta hai. """
    global TEMPLATES
    if not os.path.exists("templates"): os.makedirs("templates")
    for name, url in TEMPLATES.items():
        path = f"templates/{name}.png"
        if "YAHAN-" in url or not url.startswith("http"):
            continue # Placeholder ya invalid links ko skip karo
        if not os.path.exists(path):
            print(f"Downloading: {name}.png")
            try: urllib.request.urlretrieve(url, path)
            except Exception as e: print(f"Error downloading {name}: {e}")


def adb_screencap():
    """ ADB se phone ka screenshot leta hai. """
    try:
        with open("screen.png", "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f, check=True)
        return cv2.imread("screen.png", 0)
    except Exception as e:
        print(f"ADB screencap error: {e}. Device connected hai?"); time.sleep(3); return None

def adb_swipe(x1, y1, x2, y2, duration=300):
    """ Screen par swipe karne ke liye. """
    print(f"Swiping from ({x1},{y1}) to ({x2},{y2})")
    subprocess.run(["adb", "shell", "input", "swipe", 
                    str(x1), str(y1), str(x2), str(y2), str(duration)])
    time.sleep(1)


def find_on_screen_adaptive(screen, template_name, threshold=0.8):
    """ Screen par template image ko dhoondhta hai. """
    global TEMPLATES
    path = f"templates/{template_name}.png"
    if not os.path.exists(path):
        if template_name in TEMPLATES and "YAHAN-" not in TEMPLATES[template_name]:
            print(f"Template '{template_name}' missing, download ki koshish...")
            setup_templates_folder() 
        else:
            return None
            
    template = cv2.imread(path, 0)
    if template is None: return None
    
    (tH, tW) = template.shape[:2]
    found = None
    for s in np.linspace(0.8, 1.2, 20)[::-1]:
        try:
            resized = cv2.resize(template, (int(tW * s), int(tH * s)))
            if resized.shape[0] > screen.shape[0] or resized.shape[1] > screen.shape[1]:
                continue
            res = cv2.matchTemplate(screen, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if found is None or max_val > found[0]: found = (max_val, max_loc, s)
        except:
            continue
    if found is None: return None
    (max_val, max_loc, scale) = found
    if max_val >= threshold:
        (startX, startY) = max_loc
        (endX, endY) = (startX + int(tW*scale), startY + int(tH*scale))
        return ((startX + endX) // 2, (startY + endY) // 2)
    return None

def tap(coords):
    if coords:
        print(f"Tapping at: {coords}"); subprocess.run(["adb", "shell", "input", "tap", str(coords[0]), str(coords[1])]); time.sleep(1)

def get_elements(screen):
    global ELEMENT_ADVANTAGE, MY_PETS_IN_SLOTS
    my_element, enemy_element = None, None
    all_elements = set(list(ELEMENT_ADVANTAGE.keys()) + [item for sublist in ELEMENT_ADVANTAGE.values() for item in (sublist if isinstance(sublist, list) else [sublist])])
    for el in all_elements:
        if enemy_element is None and find_on_screen_adaptive(screen, f"enemy_element_{el}"): enemy_element = el
    for pet_element in set(MY_PETS_IN_SLOTS.values()):
         if find_on_screen_adaptive(screen, f"anchor_pet_{pet_element}", 0.9): 
             my_element = pet_element
             break
    return my_element, enemy_element

def locate_buttons(screen):
    global DYNAMIC_COORDS
    if 'attack_slot_1' in DYNAMIC_COORDS: return True
    for slot in ['slot_1', 'slot_2', 'slot_3', 'slot_4']:
        coord = find_on_screen_adaptive(screen, f"anchor_attack_{slot}", 0.85)
        if coord: DYNAMIC_COORDS[f'attack_{slot}'] = coord
    return 'attack_slot_1' in DYNAMIC_COORDS

def scan_available_pets(screen):
    global MY_PETS_IN_SLOTS
    available = {}
    for slot, pet_element in MY_PETS_IN_SLOTS.items():
        coords = find_on_screen_adaptive(screen, f"anchor_pet_{pet_element}", 0.85)
        if coords:
            print(f"Mila: {pet_element} (Slot {slot})"); available[slot] = {"element": pet_element, "coords": coords}
    return available

def handle_battle(screen):
    global DYNAMIC_COORDS, ELEMENT_ADVANTAGE, PET_PRIORITY, ATTACK_STRATEGY
    if not locate_buttons(screen): print("Attack buttons nahi mil rahe."); DYNAMIC_COORDS = {}; return
    
    my_pet_element, enemy_element = get_elements(screen)
    print(f"Mera Pet: {my_pet_element}, Dushman: {enemy_element}")

    is_disadvantage = False
    advantage_check = ELEMENT_ADVANTAGE.get(enemy_element)
    if isinstance(advantage_check, list): is_disadvantage = my_pet_element in advantage_check
    else: is_disadvantage = advantage_check == my_pet_element

    if is_disadvantage and my_pet_element is not None:
        print(f"Mera '{my_pet_element}' pet kamzor hai... Switch check kar raha hu...")
        if switch_loc := find_on_screen_adaptive(screen, "switch_button"):
            tap(switch_loc); time.sleep(1.5); switch_screen = adb_screencap();
            if switch_screen is None: return
            
            available_pets_on_screen = scan_available_pets(switch_screen)
            if available_pets_on_screen:
                best_option_slot = None; lowest_priority = float('inf')
                for slot, pet_data in available_pets_on_screen.items():
                    if pet_data['element'] == my_pet_element: continue
                    
                    pet_advantage_check = ELEMENT_ADVANTAGE.get(pet_data['element'])
                    has_advantage = False
                    if isinstance(pet_advantage_check, list): has_advantage = enemy_element in pet_advantage_check
                    else: has_advantage = pet_advantage_check == enemy_element
                    
                    current_priority = PET_PRIORITY.get(slot, 99)
                    
                    if has_advantage and current_priority < lowest_priority:
                        lowest_priority = current_priority; best_option_slot = slot
                
                if best_option_slot:
                    pet_to_tap = available_pets_on_screen[best_option_slot]
                    print(f"Decision: '{pet_to_tap['element']}' ko bhej raha hu.")
                    tap(pet_to_tap['coords']); time.sleep(3); return
            
            print("Koi behtar pet nahi mila. Wapas ja raha hu.")
            if cancel_loc := find_on_screen_adaptive(switch_screen, "button_switch_cancel"): tap(cancel_loc)
            else: tap(switch_loc); time.sleep(1.5)
        else:
            print("Switch button nahi mila. Attack kar raha hu.")

    print("Decision: Attack kar raha hu.")
    attack_slot = ATTACK_STRATEGY.get(enemy_element, ATTACK_STRATEGY["default"])
    tap(DYNAMIC_COORDS.get(f'attack_{attack_slot}')); time.sleep(3.5)

# ==============================================================================
# === Bot ka Main Loop ===
# ==============================================================================

def bot_logic_loop():
    global BOT_RUNNING, DYNAMIC_COORDS, BOT_MODE
    print(f"Bot ka main loop (v6.0) background mein start ho gaya hai... Mode: {BOT_MODE}")
    
    current_my_pet = "unknown"; current_enemy_pet = "unknown"; moves_taken = 0
    
    while BOT_RUNNING:
        screen = adb_screencap()
        if screen is None: print("Screen nahi mil rahi. Loop pause."); time.sleep(5); continue
        
        try:
            # --- Part 1: Common Handlers (Popups, Match End) ---
            if (loc := find_on_screen_adaptive(screen, "popup_connection_lost", 0.85)):
                print("Connection lost!"); tap(find_on_screen_adaptive(screen, "ok_button", 0.8)); time.sleep(5); continue
            if (loc := find_on_screen_adaptive(screen, "popup_daily_reward", 0.85)):
                print("Daily reward!"); tap(loc); time.sleep(2); continue
            if (loc := find_on_screen_adaptive(screen, "popup_special_offer", 0.85)):
                print("Special offer!"); tap(find_on_screen_adaptive(screen, "button_close_popup", 0.8)); time.sleep(2); continue

            # Match End Logic
            if (loc := find_on_screen_adaptive(screen, "reward_button", 0.8)) or find_on_screen_adaptive(screen, "you_win_banner", 0.8): 
                print("Match Jeet Gaye! Result database mein save kar raha hoon.")
                log_match_result("WIN", current_my_pet, current_enemy_pet, moves_taken)
                tap(loc or find_on_screen_adaptive(screen, "ok_button", 0.8))
                DYNAMIC_COORDS = {}; moves_taken = 0; time.sleep(2); continue
                
            if (loc := find_on_screen_adaptive(screen, "you_lose_banner", 0.8)):
                print("Match Haar Gaye. Result database mein save kar raha hoon.")
                log_match_result("LOSS", current_my_pet, current_enemy_pet, moves_taken)
                tap(find_on_screen_adaptive(screen, "ok_button", 0.8))
                DYNAMIC_COORDS = {}; moves_taken = 0; time.sleep(2.5); continue
                
            if (loc := find_on_screen_adaptive(screen, "ok_button", 0.8)): 
                print("OK button mila (Match ke bahar)."); tap(loc); time.sleep(2.5); continue

            # Battle Turn (Common)
            if find_on_screen_adaptive(screen, "your_turn_indicator", 0.7): 
                print("Meri baari hai...")
                my_pet, enemy_pet = get_elements(screen)
                if my_pet: current_my_pet = my_pet
                if enemy_pet: current_enemy_pet = enemy_pet
                moves_taken += 1
                handle_battle(screen)
                continue

            # --- Part 2: Mode-Specific Logic ---
            
            if BOT_MODE == 'arena':
                if (loc := find_on_screen_adaptive(screen, "event_battle_button")): 
                    print("Event Battle button mila."); tap(loc); time.sleep(2); continue
                if (loc := find_on_screen_adaptive(screen, "arena_button")): 
                    print("Arena button mila."); tap(loc); time.sleep(2); continue
            
            elif BOT_MODE == 'normal':
                if (loc := find_on_screen_adaptive(screen, "switch_pet_prompt", 0.85)):
                    print("Game specific pet maang raha hai! Bot STOP ho raha hai.")
                    BOT_RUNNING = False
                    BOT_MODE = "idle"
                    continue

                if (loc := find_on_screen_adaptive(screen, "normal_world_button", 0.8)):
                    print("Normal World button mila. Enter kar raha hoon..."); tap(loc); time.sleep(3); continue
                
                if (loc := find_on_screen_adaptive(screen, "normal_world_enemy", 0.8)):
                    print("Saamne dushman mila! Fight shuru kar raha hoon..."); tap(loc); time.sleep(3); continue
                
                print("Normal World mein kuch nahi dikh raha... Aage badh raha hoon (Swipe Up).")
                # (x1, y1, x2, y2) -> Center-bottom se Center-top
                adb_swipe(540, 1500, 540, 1000, 500) 
                time.sleep(2) 
                continue

            print(f"Waiting for game state... (Mode: {BOT_MODE})"); time.sleep(2)
            
        except Exception as e:
            print(f"Bot loop mein error aaya: {e}"); time.sleep(5)

    print(f"Bot ka main loop (Mode: {BOT_MODE}) API se stop kar diya gaya hai.")

# ==============================================================================
# === API ENDPOINTS (Updated /start) ===
# ==============================================================================

@app.route('/start', methods=['GET'])
@require_api_key
def start_bot():
    global BOT_RUNNING, bot_thread, BOT_MODE
    if BOT_RUNNING:
        return jsonify({"status": "error", "message": "Bot pehle se hi chal raha hai."})
        
    mode = request.args.get('mode', 'arena') # Default 'arena'
    if mode not in ['arena', 'normal']:
        return jsonify({"status": "error", "message": "Invalid mode. Sirf 'arena' ya 'normal' use karein."}), 400
        
    BOT_MODE = mode
    BOT_RUNNING = True
    bot_thread = threading.Thread(target=bot_logic_loop)
    bot_thread.start()
    return jsonify({"status": "success", "message": f"Bot (v6.0) '{BOT_MODE}' mode mein start ho gaya hai."})

@app.route('/stop', methods=['GET'])
@require_api_key
def stop_bot():
    global BOT_RUNNING, bot_thread, BOT_MODE
    if not BOT_RUNNING:
        return jsonify({"status": "error", "message": "Bot pehle se hi ruka hua hai."})
    
    BOT_RUNNING = False
    BOT_MODE = "idle"
    
    if bot_thread:
        print("Bot thread ko stop karne ka wait kar raha hoon (max 2 sec)...")
        bot_thread.join(timeout=2.0)
    
    return jsonify({"status": "success", "message": "Bot stop kar diya gaya hai."})

@app.route('/status', methods=['GET'])
@require_api_key
def get_status():
    global BOT_MODE
    if BOT_RUNNING:
        return jsonify({"status": "running", "mode": BOT_MODE})
    else:
        return jsonify({"status": "stopped", "mode": "idle"})

# ==============================================================================
# === NAYE API ENDPOINTS (Config & History) ===
# ==============================================================================

@app.route('/config', methods=['GET'])
@require_api_key
def get_config():
    """ Bot ki current configuration ko return karta hai. """
    global MY_PETS_IN_SLOTS, PET_PRIORITY, ATTACK_STRATEGY, ELEMENT_ADVANTAGE, TEMPLATES
    return jsonify({
        "my_pets_in_slots": MY_PETS_IN_SLOTS,
        "pet_priority": PET_PRIORITY,
        "attack_strategy": ATTACK_STRATEGY,
        "element_advantage": ELEMENT_ADVANTAGE,
        "templates": TEMPLATES
    })

@app.route('/config', methods=['POST'])
@require_api_key
def set_config():
    """ Bot ki configuration ko JSON data se update karta hai. """
    global MY_PETS_IN_SLOTS, PET_PRIORITY, ATTACK_STRATEGY, TEMPLATES, ELEMENT_ADVANTAGE
    
    if BOT_RUNNING:
        return jsonify({"status": "error", "message": "Bot chal raha hai. Config change karne ke liye pehle /stop karein."}), 400

    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Koi JSON data nahi mila."}), 400
    
    updated_any = False
    
    if 'my_pets_in_slots' in data:
        if isinstance(data['my_pets_in_slots'], dict):
            MY_PETS_IN_SLOTS = data['my_pets_in_slots']
            print("Config update: MY_PETS_IN_SLOTS updated.")
            updated_any = True
        else: return jsonify({"status": "error", "message": "'my_pets_in_slots' ek object (dict) hona chahiye."}), 400

    if 'pet_priority' in data:
        if isinstance(data['pet_priority'], dict):
            PET_PRIORITY = data['pet_priority']
            print("Config update: PET_PRIORITY updated.")
            updated_any = True
        else: return jsonify({"status": "error", "message": "'pet_priority' ek object (dict) hona chahiye."}), 400

    if 'attack_strategy' in data:
        if isinstance(data['attack_strategy'], dict):
            ATTACK_STRATEGY = data['attack_strategy']
            print("Config update: ATTACK_STRATEGY updated.")
            updated_any = True
        else: return jsonify({"status": "error", "message": "'attack_strategy' ek object (dict) hona chahiye."}), 400
            
    if 'element_advantage' in data:
        if isinstance(data['element_advantage'], dict):
            ELEMENT_ADVANTAGE = data['element_advantage']
            print("Config update: ELEMENT_ADVANTAGE updated.")
            updated_any = True
        else: return jsonify({"status": "error", "message": "'element_advantage' ek object (dict) hona chahiye."}), 400

    if 'templates' in data:
        if isinstance(data['templates'], dict):
            TEMPLATES = data['templates']
            print("Config update: TEMPLATES updated. Naye templates download kiye ja rahe hain...")
            try:
                setup_templates_folder() # Naye links ko download karo
                print("Naye templates download ho gaye.")
            except Exception as e:
                print(f"Template download error: {e}")
                return jsonify({"status": "error", "message": f"Templates update hue, lekin download mein error: {e}"}), 500
            updated_any = True
        else: return jsonify({"status": "error", "message": "'templates' ek object (dict) hona chahiye."}), 400

    if updated_any:
        return jsonify({"status": "success", "message": "Configuration update ho gaya."})
    else:
        return jsonify({"status": "info", "message": "Data mila, lekin koi valid config key nahi mili."})

@app.route('/history', methods=['GET'])
@require_api_key
def get_history():
    """ Match history ke pichle 50 results return karta hai. """
    try:
        conn = sqlite3.connect('match_history.db')
        conn.row_factory = sqlite3.Row # Taaki results dict jaise milein
        c = conn.cursor()
        c.execute("SELECT * FROM matches ORDER BY id DESC LIMIT 50") # Last 50
        rows = c.fetchall()
        conn.close()
        history = [dict(row) for row in rows]
        return jsonify({"status": "success", "history": history})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database read error: {e}"}), 500

@app.route('/history', methods=['DELETE'])
@require_api_key
def clear_history():
    """ Poori match history ko database se delete karta hai. """
    if BOT_RUNNING:
        return jsonify({"status": "error", "message": "Bot chal raha hai. History clear karne ke liye pehle /stop karein."}), 400
        
    try:
        conn = sqlite3.connect('match_history.db')
        c = conn.cursor()
        c.execute("DELETE FROM matches") # Saara data delete karo
        conn.commit()
        c.execute("VACUUM") # Database file size ko chhota karo
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Match history clear ho gayi hai."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database clear error: {e}"}), 500


# ==============================================================================
# === NAYA PING ENDPOINT (24/7 Trick Ke Liye) ===
# ==============================================================================

@app.route('/ping', methods=['GET'])
def ping_server():
    """
    Yeh ek unprotected endpoint hai taaki UptimeRobot jaisi service
    ise ping karke server ko 24/7 active rakh sake.
    """
    return jsonify({"status": "alive", "message": "Bot server is awake."}), 200

# ==============================================================================
# === Server ko Start Karne ka Code ===
# ==============================================================================

if __name__ == "__main__":
    print("Template images download ki jaa rahi hain...")
    setup_templates_folder()
    print("Database setup kiya jaa raha hai...")
    setup_database()
    print("Template setup poora hua.")
    
    port = int(os.environ.get('PORT', 5000)) # Render ke liye zaroori
    
    # App ka naam 'main' se 'app' mein badlo, taaki 'gunicorn main:app' chale
    # Yeh line zaroori nahi hai agar `app = Flask(__name__)` upar hai.
    
    print(f"Bot Server v6.0 (Full API) shuru ho raha hai... http://0.0.0.0:{port}")
    print(f"API KEY: {API_KEY}")
    print("="*30)
    print("Main Endpoints:")
    print(f"  GET /status")
    print(f"  GET /start?mode=arena")
    print(f"  GET /start?mode=normal")
    print(f"  GET /stop")
    print("Config Endpoints:")
    print(f"  GET /config")
    print(f"  POST /config (with JSON body)")
    print("History Endpoints:")
    print(f"  GET /history")
    print(f"  DELETE /history")
    print("Uptime Endpoint:")
    print(f"  GET /ping")
    print("="*30)
    
    # Server ko `python main.py` se chalaane ke liye:
    app.run(host='0.0.0.0', port=port, debug=False)
