# Jour 43 — Django auth system + DRF Authentication
📅 8 août 2026 · Module : Auth

---

## Le système d'auth Django

Django fournit un système d'auth complet out-of-the-box.

### Le modèle User

```python
from django.contrib.auth.models import User

# Créer
user = User.objects.create_user(
    username="alice",
    email="alice@exemple.com",
    password="motdepasse123"    # hashé automatiquement avec PBKDF2
)

# Authentifier
from django.contrib.auth import authenticate
user = authenticate(username="alice", password="motdepasse123")
if user is not None:
    print("Authentifié !")

# Vérifier les permissions
user.is_authenticated    # True si connecté
user.is_staff            # accès à l'admin
user.is_superuser        # tous les droits
user.has_perm("blog.add_article")
user.has_perms(["blog.add_article", "blog.delete_article"])
```

### User custom (recommandé)

```python
# models.py — à faire AVANT la première migration
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True)
    role = models.CharField(
        max_length=20,
        choices=[("admin","Admin"), ("editor","Editor"), ("viewer","Viewer")],
        default="viewer"
    )

# settings.py
AUTH_USER_MODEL = "monapp.User"
```

---

## DRF Authentication Classes

DRF a ses propres classes d'authentification, séparées du système Django.

### BasicAuthentication

```python
# Authorization: Basic base64(username:password)
# Utilise seulement pour les tests. Jamais en prod sans HTTPS.
```

### SessionAuthentication

```python
# Utilise les sessions Django (cookie sessionid)
# Idéal pour les frontends sur le même domaine
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ]
}
```

### TokenAuthentication

```bash
pip install djangorestframework
# + ajouter "rest_framework.authtoken" dans INSTALLED_APPS
# + python manage.py migrate
```

```python
# Génère un token par user
from rest_framework.authtoken.models import Token
token = Token.objects.create(user=user)
# Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4f
```

```python
# Vue de login qui retourne le token
from rest_framework.authtoken.views import obtain_auth_token
urlpatterns = [
    path("api/auth/token/", obtain_auth_token),
]
```

### JWTAuthentication (avec SimpleJWT)

```bash
pip install djangorestframework-simplejwt
```

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ]
}

# urls.py
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
urlpatterns = [
    path("api/auth/login/", TokenObtainPairView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
]
```

---

## DRF Permission Classes

### Permissions globales

```python
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",  # tout requiert auth
    ]
}
```

### Permissions par vue

```python
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny

class ArticleViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]
```

### Permission custom

```python
from rest_framework.permissions import BasePermission

class IsAuthorOrReadOnly(BasePermission):
    """Lecture publique, écriture réservée à l'auteur."""

    def has_permission(self, request, view):
        # Toujours autorisé pour lire
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        # Écriture = authentifié
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Lecture = OK
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        # Écriture = auteur uniquement
        return obj.auteur == request.user


class IsRoleOrReadOnly(BasePermission):
    """Permet l'écriture seulement à un rôle spécifique."""
    required_role = "editor"  # à surcharger

    def has_permission(self, request, view):
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) == self.required_role
        )
```

---

## Ajouter l'auth à un ViewSet complet

```python
class ArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthorOrReadOnly]

    def get_queryset(self):
        # Un user voit ses brouillons + tous les articles publiés
        from django.db.models import Q
        if self.request.user.is_authenticated:
            return Article.objects.filter(
                Q(statut="publie") | Q(auteur=self.request.user)
            ).select_related("auteur")
        return Article.objects.filter(statut="publie").select_related("auteur")

    def perform_create(self, serializer):
        serializer.save(auteur=self.request.user)
```
