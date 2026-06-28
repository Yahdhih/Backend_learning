"""
Jour 12 — Exercice : Application WSGI avec routing, query string et JSON
8 juillet 2026

Objectifs :
  - Écrire une application WSGI complète qui gère plusieurs routes
  - Parser la query string depuis environ
  - Retourner des réponses JSON avec les bons codes HTTP
  - Tester sans serveur réseau grâce à wsgiref

Instructions :
  Les sections marquées [COMPLET] sont fournies à titre d'exemple.
  Les sections marquées [A LIRE] expliquent le fonctionnement.
  Lancez ce fichier directement : python exercice.py
"""

import json
import sys
from io import BytesIO
from urllib.parse import parse_qs


# =============================================================================
# DONNÉES DE TEST (fausse base de données en mémoire)
# =============================================================================

PRODUITS = [
    {"id": 1, "nom": "Laptop",    "prix": 999.99,  "categorie": "electronique", "stock": 15},
    {"id": 2, "nom": "Souris",    "prix": 29.99,   "categorie": "electronique", "stock": 200},
    {"id": 3, "nom": "Bureau",    "prix": 349.00,  "categorie": "mobilier",     "stock": 8},
    {"id": 4, "nom": "Chaise",    "prix": 199.00,  "categorie": "mobilier",     "stock": 23},
    {"id": 5, "nom": "Clavier",   "prix": 79.99,   "categorie": "electronique", "stock": 55},
    {"id": 6, "nom": "Moniteur",  "prix": 459.00,  "categorie": "electronique", "stock": 12},
    {"id": 7, "nom": "Lampe",     "prix": 45.00,   "categorie": "mobilier",     "stock": 67},
]

COMMANDES = [
    {"id": 101, "produit_id": 1, "quantite": 2, "client": "Alice"},
    {"id": 102, "produit_id": 3, "quantite": 1, "client": "Bob"},
    {"id": 103, "produit_id": 2, "quantite": 5, "client": "Alice"},
]


# =============================================================================
# UTILITAIRES
# =============================================================================

def reponse_json(start_response, data, status=200):
    """
    [COMPLET] Utilitaire pour envoyer une réponse JSON.

    Convertit `data` en JSON, appelle start_response avec les bons en-têtes,
    et retourne le body sous forme de liste de bytes.
    """
    STATUS_MAP = {
        200: "200 OK",
        201: "201 Created",
        400: "400 Bad Request",
        401: "401 Unauthorized",
        404: "404 Not Found",
        405: "405 Method Not Allowed",
        500: "500 Internal Server Error",
    }

    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    status_str = STATUS_MAP.get(status, f"{status} Unknown")

    start_response(status_str, [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("X-Powered-By", "WSGI-From-Scratch"),
    ])
    return [body]


def parser_query(environ):
    """
    [COMPLET] Parse la query string depuis environ et retourne un dict.

    Pour une query "categorie=mobilier&limit=5&page=2", retourne :
    {'categorie': 'mobilier', 'limit': '5', 'page': '2'}

    Note : parse_qs retourne des listes, on prend le premier élément.
    """
    query_string = environ.get("QUERY_STRING", "")
    params_raw = parse_qs(query_string)  # {'categorie': ['mobilier'], 'limit': ['5']}
    # Simplification : on prend la première valeur de chaque paramètre
    return {key: vals[0] for key, vals in params_raw.items()}


def lire_body_json(environ):
    """
    [COMPLET] Lit et parse le body JSON d'une requête POST/PUT.

    Retourne (data, erreur). Si erreur != None, data est None.
    """
    try:
        content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
    except ValueError:
        return None, "Content-Length invalide"

    if content_length == 0:
        return {}, None

    body_bytes = environ["wsgi.input"].read(content_length)

    try:
        data = json.loads(body_bytes.decode("utf-8"))
        return data, None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"JSON invalide : {e}"


# =============================================================================
# GESTIONNAIRES DE ROUTES (handlers)
# =============================================================================

def handler_accueil(environ, start_response):
    """
    [COMPLET] GET /
    Retourne un message de bienvenue et la liste des routes disponibles.
    """
    data = {
        "message": "Bienvenue sur l'API WSGI des produits",
        "version": "1.0",
        "routes": [
            "GET  /",
            "GET  /produits",
            "GET  /produits?categorie=mobilier",
            "GET  /produits?prix_max=100",
            "GET  /produits?limit=3&page=2",
            "GET  /produits/{id}",
            "POST /produits",
            "GET  /commandes",
            "GET  /stats",
        ]
    }
    return reponse_json(start_response, data, 200)


def handler_liste_produits(environ, start_response):
    """
    [COMPLET] GET /produits

    Supporte les paramètres de query string :
    - categorie : filtrer par catégorie (ex: ?categorie=mobilier)
    - prix_max  : filtrer les produits dont le prix <= prix_max
    - limit     : nombre maximum de résultats (défaut: tous)
    - page      : page de résultats (utilisé avec limit)

    Exemples :
      /produits                         → tous les produits
      /produits?categorie=electronique  → que les électroniques
      /produits?prix_max=100            → produits <= 100€
      /produits?limit=3&page=1          → pagination
    """
    params = parser_query(environ)

    resultats = list(PRODUITS)  # copie pour ne pas modifier l'original

    # Filtre par catégorie
    if "categorie" in params:
        categorie = params["categorie"].lower()
        resultats = [p for p in resultats if p["categorie"] == categorie]

    # Filtre par prix maximum
    if "prix_max" in params:
        try:
            prix_max = float(params["prix_max"])
            resultats = [p for p in resultats if p["prix"] <= prix_max]
        except ValueError:
            return reponse_json(
                start_response,
                {"erreur": "prix_max doit etre un nombre"},
                400
            )

    # Pagination
    total = len(resultats)

    if "limit" in params:
        try:
            limit = int(params["limit"])
            page  = int(params.get("page", "1"))
            if limit <= 0 or page <= 0:
                raise ValueError()
            debut = (page - 1) * limit
            fin   = debut + limit
            resultats = resultats[debut:fin]
        except ValueError:
            return reponse_json(
                start_response,
                {"erreur": "limit et page doivent etre des entiers positifs"},
                400
            )

    data = {
        "total": total,
        "count": len(resultats),
        "produits": resultats,
    }
    return reponse_json(start_response, data, 200)


def handler_detail_produit(environ, start_response, produit_id):
    """
    [COMPLET] GET /produits/{id}
    Retourne le détail d'un produit par son ID.
    Retourne 404 si le produit n'existe pas.
    """
    produit = next((p for p in PRODUITS if p["id"] == produit_id), None)

    if produit is None:
        return reponse_json(
            start_response,
            {"erreur": f"Produit {produit_id} introuvable"},
            404
        )

    return reponse_json(start_response, produit, 200)


def handler_creer_produit(environ, start_response):
    """
    [COMPLET] POST /produits

    Crée un nouveau produit. Le body doit être du JSON avec :
    - nom (str, requis)
    - prix (float, requis, > 0)
    - categorie (str, requis)
    - stock (int, optionnel, défaut: 0)

    Retourne 201 Created avec le produit créé,
    ou 400 Bad Request si les données sont invalides.
    """
    data, erreur = lire_body_json(environ)

    if erreur:
        return reponse_json(start_response, {"erreur": erreur}, 400)

    # Validation des champs requis
    champs_requis = ["nom", "prix", "categorie"]
    manquants = [c for c in champs_requis if c not in data]
    if manquants:
        return reponse_json(
            start_response,
            {"erreur": f"Champs manquants : {', '.join(manquants)}"},
            400
        )

    # Validation du prix
    try:
        prix = float(data["prix"])
        if prix <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return reponse_json(
            start_response,
            {"erreur": "Le prix doit etre un nombre positif"},
            400
        )

    # Créer le nouveau produit
    nouvel_id = max(p["id"] for p in PRODUITS) + 1
    nouveau_produit = {
        "id":        nouvel_id,
        "nom":       str(data["nom"]),
        "prix":      prix,
        "categorie": str(data["categorie"]),
        "stock":     int(data.get("stock", 0)),
    }
    PRODUITS.append(nouveau_produit)

    return reponse_json(start_response, nouveau_produit, 201)


def handler_liste_commandes(environ, start_response):
    """
    [COMPLET] GET /commandes

    Retourne les commandes enrichies avec les détails des produits.
    Supporte ?client= pour filtrer par client.
    """
    params = parser_query(environ)

    commandes = list(COMMANDES)

    if "client" in params:
        commandes = [c for c in commandes if c["client"].lower() == params["client"].lower()]

    # Enrichissement : ajouter le nom du produit
    commandes_enrichies = []
    for cmd in commandes:
        produit = next((p for p in PRODUITS if p["id"] == cmd["produit_id"]), None)
        commande_enrichie = dict(cmd)
        if produit:
            commande_enrichie["produit_nom"] = produit["nom"]
            commande_enrichie["total"]       = round(produit["prix"] * cmd["quantite"], 2)
        commandes_enrichies.append(commande_enrichie)

    return reponse_json(start_response, {
        "count": len(commandes_enrichies),
        "commandes": commandes_enrichies,
    }, 200)


def handler_stats(environ, start_response):
    """
    [COMPLET] GET /stats
    Retourne des statistiques calculées sur les produits.
    """
    if not PRODUITS:
        return reponse_json(start_response, {"erreur": "Aucun produit"}, 404)

    prix_list = [p["prix"] for p in PRODUITS]

    # Regrouper par catégorie
    par_categorie = {}
    for p in PRODUITS:
        cat = p["categorie"]
        if cat not in par_categorie:
            par_categorie[cat] = {"count": 0, "total_stock": 0, "prix_moyen": 0, "prix_list": []}
        par_categorie[cat]["count"] += 1
        par_categorie[cat]["total_stock"] += p["stock"]
        par_categorie[cat]["prix_list"].append(p["prix"])

    # Calculer les prix moyens et nettoyer
    for cat, info in par_categorie.items():
        info["prix_moyen"] = round(sum(info["prix_list"]) / len(info["prix_list"]), 2)
        del info["prix_list"]

    stats = {
        "total_produits":   len(PRODUITS),
        "prix_moyen":       round(sum(prix_list) / len(prix_list), 2),
        "prix_min":         min(prix_list),
        "prix_max":         max(prix_list),
        "total_stock":      sum(p["stock"] for p in PRODUITS),
        "par_categorie":    par_categorie,
    }
    return reponse_json(start_response, stats, 200)


def handler_not_found(environ, start_response):
    """[COMPLET] Réponse 404 générique."""
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "?")
    return reponse_json(
        start_response,
        {"erreur": f"Route '{method} {path}' introuvable"},
        404
    )


def handler_method_not_allowed(environ, start_response, methodes_autorisees):
    """[COMPLET] Réponse 405 Method Not Allowed."""
    return reponse_json(
        start_response,
        {"erreur": f"Methode non autorisee. Methodes acceptees : {', '.join(methodes_autorisees)}"},
        405
    )


# =============================================================================
# ROUTEUR PRINCIPAL
# =============================================================================

def application(environ, start_response):
    """
    [COMPLET] Application WSGI principale.

    Dispatch les requêtes vers les handlers appropriés selon PATH_INFO
    et REQUEST_METHOD.

    Routes supportées :
      GET  /                → handler_accueil
      GET  /produits        → handler_liste_produits (avec filtres)
      POST /produits        → handler_creer_produit
      GET  /produits/{id}   → handler_detail_produit
      GET  /commandes       → handler_liste_commandes
      GET  /stats           → handler_stats
    """
    path   = environ.get("PATH_INFO", "/").rstrip("/") or "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # Route : GET /
    if path == "/":
        if method == "GET":
            return handler_accueil(environ, start_response)
        return handler_method_not_allowed(environ, start_response, ["GET"])

    # Route : /produits (liste + création)
    if path == "/produits":
        if method == "GET":
            return handler_liste_produits(environ, start_response)
        if method == "POST":
            return handler_creer_produit(environ, start_response)
        return handler_method_not_allowed(environ, start_response, ["GET", "POST"])

    # Route : /produits/{id} (détail)
    if path.startswith("/produits/"):
        id_str = path[len("/produits/"):]
        try:
            produit_id = int(id_str)
        except ValueError:
            return reponse_json(
                start_response,
                {"erreur": f"ID invalide : '{id_str}'"},
                400
            )

        if method == "GET":
            return handler_detail_produit(environ, start_response, produit_id)
        return handler_method_not_allowed(environ, start_response, ["GET"])

    # Route : GET /commandes
    if path == "/commandes":
        if method == "GET":
            return handler_liste_commandes(environ, start_response)
        return handler_method_not_allowed(environ, start_response, ["GET"])

    # Route : GET /stats
    if path == "/stats":
        if method == "GET":
            return handler_stats(environ, start_response)
        return handler_method_not_allowed(environ, start_response, ["GET"])

    # Aucune route trouvée
    return handler_not_found(environ, start_response)


# =============================================================================
# FONCTION DE TEST (sans serveur réseau)
# =============================================================================

def simuler_requete(app, method="GET", path="/", query="", body=b"", headers=None):
    """
    [COMPLET] Simule une requête HTTP vers l'application WSGI.

    Pas besoin d'un vrai serveur réseau — on construit l'environ manuellement
    et on appelle l'application directement.

    Args:
        app     : callable WSGI
        method  : méthode HTTP ('GET', 'POST', etc.)
        path    : chemin URL (ex: '/produits')
        query   : query string sans '?' (ex: 'categorie=mobilier&limit=3')
        body    : body de la requête en bytes (pour POST/PUT)
        headers : dict d'en-têtes HTTP supplémentaires

    Returns:
        (status_str, headers_dict, body_bytes)
    """
    if isinstance(body, str):
        body = body.encode("utf-8")

    environ = {
        "REQUEST_METHOD":  method.upper(),
        "PATH_INFO":       path,
        "QUERY_STRING":    query,
        "CONTENT_TYPE":    "application/json" if body else "",
        "CONTENT_LENGTH":  str(len(body)),
        "SERVER_NAME":     "localhost",
        "SERVER_PORT":     "8000",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_HOST":       "localhost:8000",
        "wsgi.version":    (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input":      BytesIO(body),
        "wsgi.errors":     BytesIO(),
        "wsgi.multithread":  False,
        "wsgi.multiprocess": False,
        "wsgi.run_once":     False,
    }

    if headers:
        for key, value in headers.items():
            wsgi_key = "HTTP_" + key.upper().replace("-", "_")
            environ[wsgi_key] = value

    # Capturer start_response
    captured = {"status": None, "headers": {}}

    def start_response(status, response_headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = dict(response_headers)

    body_parts = app(environ, start_response)
    body_response = b"".join(body_parts)

    return captured["status"], captured["headers"], body_response


def afficher_resultat(label, status, headers, body, afficher_body=True):
    """[COMPLET] Affichage formaté du résultat d'un test."""
    ok_statuses = {"200 OK", "201 Created", "204 No Content"}
    icone = "OK" if status in ok_statuses else "ERREUR"

    print(f"\n  [{icone}] {label}")
    print(f"       Status  : {status}")
    print(f"       C-Type  : {headers.get('Content-Type', 'non defini')}")

    if afficher_body:
        try:
            data = json.loads(body.decode("utf-8"))
            body_str = json.dumps(data, ensure_ascii=False, indent=2)
            # Limiter l'affichage à 8 lignes
            lignes = body_str.split("\n")
            if len(lignes) > 8:
                body_str = "\n".join(lignes[:8]) + f"\n       ... ({len(lignes)-8} lignes cachees)"
            print(f"       Body    :\n{body_str}")
        except Exception:
            print(f"       Body    : {body[:100]}")


def tester():
    """
    [COMPLET] Suite de tests pour l'application WSGI.

    Teste toutes les routes sans démarrer de vrai serveur.
    """
    print("=" * 60)
    print("  TESTS DE L'APPLICATION WSGI — JOUR 12")
    print("=" * 60)

    # ------------------------------------------------------------------
    print("\n--- ROUTES DE BASE ---")

    status, headers, body = simuler_requete(application, "GET", "/")
    afficher_resultat("GET /  (accueil)", status, headers, body)

    # ------------------------------------------------------------------
    print("\n--- LISTE DES PRODUITS ---")

    status, headers, body = simuler_requete(application, "GET", "/produits")
    afficher_resultat("GET /produits  (tous)", status, headers, body, afficher_body=False)
    data = json.loads(body)
    print(f"       -> {data['count']} produits retournes sur {data['total']} total")

    status, headers, body = simuler_requete(
        application, "GET", "/produits", query="categorie=electronique"
    )
    afficher_resultat("GET /produits?categorie=electronique", status, headers, body, afficher_body=False)
    data = json.loads(body)
    print(f"       -> {data['count']} produits electroniques")

    status, headers, body = simuler_requete(
        application, "GET", "/produits", query="prix_max=100"
    )
    afficher_resultat("GET /produits?prix_max=100", status, headers, body, afficher_body=False)
    data = json.loads(body)
    noms = [p["nom"] for p in data["produits"]]
    print(f"       -> Produits <= 100€ : {noms}")

    status, headers, body = simuler_requete(
        application, "GET", "/produits", query="limit=2&page=1"
    )
    afficher_resultat("GET /produits?limit=2&page=1", status, headers, body, afficher_body=False)
    data = json.loads(body)
    print(f"       -> Page 1 (2/produit) : {[p['nom'] for p in data['produits']]}")

    status, headers, body = simuler_requete(
        application, "GET", "/produits", query="limit=2&page=2"
    )
    data = json.loads(body)
    print(f"       -> Page 2 (2/produit) : {[p['nom'] for p in data['produits']]}")

    # ------------------------------------------------------------------
    print("\n--- DÉTAIL D'UN PRODUIT ---")

    status, headers, body = simuler_requete(application, "GET", "/produits/1")
    afficher_resultat("GET /produits/1", status, headers, body)

    status, headers, body = simuler_requete(application, "GET", "/produits/999")
    afficher_resultat("GET /produits/999  (inexistant)", status, headers, body)
    assert status == "404 Not Found", f"Attendu 404, got {status}"

    status, headers, body = simuler_requete(application, "GET", "/produits/abc")
    afficher_resultat("GET /produits/abc  (ID invalide)", status, headers, body)
    assert status == "400 Bad Request", f"Attendu 400, got {status}"

    # ------------------------------------------------------------------
    print("\n--- CREATION D'UN PRODUIT ---")

    nouveau = json.dumps({
        "nom":       "Tapis de souris",
        "prix":      19.99,
        "categorie": "electronique",
        "stock":     150,
    })
    status, headers, body = simuler_requete(
        application, "POST", "/produits", body=nouveau.encode()
    )
    afficher_resultat("POST /produits  (valide)", status, headers, body)
    assert status == "201 Created", f"Attendu 201, got {status}"

    # Données invalides : prix manquant
    invalide = json.dumps({"nom": "Article sans prix"})
    status, headers, body = simuler_requete(
        application, "POST", "/produits", body=invalide.encode()
    )
    afficher_resultat("POST /produits  (champs manquants)", status, headers, body)
    assert status == "400 Bad Request", f"Attendu 400, got {status}"

    # Données invalides : prix négatif
    invalide2 = json.dumps({"nom": "Article", "prix": -10, "categorie": "test"})
    status, headers, body = simuler_requete(
        application, "POST", "/produits", body=invalide2.encode()
    )
    afficher_resultat("POST /produits  (prix negatif)", status, headers, body)
    assert status == "400 Bad Request", f"Attendu 400, got {status}"

    # ------------------------------------------------------------------
    print("\n--- COMMANDES ---")

    status, headers, body = simuler_requete(application, "GET", "/commandes")
    afficher_resultat("GET /commandes", status, headers, body, afficher_body=False)
    data = json.loads(body)
    print(f"       -> {data['count']} commandes")

    status, headers, body = simuler_requete(
        application, "GET", "/commandes", query="client=Alice"
    )
    afficher_resultat("GET /commandes?client=Alice", status, headers, body, afficher_body=False)
    data = json.loads(body)
    print(f"       -> {data['count']} commandes pour Alice")

    # ------------------------------------------------------------------
    print("\n--- STATISTIQUES ---")

    status, headers, body = simuler_requete(application, "GET", "/stats")
    afficher_resultat("GET /stats", status, headers, body)

    # ------------------------------------------------------------------
    print("\n--- ERREURS ---")

    status, headers, body = simuler_requete(application, "GET", "/inexistant")
    afficher_resultat("GET /inexistant  (404)", status, headers, body)
    assert status == "404 Not Found"

    status, headers, body = simuler_requete(application, "DELETE", "/produits")
    afficher_resultat("DELETE /produits  (405)", status, headers, body)
    assert status == "405 Method Not Allowed"

    status, headers, body = simuler_requete(
        application, "GET", "/produits", query="prix_max=pas_un_nombre"
    )
    afficher_resultat("GET /produits?prix_max=pas_un_nombre  (400)", status, headers, body)
    assert status == "400 Bad Request"

    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  TOUS LES TESTS PASSES !")
    print("=" * 60)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        # Mode serveur : python exercice.py serve
        from wsgiref.simple_server import make_server
        HOST, PORT = "localhost", 8000
        print(f"Serveur WSGI de developpement sur http://{HOST}:{PORT}/")
        print("Testez avec : curl http://localhost:8000/produits")
        print("Ctrl+C pour arreter.\n")
        with make_server(HOST, PORT, application) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServeur arrete.")
    else:
        # Mode test par défaut
        tester()
