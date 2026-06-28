# Jour 35 — Project Blog : Serializers et vues CRUD (31 juillet 2026)

## Objectif du jour

Construire les **serializers** et **ViewSets** pour exposer tous les modèles du blog via une API REST. À la fin du jour, l'API sera entièrement fonctionnelle pour les opérations CRUD.

---

## Rappel rapide : le flux DRF

```
Requête HTTP
    ↓
Router → URL → ViewSet
    ↓
Permission check
    ↓
Serializer (validation / désérialisation)
    ↓
QuerySet / Model
    ↓
Serializer (sérialisation)
    ↓
Réponse JSON
```

---

## serializers.py — Code complet

```python
# blog/serializers.py

from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Category, Tag, Post, Comment


# ─────────────────────────────────────────
# Serializers simples (utilisés comme imbriqués)
# ─────────────────────────────────────────

class UserMinimalSerializer(serializers.ModelSerializer):
    """Représentation minimale d'un utilisateur (pour imbrication)"""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'post_count']
        read_only_fields = ['slug']  # auto-généré dans le modèle

    def get_post_count(self, obj):
        return obj.posts.filter(status='published').count()


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']


# ─────────────────────────────────────────
# Post Serializers
# ─────────────────────────────────────────

class PostListSerializer(serializers.ModelSerializer):
    """
    Serializer allégé pour la liste des posts.
    On n'inclut pas le contenu complet pour économiser la bande passante.
    """
    author = UserMinimalSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'excerpt',
            'author', 'category', 'tags',
            'status', 'published_at', 'created_at',
            'comment_count',
        ]
        read_only_fields = ['slug', 'published_at', 'created_at']


class PostDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le détail d'un post.
    Inclut le contenu et les commentaires.
    """
    author = UserMinimalSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    # IDs pour l'écriture (écriture seulement, pas en lecture)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source='tags',
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'excerpt',
            'author', 'category', 'tags',
            'category_id', 'tag_ids',
            'status', 'published_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['slug', 'published_at', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Extraire les tags (ManyToMany, gestion séparée)
        tags = validated_data.pop('tags', [])
        # L'auteur est injecté depuis la vue (request.user)
        post = Post.objects.create(**validated_data)
        post.tags.set(tags)
        return post

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance


class PostCreateSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour la création de posts depuis l'API.
    L'auteur est automatiquement l'utilisateur connecté.
    """
    class Meta:
        model = Post
        fields = [
            'title', 'content', 'excerpt',
            'category', 'tags', 'status',
        ]

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        # L'auteur vient du contexte de la requête
        request = self.context.get('request')
        post = Post.objects.create(author=request.user, **validated_data)
        post.tags.set(tags)
        return post


# ─────────────────────────────────────────
# Comment Serializers
# ─────────────────────────────────────────

class CommentSerializer(serializers.ModelSerializer):
    author = UserMinimalSerializer(read_only=True)
    author_id = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'author_id', 'content', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        # author_id est HiddenField, il est déjà dans validated_data comme 'author'
        # grâce à CurrentUserDefault
        return Comment.objects.create(**validated_data)


class CommentCreateSerializer(serializers.ModelSerializer):
    """Pour créer un commentaire (le post vient de l'URL)"""

    class Meta:
        model = Comment
        fields = ['content']


# ─────────────────────────────────────────
# Auth Serializers
# ─────────────────────────────────────────

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Les mots de passe ne correspondent pas.")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
```

---

## views.py — ViewSets complets

```python
# blog/views.py

from django.contrib.auth.models import User
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token

from .models import Category, Tag, Post, Comment
from .serializers import (
    CategorySerializer,
    TagSerializer,
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
    CommentSerializer,
    CommentCreateSerializer,
    UserRegisterSerializer,
    UserMinimalSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour les catégories.
    GET /api/categories/
    POST /api/categories/
    GET /api/categories/{id}/
    PUT /api/categories/{id}/
    DELETE /api/categories/{id}/
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.all().order_by('name')


class TagViewSet(viewsets.ModelViewSet):
    """CRUD complet pour les tags."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.all().order_by('name')


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les posts du blog.

    Actions personnalisées :
    - GET /api/posts/published/  → posts publiés seulement
    - GET /api/posts/my_posts/   → mes posts (auth requise)
    - POST /api/posts/{id}/publish/  → publier un post
    """
    queryset = Post.objects.all()

    def get_serializer_class(self):
        """Choisit le serializer selon l'action."""
        if self.action == 'list':
            return PostListSerializer
        elif self.action == 'create':
            return PostCreateSerializer
        return PostDetailSerializer

    def get_queryset(self):
        """
        - Utilisateurs non-auth : posts publiés seulement
        - Utilisateurs auth : leurs drafts + tous les posts publiés
        """
        qs = Post.objects.select_related('author', 'category').prefetch_related('tags')

        if self.request.user.is_authenticated:
            # L'auteur voit ses propres drafts ET les posts publiés des autres
            from django.db.models import Q
            qs = qs.filter(
                Q(status='published') | Q(author=self.request.user)
            )
        else:
            qs = qs.filter(status='published')

        return qs

    def perform_create(self, serializer):
        """L'auteur est automatiquement l'utilisateur connecté."""
        serializer.save(author=self.request.user)

    # ── Actions personnalisées ──

    @action(detail=False, methods=['get'])
    def published(self, request):
        """GET /api/posts/published/ — tous les posts publiés"""
        qs = Post.objects.filter(status='published').select_related('author', 'category')
        serializer = PostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_posts(self, request):
        """GET /api/posts/my_posts/ — mes posts (auth requise)"""
        qs = Post.objects.filter(author=request.user).select_related('category')
        serializer = PostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        """POST /api/posts/{id}/publish/ — publier un post"""
        post = self.get_object()

        if post.author != request.user:
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
        """
        GET  /api/posts/{id}/comments/ → liste des commentaires
        POST /api/posts/{id}/comments/ → ajouter un commentaire
        """
        post = self.get_object()

        if request.method == 'GET':
            comments = post.comments.select_related('author').all()
            serializer = CommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)

        # POST
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
    """CRUD pour les commentaires."""
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.select_related('author', 'post').all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# ─────────────────────────────────────────
# Vues d'authentification
# ─────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — créer un compte"""
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Créer un token automatiquement
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'user': UserMinimalSerializer(user).data,
            'token': token.key,
            'message': 'Compte créé avec succès.'
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """POST /api/auth/login/ — obtenir un token"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': 'Username et password requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.contrib.auth import authenticate
        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {'detail': 'Identifiants invalides.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user': UserMinimalSerializer(user).data,
        })
```

---

## blog/urls.py — Configuration finale du routeur

```python
# blog/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    TagViewSet,
    PostViewSet,
    CommentViewSet,
    RegisterView,
    LoginView,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
]
```

---

## URLs générées par le router

Quand tu utilises `router.register()`, le router génère automatiquement ces URLs :

| Méthode | URL | Action ViewSet |
|---------|-----|----------------|
| GET | `/api/posts/` | `list` |
| POST | `/api/posts/` | `create` |
| GET | `/api/posts/{id}/` | `retrieve` |
| PUT | `/api/posts/{id}/` | `update` |
| PATCH | `/api/posts/{id}/` | `partial_update` |
| DELETE | `/api/posts/{id}/` | `destroy` |
| GET | `/api/posts/published/` | `published` (custom) |
| GET | `/api/posts/my_posts/` | `my_posts` (custom) |
| POST | `/api/posts/{id}/publish/` | `publish` (custom) |
| GET/POST | `/api/posts/{id}/comments/` | `comments` (custom) |

---

## Tester avec curl

```bash
# 1. S'inscrire
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "password123", "password_confirm": "password123"}'

# Réponse :
# {"user": {"id": 1, "username": "alice", ...}, "token": "abc123...", "message": "Compte créé avec succès."}

# 2. Se connecter et récupérer le token
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'

# 3. Créer une catégorie (avec token)
curl -X POST http://127.0.0.1:8000/api/categories/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token abc123..." \
  -d '{"name": "Technologie", "description": "Articles tech"}'

# 4. Créer un tag
curl -X POST http://127.0.0.1:8000/api/tags/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token abc123..." \
  -d '{"name": "Python"}'

# 5. Créer un post
curl -X POST http://127.0.0.1:8000/api/posts/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token abc123..." \
  -d '{"title": "Mon premier post", "content": "Contenu...", "category": 1, "tags": [1], "status": "draft"}'

# 6. Lister les posts publiés (sans auth)
curl http://127.0.0.1:8000/api/posts/

# 7. Publier le post
curl -X POST http://127.0.0.1:8000/api/posts/1/publish/ \
  -H "Authorization: Token abc123..."

# 8. Voir mes posts
curl http://127.0.0.1:8000/api/posts/my_posts/ \
  -H "Authorization: Token abc123..."

# 9. Commenter un post
curl -X POST http://127.0.0.1:8000/api/posts/1/comments/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token abc123..." \
  -d '{"content": "Super article !"}'
```

---

## Technique : get_serializer_class()

Un ViewSet peut utiliser des serializers différents selon l'action :

```python
class PostViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer     # allégé (pas le content)
        elif self.action == 'create':
            return PostCreateSerializer   # simplifié
        return PostDetailSerializer       # complet (detail, update, etc.)
```

C'est une pratique courante pour optimiser les performances : la liste renvoie moins de données que le détail.

---

## Technique : select_related et prefetch_related

```python
def get_queryset(self):
    # select_related : JOIN SQL pour ForeignKey (author, category)
    # prefetch_related : requête séparée pour ManyToMany (tags)
    return Post.objects.select_related('author', 'category').prefetch_related('tags')
```

Sans ça, Django fait une requête SQL par post pour récupérer l'auteur et la catégorie. Avec 100 posts, ça ferait 201 requêtes au lieu de 3.

---

## Résumé du jour

Aujourd'hui tu as :
1. Créé des serializers imbriqués (Post avec author, category, tags)
2. Utilisé différents serializers pour list vs detail
3. Créé des ViewSets avec actions personnalisées (`@action`)
4. Configuré le router DRF
5. Ajouté des vues d'authentification (register, login)
6. Testé l'API avec curl

Demain (Jour 36) : on ajoute les **permissions** (IsAuthorOrReadOnly).
