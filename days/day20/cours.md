# Jour 20 — Django : Le cycle complet d'une requête
📅 16 juillet 2026 · Module : Django · Révision

---

## De l'URL à la réponse : tout ce qui se passe

Quand un client fait `GET /api/articles/` à ton app Django :

```
Requête HTTP (bytes)
        │
        ▼
┌─────────────────┐
│  WSGI Server    │  Gunicorn transforme les bytes en dict environ
│  (Gunicorn)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  WSGIHandler    │  django.core.handlers.wsgi.WSGIHandler
│  (Django entry) │  Crée un HttpRequest depuis environ
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Middleware     │  SecurityMiddleware → SessionMiddleware →
│  Stack (entrée) │  CommonMiddleware → CsrfViewMiddleware → ...
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  URL Resolver   │  urlpatterns dans urls.py
│  (URLconf)      │  "/api/articles/" → ArticleListView
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  View           │  ArticleListView.get(request)
│  (ta logique)   │  Appelle l'ORM, crée la réponse
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ORM / DB       │  SELECT * FROM blog_article WHERE statut='publie'
│  (SQLite/PG)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Middleware     │  (retour) → GZipMiddleware → ...
│  Stack (retour) │
└────────┬────────┘
         │
         ▼
   HttpResponse (bytes) → client
```

---

## Les middlewares Django par défaut

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",     # headers sécurité
    "django.contrib.sessions.middleware.SessionMiddleware",  # sessions
    "django.middleware.common.CommonMiddleware",          # slash final, etc.
    "django.middleware.csrf.CsrfViewMiddleware",         # protection CSRF
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # request.user
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

Chaque middleware a une chance d'**intercepter** la requête avant qu'elle arrive à la vue, et de **modifier** la réponse avant qu'elle parte.

---

## Récapitulatif des concepts Django

### Models → Base de données
```python
class Article(models.Model):
    titre = models.CharField(max_length=200)
    # → SQL : CREATE TABLE blog_article (id SERIAL, titre VARCHAR(200))
```

### URLs → Routage
```python
# config/urls.py
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("blog.urls")),
]

# blog/urls.py
urlpatterns = [
    path("articles/", views.ArticleListView.as_view()),
    path("articles/<int:pk>/", views.ArticleDetailView.as_view()),
]
```

### Views → Logique métier
```python
from django.http import JsonResponse
from django.views import View

class ArticleListView(View):
    def get(self, request):
        articles = Article.objects.filter(statut="publie").values("id", "titre")
        return JsonResponse(list(articles), safe=False)

    def post(self, request):
        import json
        data = json.loads(request.body)
        article = Article.objects.create(**data)
        return JsonResponse({"id": article.pk}, status=201)
```

### ORM → Requêtes SQL
```python
Article.objects.filter(statut="publie")
# SELECT * FROM blog_article WHERE statut = 'publie'

Article.objects.select_related("categorie").filter(statut="publie")
# SELECT ... FROM blog_article JOIN blog_categorie ON ...
```

---

## Les pièges courants

**1. Oublier `.save()`**
```python
article.titre = "Nouveau titre"
# article.save()  ← si oublié, la DB n'est pas mise à jour !
```

**2. N+1 dans les boucles**
```python
# Mauvais : 1 + N requêtes
for article in Article.objects.all():
    print(article.categorie.nom)  # 1 requête par article !

# Bon : 1 requête
for article in Article.objects.select_related("categorie"):
    print(article.categorie.nom)
```

**3. Migration non appliquée**
```bash
# Symptôme : OperationalError: no such column
python manage.py migrate  # toujours vérifier
```

**4. QuerySet lazy (pas encore évalué)**
```python
articles = Article.objects.filter(statut="publie")  # pas de requête encore
# La requête s'exécute seulement quand on itère :
for a in articles: ...    # ici
list(articles)             # ou là
articles.count()           # ou là (mais génère un COUNT(*) séparé)
```

**5. `request.body` consommé une seule fois**
```python
def ma_vue(request):
    data = json.loads(request.body)     # OK
    data2 = json.loads(request.body)    # Erreur ! body déjà lu
```
