# Jour 30 — DRF APIView et Response (26 juillet 2026)

## Introduction

Jusqu'ici, tu as appris à écrire des vues Django avec `View`, `ListView`, `DetailView`. DRF introduit ses propres classes de vues qui gèrent nativement JSON, la validation, la négociation de contenu, et les permissions. Ce cours couvre la couche de base : `APIView` et le système de `Response`.

---

## 1. `APIView` vs vues Django classiques

### Vues Django classiques — les limites

```python
# Vue Django standard
from django.views import View
from django.http import JsonResponse
import json

class PostView(View):
    def get(self, request):
        posts = Post.objects.all().values('id', 'title')
        return JsonResponse({'posts': list(posts)})

    def post(self, request):
        try:
            data = json.loads(request.body)  # parse manuel
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON invalide'}, status=400)
        # validation manuelle...
        # gestion des erreurs manuelle...
```

**Problèmes** :
- Parse JSON à la main
- Gestion d'erreurs boilerplate à répéter
- Pas de négociation de contenu
- Pas de permissions intégrées
- Réponses inconsistantes

### `APIView` — ce que ça change

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class PostView(APIView):
    def get(self, request):
        posts = Post.objects.all()
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)  # DRF gère JSON/HTML/etc.

    def post(self, request):
        serializer = PostSerializer(data=request.data)  # déjà parsé
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

**Ce qu'`APIView` fait pour toi** :
- `request.data` : parse automatiquement JSON, form data, multipart
- `Response` : négociation de contenu (JSON, HTML browsable, etc.)
- Exceptions converties en réponses HTTP propres
- Gestion des permissions déclarative
- Gestion des méthodes HTTP non supportées (405 automatique)
- Throttling intégré

---

## 2. L'objet `Request` DRF

`APIView` utilise `rest_framework.request.Request`, pas `django.http.HttpRequest`. C'est un wrapper autour de la requête Django standard.

### `request.data`

```python
class PostView(APIView):
    def post(self, request):
        # request.data remplace request.POST et request.body
        # Il parse automatiquement selon le Content-Type :
        # - application/json → dict depuis JSON
        # - multipart/form-data → dict depuis form
        # - application/x-www-form-urlencoded → dict depuis form

        titre = request.data.get('title')
        contenu = request.data.get('content')

        print(request.data)  # {'title': '...', 'content': '...'}
```

**Différence importante** :
- `request.POST` : seulement form data, pas JSON
- `request.data` : tous les formats (JSON inclus) — à utiliser avec DRF

### `request.query_params`

```python
class PostListView(APIView):
    def get(self, request):
        # request.query_params remplace request.GET
        # C'est un alias, mais plus explicite sémantiquement

        page = request.query_params.get('page', 1)
        search = request.query_params.get('search', '')
        status_filter = request.query_params.get('status', 'published')

        queryset = Post.objects.filter(status=status_filter)
        if search:
            queryset = queryset.filter(title__icontains=search)

        serializer = PostSerializer(queryset, many=True)
        return Response(serializer.data)
```

### Autres attributs utiles

```python
request.user         # L'utilisateur (authentifié ou AnonymousUser)
request.auth         # Token/session d'auth (selon le backend)
request.method       # 'GET', 'POST', 'PUT', 'DELETE', etc.
request.content_type # 'application/json', etc.
request.accepted_renderer  # Le renderer sélectionné
```

---

## 3. `Response` et négociation de contenu

`Response` n'est pas une `JsonResponse`. C'est une réponse "lazy" qui sérialise les données dans le format demandé par le client.

```python
from rest_framework.response import Response

# Basique
return Response({'message': 'OK'})

# Avec statut HTTP
return Response(data, status=status.HTTP_201_CREATED)

# Avec headers
return Response(data, headers={'X-Custom-Header': 'valeur'})

# Vide (204 No Content)
return Response(status=status.HTTP_204_NO_CONTENT)
```

### Comment la négociation fonctionne

Le client envoie un header `Accept` :
- `Accept: application/json` → réponse JSON
- `Accept: text/html` → réponse HTML browsable (interface DRF dans le navigateur)

DRF parcourt les renderers configurés et choisit le plus approprié.

---

## 4. Le module `status`

N'utilise jamais des nombres magiques pour les codes HTTP :

```python
from rest_framework import status

# 2xx Success
status.HTTP_200_OK           # GET réussi
status.HTTP_201_CREATED      # POST réussi, ressource créée
status.HTTP_204_NO_CONTENT   # DELETE réussi, pas de corps

# 4xx Client errors
status.HTTP_400_BAD_REQUEST   # Données invalides
status.HTTP_401_UNAUTHORIZED  # Non authentifié
status.HTTP_403_FORBIDDEN     # Authentifié mais pas autorisé
status.HTTP_404_NOT_FOUND     # Ressource inexistante
status.HTTP_405_METHOD_NOT_ALLOWED  # Méthode HTTP non supportée

# 5xx Server errors
status.HTTP_500_INTERNAL_SERVER_ERROR
```

---

## 5. Gestion des exceptions

### Exceptions DRF intégrées

DRF convertit automatiquement ces exceptions en réponses HTTP :

```python
from rest_framework.exceptions import (
    ValidationError,       # 400
    AuthenticationFailed,  # 401
    NotAuthenticated,      # 401
    PermissionDenied,      # 403
    NotFound,              # 404
    MethodNotAllowed,      # 405
    Throttled,             # 429
)

class PostDetailView(APIView):
    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            raise NotFound(f"Post #{pk} introuvable.")  # → 404 propre
        # ...
```

### Pattern `get_object_or_404`

```python
from django.shortcuts import get_object_or_404

class PostDetailView(APIView):
    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)  # → 404 si absent
        serializer = PostSerializer(post)
        return Response(serializer.data)
```

### Handler d'exceptions global (settings)

```python
# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'myapp.utils.custom_exception_handler'
}

# myapp/utils.py
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            'error': True,
            'message': str(exc),
            'detail': response.data,
            'status_code': response.status_code,
        }

    return response
```

---

## 6. Renderers

Les renderers définissent les formats de sortie supportés.

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',  # interface web
    ]
}
```

### Override par vue

```python
from rest_framework.renderers import JSONRenderer

class PostAPIView(APIView):
    renderer_classes = [JSONRenderer]  # seulement JSON pour cette vue
```

### `BrowsableAPIRenderer`

L'interface browsable DRF est activée par défaut. Elle permet de naviguer dans l'API depuis le navigateur, de faire des requêtes manuelles, et de voir la documentation auto-générée. **Désactive-la en production** si tu n'en as pas besoin :

```python
# production settings
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer']
}
```

---

## 7. Classes de permissions sur la vue

```python
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny

class PostListView(APIView):
    # Authentification obligatoire pour toutes les méthodes
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ...

class PublicView(APIView):
    # Ouvert à tous
    permission_classes = [AllowAny]
```

### Permissions par méthode

`APIView` n'a pas de support natif pour les permissions par méthode HTTP. La pratique courante est de gérer ça dans la logique :

```python
class PostDetailView(APIView):
    def get_permissions(self):
        # La méthode n'est pas encore connue ici, on utilise une permission commune
        return [IsAuthenticated()]

    def get(self, request, pk):
        # Lecture accessible à tous — géré différemment avec ViewSets (day31)
        ...
```

---

## 8. `@api_view` : décorateur pour vues fonctionnelles (FBV)

Si tu préfères les vues fonctionnelles, `@api_view` apporte les mêmes avantages que `APIView` :

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['GET', 'POST'])
def post_list(request):
    """Gère GET (liste) et POST (création)."""
    if request.method == 'GET':
        posts = Post.objects.filter(status='published')
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def post_detail(request, pk):
    """Gère GET, PUT, DELETE sur un post spécifique."""
    post = get_object_or_404(Post, pk=pk)

    if request.method == 'GET':
        serializer = PostSerializer(post)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = PostSerializer(post, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

**Quand utiliser `@api_view` vs `APIView`** :
- `@api_view` : vues simples, prototypage rapide, endpoints one-off
- `APIView` : logique complexe, beaucoup de méthodes, héritage, mixins

---

## 9. Structure recommandée d'un projet DRF

```
myapp/
├── models.py
├── serializers.py    ← tous les serializers
├── views.py          ← APIView / ViewSets
├── urls.py           ← patterns URL
├── permissions.py    ← permissions custom
└── tests/
    ├── test_serializers.py
    └── test_views.py
```

---

## 10. Comparaison des patterns de vues DRF

```
Pattern              Avantages                      Cas d'usage
─────────────────────────────────────────────────────────────────
@api_view            Simple, rapide                 Endpoints simples
APIView              Contrôle total, lisible        CRUD custom
GenericAPIView       Mixins, moins de code          CRUD standard
ViewSet              Encore moins de code, routers  APIs complètes
ModelViewSet         Minimal, magique               CRUD pur
```

---

## Points clés à retenir

1. `request.data` remplace `request.POST` + `json.loads(request.body)` — utilise toujours `request.data`
2. `request.query_params` remplace `request.GET` — même chose mais plus explicite
3. `Response` gère la négociation de contenu — pas besoin de `JsonResponse`
4. Le module `status` donne des constantes lisibles — jamais de nombres magiques
5. DRF convertit automatiquement les exceptions en réponses HTTP propres
6. `permission_classes` se déclare sur la classe pour protéger tous les endpoints
7. `@api_view` pour les FBV simples, `APIView` pour les CBV avec logique complexe
