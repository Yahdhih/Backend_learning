# Jour 49 — RBAC : Rôles, Permissions et Contrôle d'accès
📅 14 août 2026 · Module : Sécurité

---

## RBAC vs ABAC vs ACL

| Modèle | Signification | Exemple |
|--------|---------------|---------|
| **RBAC** | Role-Based Access Control | "Les admins peuvent supprimer" |
| **ABAC** | Attribute-Based Access Control | "Un auteur peut modifier son article" |
| **ACL** | Access Control List | "Alice peut lire le fichier X" |

Django utilise une combinaison RBAC (groupes/permissions) + ABAC (object-level permissions).

---

## Le système de permissions Django

Django génère automatiquement 4 permissions par modèle :

```
app.add_article
app.view_article
app.change_article
app.delete_article
```

```python
# Vérifier les permissions
user.has_perm("monapp.add_article")     # True/False
user.has_perm("monapp.change_article")

# Assigner une permission
from django.contrib.auth.models import Permission
perm = Permission.objects.get(codename="add_article")
user.user_permissions.add(perm)

# Permissions via groupe
from django.contrib.auth.models import Group
groupe_redacteurs = Group.objects.create(name="Redacteurs")
groupe_redacteurs.permissions.add(perm)
user.groups.add(groupe_redacteurs)
```

---

## Permissions custom

```python
class Article(models.Model):
    class Meta:
        permissions = [
            ("publish_article", "Peut publier des articles"),
            ("moderate_article", "Peut modérer les commentaires"),
        ]
```

---

## RBAC dans DRF

```python
from rest_framework.permissions import BasePermission, IsAuthenticated

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff

class IsRedacteur(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name="Redacteurs").exists()

class IsAuteurOrReadOnly(BasePermission):
    """Autorise la lecture à tous, l'écriture seulement à l'auteur."""
    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return obj.auteur == request.user
```

---

## Hiérarchie de rôles

```python
class NiveauAcces:
    INVITE = 0
    UTILISATEUR = 1
    MODERATEUR = 2
    REDACTEUR = 3
    ADMIN = 4


class ProfilUtilisateur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    niveau = models.IntegerField(default=NiveauAcces.UTILISATEUR)

    def peut(self, niveau_requis: int) -> bool:
        return self.niveau >= niveau_requis


class RequiertNiveau(BasePermission):
    def __init__(self, niveau_minimum: int):
        self.niveau_minimum = niveau_minimum

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profil.peut(self.niveau_minimum)
        except ProfilUtilisateur.DoesNotExist:
            return False

# Usage dans une vue
class ArticleAdminView(APIView):
    permission_classes = [RequiertNiveau(NiveauAcces.ADMIN)]
```

---

## Object-level permissions (row-level security)

```python
class IsOwnerOrAdmin(BasePermission):
    """Accès si l'objet appartient à l'utilisateur, ou si l'utilisateur est admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        # L'objet doit avoir un champ owner ou auteur
        owner = getattr(obj, "owner", None) or getattr(obj, "auteur", None)
        return owner == request.user

class ArticleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    # DRF appelle has_object_permission automatiquement pour
    # retrieve, update, partial_update, destroy
```

---

## Rôles dans l'API : token JWT avec rôles

```python
# Lors de la création du JWT
payload = {
    "user_id": user.id,
    "username": user.username,
    "roles": list(user.groups.values_list("name", flat=True)),
    "is_staff": user.is_staff,
}

# Dans la permission
class JWTRolePermission(BasePermission):
    def __init__(self, role: str):
        self.role = role

    def has_permission(self, request, view):
        token_payload = getattr(request, "jwt_payload", {})
        return self.role in token_payload.get("roles", [])
```

---

## Décorateurs de vues fonctionnelles

```python
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test

@login_required
def ma_vue(request): ...

@permission_required("monapp.publish_article", raise_exception=True)
def publier_article(request, pk): ...

@user_passes_test(lambda u: u.is_staff)
def vue_admin(request): ...
```
