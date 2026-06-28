"""
Exercice Jour 50 — Rotation des tokens et Token Family

Lance : python3 exercice.py
"""

import django, uuid, hmac, hashlib, base64, json, time
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=True,
        TIME_ZONE="UTC",
        SECRET_KEY="token-rotation-secret",
    )
    django.setup()

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import datetime


# ─── JWT minimal ─────────────────────────────────────────────────────────────

SECRET = settings.SECRET_KEY.encode()

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)

def creer_jwt(payload: dict, expire_dans: int = 900) -> str:
    payload = {**payload, "iat": int(time.time()), "exp": int(time.time()) + expire_dans}
    header = b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_b64 = b64url_encode(json.dumps(payload).encode())
    sig = b64url_encode(hmac.new(SECRET, f"{header}.{payload_b64}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload_b64}.{sig}"

def verifier_jwt(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Format invalide")
    header, payload_b64, sig = parts
    sig_attendu = b64url_encode(hmac.new(SECRET, f"{header}.{payload_b64}".encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, sig_attendu):
        raise ValueError("Signature invalide")
    payload = json.loads(b64url_decode(payload_b64))
    if payload["exp"] < time.time():
        raise ValueError("Token expiré")
    return payload


# ─── Modèle RefreshToken ─────────────────────────────────────────────────────

class RefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    token = models.TextField(unique=True)
    expire_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    famille = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valide(self) -> bool:
        return not self.revoked and self.expire_at > timezone.now()

    class Meta: app_label = "__main__"


# ─── EXERCICE 1 : Émettre une paire de tokens ────────────────────────────────

def emettre_tokens(user: User) -> dict:
    """
    Émet access + refresh tokens.
    Crée un enregistrement RefreshToken en DB avec une nouvelle famille.

    TODO :
    1. Créer access_token (15min)
    2. Créer refresh_token (7 jours)
    3. Sauvegarder RefreshToken en DB (famille = uuid.uuid4())
    4. Retourner {"access_token": ..., "refresh_token": ...}
    """
    # TODO
    pass


# ─── EXERCICE 2 : Rotation avec Token Family ──────────────────────────────────

def renouveler_access(refresh_token_str: str) -> dict:
    """
    Échange un refresh token contre une nouvelle paire.
    Détecte le vol par Token Family.

    TODO :
    1. Trouver le RefreshToken en DB
    2. S'il est révoqué → révoquer toute la famille → lever ValueError("vol détecté")
    3. S'il est expiré → lever ValueError("expiré")
    4. Révoquer l'ancien refresh
    5. Créer un nouveau refresh dans la même famille
    6. Créer un nouvel access token
    7. Retourner {"access_token": ..., "refresh_token": ...}
    """
    # TODO
    pass


def revoquer_tous_tokens(user: User):
    """Révoque tous les refresh tokens de l'utilisateur (logout global)."""
    # TODO
    pass


# ─── EXERCICE 3 : Nettoyage des tokens expirés ───────────────────────────────

def nettoyer_tokens_expires() -> int:
    """
    Supprime les refresh tokens expirés.
    Retourne le nombre de tokens supprimés.
    """
    # TODO
    pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    from django.db import connection
    with connection.schema_editor() as se:
        for m in [User, RefreshToken]:
            try: se.create_model(m)
            except: pass

    alice = User.objects.create_user("alice", password="p")

    erreurs = 0
    def ok(n, extra=""): print(f"  OK    {n}{' (' + extra + ')' if extra else ''}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    print("=== Émission ===")
    try:
        tokens = emettre_tokens(alice)
        assert tokens is not None and "access_token" in tokens
        payload = verifier_jwt(tokens["access_token"])
        assert payload["user_id"] == alice.pk
        rt = RefreshToken.objects.get(token=tokens["refresh_token"])
        assert rt.is_valide()
        ok("Émission access + refresh")
    except Exception as e: echec("émission", e)

    print("\n=== Rotation ===")
    try:
        tokens = emettre_tokens(alice)
        if not tokens: raise Exception("emettre_tokens non implémenté")

        famille_orig = RefreshToken.objects.get(token=tokens["refresh_token"]).famille

        # Première rotation
        tokens2 = renouveler_access(tokens["refresh_token"])
        assert tokens2 is not None
        assert "access_token" in tokens2
        assert "refresh_token" in tokens2
        ok("Première rotation réussie")

        # Ancien refresh doit être révoqué
        ancien = RefreshToken.objects.get(token=tokens["refresh_token"])
        assert ancien.revoked, "L'ancien refresh doit être révoqué"
        ok("Ancien token révoqué")

        # Nouvelle famille doit être la même
        nouveau = RefreshToken.objects.get(token=tokens2["refresh_token"])
        assert nouveau.famille == famille_orig, "Même famille"
        ok("Même famille préservée")

        # Deuxième rotation
        tokens3 = renouveler_access(tokens2["refresh_token"])
        assert tokens3 is not None
        ok("Deuxième rotation réussie")
    except Exception as e: echec("rotation", e)

    print("\n=== Détection de vol ===")
    try:
        tokens = emettre_tokens(alice)
        if not tokens: raise Exception("emettre_tokens non implémenté")

        tokens2 = renouveler_access(tokens["refresh_token"])  # rotation normale

        # Attaquant essaie d'utiliser l'ancien refresh (déjà révoqué)
        try:
            renouveler_access(tokens["refresh_token"])
            echec("détection vol", "Aurait dû lever ValueError")
        except ValueError as e:
            # Toute la famille doit être révoquée
            familles_revoquees = RefreshToken.objects.filter(
                token=tokens2["refresh_token"], revoked=True
            )
            ok(f"Vol détecté : {e}")
    except Exception as e: echec("détection vol", e)

    print("\n=== Nettoyage ===")
    try:
        # Créer un token déjà expiré manuellement
        RefreshToken.objects.create(
            user=alice,
            token="token-expire",
            expire_at=timezone.now() - datetime.timedelta(hours=1),
            famille=uuid.uuid4(),
        )
        nb = nettoyer_tokens_expires()
        assert nb is not None and nb >= 1
        assert not RefreshToken.objects.filter(token="token-expire").exists()
        ok(f"Nettoyage : {nb} token(s) supprimé(s)")
    except Exception as e: echec("nettoyage", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
