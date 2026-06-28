"""
Exercice Jour 44 — Simulation attaque CSRF et protection

Lance : python3 exercice.py
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                        "django.contrib.sessions", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        ROOT_URLCONF="__main__",
        SESSION_ENGINE="django.contrib.sessions.backends.db",
        SECRET_KEY="test-secret-key-for-csrf-demo",
        MIDDLEWARE=[],
    )
    django.setup()

from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.test import RequestFactory, Client
import json


# Simuler un "compte bancaire" en mémoire
comptes = {}


# ─── SERVEUR VULNÉRABLE (sans protection CSRF) ───────────────────────────────

class VirementVulnerable(View):
    """Vue vulnérable à CSRF — pas de vérification du token."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}

        # Simule : l'utilisateur est connecté (session cookie)
        user_id = request.session.get("user_id")
        if not user_id:
            return JsonResponse({"error": "Non connecté"}, status=401)

        destinataire = data.get("destinataire")
        montant = data.get("montant", 0)

        if user_id in comptes and montant > 0:
            comptes[user_id] = comptes.get(user_id, 0) - montant
            comptes[destinataire] = comptes.get(destinataire, 0) + montant
            return JsonResponse({
                "message": f"Virement de {montant}€ vers {destinataire} effectué",
                "nouveau_solde": comptes[user_id]
            })
        return JsonResponse({"error": "Erreur"}, status=400)


class SoldeView(View):
    def get(self, request):
        user_id = request.session.get("user_id", "anonyme")
        return JsonResponse({"user": user_id, "solde": comptes.get(user_id, 0)})


# ─── EXERCICE 1 : Simuler l'attaque ──────────────────────────────────────────

def simuler_attaque_csrf():
    """
    Simule une attaque CSRF :
    1. Alice est connectée à la banque (a un cookie de session)
    2. Elle visite un site malveillant
    3. Le site malveillant fait un virement à son insu

    TODO : complète la simulation
    """
    # Setup
    comptes["alice"] = 1000
    comptes["attaquant"] = 0

    factory = RequestFactory()

    # 1. Alice "se connecte" — crée une session
    session_alice = {"user_id": "alice"}

    print("--- Avant l'attaque ---")
    print(f"  Alice : {comptes['alice']}€")
    print(f"  Attaquant : {comptes['attaquant']}€")

    # 2. Simuler la requête CSRF (le site malveillant envoie une requête
    #    au nom d'Alice avec son cookie de session)
    req = factory.post(
        "/virement/",
        data=json.dumps({"destinataire": "attaquant", "montant": 500}),
        content_type="application/json",
    )

    # TODO : ajouter la session alice à la requête
    # req.session = session_alice

    # TODO : appeler VirementVulnerable et observer le résultat
    view = VirementVulnerable.as_view()
    # resp = view(req)
    # print("Réponse:", resp.status_code, json.loads(resp.content))

    print("\n--- Après l'attaque ---")
    print(f"  Alice : {comptes['alice']}€")
    print(f"  Attaquant : {comptes['attaquant']}€")

    return comptes


# ─── EXERCICE 2 : Vue protégée contre CSRF ───────────────────────────────────

CSRF_TOKENS = {}  # {user_id: token}


def generer_csrf_token(user_id: str) -> str:
    """Génère un token CSRF aléatoire pour l'utilisateur."""
    import secrets
    # TODO : générer un token aléatoire, le stocker dans CSRF_TOKENS, le retourner
    pass


class VirementProtege(View):
    """
    Vue protégée contre CSRF.
    Le client doit envoyer le header X-CSRF-Token avec le bon token.
    """

    def post(self, request):
        user_id = request.session.get("user_id")
        if not user_id:
            return JsonResponse({"error": "Non connecté"}, status=401)

        # TODO : vérifier le header X-CSRF-Token
        # csrf_token_recu = request.META.get("HTTP_X_CSRF_TOKEN")
        # csrf_token_attendu = CSRF_TOKENS.get(user_id)
        # if csrf_token_recu != csrf_token_attendu:
        #     return JsonResponse({"error": "CSRF détecté !"}, status=403)

        try:
            data = json.loads(request.body)
        except Exception:
            data = {}

        destinataire = data.get("destinataire")
        montant = data.get("montant", 0)

        if user_id in comptes and montant > 0:
            comptes[user_id] -= montant
            comptes[destinataire] = comptes.get(destinataire, 0) + montant
            return JsonResponse({"message": f"Virement de {montant}€ effectué"})
        return JsonResponse({"error": "Erreur"}, status=400)


# ─── EXERCICE 3 : Tester la protection Django CSRF ───────────────────────────

def demo_django_csrf():
    """
    Montre comment Django's CsrfViewMiddleware fonctionne.
    """
    print("\n--- Protection CSRF Django ---")
    print("Django's CsrfViewMiddleware vérifie automatiquement :")
    print("  1. Le cookie csrftoken est présent")
    print("  2. Le header X-CSRFToken (AJAX) ou le champ csrfmiddlewaretoken (form) correspond")
    print("  3. Les deux sont identiques (prevent double-submit)")
    print()
    print("Dans DRF avec SessionAuthentication, SessionAuthentication.enforce_csrf()")
    print("est appelé automatiquement — pas besoin de @csrf_exempt sur les vues DRF.")


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    from django.db import connection
    with connection.schema_editor() as se:
        try:
            from django.contrib.sessions.backends.db import SessionStore
            from django.contrib.sessions.models import Session
            se.create_model(Session)
        except: pass

    print("=== Simulation attaque CSRF ===")
    soldes = simuler_attaque_csrf()
    print("\nObservation : si VirementVulnerable accepte la requête sans token CSRF,")
    print("l'attaquant peut vider le compte d'Alice.")

    print("\n=== Test protection CSRF ===")
    if generer_csrf_token("alice"):
        comptes["alice"] = 1000
        comptes["attaquant"] = 0

        token = generer_csrf_token("alice")
        factory = RequestFactory()

        # Requête sans token → doit être refusée
        req = factory.post("/virement/", data=json.dumps({"destinataire": "attaquant", "montant": 100}),
                           content_type="application/json")
        req.session = {"user_id": "alice"}
        resp = VirementProtege.as_view()(req)
        if resp.status_code == 403:
            print("  OK    Requête sans CSRF token → 403")
        else:
            print(f"  TODO  Implémenter la vérification CSRF (statut: {resp.status_code})")

        # Requête avec bon token → doit passer
        req2 = factory.post("/virement/", data=json.dumps({"destinataire": "attaquant", "montant": 100}),
                            content_type="application/json", HTTP_X_CSRF_TOKEN=token)
        req2.session = {"user_id": "alice"}
        resp2 = VirementProtege.as_view()(req2)
        if resp2.status_code == 200:
            print("  OK    Requête avec CSRF token valide → 200")
        else:
            print(f"  TODO  Vérification token valide (statut: {resp2.status_code})")

    demo_django_csrf()


if __name__ == "__main__":
    tester()
