# Jour 10 — HTTPS et TLS : Comment le chiffrement fonctionne (6 juillet 2026)

> **Durée estimée :** 30 minutes de lecture  
> **Prérequis :** Jour 09 (headers HTTP)  
> **Objectif :** Comprendre pourquoi HTTP seul est dangereux, comment TLS sécurise les communications, et comment inspecter les certificats en Python

---

## 1. Pourquoi HTTP seul est dangereux

HTTP transmet tout en **texte brut**, non chiffré. N'importe qui capable d'intercepter le trafic réseau peut lire vos données.

### 1.1 L'attaque Man-in-the-Middle (MitM)

```
Scénario HTTP (non chiffré) :
─────────────────────────────

Vous          Wi-Fi public (café)       Attaquant        Serveur
  |                   |                    |                |
  |── GET /login ──>  |                    |                |
  |                   |── GET /login ─>    |                |
  |                   |                    |── GET /login → |
  |                   |                    |<─ formulaire ──|
  |                   |<─ formulaire ─────|                |
  |<─ formulaire ───  |                    |                |
  |                   |                    |                |
  |── POST /login ──> |                    |                |
  |   mot_de_passe=   |                    |                |
  |   "secret123"     |── POST ─────────>  |                |
  |                   |   L'attaquant LIT  |                |
  |                   |   votre mot de     |                |
  |                   |   passe !          |                |
```

**Ce qu'un attaquant peut faire avec HTTP :**
- Lire vos mots de passe, tokens, données personnelles
- Modifier les pages que vous recevez (injecter du code malveillant)
- Voler vos cookies de session et usurper votre identité
- Injecter des publicités dans les pages que vous visitez

### 1.2 Ce que HTTPS résout

HTTPS = HTTP + TLS (anciennement SSL).

TLS (Transport Layer Security) fournit trois garanties :
1. **Confidentialité** : Les données sont chiffrées → l'attaquant voit du bruit aléatoire
2. **Intégrité** : Les données ne peuvent pas être modifiées en transit sans être détectées
3. **Authentification** : Vous savez avec certitude que vous communiquez avec le bon serveur (et pas un imposteur)

---

## 2. Chiffrement symétrique vs asymétrique

Comprendre TLS nécessite de comprendre deux types de chiffrement.

### 2.1 Chiffrement symétrique

> **Une seule clé** pour chiffrer ET déchiffrer.

```
Clé secrète : "clé_secrète_123"

Alice chiffre :   "Bonjour Bob"  + clé  →  "Xr7!qP#mK9"  (envoyé)
Bob déchiffre :   "Xr7!qP#mK9"  + clé  →  "Bonjour Bob"
```

**Analogie :** Un coffre-fort avec une seule clé. Les deux parties ont la même clé.

**Avantages :** Très rapide (algorithmes : AES, ChaCha20)  
**Problème :** Comment partager la clé secrète en sécurité ? Si l'attaquant intercepte l'échange initial de clé, tout est compromis.

### 2.2 Chiffrement asymétrique

> **Deux clés liées mathématiquement** : une clé publique et une clé privée.
> Ce qui est chiffré avec la clé publique ne peut être déchiffré qu'avec la clé privée.

```
Bob génère une paire de clés :
  Clé publique :  "pub_key_xyz"  (partagée avec tout le monde)
  Clé privée :    "priv_key_abc" (jamais partagée, reste chez Bob)

Alice chiffre avec la clé publique de Bob :
  "Message secret"  + pub_key_xyz  →  "^Ψ∂≈ω§" (envoyé)

Bob déchiffre avec sa clé privée :
  "^Ψ∂≈ω§"  + priv_key_abc  →  "Message secret"

L'attaquant qui intercèpte "^Ψ∂≈ω§" ne peut PAS déchiffrer
même s'il connaît pub_key_xyz !
```

**Analogie :** Un cadenas ouvert (clé publique) que vous donnez à tout le monde. Seule votre clé privée ouvre ce cadenas. N'importe qui peut vous envoyer un message verrouillé avec votre cadenas, mais seul vous pouvez l'ouvrir.

**Avantages :** Résout le problème de l'échange de clé  
**Problème :** Beaucoup plus lent que le symétrique (algorithmes : RSA, ECDH)

### 2.3 La solution hybride (ce que TLS utilise)

TLS combine les deux approches en tirant parti de leurs avantages respectifs :

1. **Asymétrique** pour s'authentifier et s'échanger une clé secrète temporaire (lent mais sécurisé pour l'échange)
2. **Symétrique** pour chiffrer toutes les vraies données (rapide)

---

## 3. Le handshake TLS — Étape par étape

C'est le processus qui se déroule en quelques millisecondes avant votre première requête HTTPS.

### 3.1 Diagramme complet

```
Client (navigateur)              Serveur (api.exemple.com)
        |                                |
        |                                |
        |====== TCP Handshake =========> |  (connexion TCP établie d'abord)
        |                                |
        |                                |
   ─────── TLS Handshake commence ────────
        |                                |
  [1]   |──── ClientHello ────────────> |
        |  • Versions TLS supportées    |
        |  • Suites cryptographiques    |
        |  • Client Random (32 bytes)   |
        |                                |
  [2]   |<─── ServerHello ─────────────|
        |  • Version TLS choisie        |
        |  • Suite crypto choisie       |
        |  • Server Random (32 bytes)   |
        |                                |
  [3]   |<─── Certificate ─────────────|
        |  • Certificat X.509 du serveur|
        |  • Contient la clé publique   |
        |                                |
  [4]   |<─── ServerHelloDone ─────────|
        |                                |
  [5]   | Vérifie le certificat :        |
        |  • Signé par une CA de confiance?|
        |  • Non expiré?                |
        |  • Domaine correspond?        |
        |                                |
  [6]   |──── ClientKeyExchange ──────> |
        |  • Pre-Master Secret chiffré  |
        |    avec la clé publique du    |
        |    serveur                    |
        |                                |
  [7]   |  Les deux parties calculent   |
        |  le Master Secret :           |
        |  f(Pre-Master, Client Random, |
        |    Server Random)             |
        |  → Clé de session symétrique  |
        |                                |
  [8]   |──── ChangeCipherSpec ───────> |
        |  "Je passe en chiffré"        |
        |                                |
  [9]   |──── Finished ───────────────> |
        |  (chiffré avec la clé session)|
        |                                |
  [10]  |<─── ChangeCipherSpec ─────────|
        |                                |
  [11]  |<─── Finished ────────────────|
        |  (chiffré avec la clé session)|
        |                                |
   ─────── Handshake terminé ! ─────────
        |                                |
  [12]  |──── GET /api/data HTTP/1.1 -> |  (chiffré avec AES)
        |──── Host: api.exemple.com  -> |
        |                                |
  [13]  |<─── HTTP/1.1 200 OK ──────── |  (chiffré avec AES)
        |<─── {"data": "..."} ──────── |
        |                                |
```

### 3.2 Explication de chaque étape

**[1] ClientHello** — Le client s'annonce  
Le client indique quels algorithmes cryptographiques il supporte (suites cryptographiques) et génère un nombre aléatoire.

**[2] ServerHello** — Le serveur répond  
Le serveur choisit la meilleure suite crypto parmi celles proposées et génère son propre nombre aléatoire.

**[3] Certificate** — Le serveur prouve son identité  
Le serveur envoie son certificat X.509 qui contient :
- Son domaine (`api.exemple.com`)
- Sa clé publique
- La signature d'une CA (Certificate Authority) de confiance
- Les dates de validité

**[4-5] Vérification du certificat** — Le client fait confiance ou non  
Le client vérifie que le certificat est signé par une CA en laquelle il a confiance (les CAs de confiance sont pré-installées dans votre OS/navigateur).

**[6] ClientKeyExchange** — Échange de secret  
Le client génère un "Pre-Master Secret", le chiffre avec la **clé publique du serveur** et l'envoie. Seul le serveur peut le déchiffrer (avec sa clé privée).

**[7] Dérivation de la clé de session**  
Les deux parties calculent indépendamment la même clé symétrique à partir de : Pre-Master Secret + Client Random + Server Random. Cette clé ne transite jamais sur le réseau.

**[8-11] Fin du handshake**  
Les deux parties confirment qu'elles ont la même clé en s'envoyant un message chiffré.

**[12+] Communication chiffrée**  
Tout le trafic HTTP est maintenant chiffré avec AES (ou ChaCha20).

### 3.3 TLS 1.3 — La version moderne (simplifiée)

TLS 1.3 (2018) améliore le handshake :
- **1-RTT** au lieu de 2-RTT (deux fois plus rapide)
- **0-RTT** pour les reconnexions (données envoyées immédiatement)
- Suppression des algorithmes faibles (RSA pur, RC4, MD5...)
- Perfect Forward Secrecy **obligatoire** (voir ci-dessous)

---

## 4. Les certificats TLS

### 4.1 Structure d'un certificat X.509

Un certificat est un document signé numériquement qui contient :

```
Certificat X.509 pour api.exemple.com :
─────────────────────────────────────
  Version : 3
  Numéro de série : 0x1A2B3C4D...
  
  Sujet (Subject) :
    CN=api.exemple.com        ← Common Name (domaine)
    O=Exemple Corp            ← Organisation
    C=FR                      ← Pays
  
  Émetteur (Issuer) :
    CN=Let's Encrypt R3       ← Qui a signé ce certificat
    O=Let's Encrypt
    C=US
  
  Validité :
    Not Before: 2026-01-01 00:00:00
    Not After:  2026-04-01 00:00:00  ← Expire dans 90 jours (Let's Encrypt)
  
  Clé publique :
    Algorithme: RSA 2048 bits ou ECDSA 256 bits
    Valeur: [clé publique du serveur]
  
  Extensions :
    Subject Alternative Names: api.exemple.com, www.exemple.com
    ↑ Permet un certificat pour plusieurs domaines
    
    Key Usage: Digital Signature, Key Encipherment
    Extended Key Usage: TLS Web Server Authentication
  
  Signature de l'émetteur :
    [Signature cryptographique de Let's Encrypt]
    ↑ Prouve que Let's Encrypt a bien validé ce domaine
```

### 4.2 La chaîne de certificats (Certificate Chain)

La confiance est établie par une **chaîne de signatures** :

```
Certificat du serveur
  ↑ signé par
Certificat intermédiaire (Let's Encrypt R3)
  ↑ signé par
Certificat racine (ISRG Root X1)
  ↑ déjà dans votre OS/navigateur (trusted root store)
```

Votre OS/navigateur maintient une liste de **CA racines de confiance** (Root Certificate Authorities). Let's Encrypt, DigiCert, Comodo, GlobalSign... sont des CA de confiance.

Quand le client vérifie un certificat, il remonte la chaîne jusqu'à une CA racine qu'il connaît.

### 4.3 Wildcard et SAN certificates

**Wildcard :** `*.exemple.com` → valide pour `api.exemple.com`, `www.exemple.com`, etc.  
**SAN (Subject Alternative Names) :** Plusieurs domaines dans un seul certificat.

### 4.4 Let's Encrypt — Certificats gratuits et automatisés

Let's Encrypt a révolutionné HTTPS en proposant des certificats **gratuits** et **automatisés** via le protocole ACME :

```
1. Votre serveur demande un certificat pour exemple.com
2. Let's Encrypt envoie un "challenge" : placer un fichier spécifique
   à l'URL http://exemple.com/.well-known/acme-challenge/xyz
3. Votre serveur place le fichier
4. Let's Encrypt vérifie qu'il peut accéder à ce fichier
   → Prouve que vous contrôlez le domaine
5. Let's Encrypt émet le certificat (valide 90 jours)
6. Certbot renouvelle automatiquement avant expiration
```

---

## 5. Perfect Forward Secrecy (PFS)

### 5.1 Le problème sans PFS

```
Scénario SANS PFS (RSA classique) :
1. Attaquant enregistre tout le trafic chiffré pendant des années
2. Plus tard, il compromet la clé privée du serveur
3. Il peut maintenant déchiffrer TOUT le trafic historique !
```

### 5.2 La solution : clés éphémères (DHE/ECDHE)

Avec Perfect Forward Secrecy, une **nouvelle paire de clés temporaires** est générée pour chaque connexion TLS.

```
Scénario AVEC PFS (ECDHE) :
1. Même si l'attaquant enregistre tout le trafic
2. Même s'il compromet la clé privée du serveur
3. Il NE PEUT PAS déchiffrer les sessions passées
   → Les clés éphémères ont été détruites après la session
```

ECDHE = Elliptic Curve Diffie-Hellman Ephemeral.  
Obligatoire en TLS 1.3, fortement recommandé en TLS 1.2.

---

## 6. Python et TLS — Le module `ssl`

### 6.1 Connexion HTTPS de base

```python
import ssl
import socket

def connexion_tls(hostname, port=443):
    """Établit une connexion TLS et retourne les infos du certificat."""
    
    # Créer un contexte TLS avec les vérifications par défaut
    contexte = ssl.create_default_context()
    
    # Connexion TCP + TLS
    with socket.create_connection((hostname, port)) as sock:
        with contexte.wrap_socket(sock, server_hostname=hostname) as tls_sock:
            # Infos sur la connexion TLS
            print(f"Version TLS : {tls_sock.version()}")
            print(f"Suite crypto : {tls_sock.cipher()}")
            
            # Certificat du serveur
            cert = tls_sock.getpeercert()
            return cert
```

### 6.2 Inspecter un certificat

```python
import ssl
import socket
from datetime import datetime

def inspecter_certificat(hostname, port=443):
    """Affiche les informations détaillées d'un certificat TLS."""
    
    contexte = ssl.create_default_context()
    
    with socket.create_connection((hostname, port), timeout=10) as sock:
        with contexte.wrap_socket(sock, server_hostname=hostname) as tls_sock:
            cert = tls_sock.getpeercert()
    
    # --- Sujet ---
    sujet = dict(x[0] for x in cert["subject"])
    print(f"Domaine (CN) : {sujet.get('commonName', 'N/A')}")
    print(f"Organisation : {sujet.get('organizationName', 'N/A')}")
    
    # --- Émetteur ---
    emetteur = dict(x[0] for x in cert["issuer"])
    print(f"Émetteur : {emetteur.get('commonName', 'N/A')}")
    
    # --- Validité ---
    not_before = ssl.cert_time_to_seconds(cert["notBefore"])
    not_after = ssl.cert_time_to_seconds(cert["notAfter"])
    expiration = datetime.fromtimestamp(not_after)
    jours_restants = (expiration - datetime.now()).days
    
    print(f"Valide depuis : {cert['notBefore']}")
    print(f"Valide jusqu'au : {cert['notAfter']}")
    print(f"Jours restants : {jours_restants}")
    
    # --- SAN (Subject Alternative Names) ---
    san = cert.get("subjectAltName", [])
    domaines = [valeur for type_, valeur in san if type_ == "DNS"]
    print(f"Domaines couverts : {domaines}")
    
    # --- Numéro de série ---
    print(f"Numéro de série : {cert.get('serialNumber', 'N/A')}")

inspecter_certificat("www.google.com")
```

### 6.3 Obtenir les infos de chiffrement

```python
import ssl
import socket

def infos_chiffrement(hostname, port=443):
    """Affiche les détails de la suite cryptographique utilisée."""
    
    contexte = ssl.create_default_context()
    
    with socket.create_connection((hostname, port), timeout=10) as sock:
        with contexte.wrap_socket(sock, server_hostname=hostname) as tls_sock:
            
            version = tls_sock.version()  # ex: "TLSv1.3"
            cipher_info = tls_sock.cipher()
            # cipher_info = (nom_suite, protocole, nb_bits)
            # ex: ("TLS_AES_256_GCM_SHA384", "TLSv1.3", 256)
            
            print(f"Protocole TLS : {version}")
            print(f"Suite crypto : {cipher_info[0]}")
            print(f"Bits de chiffrement : {cipher_info[2]}")
            
            # Décomposer le nom de la suite (ex: TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384)
            # TLS_ = protocole
            # ECDHE_RSA = échange de clé + authentification
            # AES_256_GCM = chiffrement symétrique (algorithme_taille_mode)
            # SHA384 = MAC/hash
            
            return {
                "version_tls": version,
                "suite_crypto": cipher_info[0],
                "bits": cipher_info[2],
            }
```

### 6.4 Désactiver la vérification (pour le dev uniquement)

```python
import ssl
import urllib.request

# JAMAIS en production ! Uniquement pour les tests locaux.
contexte_non_verifie = ssl.create_default_context()
contexte_non_verifie.check_hostname = False
contexte_non_verifie.verify_mode = ssl.CERT_NONE

# Utilisation avec urllib
with urllib.request.urlopen(
    "https://localhost:8443/api",
    context=contexte_non_verifie
) as r:
    print(r.read())
```

### 6.5 Utiliser un certificat auto-signé (pour le dev)

```python
import ssl

# Charger un certificat CA personnalisé (ex: PKI interne)
contexte = ssl.create_default_context()
contexte.load_verify_locations("/chemin/vers/mon_ca.crt")

# Maintenant urllib vérifiera les certificats signés par mon_ca.crt
```

---

## 7. Lire les informations TLS avec urllib

```python
import urllib.request
import ssl
import socket

class InspecteurTLS(urllib.request.HTTPSHandler):
    """Handler personnalisé pour intercepter les infos TLS."""
    
    def __init__(self):
        self.infos_tls = {}
        super().__init__()
    
    def https_open(self, req):
        # Injecte un callback pour capturer les infos de connexion
        return self.do_open(self._creer_connexion, req)
    
    def _creer_connexion(self, host, **kwargs):
        conn = urllib.request.HTTPSHandler.https_open
        return conn

# Version plus simple avec direct ssl :
def requete_https_avec_infos(url):
    """Effectue une requête HTTPS et affiche les infos TLS."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    hostname = parsed.hostname
    port = parsed.port or 443
    
    contexte = ssl.create_default_context()
    
    with socket.create_connection((hostname, port), timeout=10) as sock:
        with contexte.wrap_socket(sock, server_hostname=hostname) as tls_sock:
            print(f"TLS : {tls_sock.version()}")
            print(f"Cipher : {tls_sock.cipher()[0]}")
            cert = tls_sock.getpeercert()
            sujet = dict(x[0] for x in cert["subject"])
            print(f"Certificat CN : {sujet.get('commonName')}")
            
            # Envoyer la requête HTTP manuellement
            chemin = parsed.path or "/"
            requete_http = f"GET {chemin} HTTP/1.0\r\nHost: {hostname}\r\n\r\n"
            tls_sock.send(requete_http.encode())
            
            reponse = b""
            while True:
                chunk = tls_sock.recv(4096)
                if not chunk:
                    break
                reponse += chunk
            
            # Extraire le statut
            premiere_ligne = reponse.decode("utf-8", errors="replace").split("\r\n")[0]
            print(f"Réponse : {premiere_ligne}")

requete_https_avec_infos("https://www.python.org/")
```

---

## 8. Erreurs TLS courantes et leur signification

| Erreur | Cause | Solution |
|--------|-------|----------|
| `CERTIFICATE_VERIFY_FAILED` | Certificat invalide, expiré ou auto-signé | Vérifier le certificat, utiliser `certifi` |
| `SSL_HANDSHAKE_FAILURE` | Protocoles/suites crypto incompatibles | Mettre à jour le serveur (TLS 1.3) |
| `WRONG_VERSION_NUMBER` | Le client essaie de parler HTTPS à un port HTTP | Utiliser le bon port (443) |
| `HOSTNAME_MISMATCH` | Le certificat ne correspond pas au domaine | Vérifier que le domaine correspond au CN/SAN |
| `CERTIFICATE_EXPIRED` | Certificat expiré | Renouveler le certificat |

```python
import ssl
import urllib.request
import urllib.error

try:
    urllib.request.urlopen("https://expired.badssl.com/")
except urllib.error.URLError as e:
    if isinstance(e.reason, ssl.SSLError):
        print(f"Erreur TLS : {e.reason.reason}")
        # → CERTIFICATE_VERIFY_FAILED
    else:
        print(f"Autre erreur : {e}")
```

---

## 9. HTTPS en Django

### 9.1 Configuration de base

```python
# settings.py — Configuration HTTPS pour la production
SECURE_SSL_REDIRECT = True          # Redirige HTTP vers HTTPS
SESSION_COOKIE_SECURE = True        # Cookie session uniquement sur HTTPS
CSRF_COOKIE_SECURE = True           # Cookie CSRF uniquement sur HTTPS
SECURE_HSTS_SECONDS = 31536000      # Forcer HTTPS pendant 1 an (HSTS)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True  # X-Content-Type-Options: nosniff
```

### 9.2 Derrière un reverse proxy (Nginx)

```python
# settings.py — Quand Nginx gère HTTPS et Django reçoit HTTP en interne
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Django saura que la requête était en HTTPS même si reçue en HTTP
```

---

## 10. Résumé visuel

```
Le voyage d'une requête HTTPS :

  Vous tapez https://api.exemple.com
           │
           ▼
  Navigateur résout DNS : api.exemple.com → 203.0.113.1
           │
           ▼
  TCP Handshake (3 messages)
           │
           ▼
  TLS Handshake :
    1. Negotiation des algos
    2. Certificat envoyé + vérifié
    3. Échange de clé asymétrique
    4. Clé symétrique dérivée
           │
           ▼
  Requête HTTP chiffrée avec AES-256
  "GET /api/data HTTP/1.1" → "4f2a8b..."
           │
           ▼
  Réponse déchiffrée : {"data": "..."}

Garanties TLS :
  Confidentialité  → AES chiffre les données
  Intégrité        → HMAC-SHA256 détecte les modifications
  Authentification → Certificat X.509 signé par une CA
  PFS              → Clés éphémères = sessions passées protégées
```

---

## 11. Points clés à retenir

1. **HTTP = texte brut = dangereux** sur les réseaux non maîtrisés
2. **HTTPS = HTTP + TLS** : confidentialité, intégrité, authentification
3. **Symétrique** (AES) = rapide mais problème d'échange de clé
4. **Asymétrique** (RSA/ECDH) = lent mais permet l'échange sécurisé de la clé symétrique
5. **TLS handshake** : asymétrique pour s'authentifier + établir la clé → symétrique pour les données
6. **Certificat** = clé publique + identité + signature d'une CA de confiance
7. **Chaîne de certificats** : votre serveur → CA intermédiaire → CA racine (dans votre OS)
8. **Perfect Forward Secrecy** : compromission de la clé privée ne compromet pas les sessions passées
9. **Let's Encrypt** : certificats gratuits et automatisés
10. En production : toujours **TLS 1.2 minimum**, préférer **TLS 1.3**

---

*Prochain cours (Jour 11) : Parser un message HTTP complet en Python*
