# Jour 34 — Project Blog : Setup et Modèles (30 juillet 2026)

## Vue d'ensemble du projet

Pendant les 5 prochains jours, nous construisons une **Blog API** complète avec Django REST Framework. Ce projet consolide tout ce que tu as appris : modèles, sérialiseurs, vues, authentification, permissions, filtres et tests.

### Ce qu'on construit

```
Blog API
├── Posts          → articles du blog (titre, contenu, auteur, catégorie, tags)
├── Categories     → catégories de posts (tech, lifestyle, etc.)
├── Tags           → étiquettes libres (python, django, api, etc.)
├── Comments       → commentaires sur les posts
└── Users          → auteurs (Django User intégré)
```

### Endpoints finaux prévus

```
GET    /api/posts/                 → liste des posts publiés
POST   /api/posts/                 → créer un post (auth requise)
GET    /api/posts/{id}/            → détail d'un post
PUT    /api/posts/{id}/            → modifier (auteur seulement)
DELETE /api/posts/{id}/            → supprimer (auteur seulement)

GET    /api/categories/            → liste des catégories
GET    /api/tags/                  → liste des tags
GET    /api/comments/              → commentaires
POST   /api/posts/{id}/comments/   → commenter un post

POST   /api/auth/login/            → obtenir un token
POST   /api/auth/register/         → créer un compte
```

---

## Structure du projet

```
blog_api/
├── manage.py
├── blog_api/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── blog/
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── permissions.py
    ├── urls.py
    ├── admin.py
    └── tests.py
```

---

## Création du projet

```bash
# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Installer les dépendances
pip install django djangorestframework django-filter

# Créer le projet et l'app
django-admin startproject blog_api .
python manage.py startapp blog

# Vérifier
python manage.py runserver
```

---

## Configuration — settings.py

```python
# blog_api/settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    # Local
    'blog',
]

# DRF configuration de base
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

## Design des modèles

Avant d'écrire le code, on réfléchit aux relations :

```
Category ──< Post >── Tag   (Many-to-Many avec Tag)
User ──< Post              (ForeignKey : auteur)
Post ──< Comment           (ForeignKey : post)
User ──< Comment           (ForeignKey : auteur)
```

### Le champ slug

Le slug est une version URL-friendly du titre :
- Titre : "Mon Premier Article Django"
- Slug : "mon-premier-article-django"

```python
from django.utils.text import slugify

title = "Mon Premier Article Django"
slug = slugify(title)
# → "mon-premier-article-django"
```

Le slug doit être **unique** car il sert dans les URLs :
```
/api/posts/mon-premier-article-django/
```

### Status choices

On utilise un champ `status` avec deux valeurs possibles :
- `draft` : brouillon, visible seulement par l'auteur
- `published` : publié, visible par tous

```python
class Post(models.Model):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    STATUS_CHOICES = [
        (DRAFT, 'Brouillon'),
        (PUBLISHED, 'Publié'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=DRAFT
    )
```

---

## models.py — Code complet

```python
# blog/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone


class Category(models.Model):
    """Catégorie d'articles (ex: Technologie, Lifestyle)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        # Auto-génération du slug si vide
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Étiquette libre (ex: python, django, api)"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Post(models.Model):
    """Article de blog"""

    # Choix de statut
    DRAFT = 'draft'
    PUBLISHED = 'published'
    STATUS_CHOICES = [
        (DRAFT, 'Brouillon'),
        (PUBLISHED, 'Publié'),
    ]

    # Champs principaux
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(
        blank=True,
        help_text="Résumé court (auto-généré si vide)"
    )

    # Relations
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts'
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='posts'
    )

    # Statut et dates
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Auto-génération du slug
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            # S'assurer que le slug est unique
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Auto-génération de l'extrait
        if not self.excerpt:
            self.excerpt = self.content[:200] + '...' if len(self.content) > 200 else self.content

        # Date de publication automatique
        if self.status == self.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        return self.status == self.PUBLISHED

    @property
    def comment_count(self):
        return self.comments.count()


class Comment(models.Model):
    """Commentaire sur un article"""
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Commentaire de {self.author.username} sur '{self.post.title}'"
```

---

## admin.py — Configuration de l'admin

```python
# blog/admin.py

from django.contrib import admin
from .models import Category, Tag, Post, Comment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'status', 'created_at', 'published_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['tags']  # Widget multi-sélection pour les tags
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    # Organisation des champs dans le formulaire admin
    fieldsets = (
        ('Contenu', {
            'fields': ('title', 'slug', 'content', 'excerpt')
        }),
        ('Méta-données', {
            'fields': ('author', 'category', 'tags')
        }),
        ('Publication', {
            'fields': ('status', 'published_at')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # Section repliable
        }),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username', 'post__title']
    readonly_fields = ['created_at', 'updated_at']
```

---

## blog_api/urls.py — URLs principales

```python
# blog_api/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('blog.urls')),
    path('api/auth/', include('rest_framework.urls')),  # Login/logout browser
]
```

---

## blog/urls.py — URLs de l'app (placeholder pour demain)

```python
# blog/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Les ViewSets seront ajoutés demain (jour 35)
router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
]
```

---

## Migrations et vérification

```bash
# Créer les migrations
python manage.py makemigrations blog

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur pour l'admin
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver
```

---

## Explorer dans le shell

```python
# python manage.py shell

from django.contrib.auth.models import User
from blog.models import Category, Tag, Post, Comment

# Créer des données de test
user = User.objects.create_user('alice', 'alice@example.com', 'password123')

cat = Category.objects.create(name='Technologie')
print(cat.slug)  # → "technologie" (auto-généré)

tag1 = Tag.objects.create(name='Python')
tag2 = Tag.objects.create(name='Django')

post = Post.objects.create(
    title='Mon premier article',
    content='Contenu de l\'article...',
    author=user,
    category=cat,
)
post.tags.add(tag1, tag2)

print(post.slug)          # → "mon-premier-article"
print(post.status)        # → "draft"
print(post.is_published)  # → False
print(post.excerpt)       # → "Contenu de l'article..."

# Publier l'article
post.status = Post.PUBLISHED
post.save()
print(post.is_published)  # → True
print(post.published_at)  # → datetime avec heure actuelle

# Ajouter un commentaire
comment = Comment.objects.create(
    post=post,
    author=user,
    content='Super article !'
)
print(post.comment_count)  # → 1

# Accéder aux posts d'un utilisateur
print(user.posts.all())    # → QuerySet avec le post

# Accéder aux posts d'une catégorie
print(cat.posts.all())     # → QuerySet avec le post
```

---

## Points clés à retenir

| Concept | Explication |
|---------|-------------|
| `SlugField` | Champ optimisé pour les slugs (URL-safe) |
| `auto_now_add=True` | Date fixée à la création, jamais modifiée |
| `auto_now=True` | Date mise à jour à chaque `save()` |
| `related_name` | Nom pour accéder en sens inverse (`post.comments`) |
| `on_delete=CASCADE` | Si l'auteur est supprimé, ses posts aussi |
| `on_delete=SET_NULL` | Si la catégorie est supprimée, le post reste (catégorie = NULL) |
| `ManyToManyField` | Un post peut avoir plusieurs tags et vice-versa |

---

## Résumé du jour

Aujourd'hui tu as :
1. Concu l'architecture d'une Blog API complète
2. Créé 4 modèles avec leurs relations (ForeignKey, ManyToMany)
3. Implémenté l'auto-génération de slugs uniques
4. Configuré l'admin Django avec fieldsets et filtres
5. Exploré les données dans le shell Django

Demain (Jour 35) : on construit les **serializers et les vues CRUD**.
