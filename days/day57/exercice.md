# Exercice Jour 57 — Gunicorn + Nginx

## Objectifs

- Installer et lancer Gunicorn avec différentes configurations de workers
- Écrire un fichier `gunicorn.conf.py` complet
- Écrire un bloc de configuration Nginx pour un projet Django
- Tester que l'ensemble fonctionne

---

## Partie 1 : Installation et lancement de Gunicorn

### Étape 1 : Préparer le projet

Utilisez un projet Django existant ou créez-en un minimal :

```bash
# Créer un projet minimal
mkdir ~/django_prod_test && cd ~/django_prod_test
python3 -m venv venv
source venv/bin/activate

pip install django gunicorn

django-admin startproject config .
python manage.py migrate
```

### Étape 2 : Lancer Gunicorn — configuration minimale

```bash
# Depuis la racine du projet (avec virtualenv activé)
gunicorn config.wsgi:application

# Vérifier que ça répond
curl http://127.0.0.1:8000/
```

**Observez :** Gunicorn affiche le nombre de workers démarrés, les accès dans les logs.

### Étape 3 : Expérimenter avec les workers

```bash
# 1 worker (voir que les requêtes se font l'une après l'autre)
gunicorn config.wsgi:application --workers 1 --bind 127.0.0.1:8000

# Calculer le bon nombre de workers pour votre machine
nproc  # ou: python3 -c "import os; print(os.cpu_count())"
# Appliquer la formule : workers = 2 * CPU + 1

# Lancer avec le bon nombre
gunicorn config.wsgi:application --workers $(( 2 * $(nproc) + 1 )) --bind 127.0.0.1:8000

# Avec gthread (threads par worker)
gunicorn config.wsgi:application \
    --worker-class gthread \
    --workers 2 \
    --threads 4 \
    --bind 127.0.0.1:8000

# Avec gevent (async)
pip install gevent
gunicorn config.wsgi:application \
    --worker-class gevent \
    --worker-connections 1000 \
    --workers 2 \
    --bind 127.0.0.1:8000
```

### Étape 4 : Test de charge basique

```bash
# Installer ab (Apache Benchmark)
sudo apt install apache2-utils  # Ubuntu
# ou: brew install httpd         # macOS

# Test avec 1 worker (séquentiel)
gunicorn config.wsgi:application --workers 1 --bind 127.0.0.1:8001 --daemon

# 100 requêtes, 10 simultanées
ab -n 100 -c 10 http://127.0.0.1:8001/

# Test avec plusieurs workers
gunicorn config.wsgi:application --workers 4 --bind 127.0.0.1:8002 --daemon

ab -n 100 -c 10 http://127.0.0.1:8002/

# Comparer les "Requests per second" dans les deux cas

# Arrêter les processes daemon
pkill gunicorn
```

---

## Partie 2 : Écrire gunicorn.conf.py

Créez le fichier `gunicorn.conf.py` à la racine de votre projet.

**Votre fichier doit inclure :**

```python
# gunicorn.conf.py — à compléter

import multiprocessing

# TODO 1 : Configurer le bind sur un socket Unix
# bind = "..."  # utilisez unix:/tmp/gunicorn_test.sock

# TODO 2 : Calculer le nombre de workers automatiquement
# workers = ...

# TODO 3 : Choisir le type de worker (commencez par sync)
# worker_class = "..."

# TODO 4 : Configurer le timeout à 30 secondes
# timeout = ...

# TODO 5 : Activer le redémarrage automatique des workers
# max_requests = ...      # après 500 requêtes
# max_requests_jitter = ...  # ajouter un peu d'aléatoire

# TODO 6 : Configurer les logs
# loglevel = "info"
# accesslog = "/tmp/gunicorn_access.log"
# errorlog = "/tmp/gunicorn_error.log"

# TODO 7 : Ajouter un callback post_fork qui affiche un message
# def post_fork(server, worker):
#     ...
```

**Solution attendue :**

```python
# gunicorn.conf.py — solution

import multiprocessing

# Binding
bind = "unix:/tmp/gunicorn_test.sock"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

# Timeouts
timeout = 30
graceful_timeout = 30
keepalive = 2

# Redémarrage automatique des workers
max_requests = 500
max_requests_jitter = 50

# Logs
loglevel = "info"
accesslog = "/tmp/gunicorn_access.log"
errorlog = "/tmp/gunicorn_error.log"
capture_output = True

# Callbacks
def post_fork(server, worker):
    server.log.info(f"[OK] Worker {worker.pid} prêt")

def on_exit(server):
    server.log.info("Gunicorn s'arrête proprement")
```

**Tester votre config :**

```bash
gunicorn --config gunicorn.conf.py config.wsgi:application

# Dans un autre terminal, tester via le socket Unix
curl --unix-socket /tmp/gunicorn_test.sock http://localhost/

# Vérifier les logs
tail -f /tmp/gunicorn_access.log
tail -f /tmp/gunicorn_error.log
```

---

## Partie 3 : Écrire un bloc de configuration Nginx

**Prérequis : installer Nginx**

```bash
# Ubuntu/Debian
sudo apt install nginx

# macOS
brew install nginx
```

### Exercice : écrire la config Nginx

Créez le fichier `/etc/nginx/sites-available/django_test` (ou `~/nginx_test.conf` si vous n'avez pas les droits sudo) :

**Template à compléter :**

```nginx
# TODO : Définir l'upstream Gunicorn
# (hint: le socket Unix est /tmp/gunicorn_test.sock)
upstream ___ {
    server ___;
}

server {
    listen ___;          # TODO : port d'écoute
    server_name ___;     # TODO : localhost

    # TODO : bloc location pour /static/
    # Les fichiers statiques sont dans ~/django_prod_test/staticfiles/
    location /static/ {
        ___
    }

    # TODO : bloc location principal qui proxy vers Gunicorn
    location / {
        proxy_pass ___;

        # TODO : ajouter les headers nécessaires
        # Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto
    }
}
```

**Solution attendue :**

```nginx
upstream gunicorn_django {
    server unix:/tmp/gunicorn_test.sock fail_timeout=0;
}

server {
    listen 8080;
    server_name localhost;

    access_log /tmp/nginx_access.log;
    error_log /tmp/nginx_error.log;

    client_max_body_size 10M;

    location /static/ {
        alias /home/user/django_prod_test/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://gunicorn_django;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

---

## Partie 4 : Tester l'ensemble

### Lancer le setup complet

```bash
# Terminal 1 : lancer Gunicorn
cd ~/django_prod_test
source venv/bin/activate

# Ajouter 'localhost' dans ALLOWED_HOSTS (settings.py)
# ALLOWED_HOSTS = ['localhost', '127.0.0.1']

gunicorn --config gunicorn.conf.py config.wsgi:application

# Terminal 2 : lancer Nginx avec la config de test
nginx -c ~/django_prod_test/nginx_test.conf -g "daemon off;"

# Terminal 3 : tester
curl http://localhost:8080/
curl -v http://localhost:8080/

# Vérifier les headers de réponse
curl -I http://localhost:8080/
```

### Collectstatic + test des fichiers statiques

```bash
# Collecter les fichiers statiques
cd ~/django_prod_test
source venv/bin/activate
python manage.py collectstatic --no-input

# Vérifier qu'ils sont là
ls staticfiles/

# Tester un fichier statique via Nginx (il ne devrait PAS passer par Gunicorn)
curl http://localhost:8080/static/admin/css/base.css

# Vérifier dans les logs que c'est bien Nginx qui a servi le fichier
# (pas de log dans /tmp/gunicorn_access.log pour cette requête)
```

### Questions de réflexion

1. Que se passe-t-il si vous arrêtez Gunicorn et faites une requête vers Nginx ?
   ```bash
   pkill gunicorn
   curl http://localhost:8080/
   # Quel code HTTP obtenez-vous ? Pourquoi ?
   ```

2. Testez la différence de performance entre servir un fichier statique via Nginx vs via Django :
   ```bash
   # Via Nginx directement
   ab -n 1000 -c 50 http://localhost:8080/static/admin/css/base.css

   # Comparer avec un benchmark de la page Django
   ab -n 100 -c 10 http://localhost:8080/
   ```

3. Que contient l'en-tête `X-Forwarded-For` ? Pourquoi est-il important pour Django ?

---

## Bonus : Service systemd (Linux uniquement)

Si vous êtes sur Linux, créez les fichiers systemd pour Gunicorn :

```bash
# Créer le fichier service (adapter les chemins)
sudo tee /etc/systemd/system/gunicorn_test.service << 'EOF'
[Unit]
Description=Gunicorn test service
After=network.target

[Service]
Type=simple
User=votre_username
WorkingDirectory=/home/votre_username/django_prod_test
Environment="PATH=/home/votre_username/django_prod_test/venv/bin"
ExecStart=/home/votre_username/django_prod_test/venv/bin/gunicorn \
    --config /home/votre_username/django_prod_test/gunicorn.conf.py \
    config.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl start gunicorn_test
sudo systemctl status gunicorn_test

# Voir les logs
sudo journalctl -u gunicorn_test -f
```

---

## Checklist de validation

- [ ] Gunicorn démarre et répond sur le socket Unix
- [ ] gunicorn.conf.py est complet avec workers auto-calculés
- [ ] La config Nginx proxy vers Gunicorn
- [ ] Nginx sert les fichiers statiques sans passer par Gunicorn
- [ ] Les headers X-Forwarded-* sont correctement configurés
- [ ] Les logs Gunicorn et Nginx fonctionnent
- [ ] (Bonus) Service systemd créé et actif
