# Jour 63 — Project Production : Nginx + Gunicorn (28 août 2026)

## Pourquoi Nginx + Gunicorn ?

Le serveur de développement Django (`manage.py runserver`) n'est **jamais** adapté à la production :
- Il ne gère qu'une requête à la fois
- Il n'est pas optimisé pour la performance
- Il ne gère pas les fichiers statiques efficacement
- Il n'a aucune protection contre les attaques

L'architecture de production standard :

```
Internet
    |
    v
[Nginx] <---- reverse proxy, SSL, fichiers statiques, rate limiting
    |
    v
[Gunicorn] <---- serveur WSGI, gère les requêtes Python
    |
    v
[Django Application]
    |
    +---> [PostgreSQL]
    +---> [Redis]
```

**Nginx** gère :
- Terminaison SSL (HTTPS)
- Servir les fichiers statiques directement (sans passer par Django)
- Rate limiting (protection contre les abus)
- Cache des réponses
- Headers de sécurité
- Redirection HTTP → HTTPS

**Gunicorn** gère :
- Exécuter l'application Django
- Multiple workers (threads/processus)
- Queue des requêtes

---

## Partie 1 : Configuration de Gunicorn

### gunicorn.conf.py
```python
"""
Configuration Gunicorn pour la production.
Fichier : gunicorn.conf.py (à la racine du projet)
"""
import multiprocessing
import os

# -------------------------------------------------------
# Binding
# -------------------------------------------------------
# Écouter sur le socket Unix (plus rapide que TCP pour Nginx local)
bind = "0.0.0.0:8000"
# Alternative avec socket Unix (encore plus rapide) :
# bind = "unix:/tmp/gunicorn.sock"

# -------------------------------------------------------
# Workers
# -------------------------------------------------------
# Règle empirique : (2 x CPU) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Type de worker
# - sync : simple, bon pour les apps I/O-bound
# - gevent/eventlet : pour les apps avec beaucoup d'I/O asynchrone
# - gthread : threads par worker
worker_class = "sync"

# Threads par worker (si worker_class = "gthread")
# threads = 2

# Connexions simultanées max par worker
worker_connections = 1000

# -------------------------------------------------------
# Timeouts
# -------------------------------------------------------
timeout = 30          # Worker tué si pas de réponse après 30s
keepalive = 5         # Keep-alive connections
graceful_timeout = 30 # Temps pour finir les requêtes en cours avant arrêt

# -------------------------------------------------------
# Gestion des workers
# -------------------------------------------------------
max_requests = 1000        # Redémarrer le worker après N requêtes (évite les fuites mémoire)
max_requests_jitter = 100  # Aléatoire pour éviter que tous les workers redémarrent en même temps

# -------------------------------------------------------
# Logging
# -------------------------------------------------------
# Logs vers stdout/stderr (capturés par Docker)
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# -------------------------------------------------------
# Process naming
# -------------------------------------------------------
proc_name = "blog_api_gunicorn"

# -------------------------------------------------------
# Sécurité
# -------------------------------------------------------
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# -------------------------------------------------------
# Hooks (callbacks)
# -------------------------------------------------------
def on_starting(server):
    """Appelé avant le démarrage du master."""
    print(f"[Gunicorn] Démarrage avec {workers} workers")

def post_fork(server, worker):
    """Appelé dans chaque worker après fork."""
    # Réinitialiser les connexions DB dans les workers
    from django.db import connections
    for conn in connections.all():
        conn.close()

def worker_exit(server, worker):
    """Appelé quand un worker se termine."""
    print(f"[Gunicorn] Worker {worker.pid} terminé")
```

### Calcul du nombre de workers

| Serveur | CPUs | Workers recommandés |
|---------|------|---------------------|
| Nano (1 vCPU) | 1 | 3 |
| Small (2 vCPUs) | 2 | 5 |
| Medium (4 vCPUs) | 4 | 9 |
| Large (8 vCPUs) | 8 | 17 |

En pratique, commence avec `(2 x CPU) + 1` et ajuste selon la charge observée.

---

## Partie 2 : Configuration Nginx pour le développement

### nginx/nginx.conf (dev — sans SSL)
```nginx
upstream django_app {
    server web:8000;
}

server {
    listen 80;
    server_name localhost;

    # Taille max des uploads
    client_max_body_size 10M;

    # Fichiers statiques — servis directement par Nginx
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Fichiers media (uploads utilisateurs)
    location /media/ {
        alias /var/www/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Application Django
    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

---

## Partie 3 : Configuration Nginx de production

### nginx/nginx.prod.conf (production complète)
```nginx
# -------------------------------------------------------
# Rate limiting — protection contre les abus
# -------------------------------------------------------
# Zone "api" : 10 requêtes par seconde par IP
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# Zone "login" : 5 requêtes par minute par IP (anti-brute-force)
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# -------------------------------------------------------
# Cache Nginx pour les fichiers statiques
# -------------------------------------------------------
proxy_cache_path /var/cache/nginx
    levels=1:2
    keys_zone=static_cache:10m
    max_size=1g
    inactive=60m
    use_temp_path=off;

# -------------------------------------------------------
# Upstream Gunicorn
# -------------------------------------------------------
upstream django_app {
    server web:8000 fail_timeout=30s max_fails=3;
    # keepalive : réutiliser les connexions vers Gunicorn
    keepalive 32;
}

# -------------------------------------------------------
# Redirection HTTP → HTTPS
# -------------------------------------------------------
server {
    listen 80;
    listen [::]:80;
    server_name votre-domaine.com www.votre-domaine.com;

    # Certbot renewal challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Tout le reste → HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# -------------------------------------------------------
# Serveur HTTPS principal
# -------------------------------------------------------
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name votre-domaine.com www.votre-domaine.com;

    # -------------------------------------------------------
    # Certificats SSL (Let's Encrypt)
    # -------------------------------------------------------
    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/votre-domaine.com/chain.pem;

    # Paramètres SSL sécurisés (Mozilla SSL Config Generator — Intermediate)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # OCSP Stapling (vérifie la validité du certificat côté serveur)
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # -------------------------------------------------------
    # Headers de sécurité
    # -------------------------------------------------------
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Cacher la version de Nginx
    server_tokens off;

    # Taille max des uploads (ex: images de posts)
    client_max_body_size 10M;

    # Timeouts
    client_body_timeout 12s;
    client_header_timeout 12s;
    send_timeout 10s;

    # -------------------------------------------------------
    # Fichiers statiques — servis directement
    # -------------------------------------------------------
    location /static/ {
        alias /var/www/static/;

        # Cache long terme (WhiteNoise génère des noms avec hash)
        expires 1y;
        add_header Cache-Control "public, immutable";

        # Compression
        gzip_static on;

        # Pas de log pour les statiques (économise le disque)
        access_log off;
    }

    # -------------------------------------------------------
    # Fichiers media (uploads)
    # -------------------------------------------------------
    location /media/ {
        alias /var/www/media/;
        expires 7d;
        add_header Cache-Control "public";
        access_log off;
    }

    # -------------------------------------------------------
    # API — avec rate limiting
    # -------------------------------------------------------
    location /api/ {
        # Rate limiting : 10 req/s, burst de 20
        limit_req zone=api burst=20 nodelay;
        limit_req_status 429;

        proxy_pass http://django_app;
        include /etc/nginx/proxy_params;
    }

    # -------------------------------------------------------
    # Endpoint de login — rate limiting strict (anti-brute-force)
    # -------------------------------------------------------
    location /api/auth/token/ {
        limit_req zone=login burst=5 nodelay;
        limit_req_status 429;

        proxy_pass http://django_app;
        include /etc/nginx/proxy_params;
    }

    # -------------------------------------------------------
    # Admin Django — accessible seulement en interne (optionnel)
    # -------------------------------------------------------
    location /admin/ {
        # Limiter l'accès à certaines IPs (décommenter en prod)
        # allow 192.168.1.0/24;
        # deny all;

        limit_req zone=api burst=5 nodelay;

        proxy_pass http://django_app;
        include /etc/nginx/proxy_params;
    }

    # -------------------------------------------------------
    # Health check — pas de rate limiting
    # -------------------------------------------------------
    location /health/ {
        proxy_pass http://django_app;
        access_log off;
    }

    # -------------------------------------------------------
    # Robots.txt
    # -------------------------------------------------------
    location = /robots.txt {
        add_header Content-Type text/plain;
        return 200 "User-agent: *\nAllow: /api/\nDisallow: /admin/\n";
    }

    # -------------------------------------------------------
    # Bloquer les tentatives d'accès aux fichiers sensibles
    # -------------------------------------------------------
    location ~ /\. {
        deny all;
        return 404;
    }

    location ~ \.(env|log|sql|bak)$ {
        deny all;
        return 404;
    }
}
```

### nginx/proxy_params (fichier partagé)
```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Request-ID $request_id;

proxy_http_version 1.1;
proxy_set_header Connection "";

proxy_connect_timeout 10s;
proxy_send_timeout 30s;
proxy_read_timeout 30s;

proxy_buffering on;
proxy_buffer_size 8k;
proxy_buffers 8 8k;
```

---

## Partie 4 : SSL avec Let's Encrypt

### Obtenir le premier certificat

```bash
# 1. Démarrer Nginx sans SSL d'abord (pour le challenge ACME)
# Commentez les lignes SSL dans nginx.prod.conf temporairement

# 2. Démarrer les services
docker-compose -f docker-compose.prod.yml up -d nginx

# 3. Obtenir le certificat
docker-compose -f docker-compose.prod.yml run --rm certbot \
    certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email admin@votre-domaine.com \
    --agree-tos \
    --no-eff-email \
    -d votre-domaine.com \
    -d www.votre-domaine.com

# 4. Décommenter les lignes SSL dans nginx.prod.conf

# 5. Recharger Nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### Renouvellement automatique

Le service `certbot` dans docker-compose.prod.yml tourne en boucle et renouvelle les certificats toutes les 12 heures. Ajouter aussi une tâche cron sur le serveur :

```bash
# Sur le serveur hôte, ajouter dans crontab -e :
0 12 * * * docker-compose -f /path/to/docker-compose.prod.yml exec nginx nginx -s reload
```

### Vérifier le certificat
```bash
# Vérifier la date d'expiration
echo | openssl s_client -servername votre-domaine.com \
    -connect votre-domaine.com:443 2>/dev/null | \
    openssl x509 -noout -dates

# Tester la configuration SSL
# Utiliser : https://www.ssllabs.com/ssltest/
```

---

## Partie 5 : Compression Gzip

Ajouter dans nginx.conf (dans le bloc `http`) :

```nginx
# Dans /etc/nginx/nginx.conf — bloc http
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_comp_level 6;
gzip_types
    text/plain
    text/css
    text/xml
    text/javascript
    application/json
    application/javascript
    application/xml+rss
    application/atom+xml
    image/svg+xml;
```

---

## Partie 6 : Monitoring Nginx

### Activer le module status
```nginx
# Dans le bloc server
location /nginx_status {
    stub_status on;
    allow 127.0.0.1;
    deny all;
}
```

### Logs structurés
```nginx
# Dans le bloc http de nginx.conf
log_format json_combined escape=json
    '{'
    '"time":"$time_iso8601",'
    '"remote_addr":"$remote_addr",'
    '"method":"$request_method",'
    '"uri":"$request_uri",'
    '"status":$status,'
    '"bytes_sent":$bytes_sent,'
    '"request_time":$request_time,'
    '"upstream_response_time":"$upstream_response_time",'
    '"http_referer":"$http_referer",'
    '"http_user_agent":"$http_user_agent",'
    '"request_id":"$request_id"'
    '}';

access_log /var/log/nginx/access.log json_combined;
```

---

## Partie 7 : Benchmark de performance

### Avec Apache Benchmark (ab)

```bash
# Installer ab
apt-get install apache2-utils

# Test simple : 1000 requêtes, 10 simultanées
ab -n 1000 -c 10 http://votre-domaine.com/api/posts/

# Test avec authentification
ab -n 1000 -c 10 \
    -H "Authorization: Bearer eyJ..." \
    http://votre-domaine.com/api/posts/

# Résultat typique attendu
# Requests per second: 150-500 req/s (selon le serveur)
# Time per request: 5-20ms (median)
```

### Avec wrk (plus moderne)

```bash
# Installer wrk
apt-get install wrk

# Test 30 secondes, 10 threads, 100 connexions simultanées
wrk -t10 -c100 -d30s http://votre-domaine.com/api/posts/

# Avec un script Lua pour les POST
cat > post_test.lua << 'EOF'
wrk.method = "POST"
wrk.body   = '{"title": "test", "content": "test content"}'
wrk.headers["Content-Type"] = "application/json"
wrk.headers["Authorization"] = "Bearer YOUR_TOKEN"
EOF

wrk -t4 -c50 -d30s -s post_test.lua http://votre-domaine.com/api/posts/
```

---

## Récapitulatif : Checklist de configuration Nginx

| Élément | Dev | Prod |
|---------|-----|------|
| SSL/HTTPS | Non | Oui |
| HTTP → HTTPS redirect | Non | Oui |
| HSTS | Non | Oui |
| Fichiers statiques via Nginx | Optionnel | Oui |
| Rate limiting | Non | Oui |
| Security headers | Minimal | Complet |
| Gzip | Non | Oui |
| Access logs JSON | Non | Oui |
| Server tokens off | Non | Oui |

---

## Commandes utiles Nginx

```bash
# Vérifier la configuration (sans redémarrer)
docker-compose exec nginx nginx -t

# Recharger la configuration (sans downtime)
docker-compose exec nginx nginx -s reload

# Voir les logs en temps réel
docker-compose logs -f nginx

# Voir le statut des connexions
docker-compose exec nginx curl -s http://localhost/nginx_status
```

---

## Prochain cours

Demain (Jour 64), on ajoute le **caching Redis** pour accélérer les endpoints critiques et on fait du **load testing** avec Locust pour mesurer l'impact.
