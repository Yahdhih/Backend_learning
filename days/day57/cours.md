# Jour 57 — Gunicorn + Nginx : Architecture production (22 août 2026)

## Pourquoi pas le serveur de développement Django en production ?

Quand on lance `python manage.py runserver`, Django démarre un serveur HTTP minimaliste écrit en Python pur. Ce serveur est parfait pour le développement : il recharge automatiquement le code, affiche les erreurs en clair, et ne nécessite aucune configuration. Mais il est absolument inadapté à la production pour plusieurs raisons fondamentales.

**Problèmes de performance :** Le serveur de développement est mono-thread et mono-process. Il ne peut traiter qu'une requête à la fois. Si deux utilisateurs font une requête simultanément, le second attend que le premier soit terminé. Avec 100 utilisateurs simultanés, les temps de réponse explosent.

**Problèmes de sécurité :** Le serveur de développement n'est pas audité pour la sécurité. Il peut exposer des informations sensibles, ne gère pas correctement les connexions SSL, et n'a pas de protection contre les attaques courantes (slowloris, etc.).

**Absence de fonctionnalités production :** Pas de gestion des fichiers statiques efficace, pas de compression gzip, pas de keep-alive HTTP, pas de gestion des erreurs 500 sans exposer la stack trace.

**La documentation officielle de Django le dit explicitement :** "Ne l'utilisez jamais en production." (`runserver` est fait pour le développement uniquement.)

La solution standard en production Python/Django est la combinaison **Gunicorn + Nginx**.

---

## Gunicorn : qu'est-ce que c'est et comment ça marche ?

**Gunicorn** (Green Unicorn) est un serveur HTTP WSGI (Web Server Gateway Interface) pour Python. WSGI est la spécification standard qui définit comment un serveur web communique avec une application Python. Django implémente l'interface WSGI via le fichier `wsgi.py` généré automatiquement.

### L'architecture WSGI

```
Client HTTP
    ↓
Nginx (reverse proxy)
    ↓
Gunicorn (serveur WSGI)
    ↓
Django (application WSGI)
    ↓
Base de données / Cache / etc.
```

Gunicorn agit comme un **supervisor de workers** : il lance plusieurs processus Python indépendants, chacun capable de traiter des requêtes. Le processus principal (master) gère les workers et les redémarre s'ils plantent.

### Comment Gunicorn reçoit les requêtes

1. Nginx reçoit la requête HTTP du client
2. Nginx transmet la requête à Gunicorn via un socket Unix ou TCP
3. Le master Gunicorn assigne la requête à un worker disponible
4. Le worker exécute l'application Django et retourne la réponse
5. Gunicorn renvoie la réponse à Nginx
6. Nginx renvoie la réponse au client

### Installation

```bash
pip install gunicorn

# Lancement minimal (depuis la racine du projet Django)
gunicorn monprojet.wsgi:application

# Avec options
gunicorn monprojet.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 30 \
    --log-level info
```

---

## Types de workers Gunicorn

Le type de worker détermine comment chaque worker gère les requêtes.

### 1. Sync workers (défaut)

```bash
gunicorn monprojet.wsgi:application --worker-class sync
```

Chaque worker traite **une requête à la fois**. Simple, robuste, adapté aux applications CPU-bound (traitement d'images, calculs, etc.) ou avec des réponses rapides.

**Quand utiliser :** La plupart des applications Django classiques. Si vos vues sont rapides (< 30ms), sync est parfait.

**Inconvénient :** Si une requête bloque (ex: appel API externe lent), le worker est bloqué et ne peut pas traiter d'autres requêtes pendant ce temps.

### 2. Gevent workers (async)

```bash
pip install gevent
gunicorn monprojet.wsgi:application --worker-class gevent --worker-connections 1000
```

Basé sur les coroutines Python via **gevent**. Un seul worker peut gérer des milliers de connexions simultanées en faisant du multiplexage I/O.

**Quand utiliser :** Applications avec beaucoup d'I/O concurrent (appels API externes, WebSockets via extensions, etc.).

**Attention :** Gevent "monkey-patche" la bibliothèque standard Python pour rendre les I/O non-bloquants. Certaines bibliothèques ne sont pas compatibles.

### 3. Gthread workers (threads)

```bash
gunicorn monprojet.wsgi:application --worker-class gthread --threads 4
```

Chaque worker est multi-threadé. Un worker avec 4 threads peut traiter 4 requêtes simultanément. Bon compromis entre sync et async.

**Quand utiliser :** Applications avec des I/O bloquants modérés, sans les risques de monkey-patching de gevent.

### Formule pour le nombre de workers

La règle empirique recommandée par la documentation Gunicorn :

```
workers = (2 × CPU_count) + 1
```

Pour un serveur avec 4 CPUs : `(2 × 4) + 1 = 9 workers`

```bash
# Vérifier le nombre de CPUs
nproc  # Linux
sysctl -n hw.ncpu  # macOS
```

---

## Configuration de Gunicorn

### Options principales en ligne de commande

```bash
gunicorn monprojet.wsgi:application \
    --bind unix:/run/gunicorn/gunicorn.sock \  # socket Unix (plus rapide que TCP)
    --workers 9 \                               # nombre de workers
    --worker-class sync \                       # type de worker
    --threads 2 \                               # threads par worker (pour gthread)
    --worker-connections 1000 \                 # connexions max par worker (gevent)
    --timeout 30 \                              # timeout en secondes
    --keepalive 2 \                             # keep-alive HTTP
    --max-requests 1000 \                       # redémarrer worker après N requêtes
    --max-requests-jitter 100 \                 # randomiser le redémarrage
    --graceful-timeout 30 \                     # timeout arrêt gracieux
    --log-level info \                          # niveau de log
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    --capture-output \                          # capturer stdout/stderr
    --daemon                                    # lancer en arrière-plan
```

### Fichier gunicorn.conf.py

Il est bien meilleur de mettre la configuration dans un fichier Python plutôt que de tout mettre en ligne de commande :

```python
# gunicorn.conf.py
import multiprocessing

# Binding
bind = "unix:/run/gunicorn/gunicorn.sock"
# Ou TCP :
# bind = "0.0.0.0:8000"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
# Pour gthread :
# worker_class = "gthread"
# threads = 4

# Timeouts
timeout = 30
graceful_timeout = 30
keepalive = 2

# Redémarrage automatique des workers (prévient les memory leaks)
max_requests = 1000
max_requests_jitter = 100

# Logs
loglevel = "info"
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
capture_output = True
enable_stdio_inheritance = True

# Sécurité
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# User/Group (si lancé en root, puis drop privileges)
# user = "www-data"
# group = "www-data"

# Callbacks
def on_starting(server):
    """Appelé au démarrage du master."""
    server.log.info("Gunicorn master starting...")

def post_fork(server, worker):
    """Appelé après le fork de chaque worker."""
    server.log.info(f"Worker {worker.pid} spawned")

def worker_exit(server, worker):
    """Appelé quand un worker s'arrête."""
    server.log.info(f"Worker {worker.pid} exited")
```

Lancement avec le fichier de config :

```bash
gunicorn --config gunicorn.conf.py monprojet.wsgi:application
```

---

## Nginx comme reverse proxy

### Qu'est-ce qu'un reverse proxy ?

Un **reverse proxy** est un serveur qui se place devant les serveurs applicatifs et qui reçoit toutes les requêtes des clients. Il décide ensuite vers quel serveur interne transmettre chaque requête.

**Pourquoi Nginx devant Gunicorn ?**

1. **Gestion des connexions lentes :** Nginx est expert pour gérer des milliers de connexions simultanées avec très peu de mémoire (architecture event-driven). Il accumule la requête complète du client (même lente) avant de la transmettre à Gunicorn, évitant que les workers Gunicorn soient bloqués par des clients lents.

2. **Fichiers statiques :** Nginx sert CSS, JS, images directement depuis le disque, sans passer par Python. C'est 10 à 100x plus rapide.

3. **SSL/TLS termination :** Nginx gère le chiffrement HTTPS. Gunicorn reçoit du HTTP simple en interne.

4. **Load balancing :** Nginx peut distribuer les requêtes sur plusieurs instances Gunicorn.

5. **Compression gzip :** Nginx compresse automatiquement les réponses.

6. **Rate limiting :** Nginx peut limiter le nombre de requêtes par IP.

7. **Caching :** Nginx peut cacher les réponses.

### Concepts Nginx clés

**Server block :** L'équivalent des VirtualHosts Apache. Définit la configuration pour un domaine.

**Location block :** Définit comment traiter les requêtes pour un chemin URL donné.

**proxy_pass :** Directive qui transmet la requête à un backend (Gunicorn).

**upstream :** Groupe de serveurs backend avec load balancing.

---

## Configuration Nginx complète

### Configuration de base

```nginx
# /etc/nginx/sites-available/monprojet

upstream gunicorn_backend {
    server unix:/run/gunicorn/gunicorn.sock fail_timeout=0;
    # Ou TCP :
    # server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name mondomaine.com www.mondomaine.com;

    # Logs
    access_log /var/log/nginx/monprojet_access.log;
    error_log /var/log/nginx/monprojet_error.log;

    # Taille max des uploads
    client_max_body_size 20M;

    # Fichiers statiques (servis directement par Nginx)
    location /static/ {
        alias /var/www/monprojet/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        gzip_static on;
    }

    # Fichiers media (uploads utilisateurs)
    location /media/ {
        alias /var/www/monprojet/media/;
        expires 30d;
        add_header Cache-Control "public";
    }

    # Tout le reste → Gunicorn
    location / {
        proxy_pass http://gunicorn_backend;

        # Headers importants
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffers
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;

        # Éviter les redirections incorrectes
        proxy_redirect off;
    }

    # Sécurité : cacher la version de Nginx
    server_tokens off;

    # Headers de sécurité
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

Activer le site :

```bash
# Créer un lien symbolique
sudo ln -s /etc/nginx/sites-available/monprojet /etc/nginx/sites-enabled/

# Vérifier la configuration
sudo nginx -t

# Recharger Nginx
sudo systemctl reload nginx
```

---

## Nginx comme serveur de fichiers statiques

Nginx est extrêmement efficace pour servir des fichiers statiques. Voici la configuration optimisée :

```nginx
location /static/ {
    alias /var/www/monprojet/staticfiles/;

    # Cache agressif pour les fichiers versionnés
    expires 1y;
    add_header Cache-Control "public, immutable";

    # Compression gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/css
        text/javascript
        application/javascript
        application/json
        image/svg+xml;

    # Servir les fichiers .gz précompressés si disponibles
    gzip_static on;

    # Ouvrir les fichiers en cache (performance)
    open_file_cache max=1000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
}
```

---

## Nginx SSL/TLS termination

SSL termination signifie que Nginx déchiffre le HTTPS entrant et communique avec Gunicorn en HTTP simple en interne. C'est plus efficace que de faire gérer SSL par chaque worker Python.

### Avec Let's Encrypt (Certbot)

```bash
# Installation de Certbot
sudo apt install certbot python3-certbot-nginx

# Obtenir un certificat
sudo certbot --nginx -d mondomaine.com -d www.mondomaine.com

# Certbot modifie automatiquement la config Nginx
```

### Configuration SSL manuelle complète

```nginx
# Redirection HTTP → HTTPS
server {
    listen 80;
    server_name mondomaine.com www.mondomaine.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name mondomaine.com www.mondomaine.com;

    # Certificats SSL
    ssl_certificate /etc/letsencrypt/live/mondomaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mondomaine.com/privkey.pem;

    # Configuration SSL moderne (Mozilla SSL Generator)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS (dire aux navigateurs de toujours utiliser HTTPS)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Session SSL
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/mondomaine.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;

    # ... reste de la config (static, media, proxy_pass)
}
```

---

## nginx.conf complet pour Django en production

```nginx
# /etc/nginx/nginx.conf

user www-data;
worker_processes auto;  # Un par CPU
pid /run/nginx.pid;

events {
    worker_connections 1024;
    multi_accept on;
    use epoll;  # Linux uniquement, plus efficace
}

http {
    # Paramètres de base
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # MIME types
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logs
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Gzip global
    gzip on;
    gzip_disable "msie6";
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml application/xml+rss text/javascript
               image/svg+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # Upstream Gunicorn
    upstream django {
        server unix:/run/gunicorn/gunicorn.sock fail_timeout=0;
        keepalive 32;
    }

    # Redirection HTTP → HTTPS
    server {
        listen 80;
        server_name mondomaine.com www.mondomaine.com;
        return 301 https://$host$request_uri;
    }

    # Serveur principal HTTPS
    server {
        listen 443 ssl http2;
        server_name mondomaine.com www.mondomaine.com;

        ssl_certificate /etc/letsencrypt/live/mondomaine.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/mondomaine.com/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;

        client_max_body_size 50M;
        keepalive_timeout 70;

        root /var/www/monprojet;

        # Fichiers statiques
        location /static/ {
            alias /var/www/monprojet/staticfiles/;
            expires 1y;
            add_header Cache-Control "public, immutable";
            access_log off;
        }

        # Fichiers media
        location /media/ {
            alias /var/www/monprojet/media/;
            expires 7d;
            add_header Cache-Control "public";
        }

        # API : rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
        }

        # Application principale
        location / {
            proxy_pass http://django;
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
            proxy_redirect off;

            # Pour les WebSockets si nécessaire
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Robots.txt
        location = /robots.txt {
            allow all;
            log_not_found off;
            access_log off;
        }

        # Favicon
        location = /favicon.ico {
            log_not_found off;
            access_log off;
        }

        # Bloquer l'accès aux fichiers cachés
        location ~ /\. {
            deny all;
            access_log off;
            log_not_found off;
        }
    }
}
```

---

## Service systemd pour Gunicorn

Systemd est le gestionnaire de services Linux. On l'utilise pour que Gunicorn démarre automatiquement au boot et se relance en cas de crash.

### Fichier socket (pour les connexions)

```ini
# /etc/systemd/system/gunicorn.socket

[Unit]
Description=Gunicorn daemon socket

[Socket]
ListenStream=/run/gunicorn/gunicorn.sock
SocketUser=www-data

[Install]
WantedBy=sockets.target
```

### Fichier service

```ini
# /etc/systemd/system/gunicorn.service

[Unit]
Description=Gunicorn daemon pour monprojet
Requires=gunicorn.socket
After=network.target

[Service]
Type=notify
# L'utilisateur qui exécute le service
User=www-data
Group=www-data

# Répertoire de travail (racine du projet)
WorkingDirectory=/var/www/monprojet

# Activer le virtualenv
Environment="PATH=/var/www/monprojet/venv/bin"

# Commande de démarrage
ExecStart=/var/www/monprojet/venv/bin/gunicorn \
    --config /var/www/monprojet/gunicorn.conf.py \
    monprojet.wsgi:application

# Redémarrage automatique en cas de crash
Restart=on-failure
RestartSec=5s

# Variables d'environnement
EnvironmentFile=/var/www/monprojet/.env

# Limites
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### Commandes systemd

```bash
# Recharger systemd après modification des fichiers service
sudo systemctl daemon-reload

# Activer le démarrage automatique au boot
sudo systemctl enable gunicorn.socket
sudo systemctl enable gunicorn.service

# Démarrer le service
sudo systemctl start gunicorn.socket
sudo systemctl start gunicorn.service

# Vérifier le statut
sudo systemctl status gunicorn

# Voir les logs
sudo journalctl -u gunicorn -f         # temps réel
sudo journalctl -u gunicorn --since "1 hour ago"

# Recharger Gunicorn (après changement de code) — sans coupure de service
sudo systemctl reload gunicorn
# ou envoyer le signal SIGHUP directement
sudo kill -HUP $(cat /run/gunicorn/gunicorn.pid)

# Redémarrer complètement
sudo systemctl restart gunicorn
```

---

## Walkthrough complet : setup production de A à Z

Voici les étapes complètes pour déployer un projet Django sur un serveur Ubuntu/Debian.

### 1. Préparer le serveur

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Installer les dépendances système
sudo apt install -y python3-pip python3-venv nginx postgresql libpq-dev

# Créer un utilisateur dédié (ne jamais faire tourner l'app en root)
sudo useradd --system --home /var/www/monprojet --shell /bin/bash www-data
```

### 2. Déployer le code

```bash
# Créer la structure
sudo mkdir -p /var/www/monprojet
sudo chown www-data:www-data /var/www/monprojet

# Cloner le projet (en tant que www-data)
sudo -u www-data git clone https://github.com/user/monprojet.git /var/www/monprojet

# Créer le virtualenv
sudo -u www-data python3 -m venv /var/www/monprojet/venv

# Installer les dépendances
sudo -u www-data /var/www/monprojet/venv/bin/pip install -r /var/www/monprojet/requirements.txt
sudo -u www-data /var/www/monprojet/venv/bin/pip install gunicorn
```

### 3. Configurer Django pour la production

```bash
# Créer le fichier .env
sudo -u www-data nano /var/www/monprojet/.env
```

```env
DEBUG=False
SECRET_KEY=votre-clé-secrète-longue-et-aléatoire
ALLOWED_HOSTS=mondomaine.com,www.mondomaine.com
DATABASE_URL=postgresql://user:password@localhost/monprojet
```

```bash
# Appliquer les migrations
sudo -u www-data /var/www/monprojet/venv/bin/python manage.py migrate

# Collecter les fichiers statiques
sudo -u www-data /var/www/monprojet/venv/bin/python manage.py collectstatic --no-input

# Créer le superuser
sudo -u www-data /var/www/monprojet/venv/bin/python manage.py createsuperuser
```

### 4. Configurer le socket Gunicorn

```bash
# Créer le répertoire pour le socket
sudo mkdir -p /run/gunicorn
sudo chown www-data:www-data /run/gunicorn

# Installer les fichiers systemd
sudo cp gunicorn.socket /etc/systemd/system/
sudo cp gunicorn.service /etc/systemd/system/

# Démarrer
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn.socket
sudo systemctl start gunicorn.service
```

### 5. Configurer Nginx

```bash
# Copier la config
sudo cp monprojet.nginx /etc/nginx/sites-available/monprojet

# Activer le site
sudo ln -s /etc/nginx/sites-available/monprojet /etc/nginx/sites-enabled/

# Supprimer la config par défaut
sudo rm /etc/nginx/sites-enabled/default

# Tester
sudo nginx -t

# Démarrer
sudo systemctl enable --now nginx
```

### 6. Certificat SSL avec Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d mondomaine.com -d www.mondomaine.com
```

### 7. Vérification finale

```bash
# Tester la connexion socket Gunicorn
curl --unix-socket /run/gunicorn/gunicorn.sock http://localhost/

# Tester via Nginx
curl -I https://mondomaine.com

# Vérifier les logs
sudo tail -f /var/log/nginx/monprojet_access.log
sudo journalctl -u gunicorn -f
```

---

## Gestion des mises à jour (déploiement continu)

```bash
#!/bin/bash
# deploy.sh — script de déploiement

set -e  # Arrêter si une commande échoue

PROJECT_DIR="/var/www/monprojet"
VENV="$PROJECT_DIR/venv/bin"

echo "Pulling latest code..."
git -C "$PROJECT_DIR" pull origin main

echo "Installing dependencies..."
$VENV/pip install -r "$PROJECT_DIR/requirements.txt"

echo "Running migrations..."
$VENV/python "$PROJECT_DIR/manage.py" migrate --no-input

echo "Collecting static files..."
$VENV/python "$PROJECT_DIR/manage.py" collectstatic --no-input

echo "Reloading Gunicorn..."
sudo systemctl reload gunicorn

echo "Deployment complete!"
```

---

## Points clés à retenir

1. **Jamais runserver en production** — utilisez toujours Gunicorn.
2. **Nginx en front** — gère SSL, fichiers statiques, connexions lentes.
3. **Socket Unix** — plus rapide que TCP pour la communication Nginx-Gunicorn sur le même serveur.
4. **workers = 2 × CPUs + 1** — formule de base pour le nombre de workers.
5. **max_requests** — redémarre les workers périodiquement pour éviter les memory leaks.
6. **systemd** — gère le cycle de vie de Gunicorn (démarrage, crash, boot).
7. **reload, pas restart** — `systemctl reload gunicorn` effectue un redémarrage gracieux (zéro interruption de service).
