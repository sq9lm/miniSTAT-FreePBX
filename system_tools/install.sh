#!/bin/bash

echo "🔧 Instalacja środowiska dla miniSTAT..."

# Aktualizacja i instalacja pakietów systemowych
apt update
apt install -y python3 python3-pip python3-venv

# Przejście do katalogu aplikacji
cd /root/miniSTAT-FreePBX || exit 1

# Tworzenie środowiska wirtualnego
python3 -m venv venv
source venv/bin/activate

# Instalacja zależności
pip install flask flask-login psutil

# Tworzenie pliku requirements.txt
pip freeze > requirements.txt

echo "✅ Instalacja zakończona."
echo "ℹ️ Uruchom aplikację: source venv/bin/activate && python3 app.py"
