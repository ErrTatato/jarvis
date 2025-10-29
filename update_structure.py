"""update_structure.py - Aggiorna directory structure JARVIS"""

import os
from pathlib import Path

# Cartelle MANCANTI da creare
NEW_DIRECTORIES = [
    'services/device_control',
    'services/geolocation',
    'services/food_delivery',
    'services/gaming',
    'services/fitness',
    'services/smart_home',
    'services/finance',
    'services/social_media',
    'services/news',
    'services/productivity',
    'utils',
    'logs',
]

def create_directories():
    """Crea tutte le cartelle mancanti"""
    for directory in NEW_DIRECTORIES:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Creata: {directory}/")

def create_init_files():
    """Crea __init__.py dove manca"""
    init_dirs = [
        'services/device_control',
        'services/geolocation',
        'services/food_delivery',
        'services/gaming',
        'services/fitness',
        'services/smart_home',
        'services/finance',
        'services/social_media',
        'services/news',
        'services/productivity',
        'utils',
    ]
    
    for directory in init_dirs:
        init_file = Path(directory) / '__init__.py'
        if not init_file.exists():
            init_file.touch()
            print(f"✅ Creato: {directory}/__init__.py")

def create_service_files():
    """Crea i file base per ogni servizio"""
    
    services = {
        'device_control': ['android_adb.py', 'ios_api.py', 'device_functions.py'],
        'geolocation': ['gps_service.py', 'maps_api.py', 'traffic_service.py', 'geo_functions.py'],
        'food_delivery': ['uber_eats.py', 'deliveroo.py', 'glovo.py', 'recipes.py', 'food_functions.py'],
        'gaming': ['league_of_legends.py', 'valorant.py', 'steam.py', 'twitch.py', 'gaming_functions.py'],
        'fitness': ['strava.py', 'tracking.py', 'calories.py', 'fitness_functions.py'],
        'smart_home': ['home_base.py', 'devices.py', 'energy.py', 'home_functions.py'],
        'finance': ['crypto.py', 'stocks.py', 'banking.py', 'finance_functions.py'],
        'social_media': ['instagram.py', 'twitter.py', 'tiktok.py', 'social_functions.py'],
        'news': ['news_api.py', 'fact_check.py', 'news_functions.py'],
        'productivity': ['time_tracking.py', 'pomodoro.py', 'notes.py', 'productivity_functions.py'],
    }
    
    for service, files in services.items():
        for file in files:
            filepath = Path(f'services/{service}/{file}')
            if not filepath.exists():
                filepath.write_text(f'"""services/{service}/{file}"""\n\n# TODO: Implementare\n')
                print(f"✅ Creato: services/{service}/{file}")

if __name__ == '__main__':
    print("🚀 Aggiornamento directory structure JARVIS...\n")
    print("📁 Creazione cartelle mancanti...\n")
    create_directories()
    print()
    
    print("📄 Creazione __init__.py...\n")
    create_init_files()
    print()
    
    print("🔧 Creazione file servizi...\n")
    create_service_files()
    print()
    
    print("✅ STRUTTURA AGGIORNATA PERFETTAMENTE!")
    print("\n📊 Prossimi step:")
    print("1. Riempi i file .py con il codice")
    print("2. Aggiorna config/.env con le API keys")
    print("3. Avvia: python main.py")
