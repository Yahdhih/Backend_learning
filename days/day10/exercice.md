# Jour 10 — Exercice : HTTPS et TLS avec openssl et curl
📅 6 juillet 2026 · Module : HTTP en profondeur

> Prérequis : `openssl` et `curl` installés. Vérifier avec `openssl version` et `curl --version`.

---

## Partie 1 — Inspecter un certificat TLS avec openssl s_client

`openssl s_client` est l'outil en ligne de commande pour établir une connexion TLS et inspecter le certificat.

### 1.1 Connexion TLS de base

```bash
openssl s_client -connect www.google.com:443 -servername www.google.com
```

La sortie contient (entre autres) :
- La chaîne de certificats
- La suite cryptographique négociée
- La version TLS
- Les informations du certificat

Appuyez sur `Ctrl+C` pour fermer la connexion (ou tapez `Q` et Entrée).

**Questions :**
- Quelle version de TLS est utilisée ? (cherchez `Protocol :`)
- Quelle suite cryptographique est négociée ? (cherchez `Cipher :`)
- Combien de certificats sont dans la chaîne ? (cherchez les blocs `Certificate chain`)

### 1.2 Afficher uniquement les infos essentielles

```bash
# Juste le résumé de la connexion (pas le certificat complet)
echo "" | openssl s_client -connect www.google.com:443 -servername www.google.com 2>/dev/null | grep -E "Protocol|Cipher|subject|issuer|notBefore|notAfter"
```

### 1.3 Comparer différents serveurs

```bash
# Python.org
echo "" | openssl s_client -connect www.python.org:443 -servername www.python.org 2>/dev/null | grep -E "Protocol|Cipher"

# GitHub
echo "" | openssl s_client -connect github.com:443 -servername github.com 2>/dev/null | grep -E "Protocol|Cipher"
```

**Question :** Utilisent-ils tous TLS 1.3 ? Quelle suite cryptographique pour chacun ?

---

## Partie 2 — Décoder un certificat avec openssl x509

### 2.1 Récupérer et décoder le certificat d'un serveur

```bash
# Étape 1 : récupérer le certificat au format PEM
echo "" | openssl s_client -connect www.python.org:443 -servername www.python.org 2>/dev/null | openssl x509 -text -noout
```

Cette commande affiche toutes les informations du certificat décodé. Repérez :
- **Subject** : à qui appartient le certificat
- **Issuer** : qui l'a signé
- **Validity** : dates de validité
- **Subject Alternative Name** : domaines couverts

### 2.2 Extraire des informations spécifiques

```bash
# Voir les dates de validité
echo "" | openssl s_client -connect www.python.org:443 -servername www.python.org 2>/dev/null | openssl x509 -noout -dates

# Voir le sujet (Subject)
echo "" | openssl s_client -connect www.python.org:443 -servername www.python.org 2>/dev/null | openssl x509 -noout -subject

# Voir qui a signé le certificat (issuer)
echo "" | openssl s_client -connect www.python.org:443 -servername www.python.org 2>/dev/null | openssl x509 -noout -issuer

# Voir les Subject Alternative Names (SANs)
echo "" | openssl s_client -connect www.python.org:443 -servername www.python.org 2>/dev/null | openssl x509 -noout -ext subjectAltName
```

### 2.3 Vérifier combien de jours reste le certificat

```bash
# Calcul automatique de la date d'expiration
echo "" | openssl s_client -connect www.python.org:443 -servername www.python.org 2>/dev/null | openssl x509 -noout -checkend 0 && echo "Certificat valide" || echo "Certificat EXPIRE"

# Vérifier si le certificat expire dans les 30 prochains jours
echo "" | openssl s_client -connect www.python.org:443 -servername www.python.org 2>/dev/null | openssl x509 -noout -checkend 2592000 && echo "Valide plus de 30 jours" || echo "Expire dans moins de 30 jours !"
```

**Questions :**
- Quel est l'émetteur (issuer) du certificat de python.org ?
- Quels domaines couvre le certificat (SANs) ?
- Combien de jours reste-t-il avant l'expiration ?

---

## Partie 3 — Observer le handshake TLS avec curl -v

`curl -v` affiche tous les détails de la connexion, y compris le handshake TLS.

### 3.1 Handshake TLS complet

```bash
curl -v https://httpbin.org/get 2>&1 | head -40
```

Repérez dans la sortie :
- Les lignes `* Connected to ...` (connexion TCP)
- Les lignes `* TLSv1.3 ...` ou `* SSL ...` (handshake TLS)
- Les lignes `* Server certificate:` (informations du certificat)
- La ligne `> GET ...` (début de la requête HTTP)

### 3.2 Forcer une version de TLS spécifique

```bash
# Forcer TLS 1.3 uniquement
curl --tlsv1.3 https://httpbin.org/get -o /dev/null -w "TLS: %{ssl_verify_result}\n" -v 2>&1 | grep -i "tls\|ssl\|cipher"

# Forcer TLS 1.2 uniquement
curl --tlsv1.2 --tls-max 1.2 https://httpbin.org/get -o /dev/null -v 2>&1 | grep -i "tls\|ssl\|cipher"
```

### 3.3 Informations TLS avec le format -w

```bash
# curl peut afficher des informations structurées sur la connexion TLS
curl -s -o /dev/null -w "
Protocole: %{ssl_verify_result}
Statut HTTP: %{http_code}
Temps total: %{time_total}s
Temps TLS: %{time_appconnect}s
IP serveur: %{remote_ip}
Port: %{remote_port}
" https://httpbin.org/get
```

**Questions :**
- Combien de temps dure le handshake TLS (time_appconnect) comparé au temps total ?
- Quelle est la proportion du temps passé en TLS ?

---

## Partie 4 — Sites badssl.com pour tester les erreurs

[badssl.com](https://badssl.com/) propose des sous-domaines avec des configurations TLS intentionnellement cassées pour tester les clients.

### 4.1 Certificat expiré

```bash
curl https://expired.badssl.com/ -v 2>&1 | grep -E "error|expire|valid|SSL"
```

**Question :** Quelle erreur curl retourne-t-il ? Comment l'ignorer (dangereux en prod) ?

### 4.2 Certificat auto-signé

```bash
curl https://self-signed.badssl.com/ -v 2>&1 | grep -E "error|self|SSL|verify"

# Ignorer la vérification (JAMAIS en production)
curl -k https://self-signed.badssl.com/ -v 2>&1 | grep -E "warning|self|SSL|200"
```

**Question :** Quelle différence entre un certificat auto-signé et un certificat signé par une CA ?

### 4.3 Mauvais nom de domaine

```bash
curl https://wrong.host.badssl.com/ -v 2>&1 | grep -E "error|host|SSL|mismatch"
```

**Question :** Pourquoi une mauvaise correspondance de nom de domaine est-elle une faille de sécurité ?

### 4.4 Site avec bonne configuration TLS

```bash
curl https://sha256.badssl.com/ -o /dev/null -v 2>&1 | grep -E "TLS|cipher|cert"
```

---

## Partie 5 — HSTS en pratique

### 5.1 Observer le header HSTS

```bash
curl -I https://github.com | grep -i "strict-transport"
curl -I https://www.google.com | grep -i "strict-transport"
curl -I https://httpbin.org | grep -i "strict-transport"
```

**Questions :**
- Quelle est la valeur `max-age` de GitHub ? En années, ça représente combien ?
- Tous les sites ont-ils HSTS ? Pourquoi certains ne l'ont pas ?

### 5.2 Test de redirection HTTP → HTTPS

```bash
# Tester qu'un site redirige de HTTP vers HTTPS
curl -I http://github.com 2>&1 | grep -E "HTTP|Location|location"

# Suivre les redirections
curl -L http://github.com -o /dev/null -w "Code final: %{http_code}\nURL finale: %{url_effective}\n"
```

**Question :** Combien de redirections ont lieu entre `http://github.com` et la page finale ?

---

## Partie 6 — Inspecter TLS en Python

### 6.1 Script à compléter et exécuter

Créez un fichier `inspect_tls.py` avec ce contenu, puis complétez les TODO :

```python
import ssl
import socket
from datetime import datetime

def inspecter_tls(hostname, port=443):
    """Affiche les informations TLS d'un serveur."""
    contexte = ssl.create_default_context()
    
    with socket.create_connection((hostname, port), timeout=10) as sock:
        with contexte.wrap_socket(sock, server_hostname=hostname) as tls_sock:
            
            # TODO 1 : Afficher la version TLS (tls_sock.version())
            
            # TODO 2 : Afficher la suite cryptographique (tls_sock.cipher())
            # cipher() retourne un tuple (nom, protocole, bits)
            
            # TODO 3 : Récupérer et afficher le certificat
            cert = tls_sock.getpeercert()
            
            # TODO 4 : Extraire et afficher les infos du certificat
            # - sujet : dict(x[0] for x in cert["subject"])
            # - émetteur : dict(x[0] for x in cert["issuer"])
            # - SANs : cert.get("subjectAltName", [])
            # - dates : cert["notBefore"] et cert["notAfter"]
            
            # TODO 5 : Calculer et afficher le nombre de jours avant expiration

# Tester avec plusieurs serveurs
for site in ["www.python.org", "github.com", "httpbin.org"]:
    print(f"\n{'='*50}")
    print(f"Serveur : {site}")
    print('='*50)
    inspecter_tls(site)
```

```bash
python3 inspect_tls.py
```

---

## Questions de synthèse

1. Quelle est la différence entre SSL et TLS ? Pourquoi dit-on encore "SSL" aujourd'hui ?

2. Expliquez en une phrase pourquoi la cryptographie hybride (asymétrique + symétrique) est utilisée dans TLS plutôt que uniquement l'une ou l'autre.

3. Un site a un certificat expiré mais toujours signé par une CA valide. Est-il sûr de l'accepter ? Pourquoi ?

4. Qu'est-ce que le Perfect Forward Secrecy (PFS) et pourquoi est-il important ?

5. Vous êtes développeur backend. Votre app Django tourne derrière Nginx qui gère TLS. Votre app reçoit-elle les requêtes en HTTPS ou en HTTP ? Pourquoi ?

6. Quelle commande openssl utiliseriez-vous pour vérifier qu'un certificat n'expire pas dans les 7 prochains jours ? (Indice : `-checkend N` où N est en secondes)

7. Que signifie `Strict-Transport-Security: max-age=31536000; includeSubDomains` et quand ce header prend-il effet ?
