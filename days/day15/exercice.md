# Exercice Jour 15 — Créer et explorer un projet Django (11 juillet 2026)

---

## Objectifs

- Créer un projet Django de zéro avec `django-admin`
- Explorer la structure générée et comprendre chaque fichier
- Lancer le serveur de développement
- Créer une première application et l'enregistrer

---

## Prérequis

Assure-toi d'avoir Django installé :

```bash
pip install django

# Vérifie la version
python -m django --version
# Doit afficher : 4.x ou 5.x
```

---

## Partie 1 — Créer le projet

```bash
# Crée un répertoire de travail
mkdir ~/django_jour15
cd ~/django_jour15

# Crée le projet Django
django-admin startproject myblog

# Explore la structure créée
ls -la myblog/
ls -la myblog/myblog/
```

**Tu dois voir :**
```
myblog/
├── manage.py
└── myblog/
    ├── __init__.py
    ├── asgi.py
    ├── settings.py
    ├── urls.py
    └── wsgi.py
```

---

## Partie 2 — Explorer les fichiers

### 2.1 Lire `manage.py`

```bash
cat myblog/manage.py
```

**Questions à te poser :**
- Quelle variable d'environnement est définie ?
- Quelle fonction est appelée avec `sys.argv` ?

### 2.2 Lire `settings.py`

```bash
cat myblog/myblog/settings.py
```

**Trouve et note :**
- La valeur de `DEBUG`
- Le moteur de base de données configuré
- Combien d'apps sont dans `INSTALLED_APPS`
- Le répertoire `BASE_DIR`

### 2.3 Lire `urls.py`

```bash
cat myblog/myblog/urls.py
```

**Questions :**
- Quelle URL mène à l'interface admin ?
- Quelle fonction Python est utilisée pour définir les routes ?

---

## Partie 3 — Lancer le serveur

```bash
cd myblog

# Applique d'abord les migrations initiales
python manage.py migrate

# Lance le serveur de développement
python manage.py runserver
```

**Tu dois voir :**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
July 11, 2026 - 09:00:00
Django version 5.x, using settings 'myblog.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

Ouvre ton navigateur sur `http://127.0.0.1:8000/`

Tu dois voir la page de bienvenue Django (la fusée).

---

## Partie 4 — Créer une première application

```bash
# Arrête le serveur (Ctrl+C) puis :
python manage.py startapp blog

# Explore la structure créée
ls -la blog/
```

**Tu dois voir :**
```
blog/
├── __init__.py
├── admin.py
├── apps.py
├── migrations/
│   └── __init__.py
├── models.py
├── tests.py
└── views.py
```

---

## Partie 5 — Enregistrer l'application

Ouvre `myblog/settings.py` et ajoute `'blog'` dans `INSTALLED_APPS` :

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'blog',  # <- ajoute cette ligne
]
```

---

## Partie 6 — Créer une vue "Hello World"

### 6.1 Modifier `blog/views.py`

```python
# blog/views.py
from django.http import HttpResponse

def accueil(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Mon Blog</title></head>
    <body>
        <h1>Bienvenue sur mon blog Django !</h1>
        <p>Le cycle MTV fonctionne.</p>
    </body>
    </html>
    """
    return HttpResponse(html)
```

### 6.2 Créer `blog/urls.py`

Crée un nouveau fichier `blog/urls.py` :

```python
# blog/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.accueil, name='accueil'),
]
```

### 6.3 Connecter les URLs dans le projet

Modifie `myblog/urls.py` :

```python
# myblog/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('blog.urls')),  # <- ajoute cette ligne
]
```

### 6.4 Tester

```bash
python manage.py runserver
```

Visite `http://127.0.0.1:8000/` — tu dois voir "Bienvenue sur mon blog Django !"

---

## Partie 7 — Créer un superutilisateur et explorer l'admin

```bash
python manage.py createsuperuser
# Entre un nom d'utilisateur, email, et mot de passe
```

Lance le serveur et visite `http://127.0.0.1:8000/admin/`

Connecte-toi avec le superutilisateur créé.

**Explorer l'admin :**
- Quelles sections vois-tu ?
- Peux-tu créer un utilisateur depuis l'admin ?

---

## Partie 8 — Commandes utiles à mémoriser

```bash
# Voir toutes les commandes disponibles
python manage.py help

# Voir les migrations disponibles
python manage.py showmigrations

# Ouvrir un shell interactif Django
python manage.py shell

# Dans le shell, essaie :
# >>> from django.conf import settings
# >>> settings.INSTALLED_APPS
# >>> settings.DEBUG
# >>> exit()
```

---

## Résumé de ce que tu as fait

- [x] Créé un projet Django avec `django-admin startproject`
- [x] Exploré la structure : `manage.py`, `settings.py`, `urls.py`
- [x] Lancé le serveur de développement
- [x] Créé l'application `blog` avec `startapp`
- [x] Enregistré l'app dans `INSTALLED_APPS`
- [x] Créé une première vue et une URL
- [x] Accédé à l'interface d'administration Django

---

## Pour aller plus loin (optionnel)

Essaie de modifier la vue `accueil` pour qu'elle affiche la date et l'heure actuelles :

```python
from django.http import HttpResponse
from datetime import datetime

def accueil(request):
    maintenant = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
    return HttpResponse(f"<h1>Bonjour ! Il est {maintenant}</h1>")
```

Que se passe-t-il quand tu rafraîchis la page ?
