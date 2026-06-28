# Jour 36 — Project Blog : Auth et Permissions (1 août 2026)

## Objectif du jour

Sécuriser l'API blog avec un système de permissions précis :
- Tout le monde peut lire les posts publiés
- Seuls les utilisateurs authentifiés peuvent créer des posts
- Seul l'auteur d'un post peut le modifier ou le supprimer
- Les drafts ne sont visibles que par leur auteur

---

## Rappel : les permissions dans DRF

DRF vérifie les permissions à deux niveaux :

```
Requête
  ↓
has_permission(request, view)       → niveau vue (ex: est-ce que l'user est auth?)
  ↓
has_object_permission(request, view, obj)  → niveau objet (ex: est-ce qu'il possède cet objet?)
  ↓
Action autorisée
```

Les permissions intégrées :
- `AllowAny` : tout le monde
- `IsAuthenticated` : utilisateurs connectés seulement
- `IsAuthenticatedOrReadOnly` : lecture libre, écriture auth requise
- `IsAdminUser` : admin seulement

---

## permissions.py — Classes personnalisées

```python
# blog/permissions.py

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthorOrReadOnly(BasePermission):
    """
    Permission personnalisée :
    - Lecture (GET, HEAD, OPTIONS) : tout le monde
    - Écriture (POST, PUT, PATCH, DELETE) : auteur seulement

    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
    """

    def has_permission(self, request, view):
        # Les méthodes de lecture sont toujours autorisées
        if request.method in SAFE_METHODS:
            return True
        # Pour écrire, il faut être authentifié
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Lecture : toujours autorisée
        if request.method in SAFE_METHODS:
            return True
        # Écriture : l'utilisateur doit être l'auteur
        return obj.author == request.user


class IsAuthorOrAdmin(BasePermission):
    """
    Permet à l'auteur OU à un admin de modifier/supprimer.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        # Admin peut tout faire
        if request.user.is_staff:
            return True
        # L'auteur peut modifier ses propres objets
        return obj.author == request.user


class IsCommentAuthorOrPostAuthor(BasePermission):
    """
    Pour les commentaires :
    - L'auteur du commentaire peut le modifier/supprimer
    - L'auteur du post peut supprimer n'importe quel commentaire de son post
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        # L'auteur du commentaire peut tout faire
        if obj.author == request.user:
            return True
        # L'auteur du post peut supprimer les commentaires
        if request.method == 'DELETE' and obj.post.author == request.user:
            return True
        return False


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission générique pour les objets avec un champ 'owner' ou 'user'.
    Adaptable selon le modèle.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        # Cherche d'abord 'author', puis 'owner', puis 'user'
        owner = getattr(obj, 'author', None) or getattr(obj, 'owner', None) or getattr(obj, 'user', None)
        return owner == request.user
```

---

## views.py — Mise à jour avec permissions

```python
# blog/views.py (version complète avec permissions)

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied

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
from .permissions import IsAuthorOrReadOnly, IsAuthorOrAdmin, IsCommentAuthorOrPostAuthor


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Catégories : lecture libre, écriture admin seulement
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['list', 'retrieve']:
            # Lecture : tout le monde
            return [AllowAny()]
        # Écriture : admin seulement
        from rest_framework.permissions import IsAdminUser
        return [IsAdminUser()]


class TagViewSet(viewsets.ModelViewSet):
    """
    Tags : lecture libre, création pour auth, suppression admin
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action in ['destroy']:
            from rest_framework.permissions import IsAdminUser
            return [IsAdminUser()]
        return [IsAuthenticated()]


class PostViewSet(viewsets.ModelViewSet):
    """
    Posts avec permissions complètes :
    - Lecture : tout le monde (posts publiés) / auteur (ses drafts)
    - Création : utilisateurs authentifiés
    - Modification/Suppression : auteur seulement
    """
    queryset = Post.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer
        elif self.action == 'create':
            return PostCreateSerializer
        return PostDetailSerializer

    def get_permissions(self):
        """
        Permissions dynamiques selon l'action :
        - list, retrieve : AllowAny (le queryset filtre déjà les drafts)
        - create : IsAuthenticated
        - update, partial_update, destroy : IsAuthorOrReadOnly
        - publish, my_posts : IsAuthenticated
        """
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action == 'create':
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthorOrReadOnly()]
        elif self.action in ['publish', 'my_posts']:
            return [IsAuthenticated()]
        elif self.action == 'published':
            return [AllowAny()]
        elif self.action == 'comments':
            return [IsAuthenticatedOrReadOnly()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Filtre le queryset selon l'authentification :
        - Non-auth : posts publiés seulement
        - Auth : posts publiés + ses propres drafts
        """
        qs = Post.objects.select_related('author', 'category').prefetch_related('tags')

        if self.request.user.is_authenticated:
            if self.request.user.is_staff:
                # Admin voit tout
                return qs
            # Auteur voit ses drafts + tous les posts publiés
            return qs.filter(
                Q(status=Post.PUBLISHED) | Q(author=self.request.user)
            )
        # Non-authentifié : seulement les posts publiés
        return qs.filter(status=Post.PUBLISHED)

    def retrieve(self, request, *args, **kwargs):
        """
        Récupérer un post : vérifier que les drafts ne sont visibles
        que par leur auteur.
        """
        instance = self.get_object()

        # Un draft ne peut être vu que par son auteur
        if instance.status == Post.DRAFT:
            if not request.user.is_authenticated or (
                instance.author != request.user and not request.user.is_staff
            ):
                raise PermissionDenied("Ce post est un brouillon privé.")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """L'auteur est automatiquement l'utilisateur connecté."""
        serializer.save(author=self.request.user)

    # ── Actions personnalisées ──

    @action(detail=False, methods=['get'])
    def published(self, request):
        """GET /api/posts/published/ — posts publiés seulement"""
        qs = Post.objects.filter(status=Post.PUBLISHED).select_related('author', 'category').prefetch_related('tags')
        serializer = PostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_posts(self, request):
        """GET /api/posts/my_posts/ — mes posts (tous statuts)"""
        qs = Post.objects.filter(author=request.user).select_related('category').prefetch_related('tags')
        serializer = PostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        """POST /api/posts/{id}/publish/ — publier un post"""
        post = self.get_object()

        # Vérifier que l'user est l'auteur
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
        """
        GET  /api/posts/{id}/comments/ — commentaires du post
        POST /api/posts/{id}/comments/ — ajouter un commentaire
        """
        post = self.get_object()

        # Vérifier l'accès au post (draft = auteur seulement)
        if post.status == Post.DRAFT:
            if not request.user.is_authenticated or post.author != request.user:
                raise PermissionDenied("Ce post n'est pas accessible.")

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
    """Commentaires avec permission IsCommentAuthorOrPostAuthor."""
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsCommentAuthorOrPostAuthor]

    def get_queryset(self):
        return Comment.objects.select_related('author', 'post').all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# ─────────────────────────────────────────
# Vues d'authentification
# ─────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/"""
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserMinimalSerializer(user).data,
            'token': token.key,
            'message': 'Compte créé avec succès.'
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """POST /api/auth/login/"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': 'Username et password requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {'detail': 'Identifiants invalides.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserMinimalSerializer(user).data,
        })


class LogoutView(generics.GenericAPIView):
    """POST /api/auth/logout/ — invalider le token"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Supprimer le token de la base de données
        request.user.auth_token.delete()
        return Response({'message': 'Déconnecté avec succès.'})


class MeView(generics.RetrieveAPIView):
    """GET /api/auth/me/ — profil de l'utilisateur connecté"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserMinimalSerializer

    def get_object(self):
        return self.request.user
```

---

## blog/urls.py — Mise à jour

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
    LogoutView,
    MeView,
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
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),
]
```

---

## Tester les permissions avec curl

```bash
# ── Setup : créer deux utilisateurs ──

# Alice
ALICE=$(curl -s -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "password123", "password_confirm": "password123"}')
ALICE_TOKEN=$(echo $ALICE | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Bob
BOB=$(curl -s -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "email": "bob@example.com", "password": "password123", "password_confirm": "password123"}')
BOB_TOKEN=$(echo $BOB | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

echo "Alice token: $ALICE_TOKEN"
echo "Bob token: $BOB_TOKEN"

# ── Alice crée un post ──
POST=$(curl -s -X POST http://127.0.0.1:8000/api/posts/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $ALICE_TOKEN" \
  -d '{"title": "Post d'\''Alice", "content": "Contenu...", "status": "draft"}')
POST_ID=$(echo $POST | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Post ID: $POST_ID"

# ── Test 1 : Bob essaie de modifier le post d'Alice ──
# Attendu : 403 Forbidden
curl -s -X PATCH http://127.0.0.1:8000/api/posts/$POST_ID/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $BOB_TOKEN" \
  -d '{"title": "Post modifié par Bob"}' | python -m json.tool
# → {"detail": "You do not have permission to perform this action."}

# ── Test 2 : Anonymous essaie de voir le draft d'Alice ──
# Attendu : 403 Forbidden (draft privé)
curl -s http://127.0.0.1:8000/api/posts/$POST_ID/ | python -m json.tool

# ── Test 3 : Alice voit son propre draft ──
# Attendu : 200 OK avec le post
curl -s http://127.0.0.1:8000/api/posts/$POST_ID/ \
  -H "Authorization: Token $ALICE_TOKEN" | python -m json.tool

# ── Test 4 : Alice publie son post ──
# Attendu : 200 OK
curl -s -X POST http://127.0.0.1:8000/api/posts/$POST_ID/publish/ \
  -H "Authorization: Token $ALICE_TOKEN" | python -m json.tool

# ── Test 5 : Anonymous voit le post publié ──
# Attendu : 200 OK
curl -s http://127.0.0.1:8000/api/posts/$POST_ID/ | python -m json.tool

# ── Test 6 : Bob essaie de supprimer le post d'Alice ──
# Attendu : 403 Forbidden
curl -s -X DELETE http://127.0.0.1:8000/api/posts/$POST_ID/ \
  -H "Authorization: Token $BOB_TOKEN"
# → 403

# ── Test 7 : Alice supprime son propre post ──
# Attendu : 204 No Content
curl -s -X DELETE http://127.0.0.1:8000/api/posts/$POST_ID/ \
  -H "Authorization: Token $ALICE_TOKEN"
# → 204

# ── Test 8 : Logout ──
curl -s -X POST http://127.0.0.1:8000/api/auth/logout/ \
  -H "Authorization: Token $ALICE_TOKEN" | python -m json.tool
# → {"message": "Déconnecté avec succès."}

# Après logout, le token est invalide
curl -s http://127.0.0.1:8000/api/posts/my_posts/ \
  -H "Authorization: Token $ALICE_TOKEN" | python -m json.tool
# → {"detail": "Invalid token."}
```

---

## Comprendre get_permissions()

La méthode `get_permissions()` dans un ViewSet permet d'avoir des permissions différentes selon l'action :

```python
def get_permissions(self):
    if self.action in ['list', 'retrieve']:
        return [AllowAny()]         # Lecture libre
    elif self.action == 'create':
        return [IsAuthenticated()]  # Créer = être connecté
    else:
        return [IsAuthorOrReadOnly()]  # Modifier = être l'auteur
```

C'est plus flexible que `permission_classes = [...]` qui s'applique à toutes les actions.

---

## Tableau récapitulatif des permissions

| Action | URL | Permission requise |
|--------|-----|--------------------|
| Lire les posts publiés | `GET /api/posts/` | Aucune |
| Voir un draft | `GET /api/posts/{id}/` | Auteur seulement |
| Créer un post | `POST /api/posts/` | Authentifié |
| Modifier un post | `PATCH /api/posts/{id}/` | Auteur |
| Supprimer un post | `DELETE /api/posts/{id}/` | Auteur |
| Publier un post | `POST /api/posts/{id}/publish/` | Auteur |
| Voir mes posts | `GET /api/posts/my_posts/` | Authentifié |
| Créer une catégorie | `POST /api/categories/` | Admin |
| Supprimer un tag | `DELETE /api/tags/{id}/` | Admin |
| Commenter | `POST /api/posts/{id}/comments/` | Authentifié |
| Supprimer son commentaire | `DELETE /api/comments/{id}/` | Auteur du commentaire |

---

## Résumé du jour

Aujourd'hui tu as :
1. Créé des classes de permission personnalisées (`IsAuthorOrReadOnly`)
2. Utilisé `get_permissions()` pour des permissions dynamiques
3. Compris la différence entre `has_permission` (niveau vue) et `has_object_permission` (niveau objet)
4. Ajouté les endpoints logout et /me/
5. Testé les permissions avec deux utilisateurs différents

Demain (Jour 37) : **pagination et filtres** pour l'API.
