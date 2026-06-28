"""
Exercice Jour 46 — Rate Limiting et Security Headers

Lance : python3 exercice.py
"""

import time
from collections import deque


# ─── EXERCICE 1 : Token Bucket ────────────────────────────────────────────────

class TokenBucket:
    """
    Rate limiter basé sur token bucket.

    Paramètres :
    - capacite : nombre max de tokens
    - tokens_par_seconde : vitesse de recharge

    Usage :
        bucket = TokenBucket(capacite=5, tokens_par_seconde=1)
        bucket.consommer()   # True si autorisé, False si rate limited
    """

    def __init__(self, capacite: int, tokens_par_seconde: float):
        # TODO
        pass

    def consommer(self, tokens: int = 1) -> bool:
        """
        Tente de consommer `tokens` tokens.
        Retourne True si autorisé, False si rate limited.

        Logique :
        1. Calculer le temps écoulé depuis le dernier remplissage
        2. Ajouter les tokens gagnés (min avec la capacité max)
        3. Si tokens disponibles >= tokens demandés → consommer et retourner True
        4. Sinon retourner False
        """
        # TODO
        pass

    @property
    def tokens_disponibles(self) -> float:
        """Nombre de tokens actuellement disponibles (après recharge)."""
        # TODO
        pass


# ─── EXERCICE 2 : Sliding Window ─────────────────────────────────────────────

class SlidingWindowLimiter:
    """
    Rate limiter avec fenêtre glissante.

    Usage :
        limiter = SlidingWindowLimiter(max_requetes=3, fenetre_secondes=1)
        limiter.est_autorise("user_alice")  # True/False
    """

    def __init__(self, max_requetes: int, fenetre_secondes: float):
        # TODO : self.max_requetes, self.fenetre, self.historique = {}
        pass

    def est_autorise(self, identifiant: str) -> bool:
        """
        Vérifie si l'identifiant est autorisé à faire une requête.

        Logique :
        1. Récupérer (ou créer) la deque de timestamps pour cet identifiant
        2. Retirer tous les timestamps hors de la fenêtre (< now - fenetre)
        3. Si len(deque) < max_requetes : ajouter now et retourner True
        4. Sinon retourner False
        """
        # TODO
        pass

    def reinitialiser(self, identifiant: str):
        """Réinitialise le compteur pour un identifiant."""
        # TODO
        pass


# ─── EXERCICE 3 : Middleware de sécurité headers ─────────────────────────────

def ajouter_security_headers(response_headers: dict) -> dict:
    """
    Ajoute les headers de sécurité recommandés à un dict de headers.

    Headers à ajouter :
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy: default-src 'self'

    Retourne le dict modifié.
    """
    # TODO : ajouter chaque header au dict
    pass


class SecurityHeadersMiddleware:
    """
    Middleware WSGI qui ajoute les headers de sécurité.
    Compatible avec n'importe quelle app WSGI/Django.
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            headers_dict = dict(headers)
            headers_dict = ajouter_security_headers(headers_dict)
            return start_response(status, list(headers_dict.items()), exc_info)

        return self.app(environ, custom_start_response)


# ─── EXERCICE 4 : Détecter les tentatives brute-force ────────────────────────

class BruteForceDetecteur:
    """
    Détecte et bloque les tentatives de brute-force sur le login.

    Bloque une IP après N échecs dans une fenêtre de temps.
    Déblocage automatique après cooldown.
    """

    def __init__(self, max_echecs: int = 5, fenetre_secondes: int = 60, cooldown_secondes: int = 300):
        # TODO
        pass

    def enregistrer_echec(self, ip: str) -> bool:
        """
        Enregistre un échec pour cette IP.
        Retourne True si l'IP doit maintenant être bloquée.
        """
        # TODO
        pass

    def est_bloquee(self, ip: str) -> bool:
        """
        Retourne True si l'IP est bloquée.
        Libère automatiquement si le cooldown est passé.
        """
        # TODO
        pass

    def enregistrer_succes(self, ip: str):
        """Réinitialise le compteur d'échecs après un login réussi."""
        # TODO
        pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    erreurs = 0
    def ok(n, extra=""): print(f"  OK    {n}{' (' + extra + ')' if extra else ''}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    print("=== Token Bucket ===")
    try:
        bucket = TokenBucket(capacite=3, tokens_par_seconde=10)
        assert bucket.consommer() == True
        assert bucket.consommer() == True
        assert bucket.consommer() == True
        assert bucket.consommer() == False   # seau vide
        ok("Token Bucket basique (3 tokens)")
    except Exception as e: echec("TokenBucket", e)

    try:
        bucket = TokenBucket(capacite=1, tokens_par_seconde=10)  # 10/s = recharge en 0.1s
        bucket.consommer()   # vide le seau
        time.sleep(0.15)     # attend 0.15s → ~1.5 tokens rechargés
        assert bucket.consommer() == True    # doit pouvoir refaire une requête
        ok("Token Bucket recharge")
    except Exception as e: echec("TokenBucket recharge", e)

    print("\n=== Sliding Window ===")
    try:
        limiter = SlidingWindowLimiter(max_requetes=3, fenetre_secondes=1)
        assert limiter.est_autorise("alice") == True
        assert limiter.est_autorise("alice") == True
        assert limiter.est_autorise("alice") == True
        assert limiter.est_autorise("alice") == False   # limite atteinte
        assert limiter.est_autorise("bob") == True      # bob non affecté
        ok("Sliding Window basique")
    except Exception as e: echec("SlidingWindow", e)

    try:
        limiter = SlidingWindowLimiter(max_requetes=2, fenetre_secondes=0.2)
        limiter.est_autorise("x")
        limiter.est_autorise("x")
        assert limiter.est_autorise("x") == False
        time.sleep(0.25)  # fenêtre expirée
        assert limiter.est_autorise("x") == True   # de nouveau autorisé
        ok("Sliding Window fenêtre glissante")
    except Exception as e: echec("SlidingWindow fenêtre", e)

    print("\n=== Security Headers ===")
    try:
        headers = ajouter_security_headers({"Content-Type": "application/json"})
        assert "Strict-Transport-Security" in headers
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in headers
        assert "Content-Security-Policy" in headers
        ok("Security headers ajoutés")
    except Exception as e: echec("security headers", e)

    print("\n=== Brute Force Détecteur ===")
    try:
        detecteur = BruteForceDetecteur(max_echecs=3, fenetre_secondes=60, cooldown_secondes=1)
        ip = "192.168.1.1"
        assert not detecteur.est_bloquee(ip)
        detecteur.enregistrer_echec(ip)
        detecteur.enregistrer_echec(ip)
        assert not detecteur.est_bloquee(ip)
        bloque = detecteur.enregistrer_echec(ip)  # 3ème échec
        assert bloque, "Doit être bloqué après 3 échecs"
        assert detecteur.est_bloquee(ip)
        ok("Blocage après 3 échecs")

        time.sleep(1.1)  # cooldown de 1s
        assert not detecteur.est_bloquee(ip), "Doit être débloqué après cooldown"
        ok("Déblocage automatique")
    except Exception as e: echec("BruteForce", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
