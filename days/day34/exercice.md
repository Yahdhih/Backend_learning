# Exercice Jour 34 — Setup du projet Blog API

## Objectif

Mettre en place le projet Django et créer tous les modèles du blog.

---

## Étape 1 : Créer le projet

```bash
# Dans ton répertoire de travail
mkdir blog_api_project
cd blog_api_project

python -m venv venv
source venv/bin/activate

pip install django djangorestframework django-filter

django-admin startproject blog_api .
python manage.py startapp blog
```

---

## Étape 2 : Configurer settings.py

Ouvre `blog_api/settings.py` et ajoute dans `INSTALLED_APPS` :

```python
INSTALLED_APPS = [
    # ... apps Django par défaut ...
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'blog',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}
```

---

## Étape 3 : Copier les modèles

Copie le code complet de `models.py` du cours dans `blog/models.py`.

Copie également le code de `admin.py` dans `blog/admin.py`.

---

## Étape 4 : Configurer les URLs

Dans `blog_api/urls.py` :

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('blog.urls')),
]
```

Crée `blog/urls.py` :

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
]
```

---

## Étape 5 : Migrations

```bash
python manage.py makemigrations blog
python manage.py migrate
python manage.py createsuperuser
```

Vérifie que les migrations se créent sans erreur :

```
Migrations for 'blog':
  blog/migrations/0001_initial.py
    - Create model Category
    - Create model Tag
    - Create model Post
    - Create model Comment
```

---

## Étape 6 : Explorer dans le shell

Lance `python manage.py shell` et exécute :

```python
from blog.models import Category, Tag, Post, Comment
from django.contrib.auth.models import User

# 1. Crée un utilisateur
user = User.objects.create_user('alice', 'alice@example.com', 'password123')

# 2. Crée une catégorie
cat = Category.objects.create(name='Technologie')

# Vérifie que le slug est auto-généré
print(cat.slug)  # doit afficher : "technologie"

# 3. Crée deux tags
tag_python = Tag.objects.create(name='Python')
tag_django = Tag.objects.create(name='Django')

# 4. Crée un post
post = Post.objects.create(
    title='Introduction à Django REST Framework',
    content='Django REST Framework est une bibliothèque puissante pour construire des APIs...',
    author=user,
    category=cat,
)
post.tags.add(tag_python, tag_django)

# Vérifie
print(post.slug)          # "introduction-a-django-rest-framework"
print(post.status)        # "draft"
print(post.is_published)  # False
print(post.excerpt)       # premiers 200 caractères du content

# 5. Publie le post
post.status = Post.PUBLISHED
post.save()
print(post.is_published)  # True
print(post.published_at)  # datetime actuelle

# 6. Ajoute un commentaire
comment = Comment.objects.create(
    post=post,
    author=user,
    content='Excellent article, très clair !'
)
print(post.comment_count)  # 1

# 7. Accès inverse
print(user.posts.count())  # 1
print(cat.posts.count())   # 1
print(tag_python.posts.count())  # 1
```

---

## Étape 7 : Vérifier l'admin

1. Lance le serveur : `python manage.py runserver`
2. Va sur `http://127.0.0.1:8000/admin/`
3. Connecte-toi avec le superutilisateur
4. Vérifie que les modèles Category, Tag, Post, Comment apparaissent
5. Crée un post depuis l'interface admin et observe l'auto-génération du slug

---

## Questions de réflexion

1. Que se passe-t-il si tu crées deux posts avec le même titre ?
   (Indice : regarde la logique dans `Post.save()`)

2. Pourquoi utiliser `on_delete=SET_NULL` pour la catégorie et `CASCADE` pour l'auteur ?

3. Quelle est la différence entre `auto_now_add=True` et `auto_now=True` ?

4. Comment accéder à tous les posts d'un tag spécifique ?

---

## Bonus

Crée un script `seed.py` à la racine du projet qui crée des données de test réalistes :

```python
# seed.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_api.settings')
django.setup()

from django.contrib.auth.models import User
from blog.models import Category, Tag, Post

# Crée 3 utilisateurs, 3 catégories, 5 tags, 10 posts
# Certains en draft, certains publiés
# Avec différentes catégories et tags
```

Lance-le avec : `python seed.py`
