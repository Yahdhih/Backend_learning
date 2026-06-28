# Jour 48 — Project Auth : Setup JWT avec Django (13 août 2026)

## Vue d'ensemble du projet

Pendant les jours 48 à 52, on construit un **système d'authentification complet** prêt pour la production. Ce n'est pas un tutoriel Hello World — c'est du code qu'on pourrait déployer dans une vraie API.

### Ce qu'on va construire

```
Auth System v1.0
├── JWT tokens (access + refresh)
├── Token rotation avec blacklist
├── RBAC (Role-Based Access Control)
├── Rate limiting sur les endpoints sensibles
├── Account lockout après N tentatives échouées
├── Email verification
├── Password reset sécurisé
├── 2FA (TOTP)
└── Test suite complète
```

### Stack technique

- **Django 4.2** + **Django REST Framework 3.14**
- **djangorestframework-simplejwt** — gestion JWT
- **django-ratelimit** — rate limiting
- **pyotp** — TOTP pour 2FA
- **PostgreSQL** (ou SQLite pour le dev)

---

## Structure du projet

```
auth_system/
├── manage.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/
│   ├── __init__.py
│   ├── models.py          ← Custom User model
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── permissions.py     ← Custom permission classes
│   └── admin.py
└── requirements.txt
```

---

## Pourquoi JWT ?

### Session classique vs JWT

**Session classique (stateful)**
```
Client → POST /login → Server crée session en DB → retourne session_id cookie
Client → GET /profile (avec cookie) → Server vérifie session en DB → répond
```
Problème : chaque requête fait une query DB. Ne passe pas à l'échelle horizontalement sans session partagée (Redis).

**JWT (stateless)**
```
Client → POST /login → Server signe un token → retourne access_token + refresh_token
Client → GET /profile (avec Bearer token) → Server vérifie la signature → répond SANS query DB
```
Le token est auto-vérifiant. Mais : on ne peut pas l'invalider sans blacklist.

### Anatomie d'un JWT

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9    ← Header (base64)
.eyJ1c2VyX2lkIjoxLCJleHAiOjE2OTk5OTk5OX0  ← Payload (base64)
.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c  ← Signature (HMAC-SHA256)
```

Payload décodé :
```json
{
  "token_type": "access",
  "exp": 1699999999,
  "iat": 1699996399,
  "jti": "3f8e9a1b2c4d5e6f",
  "user_id": 42
}
```

---

## Setup du projet

### Installation

```bash
python -m venv venv
source venv/bin/activate
pip install django djangorestframework djangorestframework-simplejwt Pillow
django-admin startproject config .
python manage.py startapp accounts
```

### requirements.txt

```
Django==4.2.7
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.0
Pillow==10.1.0
python-decouple==3.8
psycopg2-binary==2.9.9
```

---

## Custom User Model

La règle d'or : **toujours créer un custom User model au début du projet**. Impossible de changer facilement après les premières migrations.

### accounts/models.py

```python
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    """Manager personnalisé : email comme identifiant principal."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Modèle utilisateur custom.
    - email comme username
    - rôles intégrés (jour 49)
    - champs pour la sécurité (jour 51)
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        MODERATOR = "moderator", "Modérateur"
        USER = "user", "Utilisateur"

    # Identité
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # Rôle
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )

    # Statuts Django standard
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    # Sécurité (utilisé jour 51)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    # Dates
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    # Champ utilisé comme "username"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # email + password suffisent pour createsuperuser

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_locked(self):
        """Vérifie si le compte est verrouillé (jour 51)."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def reset_failed_attempts(self):
        """Reset le compteur de tentatives échouées."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def increment_failed_attempts(self, max_attempts=5, lockout_minutes=30):
        """Incrémente et verrouille si nécessaire."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_minutes)
        self.save(update_fields=["failed_login_attempts", "locked_until"])
```

---

## Settings configuration

### config/settings.py (sections clés)

```python
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-use-env-var")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost 127.0.0.1").split()

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # Pour invalider les tokens
    # Local
    "accounts",
]

# ============================================================
# AUTH — Custom User Model
# ============================================================
AUTH_USER_MODEL = "accounts.User"

# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",  # Sécurisé par défaut
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
        "login": "5/minute",       # Throttle spécifique pour le login (jour 51)
    },
}

# ============================================================
# SIMPLEJWT CONFIGURATION
# ============================================================
SIMPLE_JWT = {
    # Durées de vie
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),     # Court : 15 min
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),        # Long : 7 jours

    # Rotation (jour 50)
    "ROTATE_REFRESH_TOKENS": True,      # Nouveau refresh à chaque usage
    "BLACKLIST_AFTER_ROTATION": True,   # Ancien refresh mis en blacklist

    # Algorithme de signature
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,

    # Claims standards
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",

    # Token class (on peut personnaliser, jour 50)
    "TOKEN_OBTAIN_SERIALIZER": "accounts.serializers.CustomTokenObtainPairSerializer",

    # Type de token dans le payload
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}
```

---

## Serializers

### accounts/serializers.py

```python
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Surcharge du serializer JWT pour ajouter des claims custom dans le token.
    On ajoute : email, role, is_email_verified.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Claims additionnels (lisibles dans le token décodé)
        token["email"] = user.email
        token["role"] = user.role
        token["is_email_verified"] = user.is_email_verified

        return token

    def validate(self, attrs):
        """
        Surcharge pour vérifier le verrouillage du compte.
        (La logique complète est au jour 51.)
        """
        data = super().validate(attrs)

        # Ajouter des infos user dans la réponse
        data["user"] = {
            "id": str(self.user.id),
            "email": self.user.email,
            "role": self.user.role,
            "full_name": self.user.full_name,
        }

        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer pour l'inscription."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "first_name", "last_name"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer pour afficher/modifier le profil."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "role", "is_email_verified", "date_joined"]
        read_only_fields = ["id", "email", "role", "is_email_verified", "date_joined"]


class LogoutSerializer(serializers.Serializer):
    """Pour invalider le refresh token lors du logout."""
    refresh = serializers.CharField(required=True)

    def validate_refresh(self, value):
        self.token = RefreshToken(value)
        return value

    def save(self):
        self.token.blacklist()
```

---

## Views

### accounts/views.py

```python
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
    LogoutSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Inscription d'un nouvel utilisateur.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Générer un token JWT immédiatement après l'inscription
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Compte créé avec succès.",
                "user": UserProfileSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Retourne access + refresh token.
    Notre serializer custom ajoute role/email dans le payload.
    """
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklist le refresh token → déconnexion.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Déconnecté avec succès."}, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/profile/  → voir son profil
    PUT  /api/auth/profile/  → modifier son profil
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
```

---

## URLs

### accounts/urls.py

```python
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    LogoutView,
    ProfileView,
)

urlpatterns = [
    # Auth flow principal
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),

    # Token management
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),

    # Profil
    path("profile/", ProfileView.as_view(), name="auth-profile"),
]
```

### config/urls.py

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
]
```

---

## Admin

### accounts/admin.py

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "full_name", "role", "is_active", "is_email_verified", "date_joined"]
    list_filter = ["role", "is_active", "is_email_verified", "is_staff"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name")}),
        ("Rôle & Statut", {"fields": ("role", "is_active", "is_email_verified", "is_staff", "is_superuser")}),
        ("Sécurité", {"fields": ("failed_login_attempts", "locked_until", "last_login_ip")}),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role"),
        }),
    )

    # Remplace username_field par email
    ordering = ["email"]
```

---

## Migrations et premier lancement

```bash
# Créer les migrations du custom user model (AVANT tout autre migrate)
python manage.py makemigrations accounts
python manage.py migrate

# Créer un superuser
python manage.py createsuperuser
# Email: admin@example.com
# Password: MotDePasseStrong123!

# Lancer le serveur
python manage.py runserver
```

---

## Récapitulatif des endpoints

| Méthode | Endpoint | Auth requise | Description |
|---------|----------|-------------|-------------|
| POST | `/api/auth/register/` | Non | Inscription |
| POST | `/api/auth/login/` | Non | Login → tokens |
| POST | `/api/auth/logout/` | Oui | Logout → blacklist refresh |
| POST | `/api/auth/token/refresh/` | Non* | Renouveler access token |
| POST | `/api/auth/token/verify/` | Non | Vérifier validité d'un token |
| GET | `/api/auth/profile/` | Oui | Voir son profil |
| PUT | `/api/auth/profile/` | Oui | Modifier son profil |

*Le refresh token lui-même fait office d'authentification.

---

## Points clés à retenir

1. **AUTH_USER_MODEL doit être défini avant la première migration** — impossible de changer après sans reset complet de la DB.
2. **UUID comme primary key** — évite l'énumération des IDs (`/users/1/`, `/users/2/`...).
3. **ACCESS_TOKEN_LIFETIME court** (15 min) — réduit la fenêtre d'exploitation si un token est volé.
4. **BLACKLIST_AFTER_ROTATION = True** — quand on renouvelle un refresh token, l'ancien est immédiatement invalidé.
5. **Claims additionnels dans le token** — évite une query DB à chaque requête pour connaître le rôle.
