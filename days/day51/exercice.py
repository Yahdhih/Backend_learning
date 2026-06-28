"""
Exercice Jour 51 — Hardening : audit et correction d'une app vulnérable

Lance : python3 exercice.py
"""

import re
import hmac
import hashlib
import time


# ─── EXERCICE 1 : Comparaison timing-safe ────────────────────────────────────

def verifier_cle_api_vulnerable(cle_recue: str, cle_attendue: str) -> bool:
    """VULNÉRABLE au timing attack."""
    return cle_recue == cle_attendue

def verifier_cle_api_safe(cle_recue: str, cle_attendue: str) -> bool:
    """
    Version sécurisée avec comparaison en temps constant.
    TODO : utilise hmac.compare_digest()
    """
    # TODO
    pass


def demo_timing_attack():
    """
    Démontre que la comparaison naïve prend plus de temps
    sur un préfixe correct (fuite temporelle).
    """
    cle_reelle = "sk-prod-abc123def456ghi789"

    # Mesure avec préfixe correct (prend plus de temps car compare plus de chars)
    tentatives_correctes = [
        "sk-prod-abc123def456ghi000",  # diffère à la fin
        "sk-prod-abc123def456ghi7xx",  # diffère à la fin
    ]
    tentatives_incorrectes = [
        "xxxxxxxxxxxxxxxxxxxx",         # diffère au début
        "zzzzzzzzzzzzzzzzzzz",
    ]

    def mesurer(fn, args, n=1000):
        debut = time.perf_counter()
        for _ in range(n):
            fn(*args)
        return (time.perf_counter() - debut) / n

    print("  Timing attack démonstration :")
    t_correct = mesurer(verifier_cle_api_vulnerable, (tentatives_correctes[0], cle_reelle))
    t_incorrect = mesurer(verifier_cle_api_vulnerable, (tentatives_incorrectes[0], cle_reelle))
    print(f"    Préfixe correct : {t_correct*1e6:.2f}µs")
    print(f"    Préfixe incorrect : {t_incorrect*1e6:.2f}µs")
    print(f"    Différence : {abs(t_correct - t_incorrect)*1e6:.2f}µs (exploitable si assez grande)")


# ─── EXERCICE 2 : Validation des entrées ─────────────────────────────────────

def valider_email(email: str) -> bool:
    """
    Valide un email.
    TODO : utilise une regex raisonnable (pas parfaite, mais suffisante)
    """
    # TODO : pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    pass


def valider_username(username: str) -> tuple[bool, str]:
    """
    Valide un username.
    Règles :
    - Entre 3 et 30 caractères
    - Seulement lettres, chiffres, tirets, underscores
    - Pas de tiret/underscore au début ou à la fin

    Retourne (True, "") si valide, (False, "message d'erreur") sinon.
    """
    # TODO
    pass


def sanitiser_nom_fichier(nom: str) -> str:
    """
    Sanitise un nom de fichier pour éviter le path traversal.

    TODO :
    1. Retirer les .. et /
    2. Garder seulement les caractères alphanumériques, tirets, underscores, points
    3. Limiter à 100 caractères
    4. Retourner le nom sanitisé
    """
    # TODO
    pass


# ─── EXERCICE 3 : Middleware de sécurité ─────────────────────────────────────

class SecurityAuditMiddleware:
    """
    Middleware qui loggue les tentatives suspectes.
    """

    PATTERNS_SUSPECTS = [
        r"\.\./",           # path traversal
        r"<script",         # XSS
        r"UNION\s+SELECT",  # SQL injection
        r"etc/passwd",      # lecture système
        r"cmd\.exe",        # Windows exploitation
    ]

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS_SUSPECTS]
        self.alertes = []

    def analyser_requete(self, url: str, body: str = "") -> list[str]:
        """
        Analyse l'URL et le body pour des patterns suspects.
        Retourne la liste des patterns détectés.

        TODO :
        1. Concaténer url + body
        2. Pour chaque pattern, vérifier s'il correspond
        3. Retourner la liste des patterns détectés
        """
        # TODO
        pass


# ─── EXERCICE 4 : Rotations de SECRET_KEY ────────────────────────────────────

class SignatureDuale:
    """
    Permet de faire tourner la SECRET_KEY sans invalider toutes les sessions.
    Signe avec la nouvelle clé, accepte ancienne et nouvelle.
    """

    def __init__(self, cle_actuelle: str, cle_ancienne: str = None):
        self.cle_actuelle = cle_actuelle.encode()
        self.cle_ancienne = cle_ancienne.encode() if cle_ancienne else None

    def signer(self, data: str) -> str:
        """Signe avec la clé actuelle."""
        sig = hmac.new(self.cle_actuelle, data.encode(), hashlib.sha256).hexdigest()
        return f"{data}.{sig}"

    def verifier(self, data_signee: str) -> tuple[bool, str]:
        """
        Vérifie avec la clé actuelle, puis avec l'ancienne si nécessaire.
        Retourne (True, data) si valide, (False, "") sinon.

        TODO :
        1. Découper data_signee en data et signature
        2. Vérifier avec cle_actuelle
        3. Si invalide et cle_ancienne non None, vérifier avec cle_ancienne
        4. Retourner (True, data) ou (False, "")
        """
        # TODO
        pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    erreurs = 0
    def ok(n, extra=""): print(f"  OK    {n}{' (' + extra + ')' if extra else ''}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    print("=== Timing Attack ===")
    demo_timing_attack()
    try:
        cle = "sk-secret-key-123"
        assert verifier_cle_api_safe(cle, cle) == True
        assert verifier_cle_api_safe("mauvaise", cle) == False
        ok("Comparaison timing-safe fonctionne")
    except Exception as e: echec("timing-safe", e)

    print("\n=== Validation des entrées ===")
    try:
        assert valider_email("alice@example.com") == True
        assert valider_email("pas-un-email") == False
        assert valider_email("@nodomain") == False
        ok("Validation email")
    except Exception as e: echec("email", e)

    try:
        ok_v, _ = valider_username("alice_dev")
        assert ok_v == True
        nok, msg = valider_username("ab")  # trop court
        assert nok == False
        nok2, _ = valider_username("alice<script>")  # caractères invalides
        assert nok2 == False
        ok("Validation username")
    except Exception as e: echec("username", e)

    try:
        assert sanitiser_nom_fichier("../../../etc/passwd") == "etc/passwd" or \
               sanitiser_nom_fichier("../../../etc/passwd") == "etcpasswd" or \
               "../" not in sanitiser_nom_fichier("../../../etc/passwd")
        assert sanitiser_nom_fichier("mon fichier.txt") is not None
        ok("Sanitisation nom de fichier")
    except Exception as e: echec("nom fichier", e)

    print("\n=== Détection d'attaques ===")
    try:
        middleware = SecurityAuditMiddleware()
        alertes = middleware.analyser_requete("/search?q=<script>alert(1)</script>")
        assert alertes is not None and len(alertes) > 0
        ok("XSS détecté dans URL")

        alertes2 = middleware.analyser_requete("/articles", "UNION SELECT * FROM users")
        assert len(alertes2) > 0
        ok("SQLi détectée dans body")

        alertes3 = middleware.analyser_requete("/articles/1")
        assert len(alertes3) == 0
        ok("Requête normale : pas d'alerte")
    except Exception as e: echec("détection attaques", e)

    print("\n=== Rotation de clé ===")
    try:
        sig = SignatureDuale("nouvelle-cle", "ancienne-cle")
        data_signee = sig.signer("user_id=42")
        valide, data = sig.verifier(data_signee)
        assert valide and data == "user_id=42"
        ok("Signature avec nouvelle clé vérifiée")

        # Simuler des données signées avec l'ancienne clé
        sig_ancienne = SignatureDuale("ancienne-cle")
        data_ancienne = sig_ancienne.signer("user_id=99")
        valide2, data2 = sig.verifier(data_ancienne)
        assert valide2 and data2 == "user_id=99"
        ok("Signature ancienne clé acceptée pendant transition")

        # Données avec une clé inconnue
        sig_inconnue = SignatureDuale("cle-inconnue")
        data_inconnue = sig_inconnue.signer("user_id=evil")
        valide3, _ = sig.verifier(data_inconnue)
        assert not valide3
        ok("Signature clé inconnue refusée")
    except Exception as e: echec("rotation clé", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
