from flask import Flask, request, jsonify, send_from_directory
import jarvis_ai
import ssl
import os
import base64

app = Flask(__name__, static_url_path='', static_folder='client')

# Endpoint per trascrivere e rispondere
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    audio_chunk = data.get("audio_base64", None)
    if not audio_chunk:
        return jsonify({"error": "Nessun audio ricevuto"}), 400

    # Salva chunk temporaneamente
    filename = jarvis_ai.save_audio_chunk(audio_chunk)

    # Trascrivi chunk
    text = jarvis_ai.transcribe_audio_chunk(filename)

    # Se frase completa, genera risposta
    if text.strip():
        answer = jarvis_ai.ask_gpt(text)
        audio_base64 = jarvis_ai.speak(answer, return_base64=True)
        return jsonify({"answer": answer, "audio_base64": audio_base64})
    else:
        return jsonify({"answer": "", "audio_base64": ""})

# Servizio pagina web
@app.route("/client")
def client():
    return send_from_directory("", "index.html")

# HTTPS auto-generato
CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"

if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(KEY_FILE, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"IT"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Lazio"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Viterbo"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Jarvis"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer)\
        .public_key(key.public_key()).serial_number(x509.random_serial_number())\
        .not_valid_before(datetime.datetime.utcnow())\
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))\
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(u"localhost")]), critical=False)\
        .sign(key, hashes.SHA256())

    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context=context)
