from flask import Flask, request, jsonify, send_from_directory
import jarvis_ai
import ssl
import os

app = Flask(__name__, static_url_path='', static_folder='client')

# Endpoint principale per il client web
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("text", "")
    if not question:
        return jsonify({"error": "Nessun testo ricevuto"}), 400

    print(f"\n📱 Domanda ricevuta dal client: {question}")
    answer = jarvis_ai.ask_gpt(question)
    jarvis_ai.speak(answer)
    return jsonify({"answer": answer})

# Servizio della pagina web
@app.route("/client")
def client():
    return send_from_directory("", "index.html")

# HTTPS auto-generato con Python
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
