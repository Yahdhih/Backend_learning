# Jour 50 — Rotation des tokens et sécurité avancée
📅 15 août 2026 · Module : Sécurité

---

## Pourquoi faire tourner les tokens ?

Un access token compromis est valide jusqu'à son expiration. Un refresh token compromis l'est beaucoup plus longtemps (7 jours, 30 jours...).

**La rotation** limite la durée de vie effective d'un token volé.

---

## Token rotation : comment ça marche

```
1. Client reçoit : access_token (15min) + refresh_token_1 (7j)

2. Access expiré → client envoie refresh_token_1 pour renouveler

3. Serveur répond : nouveau access_token + refresh_token_2
   ET révoque refresh_token_1 en DB

4. Si un attaquant essaie d'utiliser refresh_token_1 → 401

Avantage : un refresh token utilisé deux fois = alerte de compromission
```

---

## Implémentation avec une allowlist DB

```python
class RefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=500, unique=True)
    expire_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    famille = models.UUIDField(default=uuid.uuid4)  # pour détecter le vol

    @classmethod
    def emettre(cls, user, token_str, expire_dans=7*24*3600):
        from django.utils import timezone
        import datetime
        return cls.objects.create(
            user=user,
            token=token_str,
            expire_at=timezone.now() + datetime.timedelta(seconds=expire_dans),
            famille=uuid.uuid4(),
        )

    def is_valide(self):
        from django.utils import timezone
        return not self.revoked and self.expire_at > timezone.now()

    def revoquer(self):
        self.revoked = True
        self.save()
```

---

## Détecter le vol de token (Token Family)

```
Famille = groupe de tokens issus du même refresh initial.

Si un refresh déjà révoqué est utilisé → toute la famille est révoquée.
→ L'utilisateur doit se reconnecter.
→ Si c'était une erreur client, peu grave.
→ Si c'était un attaquant, il est bloqué.
```

```python
def renouveler_avec_famille(refresh_token_str: str) -> dict:
    from django.utils import timezone

    try:
        rt = RefreshToken.objects.get(token=refresh_token_str)
    except RefreshToken.DoesNotExist:
        raise ValueError("Token inconnu")

    if rt.revoked:
        # ALERTE : token déjà révoqué utilisé → vol probable !
        # Révoquer toute la famille
        RefreshToken.objects.filter(famille=rt.famille).update(revoked=True)
        raise ValueError("Token révoqué — sécurité compromise, reconnexion requise")

    if rt.expire_at < timezone.now():
        raise ValueError("Token expiré")

    # Rotation
    rt.revoquer()

    # Émettre un nouveau refresh dans la même famille
    nouveau_refresh_str = creer_token({"user_id": rt.user.pk}, expire_dans=7*24*3600)
    nouveau_rt = RefreshToken.objects.create(
        user=rt.user,
        token=nouveau_refresh_str,
        expire_at=...,
        famille=rt.famille,  # même famille !
    )

    nouveau_access = creer_token({"user_id": rt.user.pk}, expire_dans=900)
    return {"access_token": nouveau_access, "refresh_token": nouveau_refresh_str}
```

---

## Nettoyage des tokens expirés

```python
# management/commands/cleanup_tokens.py
from django.core.management.base import BaseCommand
from django.utils import timezone

class Command(BaseCommand):
    def handle(self, *args, **options):
        count, _ = RefreshToken.objects.filter(
            expire_at__lt=timezone.now()
        ).delete()
        self.stdout.write(f"{count} tokens supprimés")
```

```bash
# Crontab
0 3 * * * python manage.py cleanup_tokens
```

---

## Access tokens sans état vs Refresh tokens avec état

| | Access Token | Refresh Token |
|---|---|---|
| Stockage serveur | Aucun (JWT) | DB obligatoire |
| Durée | Courte (1-15min) | Longue (7-30j) |
| Révocation | Pas possible avant expiration | Immédiate (DB) |
| Coût | 0 requête DB | 1-2 requêtes DB |

---

## Sécurité des cookies vs localStorage

```javascript
// ❌ localStorage — accessible via XSS
localStorage.setItem("access_token", token)

// ✅ Cookie HttpOnly — inaccessible en JavaScript
// Set-Cookie: access_token=xxx; HttpOnly; Secure; SameSite=Strict
```

En Django :
```python
def login(request):
    ...
    response = JsonResponse({"message": "Connecté"})
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,       # HTTPS seulement
        samesite="Strict", # pas envoyé en cross-site
        max_age=900,       # 15 minutes
    )
    return response
```
