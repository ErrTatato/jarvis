#!/usr/bin/env python3
"""
test_porcupine.py - Test rapido per verificare che Porcupine funzioni
"""
import os
import sys

print("=" * 80)
print("TEST PORCUPINE - Verifica Configurazione")
print("=" * 80)
print()

# Test 1: Verifica variabile d'ambiente
print("1. Verifica PICOVOICE_ACCESS_KEY...")
access_key = os.environ.get("PICOVOICE_ACCESS_KEY")

if not access_key:
    print("   ❌ ERRORE: Variabile d'ambiente non trovata!")
    print()
    print("   Hai eseguito questo comando?")
    print()
    if sys.platform == "win32":
        print('   setx PICOVOICE_ACCESS_KEY "la-tua-chiave"')
        print()
        print("   Poi RIAVVIA VSCode!")
    else:
        print('   export PICOVOICE_ACCESS_KEY="la-tua-chiave"')
        print("   (e aggiungi al ~/.bashrc o ~/.zshrc)")
    print()
    sys.exit(1)

print(f"   ✅ Trovata: {access_key[:10]}...{access_key[-5:]}")
print()

# Test 2: Verifica import pvporcupine
print("2. Verifica import pvporcupine...")
try:
    import pvporcupine
    print(f"   ✅ pvporcupine importato con successo")
    
    # Prova a ottenere la versione (se disponibile)
    try:
        version = pvporcupine.__version__
        print(f"   ✅ Versione: {version}")
    except AttributeError:
        # Alcune versioni non hanno __version__
        print(f"   ℹ️  Versione non rilevabile (normale per alcune versioni)")
        
except ImportError:
    print("   ❌ ERRORE: pvporcupine non installato!")
    print()
    print("   Esegui: pip install pvporcupine")
    print()
    sys.exit(1)
print()

# Test 3: Verifica wake words disponibili
print("3. Wake words built-in disponibili:")
try:
    keywords = pvporcupine.KEYWORDS
    jarvis_found = False
    
    for kw in sorted(keywords):
        if kw == "jarvis":
            print(f"  ✅ {kw} ← QUESTA USEREMO!")
            jarvis_found = True
        else:
            print(f"     {kw}")
    
    if not jarvis_found:
        print()
        print("   ⚠️  WARNING: 'jarvis' non trovata nella lista!")
        print("   Potresti dover creare una wake word custom.")
        
except Exception as e:
    print(f"   ⚠️  Non riesco a leggere le keywords: {e}")
    print("   (Procediamo comunque con il test)")
print()

# Test 4: Prova a creare istanza Porcupine
print("4. Test creazione istanza Porcupine con wake word 'jarvis'...")
try:
    porcupine = pvporcupine.create(
        access_key=access_key,
        keywords=["jarvis"]
    )
    print(f"   ✅ Porcupine creato con successo!")
    print(f"   ✅ Frame length: {porcupine.frame_length}")
    print(f"   ✅ Sample rate: {porcupine.sample_rate} Hz")
    
    # Cleanup
    porcupine.delete()
    print(f"   ✅ Cleanup completato")
    
except Exception as e:
    print(f"   ❌ ERRORE: {e}")
    print()
    print("   Possibili cause:")
    print("   - Access key non valida (controlla su https://console.picovoice.ai/)")
    print("   - Wake word 'jarvis' non disponibile per il tuo account")
    print("   - Problema di rete")
    print("   - Piattaforma non supportata")
    print()
    
    # Prova con altra wake word di test
    print("   Provo con wake word alternativa 'porcupine'...")
    try:
        porcupine_test = pvporcupine.create(
            access_key=access_key,
            keywords=["porcupine"]
        )
        print(f"   ✅ Funziona con 'porcupine'!")
        print(f"   ℹ️  Puoi usare questa temporaneamente e creare 'jarvis' custom dopo.")
        porcupine_test.delete()
    except Exception as e2:
        print(f"   ❌ Anche 'porcupine' fallisce: {e2}")
        print()
        print("   Verifica la tua Access Key su: https://console.picovoice.ai/")
        sys.exit(1)
    
    sys.exit(1)

print()
print("=" * 80)
print("✅ TUTTI I TEST SUPERATI!")
print("=" * 80)
print()
print("Porcupine è configurato correttamente! 🎉")
print()
print("PROSSIMI PASSI:")
print("  1. Avvia il server: python server_webrtc.py")
print("  2. In un ALTRO terminale, avvia: python wake_listener.py")
print("  3. Dì 'Jarvis' al microfono e JARVIS si attiverà!")
print()
print("NOTA: Servono DUE terminali separati contemporaneamente.")
print()