# Jour 52 — Tests du système d'authentification
📅 17 août 2026 · Module : Sécurité

---

## Stratégie de test pour l'auth

Un système d'authentification mal testé crée des failles qui passent inaperçues des mois. Il faut tester :

1. **Happy path** — le cas normal fonctionne
2. **Cas limites** — tokens expirés, invalides, révoqués
3. **Vecteurs d'attaque** — XSS, injection, brute-force
4. **Flux complets** — inscription → login → usage → logout

---

## Structure de test DRF

```python
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from django.test import TestCase

class AuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            password="motdepasse_securise_123",
        )
        self.client = APIClient()

    def test_login_valide(self):
        resp = self.client.post("/auth/login/", {
            "username": "alice",
            "password": "motdepasse_securise_123",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access_token", resp.data)
        self.assertIn("refresh_token", resp.data)

    def test_login_mauvais_mdp(self):
        resp = self.client.post("/auth/login/", {
            "username": "alice",
            "password": "mauvais",
        })
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("access_token", resp.data)
```

---

## Tester l'accès aux ressources protégées

```python
class ResourceProtegeeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="p")
        # Simuler un vrai login pour avoir un token
        resp = self.client.post("/auth/login/", {"username": "alice", "password": "p"})
        self.access_token = resp.data["access_token"]
        self.refresh_token = resp.data["refresh_token"]

    def test_acces_sans_token(self):
        resp = self.client.get("/api/profil/")
        self.assertEqual(resp.status_code, 401)

    def test_acces_avec_token_valide(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        resp = self.client.get("/api/profil/")
        self.assertEqual(resp.status_code, 200)

    def test_acces_avec_token_invalide(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer faux.token.ici")
        resp = self.client.get("/api/profil/")
        self.assertEqual(resp.status_code, 401)
```

---

## Tester les permissions (RBAC)

```python
class PermissionsTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="p")
        self.bob = User.objects.create_user("bob", password="p")
        self.admin = User.objects.create_user("admin", password="p", is_staff=True)
        self.article = Article.objects.create(titre="Test", auteur=self.alice)

    def test_auteur_peut_modifier(self):
        self.client.force_authenticate(user=self.alice)  # bypass auth pour tester perm
        resp = self.client.patch(f"/api/articles/{self.article.pk}/", {"titre": "Nouveau"})
        self.assertEqual(resp.status_code, 200)

    def test_autre_user_ne_peut_pas_modifier(self):
        self.client.force_authenticate(user=self.bob)
        resp = self.client.patch(f"/api/articles/{self.article.pk}/", {"titre": "Hack"})
        self.assertEqual(resp.status_code, 403)

    def test_admin_peut_tout(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(f"/api/articles/{self.article.pk}/")
        self.assertEqual(resp.status_code, 204)
```

---

## Tester la rotation des tokens

```python
class TokenRotationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="p")

    def test_rotation_basique(self):
        tokens = emettre_tokens(self.user)
        tokens2 = renouveler_access(tokens["refresh_token"])

        # Vérifier que l'ancien est révoqué
        ancien = RefreshToken.objects.get(token=tokens["refresh_token"])
        self.assertTrue(ancien.revoked)

        # Vérifier que le nouvel access est valide
        payload = verifier_jwt(tokens2["access_token"])
        self.assertEqual(payload["user_id"], self.user.pk)

    def test_detection_vol_token(self):
        tokens = emettre_tokens(self.user)
        renouveler_access(tokens["refresh_token"])  # rotation normale

        # L'attaquant essaie d'utiliser l'ancien refresh
        with self.assertRaises(ValueError):
            renouveler_access(tokens["refresh_token"])

        # Toute la famille doit être révoquée
        nb_valides = RefreshToken.objects.filter(
            user=self.user, revoked=False
        ).count()
        self.assertEqual(nb_valides, 0)
```

---

## Paramétrage des tests dans settings

```python
# settings_test.py
from settings import *

DEBUG = True
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # plus rapide en test
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Throttling désactivé en test
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
}
```
