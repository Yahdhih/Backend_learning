"""
Exercice Jour 03 — Construire un serveur HTTP à la main

Lance ce fichier :
    python3 exercice.py

Puis dans un autre terminal :
    curl -v http://localhost:8888/
    curl -v http://localhost:8888/hello
    curl -v http://localhost:8888/json

Complète les TODO ci-dessous.
"""

import socket
import json
from datetime import datetime
import time 


debut = time.time()
HOST = "127.0.0.1"
PORT = 8888


def parse_request(raw_bytes: bytes) -> dict:
    """Parse les bytes bruts d'une requête HTTP en dict."""
    text = raw_bytes.decode("utf-8", errors="replace")
    headers_part, _, body = text.partition("\r\n\r\n")
    lines = headers_part.split("\r\n")

    parts = lines[0].split(" ")
    method = parts[0] if len(parts) > 0 else "GET"
    path = parts[1] if len(parts) > 1 else "/"

    headers = {}
    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key.lower()] = value

    return {"method": method, "path": path, "headers": headers, "body": body}


def make_response(status_code: int, status_text: str, body: str, content_type: str = "text/plain") -> bytes:
    """Construit une réponse HTTP complète en bytes."""
    body_bytes = body.encode("utf-8")
    response = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}; charset=utf-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
        f"{body}"
    )
    return response.encode("utf-8")


def handle_request(request: dict) -> bytes:
    """Route la requête vers le bon handler."""
    path = request["path"]
    method = request["method"]
    print(f"  {method} {path}")

    if path == "/":
        body = "<h1>Mon serveur HTTP</h1><p>Construit avec des sockets bruts.</p>"
        return make_response(200, "OK", body, "text/html")

    elif path == "/hello":
        return make_response(200, "OK", "Bonjour depuis mon serveur !", "text/plain")

    elif path == "/json":
        data = {"message": "Bonjour", "heure": datetime.utcnow().isoformat()}
        return make_response(200, "OK", json.dumps(data), "application/json")

    # TODO 1 : Ajoute une route /time
    # Elle doit retourner {"heure": "2026-06-29T10:30:00", "timestamp": 1234567890}
    # Utilise datetime.utcnow() et datetime.utcnow().timestamp()
    elif path == "/time":
        data = {"heure":datetime.utcnow().isoformat(), "timestamp": datetime.utcnow().timestamp()}
        return make_response(200, "OK", json.dumps(data), "application/json")
    # TODO 2 : Ajoute une route /status
    # Elle retourne {"status": "ok", "uptime_seconds": X}
    # X = nombre de secondes depuis le démarrage du serveur
    # Indice : utilise time.time() au démarrage et fais la soustraction
    elif path == "/status":
        maintenant = time.time()
        data = {"status": "ok", "uptime_seconds":maintenant - debut }
        return make_response(200, "OK", json.dumps(data), "application/json")
    # TODO 3 : Ajoute une route /echo
    # Elle retourne toute la requête reçue sous forme de JSON
    # {"method": "GET", "path": "/echo", "headers": {...}}
    elif path == "/echo":
        maintenant = time.time()
        data = {"method": "GET", "path": "/echo", "headers": {"host": "localhost:8080",
        "accept": "application/json",
        "user-agent": "curl/7.88",
        "x-mon-header": "valeur-test",}}
        return make_response(200, "OK", json.dumps(data), "application/json")

    # TODO 4 (bonus) : Parse les query parameters
    # Pour /greet?name=Alice, retourne {"message": "Bonjour Alice !"}
    # Indice : le path ressemblera à "/greet?name=Alice"
    # Utilise path.split("?") pour séparer chemin et paramètres
    if "?" in path : 
        chemin, name = path.split("?")
        _, name = name.split("=")
        data = {"message": "Bonjour Alice !"}
        return make_response(200, "OK", json.dumps(data), "application/json")
    

    else:
        body = json.dumps({"error": "Route introuvable", "path": path})
        return make_response(404, "Not Found", body, "application/json")


def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)

    print(f"Serveur sur http://{HOST}:{PORT}")
    print("Ctrl+C pour arrêter\n")

    try:
        while True:
            client_socket, addr = server.accept()
            print(f"Connexion de {addr[0]}")
            try:
                raw = client_socket.recv(4096)
                if raw:
                    request = parse_request(raw)
                    response = handle_request(request)
                    client_socket.sendall(response)
            finally:
                client_socket.close()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        server.close()


if __name__ == "__main__":
    run_server()
