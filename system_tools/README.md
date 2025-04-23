# miniSTAT – Instrukcja instalacji i uruchomienia jako usługa systemowa  
**Autor: Łukasz Misiura | lmisiura@gmail.com**

---

## 📦 Wymagania systemowe
- Python 3
- `systemd` (np. Ubuntu, Debian)
- Pakiet `python3-venv` (jeśli nie masz: `apt install python3-venv`)

---

## 🛠️ Instalacja

1. Skopiuj repozytorium lub katalog do `/root/miniSTAT-FreePBX`

2. Uruchom skrypt:
```bash
chmod +x install.sh
./install.sh
```

---

## ▶️ Uruchamianie aplikacji ręcznie
```bash
cd /root/miniSTAT-FreePBX
source venv/bin/activate
python3 app.py
```

---

## ⚙️ Uruchamianie jako usługa systemowa

### 1. Stwórz plik `/etc/systemd/system/ministat.service`
```ini
[Unit]
Description=miniSTAT Flask App
After=network.target

[Service]
User=root
WorkingDirectory=/root/miniSTAT-FreePBX
ExecStart=/root/miniSTAT-FreePBX/venv/bin/python3 /root/miniSTAT-FreePBX/app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 2. Włącz i uruchom usługę
```bash
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable ministat.service
systemctl start ministat.service
```

### 3. Sprawdź status
```bash
systemctl status ministat.service
```

---

## ✅ Gotowe!
Aplikacja będzie działać na porcie `5000`:
```
http://<IP_SERWERA>:5000
```
