# Jour 32 — DRF : Pagination et Filtering
📅 28 juillet 2026 · Module : DRF

---

## Pourquoi paginer ?

Sans pagination, `GET /articles/` retourne **tous les articles** — potentiellement des milliers. C'est :
- Lent (grosse requête SQL)
- Lourd en réseau (gros JSON)
- Inutilisable côté client

La pagination découpe les résultats en pages.

---

## PageNumberPagination

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
```

Ou par ViewSet :

```python
from rest_framework.pagination import PageNumberPagination

class ArticlePagination(PageNumberPagination):
    page_size = 10                        # 10 par page par défaut
    page_size_query_param = "page_size"   # ?page_size=20 pour changer
    max_page_size = 100                   # maximum autorisé

class ArticleViewSet(viewsets.ModelViewSet):
    pagination_class = ArticlePagination
```

**URL :** `GET /articles/?page=2&page_size=10`

**Réponse :**
```json
{
  "count": 150,
  "next": "http://api.com/articles/?page=3",
  "previous": "http://api.com/articles/?page=1",
  "results": [...]
}
```

---

## LimitOffsetPagination

```python
from rest_framework.pagination import LimitOffsetPagination

class ArticlePagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 100
```

**URL :** `GET /articles/?limit=10&offset=20`  
→ articles 20 à 30

Avantage : plus flexible pour les clients.

---

## CursorPagination

```python
from rest_framework.pagination import CursorPagination

class ArticleFeedPagination(CursorPagination):
    ordering = "-date_creation"    # doit être un champ ordonnable
    page_size = 20
```

**URL :** `GET /articles/?cursor=cD0yMDI2LTA3LTI3`  
→ la prochaine page après le curseur

Avantage : stable même si des données sont ajoutées/supprimées. Idéal pour les feeds en temps réel. Inconvénient : pas d'accès direct à la page N.

---

## Filtering avec django-filter

```bash
pip install django-filter
```

```python
# settings.py
INSTALLED_APPS = ["django_filters", ...]
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"]
}
```

**Filtrage simple (exact match) :**
```python
class ArticleViewSet(viewsets.ModelViewSet):
    filterset_fields = ["statut", "auteur"]
    # → GET /articles/?statut=publie&auteur=1
```

**FilterSet personnalisé :**
```python
import django_filters

class ArticleFilter(django_filters.FilterSet):
    titre = django_filters.CharFilter(lookup_expr="icontains")  # insensible à la casse
    date_min = django_filters.DateFilter(field_name="date_creation", lookup_expr="gte")
    date_max = django_filters.DateFilter(field_name="date_creation", lookup_expr="lte")
    vues_min = django_filters.NumberFilter(field_name="vues", lookup_expr="gte")

    class Meta:
        model = Article
        fields = ["statut", "auteur", "titre", "date_min", "date_max", "vues_min"]

class ArticleViewSet(viewsets.ModelViewSet):
    filterset_class = ArticleFilter
    # → GET /articles/?titre=python&statut=publie&vues_min=100
```

---

## SearchFilter — recherche full-text

```python
from rest_framework.filters import SearchFilter

class ArticleViewSet(viewsets.ModelViewSet):
    filter_backends = [SearchFilter]
    search_fields = ["titre", "contenu", "auteur__nom"]
    # → GET /articles/?search=python
    # Cherche "python" dans titre, contenu et nom de l'auteur

    # Préfixes :
    # "titre"         → icontains (défaut)
    # "^titre"        → istartswith
    # "=titre"        → iexact
    # "@titre"        → full-text search (PostgreSQL seulement)
```

---

## OrderingFilter — tri

```python
from rest_framework.filters import OrderingFilter

class ArticleViewSet(viewsets.ModelViewSet):
    filter_backends = [OrderingFilter]
    ordering_fields = ["date_creation", "titre", "vues"]
    ordering = ["-date_creation"]   # tri par défaut

    # → GET /articles/?ordering=vues        (croissant)
    # → GET /articles/?ordering=-date_creation  (décroissant)
    # → GET /articles/?ordering=titre,-vues  (combiné)
```

---

## Combiner tout

```python
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.select_related("auteur")
    serializer_class = ArticleSerializer
    pagination_class = ArticlePagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ArticleFilter
    search_fields = ["titre", "contenu"]
    ordering_fields = ["date_creation", "vues", "titre"]
    ordering = ["-date_creation"]

# → GET /articles/?statut=publie&search=django&ordering=-vues&page=2
```
