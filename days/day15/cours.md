# Jour 15 — Architecture Django : MTV et le cycle d'une requête (11 juillet 2026)

---

## 1. Introduction : Pourquoi Django ?

Django est un framework web Python "batteries included" — il fournit tout ce dont tu as besoin pour construire une application web : gestion de base de données, authentification, interface d'administration, système de templates, routing d'URLs, etc.

**Philosophie Django :**
- **DRY** — Don't Repeat Yourself
- **Convention over configuration** — des valeurs par défaut sensées
- **Sécurité par défaut** — protection CSRF, XSS, injection SQL

---

## 2. Le pattern MTV : Model — Template — View

Django utilise le pattern **MTV**, qui est une variante de MVC (Model-View-Controller) :

| MVC (classique)  | MTV (Django)    | Rôle                              |
|------------------|-----------------|-----------------------------------|
| Model            | **Model**       | Données + logique métier          |
| View             | **Template**    | Présentation (HTML)               |
| Controller       | **View**        | Logique de traitement des requêtes|

**Attention :** ce qui s'appelle "View" en Django joue le rôle du "Controller" en MVC. C'est une source de confusion fréquente.

```
Navigateur  -->  URLs  -->  View  -->  Model (base de données)
                                  -->  Template (HTML)
                               <-- HttpResponse
```

### 2.1 Le Model

Le Model représente les données. Il correspond à une table dans la base de données.

```python
# blog/models.py
from django.db import models

class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    date_publication = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey('auth.User', on_delete=models.CASCADE)

    def __str__(self):
        return self.titre
```

### 2.2 La View (pas le Template !)

La View contient la logique. Elle reçoit une requête HTTP et retourne une réponse HTTP.

```python
# blog/views.py
from django.shortcuts import render
from .models import Article

def liste_articles(request):
    articles = Article.objects.all()          # <- Model
    return render(request, 'blog/liste.html', # <- Template
                  {'articles': articles})
```

### 2.3 Le Template

Le Template est le fichier HTML avec des balises Django pour afficher les données.

```html
<!-- templates/blog/liste.html -->
<!DOCTYPE html>
<html>
<body>
  <h1>Tous les articles</h1>
  {% for article in articles %}
    <h2>{{ article.titre }}</h2>
    <p>{{ article.contenu }}</p>
  {% endfor %}
</body>
</html>
```

---

## 3. Le cycle complet d'une requête Django

Voici ce qui se passe quand un navigateur demande `http://localhost:8000/articles/` :

```
┌─────────────────────────────────────────────────────────────────┐
│                    CYCLE D'UNE REQUÊTE DJANGO                   │
└─────────────────────────────────────────────────────────────────┘

  1. Navigateur
     │
     │  GET /articles/   HTTP/1.1
     ▼
  2. Serveur WSGI/ASGI (Gunicorn, Uvicorn, ou serveur de dev)
     │
     │  Crée un objet HttpRequest
     ▼
  3. Django Middleware (chain de traitements)
     │  - SecurityMiddleware
     │  - SessionMiddleware
     │  - AuthenticationMiddleware
     │    ...
     ▼
  4. URL Dispatcher (urls.py)
     │
     │  Lit ROOT_URLCONF = 'monprojet.urls'
     │  Compare /articles/ aux patterns
     │  path('articles/', views.liste_articles)  ✓
     ▼
  5. View Function / View Class
     │
     │  def liste_articles(request):
     │      articles = Article.objects.all()   ─────┐
     │                                               ▼
     │                                    6. ORM Django
     │                                       │  SELECT * FROM blog_article;
     │                                       ▼
     │                                    Base de données (SQLite/PostgreSQL)
     │                                       │
     │      articles = [Article1, ...]  <────┘
     │      return render(request, 'liste.html', {'articles': articles})
     │                              │
     │                              ▼
     │                    7. Template Engine
     │                       Charge liste.html
     │                       Remplace {% for %} {{ }} etc.
     │                       Produit du HTML final
     ▼
  8. HttpResponse (HTML généré)
     │
     │  Retourne à travers les Middleware
     ▼
  9. Navigateur
     Affiche la page HTML
```

---

## 4. Structure d'un projet Django

Quand tu crées un projet Django avec `django-admin startproject monprojet`, tu obtiens :

```
monprojet/                    <- répertoire racine du projet
│
├── manage.py                 <- outil de gestion (runserver, migrate, etc.)
│
└── monprojet/                <- package Python du projet (même nom)
    ├── __init__.py
    ├── settings.py           <- TOUTE la configuration
    ├── urls.py               <- URLconf principal
    ├── asgi.py               <- point d'entrée ASGI
    └── wsgi.py               <- point d'entrée WSGI
```

Quand tu crées une application avec `python manage.py startapp blog` :

```
monprojet/
│
├── manage.py
├── monprojet/
│   ├── settings.py
│   └── urls.py
│
└── blog/                     <- ton application
    ├── __init__.py
    ├── admin.py              <- enregistrement des modèles dans l'admin
    ├── apps.py               <- configuration de l'app
    ├── migrations/           <- fichiers de migration (versionning BDD)
    │   └── __init__.py
    ├── models.py             <- tes modèles (classes Python = tables BDD)
    ├── tests.py              <- tes tests unitaires
    └── views.py              <- tes vues (logique des requêtes)
```

---

## 5. `django-admin` et `manage.py`

### `django-admin` — outil global

```bash
# Créer un nouveau projet
django-admin startproject monprojet

# Voir toutes les commandes disponibles
django-admin help
```

### `manage.py` — outil de projet

`manage.py` est un wrapper autour de `django-admin` qui charge automatiquement les settings de TON projet.

```bash
# Lancer le serveur de développement
python manage.py runserver

# Lancer sur un port spécifique
python manage.py runserver 0.0.0.0:8080

# Créer une nouvelle application
python manage.py startapp blog

# Créer les fichiers de migration
python manage.py makemigrations

# Appliquer les migrations à la base de données
python manage.py migrate

# Ouvrir un shell Python avec Django chargé
python manage.py shell

# Créer un superutilisateur pour l'admin
python manage.py createsuperuser

# Voir toutes les commandes
python manage.py help
```

---

## 6. Le fichier `settings.py` en détail

C'est le cerveau de la configuration Django. Voici les parties essentielles :

```python
# monprojet/settings.py

from pathlib import Path

# Répertoire racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Clé secrète — NE JAMAIS la committer en production !
SECRET_KEY = 'django-insecure-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# Mode debug — False en production
DEBUG = True

# Hôtes autorisés (important en production)
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# ─── Applications installées ───────────────────────────────────────
INSTALLED_APPS = [
    # Apps Django intégrées
    'django.contrib.admin',        # Interface d'administration
    'django.contrib.auth',         # Système d'authentification
    'django.contrib.contenttypes', # Framework de types de contenu
    'django.contrib.sessions',     # Gestion des sessions
    'django.contrib.messages',     # Système de messages flash
    'django.contrib.staticfiles',  # Fichiers statiques (CSS, JS, images)

    # Tes applications
    'blog',                        # <- ton app ici
]

# ─── Middleware ────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ─── URLs ──────────────────────────────────────────────────────────
ROOT_URLCONF = 'monprojet.urls'  # Fichier urls.py principal

# ─── Templates ─────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Répertoire global des templates
        'APP_DIRS': True,                  # Cherche aussi dans app/templates/
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ─── Base de données ───────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
    # Pour PostgreSQL :
    # 'default': {
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'NAME': 'ma_base',
    #     'USER': 'mon_user',
    #     'PASSWORD': 'mon_mot_de_passe',
    #     'HOST': 'localhost',
    #     'PORT': '5432',
    # }
}

# ─── Fichiers statiques ────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# ─── Langue et timezone ────────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# ─── Clé primaire par défaut ───────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

---

## 7. Comment Django charge les settings

Django utilise la variable d'environnement `DJANGO_SETTINGS_MODULE` pour savoir quel fichier de settings utiliser :

```bash
# Django lit cette variable pour trouver les settings
export DJANGO_SETTINGS_MODULE='monprojet.settings'
```

`manage.py` fait ça automatiquement pour toi :

```python
# manage.py (généré automatiquement)
import os
import sys

def main():
    # Définit la variable d'environnement
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monprojet.settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Impossible d'importer Django...") from exc
    
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
```

**Bonne pratique — séparer les settings par environnement :**

```
monprojet/settings/
    __init__.py
    base.py          <- settings communs
    development.py   <- settings de dev (DEBUG=True, SQLite)
    production.py    <- settings de prod (DEBUG=False, PostgreSQL)
    testing.py       <- settings de test
```

```python
# settings/development.py
from .base import *

DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

---

## 8. Le fichier `urls.py` principal

```python
# monprojet/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),          # URL de l'interface admin
    path('articles/', include('blog.urls')),   # URLs de l'app blog
    path('', include('pages.urls')),           # URLs de l'app pages
]
```

---

## 9. Exemple complet d'une application minimale

Voici un exemple de bout en bout pour bien visualiser MTV :

```python
# blog/models.py
from django.db import models

class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    publie = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']  # Plus récents en premier
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'

    def __str__(self):
        return self.titre


# blog/views.py
from django.shortcuts import render, get_object_or_404
from .models import Article

def liste_articles(request):
    """Affiche tous les articles publiés."""
    articles = Article.objects.filter(publie=True)
    return render(request, 'blog/liste.html', {
        'articles': articles,
        'titre_page': 'Tous les articles',
    })

def detail_article(request, pk):
    """Affiche un article spécifique."""
    article = get_object_or_404(Article, pk=pk, publie=True)
    return render(request, 'blog/detail.html', {
        'article': article,
    })


# blog/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_articles, name='liste-articles'),
    path('<int:pk>/', views.detail_article, name='detail-article'),
]


# monprojet/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('articles/', include('blog.urls')),
]
```

```html
<!-- templates/blog/liste.html -->
<!DOCTYPE html>
<html lang="fr">
<head>
    <title>{{ titre_page }}</title>
</head>
<body>
    <h1>{{ titre_page }}</h1>
    
    {% if articles %}
        {% for article in articles %}
            <article>
                <h2>
                    <a href="{% url 'detail-article' article.pk %}">
                        {{ article.titre }}
                    </a>
                </h2>
                <p>{{ article.date_creation|date:"d/m/Y" }}</p>
                <p>{{ article.contenu|truncatewords:30 }}</p>
            </article>
        {% endfor %}
    {% else %}
        <p>Aucun article publié.</p>
    {% endif %}
</body>
</html>
```

---

## 10. INSTALLED_APPS : pourquoi c'est important

Quand tu ajoutes une app à `INSTALLED_APPS`, Django :

1. **Cherche ses modèles** pour générer les migrations
2. **Charge ses templates** si `APP_DIRS=True`
3. **Charge ses fichiers statiques**
4. **Exécute ses signaux** (signals)
5. **Inclut ses commandes** `manage.py` personnalisées

```python
# blog/apps.py — configuration de l'application
from django.apps import AppConfig

class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'
    verbose_name = 'Blog'  # Nom affiché dans l'admin

    def ready(self):
        """Exécuté au démarrage de Django — utile pour les signaux."""
        import blog.signals  # noqa
```

Dans `settings.py`, tu peux référencer la config complète :

```python
INSTALLED_APPS = [
    ...
    'blog.apps.BlogConfig',  # Version explicite avec config
    # ou simplement
    'blog',                   # Version courte
]
```

---

## 11. Le Middleware : la chaîne de traitement

Les middlewares sont des couches qui interceptent chaque requête/réponse :

```python
# Exemple de middleware personnalisé
# monprojet/middleware.py

import time
import logging

logger = logging.getLogger(__name__)

class TempsReponseMiddleware:
    """Mesure le temps de réponse de chaque requête."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Initialisation au démarrage du serveur

    def __call__(self, request):
        # Code exécuté AVANT la view
        debut = time.time()
        
        response = self.get_response(request)  # <- appel de la view
        
        # Code exécuté APRÈS la view
        duree = time.time() - debut
        logger.info(f"{request.path} → {duree:.3f}s")
        
        return response
```

```python
# settings.py — ajouter le middleware
MIDDLEWARE = [
    'monprojet.middleware.TempsReponseMiddleware',  # <- le tien en premier
    'django.middleware.security.SecurityMiddleware',
    ...
]
```

---

## 12. Résumé visuel MTV

```
┌─────────────────────────────────────────────────────────────┐
│                        DJANGO MTV                           │
│                                                             │
│   Requête HTTP                                              │
│       │                                                     │
│       ▼                                                     │
│   ┌──────────┐                                              │
│   │  URLconf  │  urls.py — route vers la bonne View         │
│   └──────────┘                                              │
│       │                                                     │
│       ▼                                                     │
│   ┌──────────┐    ┌──────────┐                              │
│   │   VIEW   │◄──►│  MODEL   │  Accès base de données       │
│   │ views.py │    │models.py │  (ORM Django)                │
│   └──────────┘    └──────────┘                              │
│       │                                                     │
│       ▼                                                     │
│   ┌──────────┐                                              │
│   │ TEMPLATE │  Fichier HTML + balises Django               │
│   │  .html   │                                              │
│   └──────────┘                                              │
│       │                                                     │
│       ▼                                                     │
│   HttpResponse (HTML généré)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Points clés à retenir

1. **MTV != MVC** — la View Django est le Controller, le Template est la View
2. **Le cycle requête/réponse** passe par : Middleware → URLconf → View → Model/Template → Middleware
3. **`manage.py`** est ton couteau suisse pour toutes les opérations sur le projet
4. **`settings.py`** centralise toute la configuration — ne pas mettre de secrets en dur
5. **`INSTALLED_APPS`** doit lister TOUTES tes applications pour que Django les reconnaisse
6. **Une app Django** = models + views + urls + templates + admin (chacun dans son fichier)
