# Wersja 2.42
# Autor: Łukasz Misiura | lmisiura@gmail.com

# systemowe / standardowe
import os
import re
import time
from io import BytesIO
from pathlib import Path

# zewnętrzne
import psutil
import csv
import subprocess
from flask import Flask, jsonify, request, send_file, Response, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import lru_cache

# Inicjalizacja aplikacji Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Zmień na coś bezpiecznego!

# Inicjalizacja logowania
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- do obliczania TX/RX Mb/s ---
_prev_net = {
    "t": time.time(),
    "tx": psutil.net_io_counters().bytes_sent,
    "rx": psutil.net_io_counters().bytes_recv
}

# Katalog logów Asteriska
ASTERISK_LOG_DIR = "/var/log/asterisk"
CSV_FILE_PATH = '/root/miniSTAT-FreePBX/dane/contact.csv'

@app.route("/api/system")
@login_required
def api_system():
    cpu  = psutil.cpu_percent(interval=0.2)
    ram  = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    now  = time.time()
    io   = psutil.net_io_counters()
    dt   = now - _prev_net["t"] or 1
    tx_mbps = round((io.bytes_sent - _prev_net["tx"]) * 8 / 1024 / 1024 / dt, 2)
    rx_mbps = round((io.bytes_recv - _prev_net["rx"]) * 8 / 1024 / 1024 / dt, 2)
    _prev_net.update(t=now, tx=io.bytes_sent, rx=io.bytes_recv)

    return jsonify({"cpu": cpu, "ram": ram, "disk": disk,
                    "tx": tx_mbps, "rx": rx_mbps})

@app.route("/api/logs/files")
@login_required
def get_log_files():
    try:
        files = sorted([f for f in os.listdir(ASTERISK_LOG_DIR) if os.path.isfile(os.path.join(ASTERISK_LOG_DIR, f))])
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/logs/view")
@login_required
def view_log_filtered():
    filename = request.args.get("filename")
    try:
        lines = int(request.args.get("lines", 300))
        lines = min(lines, 1000)
    except ValueError:
        lines = 300

    level = request.args.get("level", "")
    filter_text = request.args.get("filter", "")

    filepath = os.path.join(ASTERISK_LOG_DIR, filename)
    if not os.path.isfile(filepath):
        return "Plik nie istnieje", 404

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if lines > 0 else all_lines
            filtered = []
            for line in recent_lines:
                if level and level != "ALL" and not re.search(rf"\b{re.escape(level)}\b", line, re.IGNORECASE):
                    continue
                if filter_text and filter_text.lower() not in line.lower():
                    continue
                filtered.append(line)
        return render_template("log_iframe.html", log_lines=filtered)
    except Exception as e:
        return f"Błąd odczytu logu: {e}", 500

@app.route("/api/logs/download")
@login_required
def download_filtered_log():
    filename = request.args.get("filename")
    try:
        lines = int(request.args.get("lines", 300))
        lines = min(lines, 1000)
    except ValueError:
        lines = 300

    level = request.args.get("level", "")
    filter_text = request.args.get("filter", "")

    filepath = os.path.join(ASTERISK_LOG_DIR, filename)
    if not os.path.isfile(filepath):
        return "Plik nie istnieje", 404

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if lines > 0 else all_lines
            filtered = []
            for line in recent_lines:
                if level and level != "ALL" and not re.search(rf"\\b{re.escape(level)}\\b", line, re.IGNORECASE):
                    continue
                if filter_text and filter_text.lower() not in line.lower():
                    continue
                filtered.append(line)

        buffer = BytesIO("".join(filtered).encode("utf-8"))
        buffer.seek(0)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''filtered_{filename}"
        }
        return Response(buffer, mimetype="text/plain", headers=headers)
    except Exception as e:
        return f"Błąd pobierania pliku: {e}", 500


# Prosty model użytkownika (na potrzeby przykładu)
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

users = {
    1: User(1, 'misiu', 'passw0rd'), # main admin
    2: User(2, 'kris', 'kris$3122')  
}

@login_manager.user_loader
def load_user(user_id):
    return users.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = next((u for u in users.values() if u.username == username), None)
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Nieprawidłowe dane logowania')
    return render_template('login.html', error=None)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Załaduj książkę telefoniczną
phone_book = {}
try:
    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) == 2:
                exten, nazwa = row
                phone_book[exten] = nazwa
except FileNotFoundError:
    print(f"Plik {CSV_FILE_PATH} nie został znaleziony.")
except Exception as e:
    print(f"Błąd przy wczytywaniu pliku CSV: {e}")

def get_asterisk_extensions_status():
    result = subprocess.run(['asterisk', '-rx', 'pjsip show endpoints'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lines = result.stdout.splitlines()

    extensions = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Endpoint:"):
            parts = line.split()
            extension_number = parts[1].split('/')[0].strip()

            # Pomijamy nienumeryczne endpointy (np. <Endpoint>)
            if not extension_number.isdigit():
                i += 1
                continue

            ext = {
                'extension': extension_number,
                'status': 'Unavailable',
                'time': None,
                'contact': None,
                'contact_ip': None,
                'avail_ms': None,
                'caller_id': None,
                'channel_type': None,
                'exten': None,
                'raw_clcid': None,
                'name': phone_book.get(extension_number, '')
            }

            if "In use" in line:
                ext['status'] = 'In use'
            elif "Not in use" in line:
                ext['status'] = 'Not in use'

            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("Endpoint:"):
                sub_line = lines[j].strip()

                if sub_line.startswith("Contact:"):
                    ext['contact'] = sub_line.split("Contact:")[1].strip()
                    match_ip = re.search(r'@(\d{1,3}(?:\.\d{1,3}){3}:\d+)', ext['contact'])
                    if match_ip:
                        ext['contact_ip'] = match_ip.group(1)

                    match_avail = re.search(r'Avail\s+([\d.]+)', ext['contact'])
                    if match_avail:
                        ext['avail_ms'] = f"{match_avail.group(1)} ms"
                        if ext['status'] != 'In use':
                            ext['status'] = 'Available'
                    elif ext['status'] != 'In use':
                        ext['status'] = 'Available'

                elif sub_line.startswith("Channel:"):
                    if '/' in sub_line:
                        parts = sub_line.split('/')
                        if len(parts) > 2:
                            ext['channel_type'] = parts[2].split()[0]
                        duration = re.search(r'(\d{2}:\d{2}:\d{2})', sub_line)
                        if duration:
                            ext['time'] = duration.group(1)

                elif sub_line.startswith("Exten:"):
                    exten_val = sub_line.split("Exten:")[1].strip().split()[0]
                    ext['exten'] = exten_val
                    ext['name'] = phone_book.get(exten_val, ext['name'])

                elif sub_line.startswith("CLCID:"):
                    raw = sub_line.split("CLCID:")[1].strip()
                    ext['raw_clcid'] = raw
                    if raw and raw != '"" <>':
                        match_named = re.search(r'"([^"]*)"\s*<([^>]*)>', raw)
                        if match_named:
                            ext['caller_id'] = f"{match_named.group(1)} <{match_named.group(2)}>"
                        else:
                            match_only_number = re.search(r'<([^>]*)>', raw)
                            if match_only_number:
                                ext['caller_id'] = f"<{match_only_number.group(1)}>"

                j += 1

            # Formatowanie końcowego caller_id
            caller_id_parts = []
            if ext['caller_id']:
                caller_id_parts.append(ext['caller_id'])
            if ext['exten'] and ext['exten'] != 's':
                caller_id_parts.append(ext['exten'])
            if ext['raw_clcid'] and ext['raw_clcid'] != '"" <>':
                caller_id_parts.append(f"CLCID: {ext['raw_clcid']}")
            if ext['channel_type']:
                caller_id_parts.insert(0, ext['channel_type'])

            if ext['exten'] == 's' and ext['raw_clcid'] and ext['raw_clcid'] != '"" <>':
                ext['caller_id'] = f"{ext['channel_type']}, {ext['caller_id']}"
            elif ext['exten'] and not ext['caller_id']:
                ext['caller_id'] = f"{ext['channel_type']}, {ext['exten']}"
            elif not ext['caller_id'] and ext['channel_type']:
                ext['caller_id'] = ext['channel_type']
            elif not ext['exten'] and ext['raw_clcid'] and ext['raw_clcid'] != '"" <>':
                ext['caller_id'] = f"Exten, CLCID: {ext['raw_clcid']}"
            elif not ext['exten'] and ext['channel_type']:
                ext['caller_id'] = ext['channel_type']
            elif caller_id_parts:
                ext['caller_id'] = ", ".join(caller_id_parts)

            extensions.append(ext)
            i = j
        else:
            i += 1

    return extensions

@app.route('/api/uptime')
@login_required
def api_uptime():
    def format_uptime(seconds):
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{days}d {hours:02}h {minutes:02}m {secs:02}s"

    try:
        # System uptime z /proc/uptime
        with open("/proc/uptime", "r") as f:
            uptime_sec = float(f.readline().split()[0])
        sys_uptime = format_uptime(int(uptime_sec))

        # Asterisk uptime z 'core show uptime'
        result = subprocess.run(
            ['asterisk', '-rx', 'core show uptime'],
            stdout=subprocess.PIPE, text=True
        )
        ast_uptime = "?"
        for line in result.stdout.splitlines():
            if "System uptime:" in line:
                ast_uptime = line.split("System uptime:")[1].strip()
                break

        return jsonify(system=sys_uptime, asterisk=ast_uptime)
    except Exception as e:
        return jsonify(error=str(e)), 500

# ---------- status trunków + użytkowników ----------
@lru_cache(maxsize=1)
def trunks_status():
    """zwraca (online, offline); wynik trzymamy 5 s w cache"""
    out = subprocess.run(['asterisk', '-rx', 'sip show peers'],
                         stdout=subprocess.PIPE, text=True).stdout
    on = off = 0
    for ln in out.splitlines():
        if '(Unspecified)' in ln or 'UNKNOWN' in ln:
            continue
        if 'OK (' in ln:
            on += 1
        elif 'UNREACHABLE' in ln:
            off += 1
    return on, off
#trunks_status.cache_clear.__defaults__ = (5,)   # TTL nieistotny dla Py 3.7; usuń jeśli błąd

@app.route('/api/asterisk')
@login_required
def api_asterisk():
    exts = get_asterisk_extensions_status()
    ext_online = sum(1 for e in exts if e.get('contact_ip'))
    # traktujemy zarówno 'Busy', jak i 'In use' jako zajęty
    ext_busy   = sum(1 for e in exts if e.get('status') in ('Busy', 'In use'))
    ext_off    = len(exts) - ext_online
    trunk_on, trunk_off = trunks_status()
    return jsonify(ext_online=ext_online, ext_busy=ext_busy, ext_off=ext_off,
                   trunk_on=trunk_on, trunk_off=trunk_off)

@app.route('/api/extensions')
@login_required
def api_extensions():
    data = get_asterisk_extensions_status()
    return jsonify(data)

def get_user_ip():
    ip_address = request.headers.get('X-Forwarded-For')
    if ip_address:
        ip_address = ip_address.split(',')[0].strip()
    else:
        ip_address = request.headers.get('X-Real-IP')
        if not ip_address:
            ip_address = request.remote_addr
    return ip_address

@app.route('/logs/<filename>')
@login_required
def view_log(filename):
    # Zabezpieczenie przed przejściem katalogów
    if '..' in filename or '/' in filename:
        return "Nieprawidłowa nazwa pliku", 400

    filepath = os.path.join(ASTERISK_LOG_DIR, filename)
    if not os.path.isfile(filepath):
        return "Plik nie istnieje", 404

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.readlines()
    except Exception as e:
        return f"Błąd odczytu pliku: {e}", 500

    user_login = current_user.username
    user_ip = get_user_ip()
    return render_template('view_log.html', filename=filename, log_content=content, login=user_login, moje_ip=user_ip)

@app.route('/')
@login_required
def index():
    user_login = current_user.username
    user_ip = get_user_ip()
    return render_template('index.html', login=user_login, moje_ip=user_ip)

@app.route('/status')
@login_required
def status():
    user_login = current_user.username
    user_ip = get_user_ip()
    return render_template('status.html', login=user_login, moje_ip=user_ip)

@app.route('/logs')
@login_required
def logs():
    try:
        log_files = sorted([f for f in os.listdir(ASTERISK_LOG_DIR) if f.endswith('')])
    except Exception as e:
        log_files = []
        print(f"Błąd przy listowaniu logów: {e}")
    user_login = current_user.username
    user_ip = get_user_ip()
    return render_template('logs.html', log_files=log_files, login=user_login, moje_ip=user_ip)

from io import BytesIO

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)