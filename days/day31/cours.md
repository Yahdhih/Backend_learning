# Jour 31 — DRF : ViewSets et Routers
📅 27 juillet 2026 · Module : DRF

---

## Le problème des APIViews répétitives

Avec APIView, tu réécris les mêmes patterns encore et again :

```python
class ArticleList(APIView):     # list + create
class ArticleDetail(APIView):   # retrieve + update + delete
```

Pour chaque model → 2 classes × N champs × 5 opérations = beaucoup de code dupliqué.

---

## ViewSet : regrouper les actions

Un `ViewSet` regroupe toutes les actions CRUD d'une ressource dans une seule classe.

```python
from rest_framework import viewsets, status
from rest_framework.response import Response

class ArticleViewSet(viewsets.ViewSet):
    """ViewSet manuel — tu implémentes tout."""

    def list(self, request):             # GET /articles/
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    def create(self, request):           # POST /articles/
        serializer = ArticleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):  # GET /articles/{pk}/
        article = get_object_or_404(Article, pk=pk)
        return Response(ArticleSerializer(article).data)

    def update(self, request, pk=None):    # PUT /articles/{pk}/
        article = get_object_or_404(Article, pk=pk)
        serializer = ArticleSerializer(article, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):   # DELETE /articles/{pk}/
        article = get_object_or_404(Article, pk=pk)
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

---

## ModelViewSet : tout automatique

`ModelViewSet` implémente les 5 actions pour toi :

```python
class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

# Ça donne automatiquement :
# list, create, retrieve, update, partial_update, destroy
```

**Autres combinaisons :**
```python
viewsets.ReadOnlyModelViewSet   # list + retrieve seulement
viewsets.GenericViewSet         # aucune action, ajoute des mixins manuellement
```

---

## Router : URL automatiques

Le Router génère les URLs depuis le ViewSet :

```python
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")
urlpatterns = router.urls
```

Ça génère automatiquement :

| URL | Méthode | Action |
|-----|---------|--------|
| `/articles/` | GET | `list` |
| `/articles/` | POST | `create` |
| `/articles/{pk}/` | GET | `retrieve` |
| `/articles/{pk}/` | PUT | `update` |
| `/articles/{pk}/` | PATCH | `partial_update` |
| `/articles/{pk}/` | DELETE | `destroy` |

---

## Personnaliser le ViewSet

```python
class ArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        """QuerySet dynamique selon l'utilisateur ou les params."""
        qs = Article.objects.all()
        statut = self.request.query_params.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        return qs.select_related("auteur")

    def get_serializer_class(self):
        """Serializer différent selon l'action."""
        if self.action == "list":
            return ArticleListSerializer    # version compacte
        return ArticleDetailSerializer      # version complète

    def perform_create(self, serializer):
        """Appelé lors de create() — injecte l'auteur."""
        serializer.save(auteur=self.request.user)

    def perform_update(self, serializer):
        """Appelé lors de update()."""
        serializer.save()
```

---

## Actions personnalisées avec `@action`

Pour des endpoints qui ne correspondent pas aux CRUD standards :

```python
from rest_framework.decorators import action

class ArticleViewSet(viewsets.ModelViewSet):
    ...

    @action(detail=True, methods=["post"])
    def publier(self, request, pk=None):
        """POST /articles/{pk}/publier/"""
        article = self.get_object()
        article.statut = "publie"
        article.save()
        return Response({"statut": "publié"})

    @action(detail=False, methods=["get"])
    def populaires(self, request):
        """GET /articles/populaires/"""
        articles = Article.objects.filter(vues__gte=100).order_by("-vues")[:10]
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"])
    def commentaires(self, request, pk=None):
        """GET/POST /articles/{pk}/commentaires/"""
        article = self.get_object()
        if request.method == "GET":
            comments = article.commentaires.all()
            return Response(CommentSerializer(comments, many=True).data)
        # POST : créer un commentaire
        ...
```

- `detail=True` → URL avec `{pk}` : `/articles/{pk}/action/`
- `detail=False` → URL sans `{pk}` : `/articles/action/`

---

## SimpleRouter vs DefaultRouter

```python
from rest_framework.routers import SimpleRouter, DefaultRouter

# DefaultRouter ajoute une API root (liste de toutes les URLs)
# GET / → {"articles": "http://..."}
router = DefaultRouter()

# SimpleRouter : pas d'API root
router = SimpleRouter()
```

---

## Permissions par action

```python
class ArticleViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]        # lecture publique
        return [IsAuthenticated()]     # écriture protégée
```
