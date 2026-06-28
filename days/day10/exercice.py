"""
Jour 10 — Exercices : HTTPS et TLS
Date : 6 juillet 2026

Instructions :
- Complétez chaque TODO
- Lancez tester() pour vérifier vos réponses
- Utilisez uniquement la bibliothèque standard : ssl, socket, urllib
- Les exercices inspectent de vrais sites web publics
"""

import ssl
import socket
import urllib.request
import urllib.error
import json
from datetime import datetime


# ==============================================================================
# UTILITAIRES
# ==============================================================================

def titre(texte):
    print(f"\n{'='*60}")
    print(f"  {texte}")
    print(f"{'='*60}")


def obtenir_cert(hostname, port=443, timeout=10):
    """
    Établit une connexion TLS avec le serveur et retourne
    (cert_dict, cipher_info, tls_version).
    """
    contexte = ssl.create_default_context()
    with socket.create_connection((hostname, port), timeout=timeout) as sock:
        with contexte.wrap_socket(sock, server_hostname=hostname) as tls_sock:
            cert = tls_sock.getpeercert()
            cipher = tls_sock.cipher()
            version = tls_sock.version()
            return cert, cipher, version


# ==============================================================================
# EXERCICE 1 : Inspecter des certificats de vrais sites
# ==============================================================================

def exercice_1_inspecter_certificats():
    """
    Objectif : Utiliser le module ssl pour inspecter les certificats
    de sites web réels et extraire des informations utiles.
    """
    titre("EXERCICE 1 : Inspecter des certificats TLS")

    sites = [
        "www.google.com",
        "www.python.org",
        "github.com",
    ]

    # --- TODO 1.1 ---
    # Pour chaque site dans la liste :
    # 1. Connectez-vous en TLS avec obtenir_cert()
    # 2. Affichez : CN du sujet, nom de l'émetteur, dates de validité
    # 3. Calculez le nombre de jours avant expiration
    print("\n[TODO 1.1] Inspecter les certificats de plusieurs sites")
    # for hostname in sites:
    #     try:
    #         cert, cipher, version = obtenir_cert(hostname)
    #
    #         sujet = dict(x[0] for x in cert["subject"])
    #         emetteur = dict(x[0] for x in cert["issuer"])
    #
    #         not_after_ts = ssl.cert_time_to_seconds(cert["notAfter"])
    #         expiration = datetime.fromtimestamp(not_after_ts)
    #         jours = (expiration - datetime.now()).days
    #
    #         print(f"\n  {hostname}")
    #         print(f"    CN sujet  : {sujet.get('commonName', 'N/A')}")
    #         print(f"    Émetteur  : {emetteur.get('commonName', 'N/A')}")
    #         print(f"    Expire le : {cert['notAfter']}")
    #         print(f"    Jours restants : {jours}")
    #     except Exception as e:
    #         print(f"  {hostname} : Erreur — {e}")

    # --- TODO 1.2 ---
    # Pour www.python.org, affichez les Subject Alternative Names (SAN)
    # Ce sont les domaines supplémentaires couverts par le certificat
    print("\n[TODO 1.2] Subject Alternative Names de python.org")
    # cert, _, _ = obtenir_cert("www.python.org")
    # san = cert.get("subjectAltName", [])
    # domaines_dns = [valeur for type_, valeur in san if type_ == "DNS"]
    # print(f"  Domaines couverts : {domaines_dns}")

    # --- TODO 1.3 ---
    # Implémentez certificat_valide(hostname) qui retourne un tuple
    # (est_valide: bool, raison: str) indiquant si le cert est valide et non expiré
    print("\n[TODO 1.3] Vérifier la validité d'un certificat")
    def certificat_valide(hostname, port=443):
        """
        Vérifie si le certificat d'un serveur est valide et non expiré.

        Retourne (True, "OK") ou (False, "raison de l'erreur").
        """
        # TODO : Implémentez cette fonction
        # 1. Tentez de vous connecter avec obtenir_cert()
        # 2. Si la connexion réussit → le certificat est valide
        #    (ssl.create_default_context() vérifie automatiquement)
        # 3. Vérifiez que le cert expire dans plus de 0 jours
        # 4. Capturez ssl.SSLError pour les certs invalides
        # 5. Retournez (True, "OK") ou (False, "description de l'erreur")
        pass

    # Sites de test (badssl.com fournit des certs intentionnellement mauvais) :
    # tests = [
    #     ("www.python.org", "Devrait être valide"),
    #     ("expired.badssl.com", "Devrait être expiré"),
    #     ("self-signed.badssl.com", "Devrait être auto-signé"),
    # ]
    # for hostname, description in tests:
    #     try:
    #         valide, raison = certificat_valide(hostname)
    #         print(f"  {hostname} : valide={valide}, raison={raison}")
    #         print(f"    (attendu : {description})")
    #     except Exception as e:
    #         print(f"  {hostname} : exception — {e}")


# ==============================================================================
# EXERCICE 2 : Analyser les suites cryptographiques
# ==============================================================================

def exercice_2_suites_crypto():
    """
    Objectif : Comprendre et analyser les suites cryptographiques TLS.
    Une suite crypto = combinaison d'algorithmes pour le handshake et le chiffrement.
    """
    titre("EXERCICE 2 : Suites cryptographiques TLS")

    # --- TODO 2.1 ---
    # Pour chaque site, récupérez et affichez :
    # - La version TLS utilisée (TLSv1.2 ou TLSv1.3)
    # - La suite cryptographique
    # - Le nombre de bits de chiffrement
    sites = ["www.google.com", "www.github.com", "api.github.com"]
    print("\n[TODO 2.1] Versions TLS et suites crypto")
    # for hostname in sites:
    #     try:
    #         cert, cipher_info, version = obtenir_cert(hostname)
    #         nom_suite, protocole, bits = cipher_info
    #         print(f"\n  {hostname}")
    #         print(f"    Version TLS  : {version}")
    #         print(f"    Suite crypto : {nom_suite}")
    #         print(f"    Bits         : {bits}")
    #     except Exception as e:
    #         print(f"  {hostname} : {e}")

    # --- TODO 2.2 ---
    # Implémentez analyser_suite_crypto(nom_suite) qui parse le nom
    # d'une suite cryptographique et retourne ses composants.
    #
    # Exemples de noms :
    # - "TLS_AES_256_GCM_SHA384" (TLS 1.3)
    # - "ECDHE-RSA-AES256-GCM-SHA384" (TLS 1.2)
    # - "TLS_CHACHA20_POLY1305_SHA256" (TLS 1.3)
    print("\n[TODO 2.2] Parser le nom d'une suite cryptographique")
    def analyser_suite_crypto(nom_suite):
        """
        Parse le nom d'une suite crypto TLS.

        Pour TLS 1.3 (format: TLS_ALGO_MODE_HASH) :
        → {"version": "TLS 1.3", "chiffrement": "AES-256-GCM", "hash": "SHA384"}

        Pour TLS 1.2 (format: ECHANGE-AUTH-CHIFFRE-HASH) :
        → {"version": "TLS 1.2", "echange_cle": "ECDHE", "auth": "RSA",
           "chiffrement": "AES256-GCM", "hash": "SHA384"}

        Retournez au moins {"nom_complet": nom_suite, "bits_connus": bool}
        """
        # TODO : Implémentez cette fonction
        # Indice : TLS 1.3 commence toujours par "TLS_"
        pass

    # Tests :
    # suites_test = [
    #     "TLS_AES_256_GCM_SHA384",
    #     "TLS_CHACHA20_POLY1305_SHA256",
    #     "ECDHE-RSA-AES256-GCM-SHA384",
    #     "ECDHE-ECDSA-AES128-GCM-SHA256",
    # ]
    # for suite in suites_test:
    #     print(f"  {suite}")
    #     print(f"  → {analyser_suite_crypto(suite)}")

    # --- TODO 2.3 ---
    # Comparez les suites de google.com et python.org.
    # Utilisez TLS 1.3 ou TLS 1.2 ? Quel algorithme de chiffrement ?
    # Affichez un rapport comparatif.
    print("\n[TODO 2.3] Comparaison google.com vs python.org")
    # for hostname in ["www.google.com", "www.python.org"]:
    #     try:
    #         _, cipher, version = obtenir_cert(hostname)
    #         print(f"  {hostname}: {version} | {cipher[0]} | {cipher[2]} bits")
    #     except Exception as e:
    #         print(f"  {hostname}: {e}")


# ==============================================================================
# EXERCICE 3 : Chaîne de certificats
# ==============================================================================

def exercice_3_chaine_certificats():
    """
    Objectif : Comprendre la chaîne de confiance des certificats.
    """
    titre("EXERCICE 3 : Chaîne de certificats")

    # --- TODO 3.1 ---
    # Affichez l'émetteur (issuer) d'un certificat et expliquez
    # la chaîne de confiance pour www.python.org
    # Format : Sujet → Émetteur → Émetteur de l'émetteur...
    print("\n[TODO 3.1] Lire l'émetteur d'un certificat")
    # cert, _, _ = obtenir_cert("www.python.org")
    # sujet = dict(x[0] for x in cert["subject"])
    # emetteur = dict(x[0] for x in cert["issuer"])
    # print(f"  Sujet   : {sujet.get('commonName')}")
    # print(f"    signé par")
    # print(f"  Émetteur: {emetteur.get('commonName')} (org: {emetteur.get('organizationName')})")
    # print(f"    signé par")
    # print(f"  CA racine: [stockée dans votre OS/navigateur]")

    # --- TODO 3.2 ---
    # Listez les CA racines connues de Python (ssl.get_default_verify_paths())
    # et affichez le chemin vers le fichier de CA
    print("\n[TODO 3.2] Chemins des CA de confiance dans votre système")
    # chemins = ssl.get_default_verify_paths()
    # print(f"  cafile   : {chemins.cafile}")
    # print(f"  capath   : {chemins.capath}")
    # print(f"  openssl_cafile : {chemins.openssl_cafile}")
    # print(f"  openssl_capath : {chemins.openssl_capath}")

    # --- TODO 3.3 ---
    # Utilisez ssl.enum_certificates (Windows) ou lisez le cafile
    # pour compter combien de CA racines sont installées sur votre système
    # Alternative : ssl.SSLContext().load_default_certs()
    print("\n[TODO 3.3] Compter les CA racines")
    # import os
    # chemins = ssl.get_default_verify_paths()
    # cafile = chemins.cafile or chemins.openssl_cafile
    # if cafile and os.path.exists(cafile):
    #     with open(cafile, "r") as f:
    #         contenu = f.read()
    #     nb_ca = contenu.count("BEGIN CERTIFICATE")
    #     print(f"  Nombre de CA racines : {nb_ca}")
    # else:
    #     # Utiliser ssl.create_default_context() pour compter
    #     ctx = ssl.create_default_context()
    #     print(f"  Certificats CA : {len(ctx.get_ca_certs())}")


# ==============================================================================
# EXERCICE 4 : HTTPS vs HTTP — Observer la différence
# ==============================================================================

def exercice_4_https_vs_http():
    """
    Objectif : Observer concrètement la différence entre HTTP et HTTPS.
    """
    titre("EXERCICE 4 : HTTPS vs HTTP")

    # --- TODO 4.1 ---
    # Faites une requête HTTP vers http://httpbin.org/get (sans S)
    # Puis vers https://httpbin.org/get (avec S)
    # Affichez le code de statut et les headers de réponse dans les deux cas
    # Notez que la version HTTP retourne possiblement une redirection vers HTTPS
    print("\n[TODO 4.1] Comparer HTTP et HTTPS")
    # for url in ["http://httpbin.org/get", "https://httpbin.org/get"]:
    #     try:
    #         req = urllib.request.Request(url)
    #         # Désactiver le suivi automatique des redirections pour observer
    #         # En pratique, urllib suit les redirections par défaut
    #         with urllib.request.urlopen(req, timeout=10) as r:
    #             print(f"\n  URL : {url}")
    #             print(f"  Code : {r.status}")
    #             print(f"  URL finale : {r.url}")
    #             print(f"  Protocole chiffré : {'https' in r.url}")
    #     except urllib.error.HTTPError as e:
    #         print(f"\n  URL : {url}")
    #         print(f"  Redirection : {e.code} → {e.headers.get('Location')}")

    # --- TODO 4.2 ---
    # Implémentez verifier_redirection_https(domaine) qui vérifie
    # si un site redirige HTTP → HTTPS automatiquement
    print("\n[TODO 4.2] Vérifier la redirection HTTP → HTTPS")
    def verifier_redirection_https(domaine):
        """
        Vérifie si le domaine redirige HTTP vers HTTPS.

        Retourne {
            "redirige": bool,
            "code_redirect": int ou None,
            "destination": str ou None
        }
        """
        # TODO : Implémentez cette fonction
        # 1. Envoyez une requête vers http://{domaine}/
        # 2. Regardez si le code est 301 ou 302
        # 3. Regardez le header Location
        # 4. Retournez le résultat
        # Attention : urllib suit les redirections par défaut.
        # Utilisez une classe personnalisée ou gérez HTTPError
        pass

    # Tests :
    # for domaine in ["httpbin.org", "www.python.org", "www.google.com"]:
    #     try:
    #         result = verifier_redirection_https(domaine)
    #         print(f"  {domaine}: {result}")
    #     except Exception as e:
    #         print(f"  {domaine}: erreur — {e}")

    # --- TODO 4.3 ---
    # Vérifiez la présence du header HSTS (Strict-Transport-Security)
    # sur quelques sites. Ce header indique que le navigateur doit
    # toujours utiliser HTTPS pour ce domaine.
    print("\n[TODO 4.3] Vérifier le header HSTS")
    # sites = ["www.google.com", "www.python.org", "github.com"]
    # for hostname in sites:
    #     try:
    #         req = urllib.request.Request(f"https://{hostname}/")
    #         with urllib.request.urlopen(req, timeout=10) as r:
    #             hsts = r.headers.get("Strict-Transport-Security", "Absent")
    #             print(f"  {hostname}: HSTS = {hsts}")
    #     except Exception as e:
    #         print(f"  {hostname}: {e}")


# ==============================================================================
# EXERCICE 5 : Rapport de sécurité TLS
# ==============================================================================

def exercice_5_rapport_securite():
    """
    Objectif : Créer un outil de rapport de sécurité TLS pour un domaine.
    """
    titre("EXERCICE 5 : Rapport de sécurité TLS")

    # --- TODO 5.1 ---
    # Implémentez rapport_tls(hostname) qui retourne un dictionnaire
    # avec un résumé de la sécurité TLS du serveur
    print("\n[TODO 5.1] Générer un rapport de sécurité TLS")
    def rapport_tls(hostname, port=443):
        """
        Génère un rapport de sécurité TLS pour un hostname.

        Retourne un dictionnaire avec :
        - "hostname": str
        - "version_tls": str ("TLSv1.3", "TLSv1.2", etc.)
        - "suite_crypto": str
        - "bits_chiffrement": int
        - "cn_certificat": str
        - "emetteur": str
        - "expire_dans_jours": int
        - "san_domaines": list[str]
        - "score": str ("A" si TLS 1.3, "B" si TLS 1.2, "F" si < 1.2)
        """
        # TODO : Implémentez cette fonction en utilisant obtenir_cert()
        pass

    # Tests :
    # for hostname in ["www.python.org", "api.github.com"]:
    #     try:
    #         rapport = rapport_tls(hostname)
    #         if rapport:
    #             print(f"\n  === Rapport pour {hostname} ===")
    #             for cle, valeur in rapport.items():
    #                 print(f"  {cle}: {valeur}")
    #     except Exception as e:
    #         print(f"  {hostname}: erreur — {e}")

    # --- TODO 5.2 ---
    # Comparez les rapports de 3 sites différents et déterminez
    # lequel a la configuration TLS la plus moderne (TLS 1.3 préféré)
    print("\n[TODO 5.2] Comparaison de plusieurs sites")
    # sites = ["www.google.com", "www.python.org", "httpbin.org"]
    # rapports = []
    # for hostname in sites:
    #     try:
    #         r = rapport_tls(hostname)
    #         if r:
    #             rapports.append(r)
    #             print(f"  {hostname}: {r.get('version_tls')} | Score: {r.get('score')}")
    #     except Exception as e:
    #         print(f"  {hostname}: {e}")
    #
    # # Trouver le meilleur score
    # if rapports:
    #     meilleur = max(rapports, key=lambda r: r.get("score", "F"))
    #     print(f"\n  Meilleure config TLS : {meilleur['hostname']} (score {meilleur['score']})")


# ==============================================================================
# EXERCICE 6 (BONUS) : Simuler un handshake TLS simplifié
# ==============================================================================

def exercice_6_handshake_simule():
    """
    Objectif : Comprendre le TLS handshake en simulant ses étapes
    avec des données fictives (pas de vraie cryptographie).
    """
    titre("EXERCICE 6 (BONUS) : Simulation TLS handshake")
    import os
    import hashlib

    # --- TODO 6.1 ---
    # Simulez les messages du TLS handshake en créant des classes
    # représentant chaque message
    print("\n[TODO 6.1] Simuler les messages du handshake")

    class ClientHello:
        """Simule le message ClientHello TLS."""
        def __init__(self):
            self.version_max = "TLSv1.3"
            self.client_random = os.urandom(32).hex()  # 32 bytes aléatoires
            self.suites_crypto = [
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_128_GCM_SHA256",
            ]

        def __repr__(self):
            return (f"ClientHello("
                    f"version={self.version_max}, "
                    f"random={self.client_random[:16]}..., "
                    f"suites={self.suites_crypto})")

    class ServerHello:
        """Simule le message ServerHello TLS."""
        def __init__(self, client_hello):
            self.version = "TLSv1.3"
            self.server_random = os.urandom(32).hex()
            # TODO : Choisissez la première suite crypto du client (celle préférée)
            self.suite_choisie = None  # client_hello.suites_crypto[0]

        def __repr__(self):
            return (f"ServerHello("
                    f"version={self.version}, "
                    f"random={self.server_random[:16]}..., "
                    f"suite={self.suite_choisie})")

    class MasterSecretDerive:
        """Simule la dérivation du Master Secret."""
        def __init__(self, pre_master_secret, client_random, server_random):
            # TODO : Combinez les trois valeurs avec hashlib.sha256
            # pour simuler la dérivation de clé
            # master_secret = hashlib.sha256(
            #     (pre_master_secret + client_random + server_random).encode()
            # ).hexdigest()
            self.master_secret = None

    # Simulation complète :
    # client_hello = ClientHello()
    # print(f"  Étape 1 - {client_hello}")
    #
    # server_hello = ServerHello(client_hello)
    # server_hello.suite_choisie = client_hello.suites_crypto[0]
    # print(f"  Étape 2 - {server_hello}")
    #
    # # Simuler l'échange de Pre-Master Secret
    # pre_master = os.urandom(48).hex()  # 48 bytes aléatoires
    # print(f"  Étape 3 - Pre-Master Secret: {pre_master[:16]}... (chiffré avec clé pub du serveur)")
    #
    # # Dériver le Master Secret
    # ms = MasterSecretDerive(pre_master, client_hello.client_random, server_hello.server_random)
    # # ms.master_secret = hashlib.sha256(...).hexdigest()
    # print(f"  Étape 4 - Master Secret dérivé: [clé de session symétrique]")
    # print(f"  Étape 5 - Toutes les données HTTP sont maintenant chiffrées avec cette clé")


# ==============================================================================
# FONCTION PRINCIPALE DE TEST
# ==============================================================================

def tester():
    """
    Lance tous les exercices.
    Nécessite une connexion Internet pour les exercices 1-5.
    """
    print("\n" + "#"*60)
    print("#  JOUR 10 — Tests : HTTPS et TLS")
    print("#"*60)

    print("\nVérification de la connectivité...")
    try:
        cert, cipher, version = obtenir_cert("www.python.org")
        print(f"Connexion TLS à www.python.org : OK (version {version})")
    except Exception as e:
        print(f"ATTENTION : Impossible de joindre www.python.org via TLS : {e}")
        print("Les exercices 1-5 nécessitent une connexion Internet.")

    exercice_1_inspecter_certificats()
    exercice_2_suites_crypto()
    exercice_3_chaine_certificats()
    exercice_4_https_vs_http()
    exercice_5_rapport_securite()
    exercice_6_handshake_simule()

    print("\n" + "="*60)
    print("CHECKLIST FINAL")
    print("="*60)
    questions = [
        "1. Quelle est la différence entre chiffrement symétrique et asymétrique ?",
        "2. Pourquoi TLS utilise-t-il les deux types de chiffrement ?",
        "3. Qu'est-ce qu'un certificat X.509 et que contient-il ?",
        "4. Qu'est-ce que la chaîne de certificats (certificate chain) ?",
        "5. Pourquoi Perfect Forward Secrecy est-il important ?",
        "6. Comment Let's Encrypt vérifie-t-il que vous contrôlez un domaine ?",
        "7. Quelle est la différence entre TLS 1.2 et TLS 1.3 ?",
        "8. Que signifie CERTIFICATE_VERIFY_FAILED en Python ?",
    ]
    for q in questions:
        print(f"  {q}")
    print()


if __name__ == "__main__":
    tester()
