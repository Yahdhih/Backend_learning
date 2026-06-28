# Jour 37 — Project Blog : Pagination et Filtres (2 août 2026)

## Objectif du jour

Rendre l'API du blog navigable et recherchable :
- **Pagination** : découper les longues listes en pages
- **Filtres** : filtrer par catégorie, tag, auteur, statut
- **Recherche** : chercher dans le titre et le contenu
- **Tri** : ordonner par date, popularité

---

## Pourquoi la pagination ?

Sans pagination, une requête `GET /api/posts/` retournerait TOUS les posts de la base. Avec 10 000 posts, ça serait une catastrophe.

Avec pagination :
```json
{
    "count": 247,          // Total des posts
    "next": "http://api.example.com/posts/?page=3",
    "previous": "http://api.example.com/posts/?page=1",
    "results": [...]       // 10 posts de la page actuelle
}
```

---

## pagination.py — Pagination personnalisée

```python
# blog/pagination.py

from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response


class BlogPagination(PageNumberPagination):
    """
    Pagination standard pour le blog.
    ?page=2&page_size=20
    """
    page_size = 10                    # 10 posts par défaut
    page_size_query_param = 'page_size'  # Le client peut modifier la taille
    max_page_size = 100               # Limite maximale
    page_query_param = 'page'         # Nom du paramètre de page

    def get_paginated_response(self, data):
        """Format de réponse personnalisé."""
        return Response({
            'pagination': {
                'count': self.page.paginator.count,
                'page': self.page.number,
                'pages': self.page.paginator.num_pages,
                'page_size': self.get_page_size(self.request),
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'results': data
        })

    def get_paginated_response_schema(self, schema):
        """Pour la documentation automatique."""
        return {
            'type': 'object',
            'properties': {
                'pagination': {
                    'type': 'object',
                    'properties': {
                        'count': {'type': 'integer'},
                        'page': {'type': 'integer'},
                        'pages': {'type': 'integer'},
                        'next': {'type': 'string', 'nullable': True},
                        'previous': {'type': 'string', 'nullable': True},
                    }
                },
                'results': schema,
            }
        }


class SmallPagination(PageNumberPagination):
    """Pagination petite pour les commentaires, tags, etc."""
    page_size = 5
    max_page_size = 50


class BlogCursorPagination(CursorPagination):
    """
    Pagination par curseur — plus efficace pour les grands datasets.
    Pas de numéro de page, mais des curseurs opaques.
    Avantage : pas de problème si des éléments sont ajoutés entre deux requêtes.

    Utilisation :
    ?cursor=cD0yMDIz  (curseur opaque)
    """
    page_size = 10
    ordering = '-created_at'  # Tri par défaut
    cursor_query_param = 'cursor'
```

---

## filters.py — Filtres personnalisés

```python
# blog/filters.py

import django_filters
from django_filters import rest_framework as filters
from .models import Post, Comment


class PostFilter(filters.FilterSet):
    """
    Filtres pour les posts du blog.

    Exemples d'utilisation :
    ?category=1                   → posts de la catégorie 1
    ?category__slug=technologie   → posts de la catégorie "technologie"
    ?tags=1&tags=2                → posts avec le tag 1 OU 2
    ?author=alice                 → posts de l'utilisateur alice
    ?status=published             → posts publiés
    ?search=django                → posts contenant "django" dans le titre ou contenu
    ?created_after=2026-01-01     → posts créés après le 1er janvier 2026
    ?ordering=-created_at         → tri du plus récent au plus ancien
    """

    # Filtre par catégorie (par ID ou par slug)
    category = filters.NumberFilter(field_name='category__id')
    category_slug = filters.CharFilter(field_name='category__slug', lookup_expr='iexact')

    # Filtre par tag (par ID ou par slug)
    tag = filters.NumberFilter(field_name='tags__id')
    tag_slug = filters.CharFilter(field_name='tags__slug', lookup_expr='iexact')

    # Filtre par auteur (par username)
    author = filters.CharFilter(field_name='author__username', lookup_expr='iexact')

    # Filtre par statut
    status = filters.ChoiceFilter(choices=[
        ('draft', 'Brouillon'),
        ('published', 'Publié'),
    ])

    # Recherche dans le titre et le contenu
    search = filters.CharFilter(method='filter_search')

    # Filtres de dates
    created_after = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    published_after = filters.DateFilter(field_name='published_at', lookup_expr='gte')

    # Tri
    ordering = filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
            ('published_at', 'published_at'),
            ('title', 'title'),
        ),
        field_labels={
            'created_at': 'Date de création',
            '-created_at': 'Plus récent d\'abord',
            'published_at': 'Date de publication',
            'title': 'Titre',
        }
    )

    class Meta:
        model = Post
        fields = ['category', 'status', 'author']

    def filter_search(self, queryset, name, value):
        """
        Recherche dans le titre ET le contenu (insensible à la casse).
        Un post correspond si le terme est dans le titre OU dans le contenu.
        """
        from django.db.models import Q
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value) | Q(content__icontains=value)
        ).distinct()
```

---

## views.py — Mise à jour avec filtres et pagination

```python
# blog/views.py (ajouts pour les filtres et la pagination)

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q, Count
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Tag, Post, Comment
from .serializers import (
    CategorySerializer, TagSerializer,
    PostListSerializer, PostDetailSerializer, PostCreateSerializer,
    CommentSerializer, CommentCreateSerializer,
    UserRegisterSerializer, UserMinimalSerializer,
)
from .permissions import IsAuthorOrReadOnly, IsCommentAuthorOrPostAuthor
from .pagination import BlogPagination, SmallPagination
from .filters import PostFilter


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    # Filtres et tri
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        from rest_framework.permissions import IsAdminUser
        return [IsAdminUser()]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'destroy':
            from rest_framework.permissions import IsAdminUser
            return [IsAdminUser()]
        return [IsAuthenticated()]


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet complet avec filtres, recherche et pagination.
    """
    queryset = Post.objects.all()
    pagination_class = BlogPagination

    # Backends de filtres
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PostFilter

    # SearchFilter intégré DRF (en plus de notre filtre personnalisé)
    search_fields = ['title', 'content', 'author__username']

    # Tri disponibles
    ordering_fields = ['created_at', 'published_at', 'title']
    ordering = ['-created_at']  # Tri par défaut

    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer
        elif self.action == 'create':
            return PostCreateSerializer
        return PostDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'published']:
            return [AllowAny()]
        elif self.action == 'create':
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthorOrReadOnly()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Post.objects.select_related('author', 'category').prefetch_related('tags')

        # Annoter avec le nombre de commentaires pour le tri
        qs = qs.annotate(comments_count=Count('comments'))

        if self.request.user.is_authenticated:
            if self.request.user.is_staff:
                return qs
            return qs.filter(
                Q(status=Post.PUBLISHED) | Q(author=self.request.user)
            )
        return qs.filter(status=Post.PUBLISHED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == Post.DRAFT:
            if not request.user.is_authenticated or (
                instance.author != request.user and not request.user.is_staff
            ):
                raise PermissionDenied("Ce post est un brouillon privé.")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['get'])
    def published(self, request):
        """GET /api/posts/published/ — avec filtres et pagination"""
        qs = Post.objects.filter(status=Post.PUBLISHED).select_related('author', 'category').prefetch_related('tags')

        # Appliquer les filtres manuellement
        filterset = PostFilter(request.GET, queryset=qs, request=request)
        qs = filterset.qs

        # Paginer
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = PostListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = PostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_posts(self, request):
        """GET /api/posts/my_posts/ — mes posts avec pagination"""
        qs = Post.objects.filter(author=request.user).select_related('category').prefetch_related('tags')
        qs = qs.order_by('-created_at')

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = PostListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = PostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        post = self.get_object()
        if post.author != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'Vous n\'êtes pas l\'auteur de ce post.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if post.status == Post.PUBLISHED:
            return Response(
                {'detail': 'Ce post est déjà publié.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        post.status = Post.PUBLISHED
        post.save()
        serializer = PostDetailSerializer(post, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        post = self.get_object()

        if post.status == Post.DRAFT:
            if not request.user.is_authenticated or post.author != request.user:
                raise PermissionDenied("Ce post n'est pas accessible.")

        if request.method == 'GET':
            comments = post.comments.select_related('author').all()
            serializer = CommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)

        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentification requise pour commenter.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = CommentCreateSerializer(data=request.data)
        if serializer.is_valid():
            Comment.objects.create(
                post=post,
                author=request.user,
                content=serializer.validated_data['content']
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsCommentAuthorOrPostAuthor]
    pagination_class = SmallPagination

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['post']
    ordering_fields = ['created_at']
    ordering = ['created_at']

    def get_queryset(self):
        return Comment.objects.select_related('author', 'post').all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
```

---

## settings.py — Configuration django-filter

```python
# blog_api/settings.py

INSTALLED_APPS = [
    # ...
    'django_filters',
    # ...
]

REST_FRAMEWORK = {
    # ...
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'blog.pagination.BlogPagination',
    'PAGE_SIZE': 10,
}
```

---

## Tester avec curl

```bash
# ── Pagination ──

# Page 1 (par défaut)
curl -s "http://127.0.0.1:8000/api/posts/" | python -m json.tool

# Page 2
curl -s "http://127.0.0.1:8000/api/posts/?page=2" | python -m json.tool

# 20 posts par page
curl -s "http://127.0.0.1:8000/api/posts/?page_size=20" | python -m json.tool

# ── Filtres ──

# Par catégorie (par ID)
curl -s "http://127.0.0.1:8000/api/posts/?category=1" | python -m json.tool

# Par catégorie (par slug)
curl -s "http://127.0.0.1:8000/api/posts/?category_slug=technologie" | python -m json.tool

# Par tag (par slug)
curl -s "http://127.0.0.1:8000/api/posts/?tag_slug=python" | python -m json.tool

# Par auteur
curl -s "http://127.0.0.1:8000/api/posts/?author=alice" | python -m json.tool

# Posts publiés seulement
curl -s "http://127.0.0.1:8000/api/posts/?status=published" | python -m json.tool

# ── Recherche ──

# Rechercher "django" dans titre et contenu
curl -s "http://127.0.0.1:8000/api/posts/?search=django" | python -m json.tool

# Recherche personnalisée (via notre filtre)
curl -s "http://127.0.0.1:8000/api/posts/?search=framework" | python -m json.tool

# ── Tri ──

# Plus récent d'abord (défaut)
curl -s "http://127.0.0.1:8000/api/posts/?ordering=-created_at" | python -m json.tool

# Plus ancien d'abord
curl -s "http://127.0.0.1:8000/api/posts/?ordering=created_at" | python -m json.tool

# Par titre A-Z
curl -s "http://127.0.0.1:8000/api/posts/?ordering=title" | python -m json.tool

# ── Combinaisons ──

# Posts de la catégorie "tech" contenant "python", page 1, 5 par page, tri par date
curl -s "http://127.0.0.1:8000/api/posts/?category_slug=technologie&search=python&page_size=5&ordering=-created_at" | python -m json.tool

# Posts publiés après le 1er janvier 2026
curl -s "http://127.0.0.1:8000/api/posts/?created_after=2026-01-01&status=published" | python -m json.tool
```

---

## Comprendre le format de pagination personnalisé

Réponse du `BlogPagination` :

```json
{
    "pagination": {
        "count": 47,
        "page": 2,
        "pages": 5,
        "page_size": 10,
        "next": "http://localhost:8000/api/posts/?page=3",
        "previous": "http://localhost:8000/api/posts/?page=1"
    },
    "results": [
        {
            "id": 11,
            "title": "Post numéro 11",
            ...
        }
    ]
}
```

Contre le format standard DRF :

```json
{
    "count": 47,
    "next": "...",
    "previous": "...",
    "results": [...]
}
```

---

## Comprendre DjangoFilterBackend vs SearchFilter

| Critère | `DjangoFilterBackend` | `SearchFilter` |
|---------|----------------------|----------------|
| Correspondance | Exacte (ou lookup défini) | Partielle (icontains) |
| Champs | `filterset_class` ou `filterset_fields` | `search_fields` |
| Paramètre URL | `?category=1&status=published` | `?search=terme` |
| Usage | Filtres précis | Recherche full-text |

On les combine : `?category=1&search=python` → catégorie 1 ET contient "python".

---

## Résumé du jour

Aujourd'hui tu as :
1. Créé une pagination personnalisée avec format de réponse enrichi
2. Créé des filtres précis avec `django-filter` (filterset)
3. Combiné `DjangoFilterBackend`, `SearchFilter` et `OrderingFilter`
4. Ajouté la pagination aux actions personnalisées (`my_posts`, `published`)
5. Testé les combinaisons de filtres avec curl

Demain (Jour 38) : on écrit les **tests automatisés** de l'API.
