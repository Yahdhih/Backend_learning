# Jour 58 — Docker : Conteneurs, Dockerfile et docker-compose (23 août 2026)

## Qu'est-ce qu'un conteneur ?

Avant Docker, déployer une application Python impliquait de reproduire manuellement l'environnement sur chaque serveur : installer Python, les bibliothèques système, configurer les variables d'environnement, etc. Le problème classique : "Ça marche sur ma machine."

### VMs vs Conteneurs

**Machines virtuelles (VMs) :**
```
┌──────────────────────────────────────────┐
│           Application A                  │
│           Dépendances                    │
│           OS complet (Ubuntu 20.04)      │
├──────────────────────────────────────────┤
│           Hyperviseur (VMware/KVM)       │
├──────────────────────────────────────────┤
│           OS hôte                        │
│           Matériel                       │
└──────────────────────────────────────────┘
```

Une VM contient un **OS complet**. Elle isole totalement mais est lourde : chaque VM peut peser plusieurs Go, prend des minutes à démarrer.

**Conteneurs Docker :**
```
┌────────────┐  ┌────────────┐  ┌────────────┐
│  App A     │  │  App B     │  │  App C     │
│  Dépendances│  │  Dépendances│  │  Dépendances│
├────────────┴──┴────────────┴──┴────────────┤
│                Docker Engine               │
├────────────────────────────────────────────┤
│                OS hôte (kernel partagé)    │
│                Matériel                    │
└────────────────────────────────────────────┘
```

Les conteneurs partagent le **kernel du système hôte**. Ils n'ont pas leur propre OS complet. Résultat :
- Démarrage en secondes (vs minutes pour les VMs)
- Poids de quelques MB à quelques centaines de MB (vs plusieurs Go)
- Moins d'isolation (partagent le kernel) mais suffisant pour 99% des cas
- Portabilité totale : même comportement sur n'importe quel OS avec Docker

**L'idée centrale :** Un conteneur est un processus isolé qui croit être seul sur le système. Docker crée cette illusion via les namespaces et cgroups Linux.

### Ce que Docker résout

1. **"Ça marche sur ma machine"** : L'image Docker contient tout. Si ça marche localement, ça marchera en production.
2. **Déploiement reproductible** : Même image = même comportement partout.
3. **Isolation** : Les applications ne se perturbent pas mutuellement.
4. **Scalabilité** : Lancer 10 conteneurs identiques en secondes.
5. **Microservices** : Chaque service dans son conteneur.

---

## Architecture Docker

### Les composants

**Docker Daemon (dockerd) :** Le processus serveur qui tourne en arrière-plan. Il gère les images, les conteneurs, les volumes et les réseaux. Il écoute les commandes de l'API Docker.

**Docker Client (docker) :** L'outil en ligne de commande que vous utilisez (`docker build`, `docker run`, etc.). Il communique avec le daemon via l'API REST.

**Docker Registry :** Un dépôt d'images. **Docker Hub** est le registry public officiel. Vous pouvez aussi avoir des registries privés (AWS ECR, Google GCR, GitLab Registry).

```
Client docker          Daemon docker           Registry
┌──────────┐          ┌──────────────┐       ┌──────────────┐
│ docker   │  API     │ dockerd      │ pull  │ Docker Hub   │
│ build    │ ────────▶│              │◀─────▶│ (images)     │
│ docker   │          │ Gère:        │       └──────────────┘
│ run      │          │ - Images     │
│ docker   │          │ - Conteneurs │
│ push     │          │ - Volumes    │
│          │          │ - Réseaux    │
└──────────┘          └──────────────┘
```

### Commandes de base

```bash
# Version et info
docker --version
docker info

# Gestion des images
docker images                          # lister les images locales
docker pull python:3.11-slim           # télécharger une image
docker rmi python:3.11-slim            # supprimer une image

# Gestion des conteneurs
docker ps                              # conteneurs actifs
docker ps -a                           # tous les conteneurs (y compris arrêtés)
docker run python:3.11-slim python3 --version  # lancer et exécuter
docker run -it python:3.11-slim bash   # interactif
docker stop <id>                       # arrêter
docker rm <id>                         # supprimer
docker logs <id>                       # voir les logs
docker exec -it <id> bash              # shell dans un conteneur actif

# Nettoyage
docker system prune                    # nettoyer tout ce qui n'est pas utilisé
docker system prune -a --volumes       # nettoyage complet
```

---

## Images vs Conteneurs

Cette distinction est fondamentale et souvent source de confusion.

**Image :** Template en lecture seule. C'est un snapshot du système de fichiers, organisé en couches (layers). Une image est immuable. Elle décrit l'état de l'environnement.

**Conteneur :** Une instance en cours d'exécution d'une image. Un conteneur ajoute une couche en écriture au-dessus de l'image. Vous pouvez créer autant de conteneurs que vous voulez à partir d'une même image.

Analogie : l'image est la classe Python, le conteneur est l'instance.

```bash
# Une image → plusieurs conteneurs identiques
docker run -d --name web1 nginx
docker run -d --name web2 nginx
docker run -d --name web3 nginx

# Ces 3 conteneurs sont indépendants et identiques
docker ps
```

### Couches d'images (layers)

```
┌─────────────────────────────────┐  ← Couche écriture (conteneur)
├─────────────────────────────────┤
│  COPY ./requirements.txt .      │  ← Couche 5 (votre Dockerfile)
├─────────────────────────────────┤
│  RUN pip install -r req.txt     │  ← Couche 4
├─────────────────────────────────┤
│  RUN apt-get install ...        │  ← Couche 3
├─────────────────────────────────┤
│  python:3.11-slim               │  ← Couche 2 (image parente)
├─────────────────────────────────┤
│  debian:bookworm-slim           │  ← Couche 1 (base)
└─────────────────────────────────┘
```

Les couches sont cachées et partagées entre les images. Si deux images utilisent `python:3.11-slim` comme base, elles partagent ces couches en mémoire. C'est pourquoi `docker pull` ne télécharge que les couches manquantes.

---

## Instructions Dockerfile

Un Dockerfile est un fichier texte qui définit comment construire une image. Chaque instruction crée une nouvelle couche.

### FROM — image de base

```dockerfile
# Image officielle Python
FROM python:3.11-slim

# Image Ubuntu
FROM ubuntu:22.04

# Image scratch (vide, pour les binaires statiques)
FROM scratch

# Avec un alias (pour multi-stage builds)
FROM python:3.11-slim AS builder
```

**Choix de l'image de base :**
- `python:3.11` : Image complète Debian (~900MB)
- `python:3.11-slim` : Debian sans les paquets inutiles (~120MB) — **recommandé pour Django**
- `python:3.11-alpine` : Alpine Linux très léger (~50MB) mais compatible musl libc — attention aux incompatibilités

### WORKDIR — répertoire de travail

```dockerfile
WORKDIR /app
# Toutes les instructions suivantes s'exécutent dans /app
# Équivalent à : mkdir -p /app && cd /app
```

### COPY et ADD — copier des fichiers

```dockerfile
# COPY <source_locale> <destination_conteneur>
COPY requirements.txt .
COPY . .

# ADD peut aussi extraire des archives et télécharger des URLs
# Préférez COPY pour les fichiers locaux (plus prévisible)
ADD https://example.com/file.tar.gz /tmp/
```

**Ordre important :** Copiez d'abord requirements.txt, puis installez les dépendances, puis copiez le reste du code. Ainsi Docker peut utiliser le cache pour les dépendances si seul votre code change.

### RUN — exécuter des commandes

```dockerfile
# Chaque RUN crée une nouvelle couche
# Mauvais : 3 couches séparées
RUN apt-get update
RUN apt-get install -y libpq-dev
RUN rm -rf /var/lib/apt/lists/*

# Bon : 1 seule couche, plus efficace
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev && \
    rm -rf /var/lib/apt/lists/*
```

### ENV — variables d'environnement

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production

# Ces variables sont disponibles dans le conteneur à l'exécution
```

`PYTHONDONTWRITEBYTECODE=1` : ne pas créer les fichiers .pyc
`PYTHONUNBUFFERED=1` : afficher les logs Python immédiatement (sans buffer)

### EXPOSE — documenter les ports

```dockerfile
EXPOSE 8000
# Note : EXPOSE est DOCUMENTAIRE seulement.
# Il ne publie pas réellement le port sur l'hôte.
# C'est avec -p lors de docker run qu'on publie les ports.
```

### CMD et ENTRYPOINT — commande par défaut

```dockerfile
# CMD : commande par défaut, peut être remplacée
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]

# ENTRYPOINT : point d'entrée fixe (plus difficile à remplacer)
ENTRYPOINT ["gunicorn"]
CMD ["config.wsgi:application"]  # arguments par défaut pour ENTRYPOINT

# Combinaison courante pour les scripts d'init
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application"]
```

**Différence CMD vs ENTRYPOINT :**
- `CMD` : facilement remplaçable : `docker run image autre_commande`
- `ENTRYPOINT` : toujours exécuté, CMD devient les arguments

### ARG — arguments de build

```dockerfile
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

# Passer lors du build :
# docker build --build-arg PYTHON_VERSION=3.12 .
```

### USER — changer d'utilisateur

```dockerfile
# Créer un utilisateur non-root
RUN groupadd -r django && useradd -r -g django django

# Changer vers cet utilisateur
USER django
# Les instructions suivantes s'exécutent en tant que 'django'
```

---

## Multi-stage builds

Un pattern puissant pour réduire la taille de l'image finale. On utilise une première image avec tous les outils de build, puis on copie uniquement les artefacts dans une image finale légère.

```dockerfile
# Stage 1 : Builder (avec tous les outils)
FROM python:3.11 AS builder

WORKDIR /build

# Installer les dépendances de compilation
RUN apt-get update && apt-get install -y gcc libpq-dev

COPY requirements.txt .
# Installer dans un répertoire personnalisé
RUN pip install --prefix=/install -r requirements.txt

# Stage 2 : Image finale (légère)
FROM python:3.11-slim AS final

# Installer uniquement les dépendances runtime
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

# Copier les packages installés depuis le builder
COPY --from=builder /install /usr/local

WORKDIR /app
COPY . .

RUN groupadd -r django && useradd -r -g django django
USER django

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

L'image finale ne contient pas `gcc` ni les headers de développement — elle est bien plus petite.

---

## .dockerignore

Comme `.gitignore`, ce fichier liste les éléments à exclure du contexte de build Docker. Très important pour la vitesse de build et la sécurité.

```
# .dockerignore

# Virtualenv local (ne pas copier dans le conteneur)
venv/
.venv/
env/

# Git
.git/
.gitignore

# Cache Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Tests
.pytest_cache/
htmlcov/
.coverage

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Secrets (très important !)
.env
.env.local
*.env

# Fichiers statiques collectés (générés, pas source)
staticfiles/
media/

# Documentation
docs/
*.md

# Docker lui-même
Dockerfile
docker-compose*.yml
```

---

## Docker Networking

### Réseau bridge (par défaut)

Quand vous lancez des conteneurs, Docker les connecte par défaut au réseau `bridge`. Les conteneurs sur le même réseau peuvent se contacter par leur nom.

```bash
# Créer un réseau personnalisé
docker network create mon_reseau

# Lancer des conteneurs sur ce réseau
docker run -d --name db --network mon_reseau postgres:15
docker run -d --name web --network mon_reseau myapp

# Le conteneur 'web' peut joindre 'db' par son nom :
# psql -h db -U postgres
```

### Types de réseaux

```bash
# Bridge (défaut) : réseau privé, les conteneurs se parlent
docker network create --driver bridge mon_reseau

# Host : partage le réseau de l'hôte (Linux uniquement)
docker run --network host nginx

# None : pas de réseau
docker run --network none myapp
```

### Exposition des ports

```bash
# -p <port_hôte>:<port_conteneur>
docker run -p 8000:8000 myapp      # port 8000 de l'hôte → 8000 du conteneur
docker run -p 80:8000 myapp         # port 80 de l'hôte → 8000 du conteneur
docker run -p 127.0.0.1:8000:8000  # uniquement depuis localhost
```

---

## docker-compose

Docker Compose permet de définir et gérer une application multi-conteneurs avec un seul fichier YAML. Indispensable pour les setups Django (web + db + redis + worker...).

### Structure du fichier

```yaml
# docker-compose.yml

version: "3.9"

services:
  web:           # nom du service
    build: .     # construire depuis le Dockerfile local
    ...

  db:
    image: postgres:15  # utiliser une image Docker Hub
    ...

  redis:
    image: redis:7-alpine
    ...

volumes:         # volumes persistants
  postgres_data:

networks:        # réseaux
  backend:
```

### Commandes docker-compose

```bash
# Construire les images
docker-compose build

# Démarrer tous les services (en arrière-plan)
docker-compose up -d

# Voir les logs
docker-compose logs -f
docker-compose logs -f web   # logs d'un seul service

# Arrêter les services
docker-compose stop

# Arrêter et supprimer les conteneurs
docker-compose down

# Arrêter et supprimer les conteneurs + volumes
docker-compose down -v

# Exécuter une commande dans un service
docker-compose exec web python manage.py migrate
docker-compose exec web bash

# Voir l'état des services
docker-compose ps

# Reconstruire et relancer
docker-compose up -d --build
```

---

## Dockerfile complet pour Django

```dockerfile
# Dockerfile

# ─── Stage 1 : Dépendances ───────────────────────────────────────────────────
FROM python:3.11-slim AS deps

# Variables d'environnement pour Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances système pour psycopg2 et Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /deps

COPY requirements.txt .
RUN pip install --prefix=/deps/install -r requirements.txt

# ─── Stage 2 : Image de production ───────────────────────────────────────────
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=8000

# Dépendances runtime uniquement (pas les headers de compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN groupadd -r django && useradd -r -g django -m django

# Copier les packages Python depuis le stage deps
COPY --from=deps /deps/install /usr/local

# Créer les répertoires nécessaires
RUN mkdir -p /app /app/staticfiles /app/media && \
    chown -R django:django /app

WORKDIR /app

# Copier le code source
COPY --chown=django:django . .

# Passer à l'utilisateur non-root
USER django

# Collecte des fichiers statiques (optionnel ici, souvent en entrypoint)
# RUN python manage.py collectstatic --no-input

EXPOSE 8000

# Script d'entrée
COPY --chown=django:django docker/entrypoint.sh /entrypoint.sh

# Note: le script doit être exécutable AVANT de passer en USER django
# Donc on fait ça en root :
USER root
RUN chmod +x /entrypoint.sh
USER django

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Script entrypoint.sh

```bash
#!/bin/bash
# docker/entrypoint.sh

set -e

echo "Waiting for database..."
while ! python -c "
import os
import psycopg2
try:
    psycopg2.connect(os.environ.get('DATABASE_URL', ''))
    print('Database ready')
except:
    exit(1)
" 2>/dev/null; do
    echo "Database not ready, retrying in 1s..."
    sleep 1
done

echo "Running migrations..."
python manage.py migrate --no-input

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting application..."
exec "$@"
```

---

## docker-compose.yml complet : web + db + redis

```yaml
# docker-compose.yml

version: "3.9"

services:

  # ─── Base de données PostgreSQL ──────────────────────────────────────────
  db:
    image: postgres:15-alpine
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-monprojet}
      POSTGRES_USER: ${POSTGRES_USER:-monprojet}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
    ports:
      - "5432:5432"   # exposer en local pour debug (ne pas faire en prod)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-monprojet}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  # ─── Redis (cache + Celery broker) ────────────────────────────────────────
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  # ─── Application Django ───────────────────────────────────────────────────
  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    restart: unless-stopped
    volumes:
      - static_files:/app/staticfiles
      - media_files:/app/media
      # En développement, monter le code source pour hot-reload :
      # - .:/app
    environment:
      DEBUG: ${DEBUG:-False}
      SECRET_KEY: ${SECRET_KEY:?SECRET_KEY is required}
      DATABASE_URL: postgresql://${POSTGRES_USER:-monprojet}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-monprojet}
      REDIS_URL: redis://redis:6379/0
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:-localhost,127.0.0.1}
      DJANGO_SETTINGS_MODULE: config.settings.production
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - backend

  # ─── Celery Worker (tâches asynchrones) ───────────────────────────────────
  celery:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    restart: unless-stopped
    command: celery -A config worker -l info -c 4
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-monprojet}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-monprojet}
      REDIS_URL: redis://redis:6379/0
      DJANGO_SETTINGS_MODULE: config.settings.production
      SECRET_KEY: ${SECRET_KEY:?SECRET_KEY is required}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - backend

  # ─── Nginx (reverse proxy + static files) ─────────────────────────────────
  nginx:
    image: nginx:1.25-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - static_files:/var/www/static:ro
      - media_files:/var/www/media:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - web
    networks:
      - backend

# ─── Volumes persistants ─────────────────────────────────────────────────────
volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  static_files:
    driver: local
  media_files:
    driver: local

# ─── Réseaux ─────────────────────────────────────────────────────────────────
networks:
  backend:
    driver: bridge
```

### docker-compose.dev.yml — override pour le développement

```yaml
# docker-compose.dev.yml
# Utiliser avec : docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

version: "3.9"

services:
  web:
    build:
      target: deps  # stage sans optimisations prod
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app      # code source monté pour hot-reload
    environment:
      DEBUG: "True"
      DJANGO_SETTINGS_MODULE: config.settings.local
    ports:
      - "8000:8000"

  # Pas de Nginx en dev, on accède directement à Django
  nginx:
    profiles: ["prod"]  # désactiver en dev
```

---

## Commandes Docker essentielles pour le debugging

```bash
# Voir les logs en temps réel
docker-compose logs -f web

# Entrer dans un conteneur en cours d'exécution
docker-compose exec web bash
docker-compose exec web python manage.py shell

# Lancer un conteneur temporaire
docker-compose run --rm web python manage.py migrate

# Inspecter un conteneur
docker inspect <container_id>

# Voir les ressources utilisées
docker stats

# Voir les couches d'une image
docker history monimage:latest

# Exporter/importer des images
docker save monimage:latest | gzip > monimage.tar.gz
docker load < monimage.tar.gz

# Copier des fichiers depuis/vers un conteneur
docker cp web:/app/log.txt ./log.txt
docker cp ./config.py web:/app/config.py

# Variables d'environnement dans le conteneur
docker-compose exec web env | sort

# Déboguer un conteneur qui plante au démarrage
docker-compose run --rm --entrypoint bash web

# Voir les événements Docker
docker events

# Nettoyer
docker-compose down -v            # supprimer conteneurs + volumes
docker system prune -a            # tout nettoyer (images, conteneurs, réseaux)
docker volume prune               # supprimer les volumes non utilisés
```

---

## Bonnes pratiques Docker pour Django

1. **Image slim** : Utilisez `python:3.11-slim`, pas `python:3.11`.
2. **Multi-stage builds** : Séparez les étapes de build et de runtime.
3. **Non-root** : Créez un utilisateur dédié, n'exécutez pas en root.
4. **Layer caching** : Copiez `requirements.txt` avant le code source.
5. **.dockerignore** : Excluez venv, .git, .env, staticfiles.
6. **Healthchecks** : Définissez des checks pour tous les services.
7. **Variables d'environnement** : Ne mettez pas de secrets dans le Dockerfile.
8. **Pas de données dans les conteneurs** : Utilisez des volumes pour les données persistantes.
9. **One process per container** : Gunicorn dans un conteneur, Celery dans un autre, db dans un autre.
10. **Versions explicites** : `python:3.11-slim` pas `python:latest` (les versions `latest` changent).
