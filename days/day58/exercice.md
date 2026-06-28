# Exercice Jour 58 — Docker : Dockerfile et docker-compose

## Objectifs

- Écrire un Dockerfile complet pour une application Django
- Écrire un docker-compose.yml avec web, db (PostgreSQL) et redis
- Construire l'image et lancer les services
- Maîtriser les commandes de debugging Docker

---

## Prérequis

```bash
# Vérifier que Docker est installé
docker --version          # Docker Engine ≥ 24
docker-compose --version  # ou: docker compose version (plugin intégré)
```

---

## Partie 1 : Dockerfile pour Django

### Structure du projet

Créez cette structure si elle n'existe pas :

```
monprojet/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── requirements.txt
├── manage.py
├── .dockerignore
└── Dockerfile
```

### Étape 1 : Créer requirements.txt

```
Django==4.2.14
gunicorn==21.2.0
psycopg2-binary==2.9.9
redis==5.0.1
django-redis==5.4.0
Pillow==10.4.0
python-decouple==3.8
whitenoise==6.7.0
```

### Étape 2 : Créer .dockerignore

Créez le fichier `.dockerignore` à la racine du projet :

```
# TODO : lister les éléments à exclure

# Virtualenv
venv/
.venv/

# TODO : ajouter les autres exclusions importantes
# (git, cache python, IDE, fichiers secrets, staticfiles)
```

**Solution attendue :**

```
venv/
.venv/
env/

.git/
.gitignore

__pycache__/
*.pyc
*.pyo

.pytest_cache/
.coverage
htmlcov/

.vscode/
.idea/

.env
.env.*
!.env.example

staticfiles/
media/

Dockerfile
docker-compose*.yml

*.md
docs/

.DS_Store
```

### Étape 3 : Écrire le Dockerfile

Complétez ce template :

```dockerfile
# Dockerfile — à compléter

# TODO 1 : Choisir l'image de base Python (version slim recommandée)
FROM ___

# TODO 2 : Définir les variables d'environnement Python
ENV PYTHONDONTWRITEBYTECODE=___ \
    PYTHONUNBUFFERED=___

# TODO 3 : Installer les dépendances système pour psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    ___ \
    && rm -rf /var/lib/apt/lists/*

# TODO 4 : Définir le répertoire de travail
WORKDIR ___

# TODO 5 : Copier requirements.txt SEUL (avant le code source)
COPY ___ .

# TODO 6 : Installer les dépendances Python
RUN pip install --no-cache-dir ___

# TODO 7 : Copier le reste du code source
COPY . .

# TODO 8 : Créer un utilisateur non-root
RUN groupadd -r django && useradd -r -g django django

# TODO 9 : Créer les répertoires pour static/media et changer le propriétaire
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R django:django /app

# TODO 10 : Passer à l'utilisateur non-root
USER ___

# TODO 11 : Documenter le port exposé
EXPOSE ___

# TODO 12 : Commande par défaut (gunicorn)
CMD [___, ___, ___, ___]
```

**Solution attendue :**

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd -r django && useradd -r -g django -m django

RUN mkdir -p /app/staticfiles /app/media
RUN chown -R django:django /app

USER django

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "30"]
```

### Étape 4 : Construire l'image

```bash
# Construire l'image
docker build -t monprojet:latest .

# Voir l'image créée
docker images monprojet

# Voir les couches
docker history monprojet:latest

# Lancer un conteneur de test
docker run --rm monprojet:latest python manage.py check

# Lancer avec des variables d'environnement
docker run --rm \
    -e DEBUG=True \
    -e SECRET_KEY=test-secret \
    -p 8000:8000 \
    monprojet:latest
```

---

## Partie 2 : docker-compose.yml

### Étape 1 : Créer le fichier .env

```bash
# .env (ne pas committer ce fichier !)
SECRET_KEY=django-insecure-dev-key-changeme-in-production
DEBUG=True
POSTGRES_DB=monprojet
POSTGRES_USER=monprojet
POSTGRES_PASSWORD=devpassword123
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Étape 2 : Écrire docker-compose.yml

Complétez ce template :

```yaml
# docker-compose.yml — à compléter

version: "3.9"

services:

  # Base de données PostgreSQL
  db:
    image: ___  # TODO : postgres version alpine
    restart: unless-stopped
    volumes:
      - postgres_data:___  # TODO : chemin des données postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    # TODO : ajouter un healthcheck (pg_isready)
    networks:
      - backend

  # Redis
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - backend

  # Application Django
  web:
    build: .  # TODO : utiliser le Dockerfile local
    restart: unless-stopped
    environment:
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: ${DEBUG}
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379/0
      ALLOWED_HOSTS: ${ALLOWED_HOSTS}
    ports:
      - "___:8000"  # TODO : exposer le port 8000
    depends_on:
      # TODO : dépendre de db avec la condition service_healthy
      db:
        condition: ___
      redis:
        condition: service_started
    networks:
      - backend

# TODO : déclarer les volumes
volumes:
  ___:
  ___:

# TODO : déclarer le réseau
networks:
  backend:
```

**Solution attendue :**

```yaml
version: "3.9"

services:
  db:
    image: postgres:15-alpine
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  web:
    build: .
    restart: unless-stopped
    environment:
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: ${DEBUG}
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379/0
      ALLOWED_HOSTS: ${ALLOWED_HOSTS}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - backend

volumes:
  postgres_data:
  redis_data:

networks:
  backend:
    driver: bridge
```

---

## Partie 3 : Build et Run

```bash
# Construire toutes les images
docker-compose build

# Lancer tous les services en arrière-plan
docker-compose up -d

# Vérifier que tout fonctionne
docker-compose ps

# Voir les logs
docker-compose logs -f

# Appliquer les migrations
docker-compose exec web python manage.py migrate

# Créer un superuser
docker-compose exec web python manage.py createsuperuser

# Tester l'application
curl http://localhost:8000/

# Vérifier la connexion à Redis
docker-compose exec web python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
r.set('test', 'hello')
print(r.get('test'))
"
```

---

## Partie 4 : Commandes de debugging

```bash
# Voir les logs d'un service spécifique
docker-compose logs web
docker-compose logs db
docker-compose logs -f --tail=50 web

# Entrer dans le conteneur web
docker-compose exec web bash
docker-compose exec web python manage.py shell

# Entrer dans la base de données
docker-compose exec db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

# Voir les ressources consommées
docker stats

# Inspecter le réseau
docker network ls
docker network inspect monprojet_backend

# Voir les volumes
docker volume ls
docker volume inspect monprojet_postgres_data

# Rebuild forcé (sans cache)
docker-compose build --no-cache web

# Relancer uniquement un service
docker-compose restart web

# Lancer une commande dans un nouveau conteneur (sans démarrer le service)
docker-compose run --rm web python manage.py check

# Simuler un crash et voir le restart
docker-compose kill -s SIGKILL web
docker-compose ps  # devrait se relancer si restart: unless-stopped
```

---

## Questions de réflexion

1. **Ordre des COPY dans le Dockerfile :** Pourquoi copier `requirements.txt` avant de copier tout le code source ? Que se passe-t-il au niveau du cache Docker si vous modifiez une ligne dans `views.py` ?

2. **Résolution DNS interne :** Depuis le conteneur `web`, quel hostname utiliser pour joindre PostgreSQL ? Pourquoi ?

3. **Volumes vs Bind Mounts :** Quelle est la différence entre `- postgres_data:/var/lib/postgresql/data` et `- ./data:/var/lib/postgresql/data` ? Quand utiliser l'un ou l'autre ?

4. **healthcheck :** Supprimez le healthcheck de `db` et observez ce qui se passe au démarrage. Quel problème survient ?

5. **SECRET_KEY dans .env :** En production, le fichier `.env` est-il la bonne façon de gérer les secrets ? Quelles alternatives existent ?

---

## Bonus : Ajouter un service Celery

Étendez votre `docker-compose.yml` pour ajouter un worker Celery :

```yaml
# Ajouter dans services:
celery_worker:
  build: .
  command: celery -A config worker -l info
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    REDIS_URL: redis://redis:6379/0
    SECRET_KEY: ${SECRET_KEY}
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
  networks:
    - backend

celery_beat:
  build: .
  command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    REDIS_URL: redis://redis:6379/0
    SECRET_KEY: ${SECRET_KEY}
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
  networks:
    - backend
```

---

## Checklist de validation

- [ ] `.dockerignore` exclut venv, .git, .env, __pycache__
- [ ] Le Dockerfile copie requirements.txt AVANT le code source
- [ ] L'image utilise un utilisateur non-root
- [ ] `docker build` réussit sans erreur
- [ ] `docker-compose up -d` lance les 3 services (db, redis, web)
- [ ] `docker-compose ps` montre tous les services "Up"
- [ ] Les migrations s'appliquent avec `docker-compose exec web python manage.py migrate`
- [ ] L'application répond sur http://localhost:8000
- [ ] Les logs sont accessibles avec `docker-compose logs`
- [ ] (Bonus) Service Celery ajouté et fonctionnel
