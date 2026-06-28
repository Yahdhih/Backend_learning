"""
Exercice Jour 41 — JWT : implémenter from scratch

Lance : python3 exercice.py
"""

import hmac, hashlib, base64, json, time


SECRET = b"mon-secret-backend-learning-2026-tres-long"


# ─── PARTIE 1 : Fonctions de base ────────────────────────────────────────────

def base64url_encode(data: bytes) -> str:
    """Encode en base64url sans padding."""
    # TODO : base64.urlsafe_b64encode + strip "=" + decode en str
    pass


def base64url_decode(s: str) -> bytes:
    """Décode depuis base64url (rajoute le padding si nécessaire)."""
    # TODO : rajouter "=" jusqu'à len % 4 == 0, puis base64.urlsafe_b64decode
    pass


# ─── PARTIE 2 : Créer un JWT ─────────────────────────────────────────────────

def creer_token(user_id: int, expiration_minutes: int = 15, **extra_claims) -> str:
    """
    Crée un JWT signé avec HMAC-SHA256.

    Structure : base64url(header).base64url(payload).base64url(signature)

    Header : {"alg": "HS256", "typ": "JWT"}
    Payload : {"sub": str(user_id), "iat": timestamp_now, "exp": timestamp_expiration, ...extra_claims}
    Signature : HMAC-SHA256(header_encoded + "." + payload_encoded, SECRET)

    >>> token = creer_token(42, expiration_minutes=15)
    >>> len(token.split(".")) == 3
    True
    """
    # TODO
    pass


# ─── PARTIE 3 : Vérifier un JWT ──────────────────────────────────────────────

def verifier_token(token: str) -> dict:
    """
    Vérifie et décode un JWT.

    Lève ValueError si :
    - Le format est incorrect (pas 3 parties)
    - La signature ne correspond pas
    - Le token est expiré (exp < now)

    Retourne le payload (dict) si valide.

    >>> payload = verifier_token(creer_token(42))
    >>> payload["sub"] == "42"
    True
    """
    # TODO :
    # 1. Split sur "."
    # 2. Recalculer la signature attendue
    # 3. Comparer avec hmac.compare_digest (timing-safe !)
    # 4. Vérifier exp
    # 5. Retourner le payload décodé
    pass


# ─── PARTIE 4 : Access + Refresh tokens ──────────────────────────────────────

def creer_access_token(user_id: int) -> str:
    """Token court durée (15 min) avec type="access"."""
    # TODO : creer_token avec expiration=15 et type="access"
    pass


def creer_refresh_token(user_id: int) -> str:
    """Token longue durée (7 jours) avec type="refresh"."""
    # TODO : creer_token avec expiration=7*24*60 et type="refresh"
    pass


def rafraichir_tokens(refresh_token: str) -> dict:
    """
    Échange un refresh token valide contre un nouveau pair access+refresh.
    Lève ValueError si le token est invalide ou si ce n'est pas un refresh token.

    Retourne {"access_token": ..., "refresh_token": ...}
    """
    # TODO :
    # 1. verifier_token(refresh_token)
    # 2. Vérifier que payload["type"] == "refresh"
    # 3. Créer nouveaux access + refresh tokens
    pass


# ─── PARTIE 5 : Démontrer la vulnérabilité alg:none ─────────────────────────

def creer_token_sans_signature(user_id: int) -> str:
    """
    Crée un JWT SANS signature (alg: none).
    Démontre pourquoi c'est dangereux.
    """
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": str(user_id), "exp": int(time.time()) + 3600}
    h = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h}.{p}."  # pas de signature


def verifier_token_vulnerable(token: str) -> dict:
    """
    Vérifie un token SANS vérifier l'algorithme.
    VULNÉRABLE à l'attaque alg:none.
    Ne jamais faire ça en production !
    """
    parts = token.split(".")
    header = json.loads(base64url_decode(parts[0]))
    payload = json.loads(base64url_decode(parts[1]))

    if header.get("alg") == "none":
        # Bug : on fait confiance à un token non signé !
        return payload

    # Vérification normale...
    return verifier_token(token)


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    erreurs = 0

    def ok(n): print(f"  OK    {n}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    # Test encode/decode
    try:
        data = b"hello world"
        encoded = base64url_encode(data)
        assert "=" not in encoded
        assert base64url_decode(encoded) == data
        ok("base64url encode/decode")
    except Exception as e: echec("base64url", e)

    # Test créer/vérifier token
    try:
        token = creer_token(42)
        assert len(token.split(".")) == 3
        payload = verifier_token(token)
        assert payload["sub"] == "42"
        ok("creer_token + verifier_token")
    except Exception as e: echec("token basique", e)

    # Test token expiré
    try:
        token = creer_token(42, expiration_minutes=0)
        time.sleep(1)
        try:
            verifier_token(token)
            echec("token expiré", "Devrait lever ValueError")
        except ValueError as e:
            assert "expiré" in str(e).lower() or "exp" in str(e).lower()
            ok("Token expiré détecté")
    except Exception as e: echec("expiration", e)

    # Test signature modifiée
    try:
        token = creer_token(42)
        parties = token.split(".")
        # Modifier le payload
        payload_modifie = {"sub": "1", "exp": int(time.time()) + 3600}
        parties[1] = base64url_encode(json.dumps(payload_modifie).encode())
        token_modifie = ".".join(parties)
        try:
            verifier_token(token_modifie)
            echec("signature invalide", "Devrait lever ValueError")
        except ValueError:
            ok("Signature invalide détectée")
    except Exception as e: echec("signature", e)

    # Test access + refresh
    try:
        access = creer_access_token(99)
        refresh = creer_refresh_token(99)
        p_access = verifier_token(access)
        p_refresh = verifier_token(refresh)
        assert p_access.get("type") == "access"
        assert p_refresh.get("type") == "refresh"
        ok("Access + refresh tokens")
    except Exception as e: echec("access/refresh", e)

    # Test rafraîchissement
    try:
        refresh = creer_refresh_token(99)
        nouveaux = rafraichir_tokens(refresh)
        assert "access_token" in nouveaux
        assert "refresh_token" in nouveaux
        ok("Rafraîchissement de tokens")
    except Exception as e: echec("rafraîchir", e)

    # Démonstration vulnérabilité
    print("\n  --- Démonstration vulnérabilité alg:none ---")
    try:
        token_sans_sig = creer_token_sans_signature(999)
        payload = verifier_token_vulnerable(token_sans_sig)
        print(f"  DANGER : token accepté sans signature pour user_id={payload['sub']}")
        print(f"  En production, un attaquant pourrait se faire passer pour n'importe quel user !")
        ok("Vulnérabilité démontrée (ne pas reproduire en prod)")
    except Exception as e: echec("démo vulnérabilité", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
