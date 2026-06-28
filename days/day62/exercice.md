# Exercice Jour 62 — Dockeriser l'application

## Objectif

Mettre en place la configuration Docker complète pour le projet Blog API et vérifier que tout fonctionne.

---

## Partie 1 : Mise en place des fichiers

### 1.1 — Créer la structure de répertoires
```bash
# Depuis la racine de ton projet blog_api
mkdir -p requirements scripts nginx

# Vérifier
ls -la
```

### 1.2 — Créer les fichiers de requirements
```bash
# Créer requirements/base.txt
cat > requirements/base.txt << 'EOF'
Django==4.2.13
djangorestframework==3.15.1
djangorestframework-simplejwt==5.3.1
psycopg2-binary==2.9.9
django-cors-headers==4.3.1
python-decouple==3.8
Pillow==10.3.0
EOF

# Créer requirements/development.txt
cat > requirements/development.txt << 'EOF'
-r base.txt
django-debug-toolbar==4.3.0
factory-boy==3.3.0
faker==25.2.0
pytest-django==4.8.0
ipython==8.24.0
EOF

# Créer requirements/production.txt
cat > requirements/production.txt << 'EOF'
-r base.txt
gunicorn==22.0.0
redis==5.0.4
django-redis==5.4.0
sentry-sdk==2.3.1
python-json-logger==2.0.7
whitenoise==6.6.0
EOF
```

### 1.3 — Organiser les settings
```bash
mkdir -p blog_api/settings
touch blog_api/settings/__init__.py

# Le fichier settings.py actuel devient base.py
mv blog_api/settings.py blog_api/settings/base.py

# Créer development.py et production.py comme dans le cours
```

### 1.4 — Créer le fichier .env
```bash
cp .env.example .env
# Éditer .env avec tes valeurs
nano .env
```

### 1.5 — Créer le script entrypoint.sh
```bash
# Copier le contenu du cours dans scripts/entrypoint.sh
chmod +x scripts/entrypoint.sh
```

---

## Partie 2 : Build et démarrage

### 2.1 — Construire les images
```bash
# Construire (vérifier qu'il n'y a pas d'erreurs)
docker-compose build

# Si erreur, voir les logs détaillés
docker-compose build --no-cache --progress=plain 2>&1 | head -100
```

### 2.2 — Démarrer les services
```bash
# Démarrer en avant-plan pour voir les logs
docker-compose up

# Dans un autre terminal, vérifier que les services sont UP
docker-compose ps
```

Résultat attendu :
```
NAME                    COMMAND                  SERVICE   STATUS          PORTS
blog_api-db-1           "docker-entrypoint.s…"   db        Up (healthy)    0.0.0.0:5432->5432/tcp
blog_api-redis-1        "docker-entrypoint.s…"   redis     Up (healthy)    0.0.0.0:6379->6379/tcp
blog_api-web-1          "/entrypoint.sh pyth…"   web       Up              0.0.0.0:8000->8000/tcp
```

### 2.3 — Vérifier l'application
```bash
# Test de base
curl http://localhost:8000/api/posts/

# Vérifier les headers
curl -I http://localhost:8000/api/posts/

# Tester l'admin
open http://localhost:8000/admin/
```

---

## Partie 3 : Vérifications et debugging

### 3.1 — Accéder aux logs
```bash
# Logs de tous les services
docker-compose logs

# Logs d'un service spécifique, en continu
docker-compose logs -f web

# Les 50 dernières lignes
docker-compose logs --tail=50 web
```

### 3.2 — Exécuter des commandes dans les conteneurs
```bash
# Shell Django
docker-compose exec web python manage.py shell

# Dans le shell, vérifier la config
from django.conf import settings
print(settings.DATABASES)
print(settings.CACHES)
exit()

# Créer un superutilisateur manuellement
docker-compose exec web python manage.py createsuperuser

# Vérifier les migrations
docker-compose exec web python manage.py showmigrations

# Accéder au shell PostgreSQL
docker-compose exec db psql -U blog_user -d blog_db

# Accéder au shell Redis
docker-compose exec redis redis-cli ping
# Doit répondre: PONG
```

### 3.3 — Inspecter les ressources Docker
```bash
# Voir les images créées
docker images | grep blog

# Voir les conteneurs qui tournent
docker ps

# Voir la consommation de ressources
docker stats

# Inspecter un conteneur
docker-compose exec web env | sort   # Variables d'environnement
docker-compose exec web df -h        # Espace disque
```

---

## Partie 4 : Test du build de production

### 4.1 — Construire l'image de production
```bash
# Build multi-stage — vérifier la taille de l'image finale
docker-compose -f docker-compose.prod.yml build web

# Comparer les tailles
docker images | grep blog_api
# blog_api   dev    xxx   xxx MB   <- image de dev (avec gcc, etc.)
# blog_api   prod   xxx   xxx MB   <- image de prod (plus petite)
```

### 4.2 — Vérifier le .dockerignore
```bash
# Simuler ce que Docker voit (nécessite docker buildx)
docker buildx build --no-cache --progress=plain . 2>&1 | grep "COPY"

# Vérifier que .env n'est pas dans l'image
docker-compose run --rm web find /app -name ".env" 2>/dev/null
# Ne doit rien afficher
```

---

## Partie 5 : Commandes de gestion courantes

### Reset complet
```bash
# Arrêter tout et supprimer les volumes (ATTENTION : perd les données !)
docker-compose down -v

# Supprimer aussi les images
docker-compose down -v --rmi all

# Supprimer les images non utilisées
docker image prune -f
```

### Mise à jour du code
```bash
# Si tu modifies du Python, redémarrer seulement le service web
docker-compose restart web

# Si tu modifies les requirements
docker-compose build web
docker-compose up -d web
```

### Backup de la base de données
```bash
# Sauvegarder
docker-compose exec db pg_dump -U blog_user blog_db > backup.sql

# Restaurer
docker-compose exec -T db psql -U blog_user blog_db < backup.sql
```

---

## Partie 6 : Validation finale

Coche chaque point :

- [ ] `docker-compose build` se termine sans erreur
- [ ] `docker-compose up` démarre les 3 services (web, db, redis)
- [ ] `docker-compose ps` montre tous les services en état `Up`
- [ ] `curl http://localhost:8000/api/posts/` répond (même si liste vide)
- [ ] `docker-compose exec web python manage.py showmigrations` montre les migrations appliquées
- [ ] `docker-compose exec redis redis-cli ping` répond `PONG`
- [ ] L'image de prod est construite sans erreur
- [ ] Le fichier `.env` n'est pas inclus dans l'image Docker
- [ ] Les volumes persistent les données entre redémarrages
- [ ] `docker-compose down` et `docker-compose up` redémarre proprement

---

## Bonus : Optimiser le temps de build

```bash
# Activer BuildKit pour des builds plus rapides
export DOCKER_BUILDKIT=1

# Ou dans docker-compose
export COMPOSE_DOCKER_CLI_BUILD=1

# Vérifier le temps de build
time docker-compose build --no-cache web
```

**Astuce** : La ligne `COPY requirements/ requirements/` est placée AVANT `COPY . .` intentionnellement. Ainsi, si tu ne modifies que le code Python (pas les requirements), Docker réutilise le cache pour l'étape d'installation des dépendances.
