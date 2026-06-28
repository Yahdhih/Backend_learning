"""
Jour 08 — Exercices : Méthodes HTTP, Idempotence et Codes de Statut
Date : 4 juillet 2026

Instructions :
- Complétez chaque TODO
- Lancez tester() pour vérifier vos réponses
- Utilisez uniquement urllib.request (bibliothèque standard, pas de pip requis)
- Les requêtes vont vers httpbin.org, une API publique de test HTTP
"""

import urllib.request
import urllib.error
import json
import time


# ==============================================================================
# UTILITAIRES DE BASE
# (Ces fonctions sont données — lisez-les pour comprendre leur fonctionnement)
# ==============================================================================

def requete(methode, url, donnees=None, headers=None):
    """
    Effectue une requête HTTP et retourne (code_statut, headers, body_dict).
    Gère les erreurs 4xx et 5xx proprement.
    """
    body_bytes = None
    if donnees is not None:
        body_bytes = json.dumps(donnees).encode("utf-8")

    h = {"Content-Type": "application/json"} if donnees else {}
    if headers:
        h.update(headers)

    req = urllib.request.Request(url, data=body_bytes, method=methode, headers=h)

    try:
        with urllib.request.urlopen(req) as reponse:
            body_raw = reponse.read().decode("utf-8")
            try:
                body = json.loads(body_raw)
            except json.JSONDecodeError:
                body = {"raw": body_raw}
            return reponse.status, dict(reponse.headers), body
    except urllib.error.HTTPError as e:
        body_raw = e.read().decode("utf-8")
        try:
            body = json.loads(body_raw)
        except json.JSONDecodeError:
            body = {"raw": body_raw}
        return e.code, dict(e.headers), body


def afficher_reponse(titre, code, headers, body):
    """Affiche une réponse HTTP de façon lisible."""
    print(f"\n{'='*60}")
    print(f"  {titre}")
    print(f"{'='*60}")
    print(f"  Statut : {code}")
    print(f"  Headers clés :")
    for k in ["Content-Type", "Server", "Date"]:
        if k in headers:
            print(f"    {k}: {headers[k]}")
    print(f"  Body (extrait) :")
    body_str = json.dumps(body, indent=2, ensure_ascii=False)
    lignes = body_str.split("\n")[:15]  # 15 premières lignes
    for ligne in lignes:
        print(f"    {ligne}")
    if len(body_str.split("\n")) > 15:
        print("    ...")
    print()


# ==============================================================================
# EXERCICE 1 : Faire des requêtes avec différentes méthodes
# ==============================================================================

def exercice_1_methodes_http():
    """
    Objectif : Utiliser GET, POST, PUT, PATCH, DELETE avec httpbin.org
    httpbin.org est une API de test qui renvoie les données de la requête.

    URLs utiles :
    - GET    https://httpbin.org/get
    - POST   https://httpbin.org/post
    - PUT    https://httpbin.org/put
    - PATCH  https://httpbin.org/patch
    - DELETE https://httpbin.org/delete
    """
    print("\n" + "="*60)
    print("EXERCICE 1 : Les méthodes HTTP")
    print("="*60)

    # --- TODO 1.1 ---
    # Faites une requête GET vers https://httpbin.org/get
    # Affichez le code de statut et l'URL dans le body (clé "url")
    print("\n[TODO 1.1] GET /get")
    # code, headers, body = requete("GET", "https://httpbin.org/get")
    # print(f"Code : {code}")
    # print(f"URL confirmée par httpbin : {body['url']}")

    # --- TODO 1.2 ---
    # Faites une requête POST vers https://httpbin.org/post
    # Envoyez {"nom": "Alice", "role": "admin"}
    # Affichez le code de statut et les données JSON reçues par httpbin (clé "json")
    print("\n[TODO 1.2] POST /post avec données")
    # donnees = {"nom": "Alice", "role": "admin"}
    # code, headers, body = requete("POST", "https://httpbin.org/post", donnees)
    # print(f"Code : {code}")
    # print(f"Données reçues par httpbin : {body['json']}")

    # --- TODO 1.3 ---
    # Faites une requête PUT vers https://httpbin.org/put
    # Envoyez {"id": 42, "nom": "Bob", "email": "bob@exemple.com"}
    # Affichez le code et les données JSON dans la réponse
    print("\n[TODO 1.3] PUT /put")
    # donnees = {"id": 42, "nom": "Bob", "email": "bob@exemple.com"}
    # ...

    # --- TODO 1.4 ---
    # Faites une requête PATCH vers https://httpbin.org/patch
    # Envoyez uniquement {"email": "nouveau@exemple.com"} (modification partielle)
    # Affichez le code et les données reçues
    print("\n[TODO 1.4] PATCH /patch")
    # ...

    # --- TODO 1.5 ---
    # Faites une requête DELETE vers https://httpbin.org/delete
    # Affichez le code de statut
    # (Pas de body à envoyer pour DELETE)
    print("\n[TODO 1.5] DELETE /delete")
    # req_delete = urllib.request.Request("https://httpbin.org/delete", method="DELETE")
    # with urllib.request.urlopen(req_delete) as r:
    #     print(f"Code : {r.status}")

    # --- TODO 1.6 ---
    # Faites une requête HEAD vers https://httpbin.org/get
    # HEAD doit retourner les mêmes headers que GET mais SANS body
    # Vérifiez que le body est vide (longueur 0) et affichez les headers
    print("\n[TODO 1.6] HEAD /get (headers sans body)")
    # req_head = urllib.request.Request("https://httpbin.org/get", method="HEAD")
    # with urllib.request.urlopen(req_head) as r:
    #     print(f"Code : {r.status}")
    #     body_head = r.read()
    #     print(f"Longueur du body : {len(body_head)} octets (doit être 0)")
    #     print(f"Content-Type : {r.headers['Content-Type']}")


# ==============================================================================
# EXERCICE 2 : Tester l'idempotence
# ==============================================================================

def exercice_2_idempotence():
    """
    Objectif : Vérifier empiriquement l'idempotence de PUT et la
    non-idempotence de POST.

    Un appel est idempotent si l'état final du serveur est identique
    après 1 appel ou N appels.

    httpbin.org renvoie dans le body les données qu'on lui envoie,
    ce qui nous permet de vérifier que PUT produit toujours la même réponse.
    """
    print("\n" + "="*60)
    print("EXERCICE 2 : Idempotence")
    print("="*60)

    # --- TODO 2.1 ---
    # Appelez PUT https://httpbin.org/put 3 fois avec les mêmes données
    # {"ressource": "article", "id": 42, "titre": "Mon titre"}
    # Comparez les champs "json" dans chaque réponse
    # Ils doivent être IDENTIQUES (PUT est idempotent)
    # Affichez True si les 3 réponses ont le même "json", False sinon
    print("\n[TODO 2.1] PUT 3 fois — est-ce idempotent ?")
    # donnees_put = {"ressource": "article", "id": 42, "titre": "Mon titre"}
    # resultats_put = []
    # for i in range(3):
    #     code, headers, body = requete("PUT", "https://httpbin.org/put", donnees_put)
    #     resultats_put.append(body["json"])
    #     print(f"  Appel {i+1} : {body['json']}")
    # idempotent = resultats_put[0] == resultats_put[1] == resultats_put[2]
    # print(f"  PUT est idempotent : {idempotent}")

    # --- TODO 2.2 ---
    # Appelez POST https://httpbin.org/post 3 fois avec les mêmes données
    # {"action": "creer_commentaire", "texte": "Super !"}
    # Affichez les 3 réponses — dans un vrai serveur, chaque POST créerait un
    # objet différent (avec un nouvel ID). httpbin.org renvoie la même réponse
    # mais notez que dans une vraie API, ce comportement différerait.
    # Expliquez en commentaire pourquoi POST n'est PAS idempotent dans une vraie API.
    print("\n[TODO 2.2] POST 3 fois — pourquoi n'est-ce pas idempotent ?")
    # donnees_post = {"action": "creer_commentaire", "texte": "Super !"}
    # for i in range(3):
    #     code, _, body = requete("POST", "https://httpbin.org/post", donnees_post)
    #     print(f"  Appel {i+1} — Code: {code}")
    # # Explication : Dans une vraie API, chaque POST /commentaires créerait un
    # # nouveau commentaire avec un nouvel ID. Appeler 3 fois POST créerait 3 commentaires.
    # # Appeler 3 fois PUT /commentaires/42 ne modifierait l'article 42 qu'une seule fois.

    # --- TODO 2.3 ---
    # Démontrez qu'un DELETE est idempotent :
    # - Premier DELETE : ressource supprimée → 200 (httpbin répond 200)
    # - Dans une vraie API, le 2ème DELETE renverrait 404 (ressource déjà supprimée)
    # - Mais l'ÉTAT du serveur est le même : la ressource n'existe plus
    # Affichez les codes de DELETE appelé 2 fois et expliquez en commentaire
    # pourquoi DELETE reste idempotent même si le code change de 200 à 404.
    print("\n[TODO 2.3] DELETE est-il idempotent ? (expliquez)")
    # # Avec httpbin, les 2 appels renvoient 200 mais le concept important est :
    # for i in range(2):
    #     code, _, _ = requete("DELETE", "https://httpbin.org/delete")
    #     print(f"  DELETE appel {i+1} : Code {code}")
    # # Explication : DELETE est idempotent car l'état final du serveur est le même :
    # # la ressource est absente. Le code 404 au 2ème appel indique juste que
    # # l'état était déjà le bon — la ressource était déjà supprimée.


# ==============================================================================
# EXERCICE 3 : Codes de statut HTTP
# ==============================================================================

def exercice_3_codes_statut():
    """
    Objectif : Comprendre les codes de statut en les observant réellement.
    httpbin.org/status/{code} permet de forcer n'importe quel code de statut.
    """
    print("\n" + "="*60)
    print("EXERCICE 3 : Codes de statut")
    print("="*60)

    # --- TODO 3.1 ---
    # Demandez ces codes de statut à httpbin.org/status/{code}
    # et affichez pour chaque : code + interprétation (ce que ça signifie)
    # Codes à tester : 200, 201, 204, 301, 400, 401, 403, 404, 422, 429, 500, 503
    codes_a_tester = [200, 201, 204, 301, 400, 401, 403, 404, 422, 429, 500, 503]
    interpretations = {
        200: "OK — Succès standard",
        201: "Created — Ressource créée",
        204: "No Content — Succès sans body",
        301: "Moved Permanently — Redirection permanente",
        400: "Bad Request — Requête malformée",
        401: "Unauthorized — Non authentifié",
        403: "Forbidden — Authentifié mais non autorisé",
        404: "Not Found — Ressource inexistante",
        422: "Unprocessable Entity — Validation échouée",
        429: "Too Many Requests — Rate limit dépassé",
        500: "Internal Server Error — Bug côté serveur",
        503: "Service Unavailable — Serveur indisponible",
    }

    print("\n[TODO 3.1] Observer les codes de statut")
    # for code in codes_a_tester:
    #     url = f"https://httpbin.org/status/{code}"
    #     req = urllib.request.Request(url)
    #     try:
    #         with urllib.request.urlopen(req) as r:
    #             recu = r.status
    #     except urllib.error.HTTPError as e:
    #         recu = e.code
    #     interpretation = interpretations.get(code, "???")
    #     print(f"  {recu} — {interpretation}")

    # --- TODO 3.2 ---
    # Écrivez une fonction classifier_code(code) qui retourne la famille du code :
    # "Informationnel" pour 1xx
    # "Succès" pour 2xx
    # "Redirection" pour 3xx
    # "Erreur client" pour 4xx
    # "Erreur serveur" pour 5xx
    # Testez-la avec les codes : 100, 200, 204, 302, 404, 422, 500, 503
    print("\n[TODO 3.2] Classifier les codes de statut")
    def classifier_code(code):
        # TODO : Implémentez cette fonction
        # Indice : utilisez la division entière code // 100
        pass

    # codes_test = [100, 200, 204, 302, 404, 422, 500, 503]
    # for c in codes_test:
    #     print(f"  {c} → {classifier_code(c)}")

    # --- TODO 3.3 ---
    # Distinguez 401 et 403 :
    # Faites une requête vers https://httpbin.org/status/401
    # Faites une requête vers https://httpbin.org/status/403
    # Expliquez en commentaire la différence dans le contexte d'une API Django
    print("\n[TODO 3.3] 401 vs 403 — quelle différence ?")
    # for code in [401, 403]:
    #     url = f"https://httpbin.org/status/{code}"
    #     req = urllib.request.Request(url)
    #     try:
    #         urllib.request.urlopen(req)
    #     except urllib.error.HTTPError as e:
    #         print(f"  Code reçu : {e.code} — {e.reason}")
    # # 401 = Non authentifié : l'utilisateur n'a pas fourni de credentials valides
    # # 403 = Non autorisé : l'utilisateur est identifié mais n'a pas les droits
    # # Exemple Django : 401 si le token JWT est absent, 403 si token valide mais rôle insuffisant


# ==============================================================================
# EXERCICE 4 : Mini-analyse d'une API réelle
# ==============================================================================

def exercice_4_analyse_api():
    """
    Objectif : Explorer l'API publique de JSONPlaceholder (https://jsonplaceholder.typicode.com)
    C'est une fausse API REST de démonstration, idéale pour s'entraîner.

    Endpoints disponibles :
    - GET  /posts          → liste de posts
    - GET  /posts/1        → post #1
    - POST /posts          → créer un post (simulé)
    - PUT  /posts/1        → remplacer post #1 (simulé)
    - DELETE /posts/1      → supprimer post #1 (simulé)
    """
    BASE = "https://jsonplaceholder.typicode.com"
    print("\n" + "="*60)
    print("EXERCICE 4 : Explorer JSONPlaceholder")
    print("="*60)

    # --- TODO 4.1 ---
    # Récupérez la liste de tous les posts (GET /posts)
    # Affichez le nombre de posts reçus et les champs du premier post
    print("\n[TODO 4.1] GET /posts — combien de posts ?")
    # code, headers, body = requete("GET", BASE + "/posts")
    # print(f"  Code : {code}")
    # print(f"  Nombre de posts : {len(body)}")
    # print(f"  Clés du premier post : {list(body[0].keys())}")

    # --- TODO 4.2 ---
    # Récupérez uniquement le post #5 (GET /posts/5)
    # Affichez son titre et son userId
    print("\n[TODO 4.2] GET /posts/5 — détails du post")
    # code, headers, body = requete("GET", BASE + "/posts/5")
    # print(f"  Code : {code}")
    # print(f"  Titre : {body['title']}")
    # print(f"  UserId : {body['userId']}")

    # --- TODO 4.3 ---
    # Créez un nouveau post (POST /posts)
    # Envoyez : {"title": "Mon super post", "body": "Contenu de mon post", "userId": 1}
    # Affichez le code de statut (devrait être 201) et l'ID attribué
    print("\n[TODO 4.3] POST /posts — créer un nouveau post")
    # nouveau_post = {
    #     "title": "Mon super post",
    #     "body": "Contenu de mon post",
    #     "userId": 1
    # }
    # code, headers, body = requete("POST", BASE + "/posts", nouveau_post)
    # print(f"  Code : {code}")
    # print(f"  Post créé avec ID : {body.get('id')}")

    # --- TODO 4.4 ---
    # Remplacez entièrement le post #1 (PUT /posts/1)
    # Envoyez tous les champs : {"id": 1, "title": "Nouveau titre", "body": "...", "userId": 1}
    # Puis modifiez partiellement le même post (PATCH /posts/1)
    # Envoyez seulement : {"title": "Titre mis à jour via PATCH"}
    # Comparez les deux réponses
    print("\n[TODO 4.4] PUT puis PATCH — quelle différence dans la réponse ?")
    # # PUT — remplacement total
    # put_data = {"id": 1, "title": "Nouveau titre complet", "body": "Corps complet", "userId": 1}
    # code_put, _, body_put = requete("PUT", BASE + "/posts/1", put_data)
    # print(f"  PUT code : {code_put}, réponse : {body_put}")
    # # PATCH — modification partielle
    # patch_data = {"title": "Titre mis à jour via PATCH"}
    # code_patch, _, body_patch = requete("PATCH", BASE + "/posts/1", patch_data)
    # print(f"  PATCH code : {code_patch}, réponse : {body_patch}")

    # --- TODO 4.5 ---
    # Supprimez le post #1 (DELETE /posts/1)
    # Affichez le code de statut (devrait être 200 ou 204)
    # Tentez ensuite de récupérer ce même post — qu'obtient-on ?
    # (JSONPlaceholder simule la suppression mais retourne quand même le post pour les tests)
    print("\n[TODO 4.5] DELETE /posts/1 puis GET /posts/1")
    # req_del = urllib.request.Request(BASE + "/posts/1", method="DELETE")
    # with urllib.request.urlopen(req_del) as r:
    #     print(f"  DELETE code : {r.status}")
    # code_get, _, body_get = requete("GET", BASE + "/posts/1")
    # print(f"  GET après DELETE code : {code_get}")
    # # Note : JSONPlaceholder simule — en vraie API, on aurait 404


# ==============================================================================
# EXERCICE 5 (BONUS) : Implémenter un retry intelligent
# ==============================================================================

def exercice_5_retry():
    """
    Objectif : Écrire une fonction de retry qui respecte les principes HTTP.

    Règles d'un retry correct :
    - On ne retente que si la méthode est idempotente (GET, PUT, DELETE, HEAD)
    - On ne retente pas POST (non idempotent)
    - On retente les erreurs 5xx (erreurs serveur transitoires)
    - On ne retente pas les erreurs 4xx (erreurs client permanentes)
    - On respecte le header Retry-After si présent
    """
    print("\n" + "="*60)
    print("EXERCICE 5 (BONUS) : Retry intelligent")
    print("="*60)

    # --- TODO 5.1 ---
    # Implémentez la fonction requete_avec_retry ci-dessous
    def requete_avec_retry(methode, url, donnees=None, max_tentatives=3, delai=1.0):
        """
        Effectue une requête HTTP avec retry pour les erreurs 5xx.
        Ne retente que si la méthode est idempotente.

        Retourne (code, headers, body) comme la fonction requete().
        """
        # TODO : Implémentez cette logique :
        # 1. Vérifiez si la méthode est idempotente
        #    methodes_idempotentes = {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}
        # 2. Si non idempotente → faites la requête une seule fois, retournez le résultat
        # 3. Si idempotente → boucle de max_tentatives tentatives :
        #    - Faites la requête
        #    - Si code < 500 → retournez le résultat
        #    - Si code >= 500 → attendez delai secondes et réessayez
        # 4. Après max_tentatives échecs → retournez le dernier résultat
        pass

    # --- TODO 5.2 ---
    # Testez requete_avec_retry sur un endpoint qui fonctionne
    # Affichez combien de tentatives ont été nécessaires
    print("\n[TODO 5.2] Test de retry sur un endpoint valide")
    # code, _, body = requete_avec_retry("GET", "https://httpbin.org/get")
    # print(f"  Résultat : {code}")

    # --- TODO 5.3 ---
    # Testez que POST n'est jamais retenté même en cas d'erreur
    # Que se passe-t-il si vous appelez requete_avec_retry("POST", ...) ?
    print("\n[TODO 5.3] POST n'est pas retenté (vérification)")
    # code, _, _ = requete_avec_retry("POST", "https://httpbin.org/post",
    #                                  {"data": "test"}, max_tentatives=3)
    # print(f"  POST code : {code} (jamais retenté)")


# ==============================================================================
# FONCTION PRINCIPALE DE TEST
# ==============================================================================

def tester():
    """
    Lance tous les exercices et vérifie les résultats.
    Décommentez les TODO dans chaque exercice pour que les tests fonctionnent.
    """
    print("\n" + "#"*60)
    print("#  JOUR 08 — Tests : Méthodes HTTP et Codes de Statut")
    print("#"*60)

    print("\nNOTE : Ce fichier se connecte à httpbin.org et jsonplaceholder.typicode.com")
    print("       Assurez-vous d'avoir une connexion Internet.\n")

    # Vérification de connectivité
    try:
        with urllib.request.urlopen("https://httpbin.org/get", timeout=10) as r:
            print(f"Connexion a httpbin.org : OK (code {r.status})")
    except Exception as e:
        print(f"ATTENTION : Impossible de joindre httpbin.org : {e}")
        print("Les exercices nécessitent une connexion Internet.")
        return

    try:
        exercice_1_methodes_http()
        print("Exercice 1 : Lancé (décommentez les TODO pour voir les résultats)")
    except Exception as e:
        print(f"Exercice 1 erreur : {e}")

    try:
        exercice_2_idempotence()
        print("Exercice 2 : Lancé")
    except Exception as e:
        print(f"Exercice 2 erreur : {e}")

    try:
        exercice_3_codes_statut()
        print("Exercice 3 : Lancé")
    except Exception as e:
        print(f"Exercice 3 erreur : {e}")

    try:
        exercice_4_analyse_api()
        print("Exercice 4 : Lancé")
    except Exception as e:
        print(f"Exercice 4 erreur : {e}")

    try:
        exercice_5_retry()
        print("Exercice 5 (BONUS) : Lancé")
    except Exception as e:
        print(f"Exercice 5 erreur : {e}")

    print("\n" + "="*60)
    print("CHECKLIST FINAL — Répondez mentalement :")
    print("="*60)
    questions = [
        "1. Quelle est la différence entre PUT et PATCH ?",
        "2. Pourquoi POST n'est-il pas idempotent ?",
        "3. Quelle méthode utiliser pour vérifier qu'un fichier existe sans le télécharger ?",
        "4. Quelle est la différence entre 401 et 403 ?",
        "5. Quel code retourner après un POST qui crée une ressource ?",
        "6. Quelle famille de codes indique une erreur du CLIENT ?",
        "7. GET est-il safe ? Est-il idempotent ?",
        "8. Dans quel cas utiliser 422 plutôt que 400 ?",
    ]
    for q in questions:
        print(f"  {q}")
    print()


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

if __name__ == "__main__":
    tester()
