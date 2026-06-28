# Day 40 — Exercice : Hachage de mots de passe
# Comparer les méthodes, mesurer les performances, implémenter un vérificateur de force

"""
Cet exercice compare :
1. SHA-256 simple (insuffisant)
2. SHA-256 + sel (meilleur, mais encore trop rapide)
3. PBKDF2 avec 600 000 itérations (standard Django)
4. bcrypt si disponible
5. Mesure du temps de chaque méthode
6. Vérificateur de force de mot de passe

Exécution : python exercice.py
"""

import hashlib
import hmac
import os
import re
import secrets
import time
import unittest
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# 1. SHA-256 simple — INSUFFISANT (démonstration)
# ---------------------------------------------------------------------------

def hash_sha256_simple(password: str) -> str:
    """
    SHA-256 sans sel. NE PAS utiliser en production.
    Problèmes :
    - Même mot de passe → même hash (rainbow tables)
    - Extrêmement rapide → brute force trivial
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verifier_sha256_simple(password: str, stored_hash: str) -> bool:
    """Vérification — utilise compare_digest pour éviter les timing attacks."""
    calculé = hash_sha256_simple(password)
    return hmac.compare_digest(calculé, stored_hash)


# ---------------------------------------------------------------------------
# 2. SHA-256 + sel — Meilleur, mais toujours trop rapide
# ---------------------------------------------------------------------------

def hash_sha256_avec_sel(password: str) -> tuple[str, str]:
    """
    SHA-256 avec sel aléatoire.
    Corrige le problème des rainbow tables mais reste vulnérable au brute force
    car SHA-256 est conçu pour être rapide.

    Retourne : (hash_hex, sel_hex)
    """
    sel = secrets.token_bytes(32)  # 256 bits de sel
    hash_bytes = hashlib.sha256(sel + password.encode("utf-8")).digest()
    return hash_bytes.hex(), sel.hex()


def verifier_sha256_avec_sel(password: str, stored_hash: str, stored_sel: str) -> bool:
    sel = bytes.fromhex(stored_sel)
    hash_bytes = hashlib.sha256(sel + password.encode("utf-8")).digest()
    return hmac.compare_digest(hash_bytes.hex(), stored_hash)


# ---------------------------------------------------------------------------
# 3. PBKDF2 avec 600 000 itérations — Standard Django
# ---------------------------------------------------------------------------

PBKDF2_ITERATIONS = 600_000
PBKDF2_HASH = "sha256"
PBKDF2_KEY_LENGTH = 32  # 256 bits


def hash_pbkdf2(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    """
    PBKDF2-SHA256 avec sel aléatoire.
    Format de stockage similaire à Django :
    'pbkdf2_sha256$iterations$sel_b64$hash_b64'
    """
    import base64

    sel = secrets.token_bytes(16)  # 128 bits
    hash_bytes = hashlib.pbkdf2_hmac(
        PBKDF2_HASH,
        password.encode("utf-8"),
        sel,
        iterations,
        dklen=PBKDF2_KEY_LENGTH,
    )
    sel_b64 = base64.b64encode(sel).decode("ascii")
    hash_b64 = base64.b64encode(hash_bytes).decode("ascii")
    return f"pbkdf2_sha256${iterations}${sel_b64}${hash_b64}"


def verifier_pbkdf2(password: str, stored: str) -> bool:
    """Vérifie un mot de passe contre un hash PBKDF2 stocké."""
    import base64

    try:
        algo, iterations_str, sel_b64, hash_b64 = stored.split("$")
        iterations = int(iterations_str)
        sel = base64.b64decode(sel_b64)
        stored_hash = base64.b64decode(hash_b64)
    except (ValueError, Exception):
        return False

    calculé = hashlib.pbkdf2_hmac(
        PBKDF2_HASH,
        password.encode("utf-8"),
        sel,
        iterations,
        dklen=PBKDF2_KEY_LENGTH,
    )
    return hmac.compare_digest(calculé, stored_hash)


# ---------------------------------------------------------------------------
# 4. Mesure des performances
# ---------------------------------------------------------------------------

@dataclass
class ResultatMesure:
    methode: str
    temps_ms: float
    hash_exemple: str
    attaques_par_seconde_estimees: float


def mesurer_performance(methode_nom: str, fn_hash, fn_verif, password: str) -> ResultatMesure:
    """Mesure le temps de hachage et estime la résistance au brute force."""
    # Mesure sur plusieurs répétitions pour la précision
    n = 3
    debut = time.perf_counter()
    hash_val = None
    for _ in range(n):
        hash_val = fn_hash(password)
    fin = time.perf_counter()
    temps_moyen_s = (fin - debut) / n
    temps_ms = temps_moyen_s * 1000

    # Vérification (ne devrait pas ajouter de temps significatif)
    if fn_verif:
        if methode_nom == "SHA-256 simple":
            fn_verif(password, hash_val)
        elif methode_nom == "SHA-256 + sel":
            hash_h, sel_h = hash_val
            fn_verif(password, hash_h, sel_h)
        else:
            fn_verif(password, hash_val)

    # Estimation : combien de tentatives/seconde un attaquant peut faire
    attaques_par_s = 1.0 / temps_moyen_s if temps_moyen_s > 0 else float("inf")

    # Formater le hash pour l'affichage
    if isinstance(hash_val, tuple):
        hash_exemple = hash_val[0][:32] + "..."
    else:
        hash_exemple = str(hash_val)[:40] + "..."

    return ResultatMesure(
        methode=methode_nom,
        temps_ms=temps_ms,
        hash_exemple=hash_exemple,
        attaques_par_seconde_estimees=attaques_par_s,
    )


def benchmark_complet():
    """Lance tous les benchmarks et affiche un rapport comparatif."""
    print("\n" + "=" * 70)
    print("BENCHMARK — Comparaison des méthodes de hachage")
    print("=" * 70)

    password = "MonMotDePasse123!"

    def sha256_simple_wrap(p):
        return hash_sha256_simple(p)

    def sha256_sel_wrap(p):
        return hash_sha256_avec_sel(p)

    def pbkdf2_wrap(p):
        return hash_pbkdf2(p)

    mesures = [
        mesurer_performance("SHA-256 simple", sha256_simple_wrap, verifier_sha256_simple, password),
        mesurer_performance("SHA-256 + sel", sha256_sel_wrap, None, password),
        mesurer_performance("PBKDF2 (600k iter)", pbkdf2_wrap, verifier_pbkdf2, password),
    ]

    print(f"\n{'Méthode':<22} {'Temps (ms)':<15} {'Attaques/sec (estimé)':<25} {'Sécurité'}")
    print("-" * 80)

    for m in mesures:
        if m.attaques_par_seconde_estimees > 1_000_000:
            securite = "DANGEREUX"
        elif m.attaques_par_seconde_estimees > 1000:
            securite = "INSUFFISANT"
        elif m.attaques_par_seconde_estimees > 10:
            securite = "ACCEPTABLE"
        else:
            securite = "BON"

        print(
            f"{m.methode:<22} "
            f"{m.temps_ms:<15.3f} "
            f"{m.attaques_par_seconde_estimees:<25,.0f} "
            f"{securite}"
        )

    print()
    print("Note : En pratique, un GPU peut faire ~10x plus d'attaques")
    print("       que ce benchmark single-thread ne le montre.")
    print()

    # Démonstration du problème du hash identique
    print("--- Problème SHA-256 simple : hashes identiques ---")
    h1 = hash_sha256_simple("password123")
    h2 = hash_sha256_simple("password123")
    print(f"SHA-256('password123') #1 = {h1}")
    print(f"SHA-256('password123') #2 = {h2}")
    print(f"Identiques ? {h1 == h2}  ← Problème : rainbow tables fonctionnent !")

    print()
    print("--- SHA-256 + sel : hashes différents ---")
    h1, s1 = hash_sha256_avec_sel("password123")
    h2, s2 = hash_sha256_avec_sel("password123")
    print(f"Hash #1 = {h1[:32]}...")
    print(f"Hash #2 = {h2[:32]}...")
    print(f"Identiques ? {h1 == h2}  ← Les sels différents créent des hashes différents !")

    return mesures


# ---------------------------------------------------------------------------
# 5. Vérificateur de force de mot de passe
# ---------------------------------------------------------------------------

class ForceMotDePasse(Enum):
    TRES_FAIBLE = 0
    FAIBLE = 1
    MOYEN = 2
    FORT = 3
    TRES_FORT = 4


@dataclass
class ResultatForce:
    force: ForceMotDePasse
    score: int
    max_score: int
    criteres_passes: list[str]
    criteres_manquants: list[str]
    suggestions: list[str]


# Liste de mots de passe courants à rejeter
MOTS_DE_PASSE_COURANTS = {
    "password", "password123", "123456", "12345678", "qwerty",
    "abc123", "monkey", "1234567890", "letmein", "master",
    "login", "hello", "welcome", "dragon", "passw0rd",
    "motdepasse", "azerty", "soleil", "bonjour",
}


def verifier_force_mot_de_passe(password: str) -> ResultatForce:
    """
    Évalue la force d'un mot de passe selon plusieurs critères.
    Retourne un score et des recommandations.
    """
    criteres_passes = []
    criteres_manquants = []
    suggestions = []
    score = 0
    max_score = 10

    # 1. Longueur minimale (2 points)
    if len(password) >= 12:
        score += 2
        criteres_passes.append("Longueur ≥ 12 caractères")
    elif len(password) >= 8:
        score += 1
        criteres_passes.append("Longueur ≥ 8 caractères")
        criteres_manquants.append("Longueur < 12 caractères")
        suggestions.append("Utilisez au moins 12 caractères")
    else:
        criteres_manquants.append("Trop court (< 8 caractères)")
        suggestions.append("Le mot de passe doit faire au moins 8 caractères")

    # 2. Lettres minuscules (1 point)
    if re.search(r"[a-z]", password):
        score += 1
        criteres_passes.append("Contient des minuscules")
    else:
        criteres_manquants.append("Pas de minuscules")
        suggestions.append("Ajoutez des lettres minuscules")

    # 3. Lettres majuscules (1 point)
    if re.search(r"[A-Z]", password):
        score += 1
        criteres_passes.append("Contient des majuscules")
    else:
        criteres_manquants.append("Pas de majuscules")
        suggestions.append("Ajoutez des lettres majuscules")

    # 4. Chiffres (1 point)
    if re.search(r"\d", password):
        score += 1
        criteres_passes.append("Contient des chiffres")
    else:
        criteres_manquants.append("Pas de chiffres")
        suggestions.append("Ajoutez des chiffres")

    # 5. Caractères spéciaux (2 points)
    if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password):
        score += 2
        criteres_passes.append("Contient des caractères spéciaux")
    else:
        criteres_manquants.append("Pas de caractères spéciaux")
        suggestions.append("Ajoutez des caractères spéciaux (!@#$%...)")

    # 6. Pas dans la liste des mots de passe courants (2 points)
    if password.lower() not in MOTS_DE_PASSE_COURANTS:
        score += 2
        criteres_passes.append("N'est pas un mot de passe courant")
    else:
        score = max(0, score - 3)  # Pénalité
        criteres_manquants.append("Mot de passe trop courant")
        suggestions.append("Évitez les mots de passe évidents")

    # 7. Pas de répétitions excessives (1 point)
    if not re.search(r"(.)\1{3,}", password):  # pas plus de 3 répétitions
        score += 1
        criteres_passes.append("Pas de répétitions excessives")
    else:
        criteres_manquants.append("Contient des répétitions (ex: aaa, 1111)")
        suggestions.append("Évitez les répétitions de caractères")

    # Calculer la force
    ratio = score / max_score
    if ratio < 0.3:
        force = ForceMotDePasse.TRES_FAIBLE
    elif ratio < 0.5:
        force = ForceMotDePasse.FAIBLE
    elif ratio < 0.7:
        force = ForceMotDePasse.MOYEN
    elif ratio < 0.9:
        force = ForceMotDePasse.FORT
    else:
        force = ForceMotDePasse.TRES_FORT

    return ResultatForce(
        force=force,
        score=score,
        max_score=max_score,
        criteres_passes=criteres_passes,
        criteres_manquants=criteres_manquants,
        suggestions=suggestions,
    )


def afficher_force(password: str) -> None:
    """Affiche une analyse de la force d'un mot de passe."""
    result = verifier_force_mot_de_passe(password)

    barres = "█" * result.score + "░" * (result.max_score - result.score)
    print(f"\nMot de passe : {'*' * len(password)}")
    print(f"Force   : {result.force.name} [{barres}] {result.score}/{result.max_score}")
    print(f"Critères réussis :")
    for c in result.criteres_passes:
        print(f"  ✓ {c}")
    if result.criteres_manquants:
        print(f"Critères manquants :")
        for c in result.criteres_manquants:
            print(f"  ✗ {c}")
    if result.suggestions:
        print(f"Suggestions :")
        for s in result.suggestions:
            print(f"  → {s}")


# ---------------------------------------------------------------------------
# 6. Suite de tests
# ---------------------------------------------------------------------------

class TestHashageSHA256Simple(TestCase):

    def test_hash_consistant(self):
        h1 = hash_sha256_simple("test")
        h2 = hash_sha256_simple("test")
        self.assertEqual(h1, h2)

    def test_hash_different_pour_mdp_different(self):
        self.assertNotEqual(hash_sha256_simple("a"), hash_sha256_simple("b"))

    def test_verification_valide(self):
        h = hash_sha256_simple("secret")
        self.assertTrue(verifier_sha256_simple("secret", h))

    def test_verification_invalide(self):
        h = hash_sha256_simple("secret")
        self.assertFalse(verifier_sha256_simple("mauvais", h))

    def test_probleme_rainbow_table(self):
        """Démontrer pourquoi SHA-256 simple est vulnérable."""
        h1 = hash_sha256_simple("password")
        h2 = hash_sha256_simple("password")
        # Le même hash révèle que deux utilisateurs ont le même mot de passe
        self.assertEqual(h1, h2, "SHA-256 simple produit des hashes identiques")


class TestHashageSHA256AvecSel(TestCase):

    def test_hashes_differents_meme_mdp(self):
        """Le sel garantit des hashes différents même pour des mots de passe identiques."""
        h1, s1 = hash_sha256_avec_sel("password")
        h2, s2 = hash_sha256_avec_sel("password")
        self.assertNotEqual(h1, h2)
        self.assertNotEqual(s1, s2)

    def test_verification_valide(self):
        h, s = hash_sha256_avec_sel("secret")
        self.assertTrue(verifier_sha256_avec_sel("secret", h, s))

    def test_verification_mauvais_mdp(self):
        h, s = hash_sha256_avec_sel("secret")
        self.assertFalse(verifier_sha256_avec_sel("mauvais", h, s))

    def test_verification_mauvais_sel(self):
        """Un sel incorrect doit faire échouer la vérification."""
        h, s = hash_sha256_avec_sel("secret")
        faux_sel = secrets.token_bytes(32).hex()
        self.assertFalse(verifier_sha256_avec_sel("secret", h, faux_sel))


class TestHashagePBKDF2(TestCase):

    def test_format_stockage(self):
        h = hash_pbkdf2("test", iterations=1000)
        parties = h.split("$")
        self.assertEqual(len(parties), 4)
        self.assertEqual(parties[0], "pbkdf2_sha256")
        self.assertEqual(parties[1], "1000")

    def test_verification_valide(self):
        h = hash_pbkdf2("secret", iterations=1000)
        self.assertTrue(verifier_pbkdf2("secret", h))

    def test_verification_invalide(self):
        h = hash_pbkdf2("secret", iterations=1000)
        self.assertFalse(verifier_pbkdf2("mauvais", h))

    def test_hashes_differents_meme_mdp(self):
        h1 = hash_pbkdf2("password", iterations=1000)
        h2 = hash_pbkdf2("password", iterations=1000)
        self.assertNotEqual(h1, h2)

    def test_hash_corrompu_ne_plante_pas(self):
        self.assertFalse(verifier_pbkdf2("test", "hash_invalide"))

    def test_iterations_dans_le_hash(self):
        h = hash_pbkdf2("test", iterations=12345)
        self.assertIn("12345", h)


class TestVerificateurForce(TestCase):

    def test_mot_de_passe_tres_faible(self):
        r = verifier_force_mot_de_passe("abc")
        self.assertLessEqual(r.force.value, ForceMotDePasse.FAIBLE.value)

    def test_mot_de_passe_courant_penalise(self):
        r = verifier_force_mot_de_passe("password")
        self.assertIn("Mot de passe trop courant", r.criteres_manquants)

    def test_mot_de_passe_fort(self):
        r = verifier_force_mot_de_passe("Tr0ub4dor&3-correct")
        self.assertGreaterEqual(r.force.value, ForceMotDePasse.FORT.value)

    def test_sans_majuscules(self):
        r = verifier_force_mot_de_passe("motdepasse123!")
        self.assertIn("Pas de majuscules", r.criteres_manquants)

    def test_sans_chiffres(self):
        r = verifier_force_mot_de_passe("MotDePasseFort!")
        self.assertIn("Pas de chiffres", r.criteres_manquants)

    def test_sans_special(self):
        r = verifier_force_mot_de_passe("MotDePasse123")
        self.assertIn("Pas de caractères spéciaux", r.criteres_manquants)

    def test_repetitions_penalisees(self):
        r = verifier_force_mot_de_passe("aaaaaBBBB1!")
        self.assertIn("Contient des répétitions (ex: aaa, 1111)", r.criteres_manquants)

    def test_tres_long_secure(self):
        r = verifier_force_mot_de_passe("Tr0ub4d0r&3!xYz@9Kp")
        self.assertGreaterEqual(r.score, 8)

    def test_score_entre_0_et_max(self):
        for mdp in ["a", "password", "Tr0ub4dor&3"]:
            r = verifier_force_mot_de_passe(mdp)
            self.assertGreaterEqual(r.score, 0)
            self.assertLessEqual(r.score, r.max_score)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import unittest

    print("=" * 70)
    print("Day 40 — Hachage de mots de passe")
    print("=" * 70)

    # Benchmark des méthodes
    print("\n[1] Benchmark des méthodes de hachage")
    print("    (PBKDF2 avec 600k itérations prend quelques secondes...)")
    benchmark_complet()

    # Démo vérificateur de force
    print("\n[2] Vérificateur de force de mot de passe")
    mots_de_passe_test = [
        "abc",
        "password",
        "motdepasse123",
        "MotDePasse1!",
        "Tr0ub4dor&3-correct-horse",
    ]
    for mdp in mots_de_passe_test:
        afficher_force(mdp)

    # Tests unitaires
    print("\n\n[3] Tests unitaires")
    print("-" * 50)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestHashageSHA256Simple, TestHashageSHA256AvecSel,
                TestHashagePBKDF2, TestVerificateurForce]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
