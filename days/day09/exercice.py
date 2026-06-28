"""
Jour 09 — Exercices : Headers HTTP
Date : 5 juillet 2026

Instructions :
- Complétez chaque TODO
- Lancez tester() pour vérifier vos réponses
- Utilisez uniquement urllib.request (bibliothèque standard)
- Les requêtes vont vers httpbin.org qui renvoie les headers qu'il reçoit
"""

import urllib.request
import urllib.error
import urllib.parse
import json
import base64


# ==============================================================================
# UTILITAIRES
# ==============================================================================

def requete(methode, url, body=None, headers=None):
    """Effectue une requête HTTP et retourne (code, headers_reponse, body_dict)."""
    h = {}
    if headers:
        h.update(headers)
    if body and isinstance(body, dict):
        body = json.dumps(body).encode("utf-8")
        h.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=body, method=methode, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"raw": raw}
            return r.status, dict(r.headers), parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return e.code, dict(e.headers), parsed


def titre(texte):
    print(f"\n{'='*60}")
    print(f"  {texte}")
    print(f"{'='*60}")


# ==============================================================================
# EXERCICE 1 : Envoyer et observer des headers de requête
# ==============================================================================

def exercice_1_envoyer_headers():
    """
    Objectif : Envoyer des headers HTTP personnalisés et vérifier
    qu'ils sont bien reçus par le serveur.

    httpbin.org/headers renvoie dans sa réponse les headers qu'il a reçus.
    httpbin.org/get renvoie également les headers reçus dans la clé "headers".
    """
    titre("EXERCICE 1 : Envoyer des headers personnalisés")

    # --- TODO 1.1 ---
    # Envoyez une requête GET vers https://httpbin.org/headers
    # avec les headers suivants :
    #   Accept: application/json
    #   User-Agent: Backend-Learning/1.0
    #   X-Custom-Header: bonjour-monde
    # Affichez les headers reçus par httpbin (dans body["headers"])
    print("\n[TODO 1.1] GET avec headers personnalisés")
    # mes_headers = {
    #     "Accept": "application/json",
    #     "User-Agent": "Backend-Learning/1.0",
    #     "X-Custom-Header": "bonjour-monde",
    # }
    # code, _, body = requete("GET", "https://httpbin.org/headers", headers=mes_headers)
    # print(f"Code : {code}")
    # print("Headers reçus par httpbin :")
    # for nom, val in body["headers"].items():
    #     print(f"  {nom}: {val}")

    # --- TODO 1.2 ---
    # Envoyez une requête POST avec Content-Type: application/json
    # vers https://httpbin.org/post avec le body {"langage": "Python", "jour": 9}
    # Vérifiez dans la réponse que httpbin a bien vu le Content-Type
    print("\n[TODO 1.2] POST avec Content-Type application/json")
    # donnees = {"langage": "Python", "jour": 9}
    # code, _, body = requete("POST", "https://httpbin.org/post", body=donnees)
    # print(f"Code : {code}")
    # print(f"Content-Type reçu par httpbin : {body['headers'].get('Content-Type')}")
    # print(f"Données JSON reçues : {body['json']}")

    # --- TODO 1.3 ---
    # Envoyez une requête POST avec Content-Type: application/x-www-form-urlencoded
    # (format des formulaires HTML classiques)
    # Body : "nom=Alice&age=30" (encodé comme un formulaire)
    # vers https://httpbin.org/post
    # Comparez body["json"] (devrait être None) et body["form"] (devrait avoir vos données)
    print("\n[TODO 1.3] POST avec Content-Type application/x-www-form-urlencoded")
    # form_data = urllib.parse.urlencode({"nom": "Alice", "age": "30"}).encode("utf-8")
    # req = urllib.request.Request(
    #     "https://httpbin.org/post",
    #     data=form_data,
    #     method="POST",
    #     headers={"Content-Type": "application/x-www-form-urlencoded"}
    # )
    # with urllib.request.urlopen(req) as r:
    #     body = json.loads(r.read())
    #     print(f"body['json'] : {body['json']}")  # None (pas du JSON)
    #     print(f"body['form'] : {body['form']}")  # {'nom': 'Alice', 'age': '30'}


# ==============================================================================
# EXERCICE 2 : Authentification HTTP
# ==============================================================================

def exercice_2_authentification():
    """
    Objectif : Implémenter les différents schémas d'authentification HTTP.

    httpbin.org offre des endpoints d'authentification pratiques :
    - /basic-auth/{user}/{password} → vérifie Basic Auth
    - /bearer → vérifie un Bearer token (accepte n'importe quel token)
    - /headers → permet de vérifier les headers envoyés
    """
    titre("EXERCICE 2 : Authentification HTTP")

    # --- TODO 2.1 ---
    # Implémentez la fonction encoder_basic_auth(username, password)
    # qui retourne la valeur du header Authorization pour Basic Auth.
    # Format : "Basic " + base64("username:password")
    print("\n[TODO 2.1] Encoder des credentials Basic Auth")
    def encoder_basic_auth(username, password):
        # TODO : Implémentez cette fonction
        # 1. Créez la chaîne "username:password"
        # 2. Encodez-la en bytes (UTF-8)
        # 3. Encodez en base64
        # 4. Décodez le résultat en string
        # 5. Retournez "Basic " + résultat
        pass

    # Test de la fonction :
    # header_value = encoder_basic_auth("alice", "motdepasse123")
    # print(f"Header : {header_value}")
    # # Vérification : le décodage doit donner "alice:motdepasse123"
    # partie_b64 = header_value.split(" ")[1]
    # decoded = base64.b64decode(partie_b64).decode()
    # assert decoded == "alice:motdepasse123", f"Erreur : {decoded}"
    # print(f"Vérifié : {decoded}")

    # --- TODO 2.2 ---
    # Utilisez encoder_basic_auth pour vous authentifier sur httpbin.org
    # URL : https://httpbin.org/basic-auth/alice/secret123
    # Envoyez les bons credentials (alice / secret123) et affichez la réponse
    # Puis essayez avec de mauvais credentials → observez le code 401
    print("\n[TODO 2.2] Requête avec Basic Auth")
    # # Bons credentials
    # auth_header = encoder_basic_auth("alice", "secret123")
    # code, _, body = requete("GET", "https://httpbin.org/basic-auth/alice/secret123",
    #                          headers={"Authorization": auth_header})
    # print(f"Bons credentials → code : {code}, body : {body}")

    # # Mauvais credentials
    # mauvais_auth = encoder_basic_auth("alice", "mauvais_mdp")
    # code_401, _, _ = requete("GET", "https://httpbin.org/basic-auth/alice/secret123",
    #                           headers={"Authorization": mauvais_auth})
    # print(f"Mauvais credentials → code : {code_401}")  # Doit être 401

    # --- TODO 2.3 ---
    # Envoyez une requête avec un Bearer token vers https://httpbin.org/bearer
    # Utilisez n'importe quel token fictif : "mon-token-jwt-abc123"
    # Affichez le code de statut et les données retournées
    print("\n[TODO 2.3] Requête avec Bearer token")
    # token = "mon-token-jwt-abc123"
    # code, _, body = requete("GET", "https://httpbin.org/bearer",
    #                          headers={"Authorization": f"Bearer {token}"})
    # print(f"Code : {code}")
    # print(f"Body : {body}")

    # --- TODO 2.4 ---
    # Implémentez decoder_jwt_payload(token) qui extrait le payload d'un JWT
    # sans valider la signature (pour l'inspection seulement)
    # Format JWT : header.payload.signature (base64url encodé)
    print("\n[TODO 2.4] Décoder un payload JWT")
    def decoder_jwt_payload(token):
        # TODO : Implémentez cette fonction
        # 1. Splittez le token sur "."
        # 2. Prenez la 2ème partie (index 1) = le payload
        # 3. Ajoutez du padding base64 si nécessaire : partie += "=" * (4 - len(partie) % 4)
        # 4. Décodez en base64 puis en JSON
        pass

    # Token de test (sans signature valide, juste pour l'exercice)
    jwt_test = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQyLCJub20iOiJBbGljZSIsImV4cCI6MTc1MTY3MDAwMH0.signature"
    # payload = decoder_jwt_payload(jwt_test)
    # print(f"Payload décodé : {payload}")
    # # Résultat attendu : {"userId": 42, "nom": "Alice", "exp": 1751670000}


# ==============================================================================
# EXERCICE 3 : Négociation de contenu
# ==============================================================================

def exercice_3_content_negotiation():
    """
    Objectif : Implémenter et observer la négociation de contenu via
    les headers Accept et Content-Type.
    """
    titre("EXERCICE 3 : Négociation de contenu")

    # --- TODO 3.1 ---
    # Envoyez une requête GET vers https://httpbin.org/get
    # Avec Accept: application/json
    # Vérifiez que le Content-Type de la réponse est bien application/json
    print("\n[TODO 3.1] Requête avec Accept: application/json")
    # code, headers_rep, body = requete("GET", "https://httpbin.org/get",
    #                                    headers={"Accept": "application/json"})
    # print(f"Accept envoyé : application/json")
    # print(f"Content-Type reçu : {headers_rep.get('Content-Type')}")

    # --- TODO 3.2 ---
    # Implémentez la fonction parse_accept_header(accept_str) qui parse
    # un header Accept et retourne une liste triée de (type, qualité)
    # Ex: "application/json, text/html;q=0.9, */*;q=0.8"
    # → [("application/json", 1.0), ("text/html", 0.9), ("*/*", 0.8)]
    print("\n[TODO 3.2] Parser un header Accept")
    def parse_accept_header(accept_str):
        # TODO : Implémentez cette fonction
        # 1. Splittez sur ","
        # 2. Pour chaque type, splittez sur ";" pour trouver q=
        # 3. Si pas de q=, qualité = 1.0
        # 4. Triez par qualité décroissante
        pass

    # Tests :
    # result = parse_accept_header("application/json, text/html;q=0.9, */*;q=0.8")
    # print(f"Parsé : {result}")
    # # Attendu : [("application/json", 1.0), ("text/html", 0.9), ("*/*", 0.8)]

    # result2 = parse_accept_header("text/html;q=0.8, application/json;q=0.9")
    # print(f"Parsé (trié) : {result2}")
    # # Attendu : [("application/json", 0.9), ("text/html", 0.8)]

    # --- TODO 3.3 ---
    # Implémentez choisir_content_type(accept_header, types_disponibles)
    # qui choisit le meilleur Content-Type à retourner selon l'Accept du client
    print("\n[TODO 3.3] Choisir le Content-Type optimal")
    def choisir_content_type(accept_header, types_disponibles):
        """
        Choisit le meilleur type de contenu selon les préférences du client.

        Args:
            accept_header: str, ex "application/json, text/html;q=0.9"
            types_disponibles: list, ex ["application/json", "text/html"]

        Returns:
            str: le meilleur type disponible, ou None si aucun match
        """
        # TODO : Implémentez cette fonction
        # 1. Parsez l'Accept header avec parse_accept_header
        # 2. Cherchez le premier type accepté qui est dans types_disponibles
        # 3. Gérez le wildcard "*/*" (accepte tout)
        # 4. Retournez None si aucun type ne convient
        pass

    # Tests :
    # print(choisir_content_type(
    #     "application/json, text/html;q=0.9",
    #     ["text/html", "application/json"]
    # ))  # → "application/json" (préféré)

    # print(choisir_content_type(
    #     "text/html",
    #     ["application/json"]
    # ))  # → None (pas de match)

    # print(choisir_content_type(
    #     "*/*",
    #     ["application/json"]
    # ))  # → "application/json" (wildcard accepte tout)


# ==============================================================================
# EXERCICE 4 : Analyser les headers de réponse
# ==============================================================================

def exercice_4_analyser_reponses():
    """
    Objectif : Extraire et interpréter les headers de réponse importants.
    """
    titre("EXERCICE 4 : Analyser les headers de réponse")

    # --- TODO 4.1 ---
    # Faites une requête HEAD vers https://httpbin.org/get
    # et listez TOUS les headers de réponse avec leurs valeurs
    print("\n[TODO 4.1] Lister tous les headers de réponse")
    # req = urllib.request.Request("https://httpbin.org/get", method="HEAD")
    # with urllib.request.urlopen(req) as r:
    #     print(f"Statut : {r.status}")
    #     print("Headers de réponse :")
    #     for nom, valeur in sorted(r.headers.items()):
    #         print(f"  {nom}: {valeur}")

    # --- TODO 4.2 ---
    # Implémentez analyser_cache_control(header_value) qui parse
    # le header Cache-Control et retourne un dictionnaire de directives
    # Ex: "public, max-age=3600, must-revalidate"
    # → {"public": True, "max-age": "3600", "must-revalidate": True}
    print("\n[TODO 4.2] Parser Cache-Control")
    def analyser_cache_control(header_value):
        # TODO : Implémentez cette fonction
        # 1. Splittez sur ","
        # 2. Pour chaque directive, splittez sur "=" si présent
        # 3. Directives sans valeur → True
        # 4. Directives avec valeur → leur valeur string
        pass

    # Tests :
    # print(analyser_cache_control("public, max-age=3600"))
    # # → {"public": True, "max-age": "3600"}

    # print(analyser_cache_control("no-cache, no-store, must-revalidate"))
    # # → {"no-cache": True, "no-store": True, "must-revalidate": True}

    # print(analyser_cache_control("private, max-age=0"))
    # # → {"private": True, "max-age": "0"}

    # --- TODO 4.3 ---
    # Implémentez analyser_set_cookie(header_value) qui parse un header Set-Cookie
    # et retourne un dictionnaire avec les attributs du cookie
    print("\n[TODO 4.3] Parser Set-Cookie")
    def analyser_set_cookie(header_value):
        """
        Parse un header Set-Cookie.

        Exemple :
            "session=abc123; HttpOnly; Secure; SameSite=Lax; Max-Age=3600"

        Retourne :
            {
                "nom": "session",
                "valeur": "abc123",
                "httponly": True,
                "secure": True,
                "samesite": "Lax",
                "max-age": "3600"
            }
        """
        # TODO : Implémentez cette fonction
        # 1. Splittez sur ";" (le premier élément est "nom=valeur")
        # 2. Parsez le nom et la valeur du cookie
        # 3. Pour chaque attribut supplémentaire :
        #    - Si "=" est présent → clé: valeur (en minuscules)
        #    - Sinon → clé: True (en minuscules)
        pass

    # Tests :
    # cookie1 = analyser_set_cookie("session=abc123; HttpOnly; Secure; SameSite=Lax; Max-Age=3600")
    # print(f"Cookie 1 : {cookie1}")

    # cookie2 = analyser_set_cookie("langue=fr; Path=/; Domain=.exemple.com; Max-Age=86400")
    # print(f"Cookie 2 : {cookie2}")

    # --- TODO 4.4 ---
    # Faites une requête vers https://httpbin.org/cookies/set?session=test123
    # (cette URL définit un cookie dans la réponse)
    # Lisez le header Set-Cookie dans la réponse
    # Parsez-le avec votre fonction analyser_set_cookie
    print("\n[TODO 4.4] Observer un vrai header Set-Cookie")
    # # Note : urllib ne suit pas les redirections par défaut pour cette URL
    # try:
    #     req = urllib.request.Request("https://httpbin.org/cookies/set?session=test123")
    #     with urllib.request.urlopen(req) as r:
    #         set_cookie = r.headers.get("Set-Cookie", "Pas de Set-Cookie")
    #         print(f"Set-Cookie : {set_cookie}")
    # except urllib.error.HTTPError as e:
    #     # httpbin redirige — regardons les headers de la réponse 302
    #     set_cookie = e.headers.get("Set-Cookie", "Pas de Set-Cookie")
    #     print(f"Set-Cookie (dans 302) : {set_cookie}")
    #     if set_cookie and set_cookie != "Pas de Set-Cookie":
    #         parsed = analyser_set_cookie(set_cookie)
    #         print(f"Parsé : {parsed}")


# ==============================================================================
# EXERCICE 5 : Simuler CORS
# ==============================================================================

def exercice_5_cors():
    """
    Objectif : Comprendre et simuler le mécanisme CORS.
    On va envoyer des requêtes avec le header Origin et observer
    les headers Access-Control-* dans les réponses de httpbin.org.

    httpbin.org/get répond toujours avec CORS activé.
    """
    titre("EXERCICE 5 : Observer CORS")

    # --- TODO 5.1 ---
    # Envoyez une requête GET vers https://httpbin.org/get
    # avec le header Origin: https://monapp.com
    # Affichez les headers Access-Control-* dans la réponse
    print("\n[TODO 5.1] Requête avec Origin header")
    # code, headers_rep, body = requete(
    #     "GET", "https://httpbin.org/get",
    #     headers={"Origin": "https://monapp.com"}
    # )
    # print(f"Code : {code}")
    # print("Headers CORS dans la réponse :")
    # for nom, val in headers_rep.items():
    #     if nom.lower().startswith("access-control"):
    #         print(f"  {nom}: {val}")

    # --- TODO 5.2 ---
    # Simulez une requête OPTIONS (preflight CORS)
    # vers https://httpbin.org/put (méthode qui requiert un preflight)
    # Envoyez les headers de preflight standards :
    #   Origin: https://monapp.com
    #   Access-Control-Request-Method: PUT
    #   Access-Control-Request-Headers: Authorization, Content-Type
    # Affichez tous les headers Access-Control-* de la réponse
    print("\n[TODO 5.2] Requête OPTIONS (preflight CORS)")
    # headers_preflight = {
    #     "Origin": "https://monapp.com",
    #     "Access-Control-Request-Method": "PUT",
    #     "Access-Control-Request-Headers": "Authorization, Content-Type",
    # }
    # req = urllib.request.Request(
    #     "https://httpbin.org/put",
    #     method="OPTIONS",
    #     headers=headers_preflight
    # )
    # try:
    #     with urllib.request.urlopen(req) as r:
    #         print(f"Code preflight : {r.status}")
    #         print("Headers CORS de la réponse preflight :")
    #         for nom, val in r.headers.items():
    #             if nom.lower().startswith("access-control"):
    #                 print(f"  {nom}: {val}")
    # except urllib.error.HTTPError as e:
    #     print(f"Code preflight : {e.code}")
    #     for nom, val in e.headers.items():
    #         if nom.lower().startswith("access-control"):
    #             print(f"  {nom}: {val}")

    # --- TODO 5.3 ---
    # Implémentez verifier_cors_autorise(origin, headers_reponse) qui
    # retourne True si l'origine est autorisée selon les headers CORS
    print("\n[TODO 5.3] Vérifier si une origine est autorisée par CORS")
    def verifier_cors_autorise(origin, headers_reponse):
        """
        Vérifie si une origine est autorisée selon les headers CORS.

        Retourne True si :
        - Access-Control-Allow-Origin == origin, OU
        - Access-Control-Allow-Origin == "*"
        """
        # TODO : Implémentez cette fonction
        allow_origin = headers_reponse.get("Access-Control-Allow-Origin", "")
        # ...
        pass

    # Tests :
    # headers_ok = {"Access-Control-Allow-Origin": "https://monapp.com"}
    # headers_wildcard = {"Access-Control-Allow-Origin": "*"}
    # headers_autre = {"Access-Control-Allow-Origin": "https://autreapp.com"}
    # headers_absent = {}

    # print(verifier_cors_autorise("https://monapp.com", headers_ok))       # True
    # print(verifier_cors_autorise("https://monapp.com", headers_wildcard))  # True
    # print(verifier_cors_autorise("https://monapp.com", headers_autre))     # False
    # print(verifier_cors_autorise("https://monapp.com", headers_absent))    # False


# ==============================================================================
# EXERCICE 6 (BONUS) : Mini-framework de headers
# ==============================================================================

def exercice_6_mini_framework():
    """
    Objectif : Construire un petit utilitaire de gestion de headers HTTP.
    """
    titre("EXERCICE 6 (BONUS) : Mini-framework de headers")

    # --- TODO 6.1 ---
    # Implémentez la classe HeaderBuilder qui facilite la construction
    # d'un dictionnaire de headers
    print("\n[TODO 6.1] Classe HeaderBuilder")
    class HeaderBuilder:
        """
        Facilitateur pour construire des headers HTTP.

        Usage :
            headers = (HeaderBuilder()
                .accepter("application/json")
                .autorisation_bearer("mon-token")
                .langue("fr-FR")
                .construire())
        """
        def __init__(self):
            self._headers = {}

        def accepter(self, content_type):
            """Définit le header Accept."""
            # TODO : self._headers["Accept"] = content_type; return self
            pass

        def autorisation_bearer(self, token):
            """Définit le header Authorization avec un Bearer token."""
            # TODO
            pass

        def autorisation_basic(self, username, password):
            """Définit le header Authorization avec Basic Auth."""
            # TODO : utilisez base64.b64encode
            pass

        def content_type(self, ct):
            """Définit le Content-Type."""
            # TODO
            pass

        def langue(self, lang):
            """Définit Accept-Language."""
            # TODO
            pass

        def custom(self, nom, valeur):
            """Ajoute un header personnalisé."""
            # TODO
            pass

        def construire(self):
            """Retourne le dictionnaire de headers."""
            return dict(self._headers)

    # Test du HeaderBuilder :
    # headers = (HeaderBuilder()
    #     .accepter("application/json")
    #     .autorisation_bearer("mon-super-token")
    #     .langue("fr-FR, fr;q=0.9")
    #     .custom("X-App-Version", "2.1")
    #     .construire())
    # print(f"Headers construits : {json.dumps(headers, indent=2)}")
    #
    # # Utiliser avec une vraie requête :
    # code, _, body = requete("GET", "https://httpbin.org/headers", headers=headers)
    # print(f"Headers vus par httpbin : {body['headers']}")


# ==============================================================================
# FONCTION PRINCIPALE DE TEST
# ==============================================================================

def tester():
    """
    Lance tous les exercices.
    Décommentez les lignes dans chaque exercice pour voir les résultats.
    """
    print("\n" + "#"*60)
    print("#  JOUR 09 — Tests : Headers HTTP")
    print("#"*60)

    print("\nNOTE : Ce fichier se connecte à httpbin.org")
    print("       Assurez-vous d'avoir une connexion Internet.\n")

    # Vérification de connectivité
    try:
        with urllib.request.urlopen("https://httpbin.org/get", timeout=10) as r:
            print(f"Connexion a httpbin.org : OK (code {r.status})\n")
    except Exception as e:
        print(f"ATTENTION : Impossible de joindre httpbin.org : {e}")
        return

    exercice_1_envoyer_headers()
    exercice_2_authentification()
    exercice_3_content_negotiation()
    exercice_4_analyser_reponses()
    exercice_5_cors()
    exercice_6_mini_framework()

    print("\n" + "="*60)
    print("CHECKLIST FINAL")
    print("="*60)
    questions = [
        "1. Quelle est la différence entre Content-Type et Accept ?",
        "2. Pourquoi ne pas utiliser Basic Auth sans HTTPS ?",
        "3. Qu'est-ce qu'un preflight CORS et quand est-il déclenché ?",
        "4. Pourquoi mettre HttpOnly sur un cookie de session ?",
        "5. Quelle est la différence entre SameSite=Strict et SameSite=Lax ?",
        "6. Quand utiliser ETag vs Last-Modified ?",
        "7. Que signifie 'Access-Control-Allow-Origin: *' et quand est-ce dangereux ?",
        "8. Comment Content-Type et Accept permettent-ils la négociation de contenu ?",
    ]
    for q in questions:
        print(f"  {q}")
    print()


if __name__ == "__main__":
    tester()
