# Jour 16 — Django : URLs et Vues
📅 12 juillet 2026 · Module : Django

---

## 1. Le système d'URL de Django (URLconf)

### Comment Django résout une URL

Quand une requête arrive, Django parcourt `ROOT_URLCONF` (défini dans `settings.py`) de haut en bas. Dès qu'un pattern correspond, il appelle la vue associée. S'il n'en trouve aucun, il renvoie une 404.

```python
# myproject/urls.py (ROOT_URLCONF)
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('articles/', include('articles.urls')),  # délègue à l'app
    path('api/', include('api.urls', namespace='api')),
]
```

### `path()` — le cas courant

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),                        # /
    path('articles/', views.liste_articles, name='article-list'),
    path('articles/<int:pk>/', views.detail_article, name='article-detail'),
    path('articles/<slug:slug>/', views.detail_par_slug, name='article-slug'),
    path('archives/<int:annee>/<int:mois>/', views.archives, name='archives'),
]
```

**Convertisseurs de types intégrés :**

| Convertisseur | Correspond à | Type Python |
|---------------|--------------|-------------|
| `<int:pk>` | Entier positif | `int` |
| `<str:nom>` | N'importe quelle chaîne sans `/` | `str` |
| `<slug:slug>` | Lettres, chiffres, tirets, underscores | `str` |
| `<uuid:id>` | UUID formaté | `uuid.UUID` |
| `<path:fichier>` | Chaîne avec `/` inclus | `str` |

### `re_path()` — quand `path()` ne suffit pas

```python
from django.urls import re_path

urlpatterns = [
    # Année sur 4 chiffres, mois sur 2 chiffres
    re_path(r'^archives/(?P<annee>[0-9]{4})/(?P<mois>[0-9]{2})/$',
            views.archives, name='archives'),
    # Extension facultative
    re_path(r'^export/(?P<fmt>csv|json|xlsx)/$',
            views.export, name='export'),
]
```

Note : depuis Django 3.1, préférer `path()` avec des convertisseurs custom si possible — c'est plus lisible.

### `include()` — modulariser les URLs

```python
# articles/urls.py
from django.urls import path
from . import views

app_name = 'articles'  # namespace de l'application

urlpatterns = [
    path('', views.liste, name='liste'),
    path('<int:pk>/', views.detail, name='detail'),
    path('nouveau/', views.creer, name='creer'),
    path('<int:pk>/modifier/', views.modifier, name='modifier'),
    path('<int:pk>/supprimer/', views.supprimer, name='supprimer'),
]
```

```python
# myproject/urls.py
urlpatterns = [
    path('articles/', include('articles.urls')),
]
```

### Namespaces — éviter les collisions

Sans namespace, si deux apps ont un URL nommé `detail`, `reverse('detail')` est ambigu.

```python
# Dans urls.py de l'app, définir app_name :
app_name = 'articles'

# Dans ROOT_URLCONF, on peut aussi passer le namespace à include() :
path('articles/', include(('articles.urls', 'articles'), namespace='articles'))
```

**Utilisation dans les templates et le code :**

```python
# Dans une vue :
from django.urls import reverse
url = reverse('articles:detail', kwargs={'pk': 42})
# → '/articles/42/'

# Avec reverse_lazy (pour les attributs de classe dans les CBV) :
from django.urls import reverse_lazy
success_url = reverse_lazy('articles:liste')
```

```html
<!-- Dans un template -->
<a href="{% url 'articles:detail' pk=article.pk %}">Lire</a>
```

---

## 2. Les vues fonctionnelles (FBV)

### Anatomie d'une vue

Une vue Django est simplement une fonction Python qui reçoit un `HttpRequest` et renvoie un `HttpResponse`.

```python
from django.http import HttpRequest, HttpResponse

def ma_vue(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Bonjour !", content_type="text/plain")
```

### L'objet `HttpRequest`

```python
def inspecter_requete(request):
    print(request.method)           # 'GET', 'POST', 'PUT', 'DELETE', ...
    print(request.path)             # '/articles/42/'
    print(request.GET)              # QueryDict des paramètres GET
    print(request.POST)             # QueryDict des données POST form-encoded
    print(request.body)             # bytes — corps brut (pour JSON)
    print(request.headers)          # dict des en-têtes HTTP
    print(request.META)             # dict complet incluant REMOTE_ADDR, etc.
    print(request.user)             # utilisateur authentifié (ou AnonymousUser)
    print(request.session)          # session courante
    print(request.FILES)            # fichiers uploadés
    print(request.COOKIES)          # cookies reçus
```

**Accéder aux paramètres GET avec valeur par défaut :**

```python
page = request.GET.get('page', 1)
tri = request.GET.get('tri', 'date')
```

### `HttpResponse` et variantes

```python
from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseForbidden,
    HttpResponseRedirect,
    Http404,
)
from django.shortcuts import get_object_or_404, redirect

# Réponse simple
return HttpResponse("OK", status=200)

# Réponse 404 — deux façons
return HttpResponseNotFound("Pas trouvé")
raise Http404("Article inexistant")  # déclenche la 404 page handler

# Redirection
return HttpResponseRedirect('/articles/')
return redirect('articles:liste')  # utilise reverse()
return redirect('articles:detail', pk=42)

# get_object_or_404 — raccourci très utilisé
article = get_object_or_404(Article, pk=pk)
```

**Codes de statut courants :**

| Code | Signification | Classe ou `status=` |
|------|--------------|---------------------|
| 200 | OK | `HttpResponse` (défaut) |
| 201 | Created | `status=201` |
| 204 | No Content | `status=204` |
| 301 | Moved Permanently | `HttpResponsePermanentRedirect` |
| 302 | Found (redirect) | `HttpResponseRedirect` |
| 400 | Bad Request | `status=400` |
| 403 | Forbidden | `HttpResponseForbidden` |
| 404 | Not Found | `HttpResponseNotFound` / `Http404` |
| 405 | Method Not Allowed | `HttpResponseNotAllowed` |
| 500 | Server Error | (géré automatiquement) |

### `JsonResponse` — renvoyer du JSON

```python
from django.http import JsonResponse

def api_articles(request):
    data = {
        'articles': [
            {'id': 1, 'titre': 'Premier article'},
            {'id': 2, 'titre': 'Deuxième article'},
        ],
        'total': 2,
    }
    return JsonResponse(data)
    # Content-Type: application/json
    # Corps: {"articles": [...], "total": 2}

# Pour renvoyer une liste à la racine (désactivation de la protection) :
return JsonResponse([1, 2, 3], safe=False)

# Avec un status code custom :
return JsonResponse({'erreur': 'Non trouvé'}, status=404)
```

### Passer des paramètres depuis l'URL

```python
# urls.py
path('articles/<int:pk>/', views.detail_article, name='article-detail'),

# views.py — le paramètre est passé en argument nommé
def detail_article(request, pk):
    # pk est déjà un int, Django l'a converti
    article = get_object_or_404(Article, pk=pk)
    return JsonResponse({
        'id': article.pk,
        'titre': article.titre,
        'contenu': article.contenu,
    })
```

```python
# Plusieurs paramètres
path('archives/<int:annee>/<int:mois>/', views.archives),

def archives(request, annee, mois):
    articles = Article.objects.filter(
        date_publication__year=annee,
        date_publication__month=mois,
    )
    ...
```

### Lire les données JSON dans POST

```python
import json
from django.http import JsonResponse

def creer_article(request):
    if request.method != 'POST':
        return JsonResponse({'erreur': 'Méthode non autorisée'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'erreur': 'JSON invalide'}, status=400)

    titre = data.get('titre', '').strip()
    if not titre:
        return JsonResponse({'erreur': 'Le titre est requis'}, status=400)

    # Créer l'objet...
    return JsonResponse({'id': 1, 'titre': titre}, status=201)
```

---

## 3. Décorateurs de vue

Les décorateurs sont des fonctions qui enveloppent une vue pour lui ajouter un comportement sans modifier son code.

### `@require_http_methods`

```python
from django.views.decorators.http import (
    require_http_methods,
    require_GET,
    require_POST,
    require_safe,  # GET + HEAD
)

@require_GET
def liste_articles(request):
    # Garantit que seul GET passe — Django renvoie 405 sinon
    ...

@require_POST
def creer_article(request):
    ...

@require_http_methods(['GET', 'POST'])
def article_form(request):
    if request.method == 'POST':
        ...
    else:
        ...
```

### `@login_required`

```python
from django.contrib.auth.decorators import login_required, permission_required

@login_required
def mon_profil(request):
    # Redirige vers settings.LOGIN_URL si non authentifié
    return HttpResponse(f"Bonjour {request.user.username}")

@login_required(login_url='/connexion/')  # URL custom
def tableau_de_bord(request):
    ...

@permission_required('articles.add_article', raise_exception=True)
def creer_article(request):
    # raise_exception=True → 403 au lieu de redirection
    ...
```

### Combiner des décorateurs

```python
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def supprimer_article(request, pk):
    # @login_required s'applique en premier (extérieur)
    # @require_POST s'applique en second (intérieur)
    article = get_object_or_404(Article, pk=pk, auteur=request.user)
    article.delete()
    return JsonResponse({'supprime': True})
```

### Écrire un décorateur custom

```python
from functools import wraps
from django.http import JsonResponse

def json_only(view_func):
    """Vérifie que Content-Type est application/json."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        content_type = request.headers.get('Content-Type', '')
        if request.method in ('POST', 'PUT', 'PATCH'):
            if 'application/json' not in content_type:
                return JsonResponse(
                    {'erreur': 'Content-Type doit être application/json'},
                    status=415
                )
        return view_func(request, *args, **kwargs)
    return wrapper

@json_only
@require_POST
def creer_article(request):
    data = json.loads(request.body)
    ...
```

---

## 4. Exemple complet : vue CRUD basique

```python
# articles/views.py
import json
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt  # seulement pour API pure
from .models import Article


def serialiser_article(article):
    """Convertit un Article en dict JSON-compatible."""
    return {
        'id': article.pk,
        'titre': article.titre,
        'contenu': article.contenu,
        'auteur': article.auteur.username,
        'publie': article.publie,
        'date_creation': article.date_creation.isoformat(),
    }


@require_http_methods(['GET'])
def liste_articles(request):
    """GET /articles/ — liste paginée des articles publiés."""
    page = int(request.GET.get('page', 1))
    par_page = int(request.GET.get('par_page', 10))
    debut = (page - 1) * par_page
    fin = debut + par_page

    articles = Article.objects.filter(publie=True).order_by('-date_creation')
    total = articles.count()
    articles_page = articles[debut:fin]

    return JsonResponse({
        'articles': [serialiser_article(a) for a in articles_page],
        'pagination': {
            'page': page,
            'par_page': par_page,
            'total': total,
            'pages': (total + par_page - 1) // par_page,
        }
    })


@require_http_methods(['GET'])
def detail_article(request, pk):
    """GET /articles/<pk>/ — détail d'un article."""
    try:
        article = Article.objects.get(pk=pk, publie=True)
    except Article.DoesNotExist:
        return JsonResponse({'erreur': 'Article non trouvé'}, status=404)

    return JsonResponse(serialiser_article(article))


@csrf_exempt  # En production, utiliser l'authentification par token
@login_required
@require_http_methods(['POST'])
def creer_article(request):
    """POST /articles/ — créer un article (authentifié)."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'erreur': 'JSON invalide'}, status=400)

    titre = data.get('titre', '').strip()
    contenu = data.get('contenu', '').strip()

    erreurs = {}
    if not titre:
        erreurs['titre'] = 'Ce champ est requis.'
    elif len(titre) > 200:
        erreurs['titre'] = '200 caractères maximum.'
    if not contenu:
        erreurs['contenu'] = 'Ce champ est requis.'

    if erreurs:
        return JsonResponse({'erreurs': erreurs}, status=400)

    article = Article.objects.create(
        titre=titre,
        contenu=contenu,
        auteur=request.user,
        publie=data.get('publie', False),
    )

    return JsonResponse(serialiser_article(article), status=201)


@csrf_exempt
@login_required
@require_http_methods(['PUT'])
def modifier_article(request, pk):
    """PUT /articles/<pk>/ — modifier un article (auteur uniquement)."""
    try:
        article = Article.objects.get(pk=pk, auteur=request.user)
    except Article.DoesNotExist:
        return JsonResponse({'erreur': 'Non trouvé ou non autorisé'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'erreur': 'JSON invalide'}, status=400)

    if 'titre' in data:
        article.titre = data['titre'].strip()
    if 'contenu' in data:
        article.contenu = data['contenu'].strip()
    if 'publie' in data:
        article.publie = bool(data['publie'])

    article.save()
    return JsonResponse(serialiser_article(article))


@csrf_exempt
@login_required
@require_http_methods(['DELETE'])
def supprimer_article(request, pk):
    """DELETE /articles/<pk>/ — supprimer (auteur uniquement)."""
    try:
        article = Article.objects.get(pk=pk, auteur=request.user)
    except Article.DoesNotExist:
        return JsonResponse({'erreur': 'Non trouvé ou non autorisé'}, status=404)

    article.delete()
    return JsonResponse({}, status=204)
```

```python
# articles/urls.py
from django.urls import path
from . import views

app_name = 'articles'

urlpatterns = [
    path('', views.liste_articles, name='liste'),
    path('<int:pk>/', views.detail_article, name='detail'),
    path('nouveau/', views.creer_article, name='creer'),
    path('<int:pk>/modifier/', views.modifier_article, name='modifier'),
    path('<int:pk>/supprimer/', views.supprimer_article, name='supprimer'),
]
```

---

## Points clés à retenir

- **`path()` suffit** pour la grande majorité des URLs. `re_path()` est pour les cas complexes.
- **Les namespaces** évitent les collisions quand plusieurs apps ont des URLs de même nom.
- **`HttpRequest`** contient tout : méthode, paramètres, corps, user, session.
- **`JsonResponse`** sérialise automatiquement le dict et pose le bon `Content-Type`.
- **Les décorateurs** (`@require_GET`, `@login_required`) ajoutent des gardes sans polluer le code métier.
- **`get_object_or_404`** est un raccourci pour le pattern try/except DoesNotExist → 404.
