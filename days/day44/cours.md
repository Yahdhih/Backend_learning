# Jour 44 — CSRF : Attaque et Protection (9 août 2026)

---

## 1. Qu'est-ce que le CSRF ?

**CSRF** (Cross-Site Request Forgery, aussi appelé Sea-Surf ou XSRF) est une attaque qui force un utilisateur authentifié à exécuter des actions non désirées sur une application web dans laquelle il est connecté.

L'idée centrale : l'attaquant exploite la **confiance** que le serveur a envers le navigateur de la victime.

### Analogie simple

Imaginez que vous êtes connecté à votre banque. Vous ouvrez un autre onglet et visitez un site malveillant. Ce site contient du code HTML qui, silencieusement, envoie une requête à votre banque pour virer de l'argent. Le navigateur inclut automatiquement vos cookies de session de la banque. Le serveur de la banque reçoit une requête avec vos credentials valides — et exécute le virement.

Vous n'avez rien fait volontairement. L'attaquant a utilisé votre navigateur comme un relais.

---

## 2. Scénario d'attaque pas à pas

### Contexte

- Alice est connectée à `https://banque.com`
- Son cookie de session : `session_id=abc123`
- L'endpoint de virement : `POST /virement` avec le body `{ montant: 500, destination: "FR76..." }`

### Étape 1 : Alice se connecte à la banque

```
POST /login HTTP/1.1
Host: banque.com
Content-Type: application/x-www-form-urlencoded

username=alice&password=secret

-- Réponse --
Set-Cookie: session_id=abc123; HttpOnly; Path=/
```

Alice est authentifiée. Son navigateur stocke le cookie.

### Étape 2 : L'attaquant prépare sa page piège

L'attaquant crée `https://site-malveillant.com/gagnez-un-iphone.html` :

```html
<!DOCTYPE html>
<html>
<head>
    <title>Vous avez gagné un iPhone !</title>
</head>
<body>
    <h1>Cliquez ici pour réclamer votre prix !</h1>

    <!-- Formulaire caché qui se soumet automatiquement -->
    <form id="csrf-form"
          action="https://banque.com/virement"
          method="POST"
          style="display: none;">
        <input type="hidden" name="montant" value="5000" />
        <input type="hidden" name="destination" value="FR76ATTAQUANT0000" />
    </form>

    <script>
        // Le formulaire se soumet dès le chargement de la page
        document.getElementById('csrf-form').submit();
    </script>
</body>
</html>
```

### Étape 3 : Alice visite la page piège

Alice clique sur un lien dans un email ou sur les réseaux sociaux. Son navigateur :

1. Charge `https://site-malveillant.com/gagnez-un-iphone.html`
2. Exécute le JavaScript
3. Soumet le formulaire vers `https://banque.com/virement`
4. **Inclut automatiquement le cookie** `session_id=abc123`

### Étape 4 : Le serveur exécute la requête

```
POST /virement HTTP/1.1
Host: banque.com
Cookie: session_id=abc123        <-- Cookie légitime d'Alice
Content-Type: application/x-www-form-urlencoded
Referer: https://site-malveillant.com/gagnez-un-iphone.html

montant=5000&destination=FR76ATTAQUANT0000
```

Le serveur voit un cookie valide → il exécute le virement. Le compte d'Alice est débité.

### Attaque par image (GET)

Pour les actions déclenchées par GET (mauvaise pratique mais ça existe) :

```html
<!-- Une simple balise img peut déclencher une requête GET authentifiée -->
<img src="https://banque.com/supprimer-compte?id=42" width="1" height="1" />
```

### Attaque par fetch/XMLHttpRequest

```html
<script>
fetch('https://banque.com/virement', {
    method: 'POST',
    credentials: 'include',  // Inclut les cookies !
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ montant: 5000, destination: 'FR76ATTAQUANT' })
});
</script>
```

Note : CORS bloque la **lecture** de la réponse, mais la **requête est quand même envoyée** et exécutée si le serveur ne valide pas le CSRF token.

---

## 3. Pourquoi les cookies sont le problème

Le comportement fondamental des navigateurs : **les cookies sont envoyés automatiquement avec chaque requête vers le domaine correspondant**, quelle que soit l'origine de la requête.

```
Requête vers banque.com depuis banque.com     → Cookies envoyés ✓ (normal)
Requête vers banque.com depuis malveillant.com → Cookies envoyés ✓ (problème !)
```

C'est une fonctionnalité du web (pas un bug), conçue pour maintenir les sessions. CSRF l'exploite.

### Ce que l'attaquant peut et ne peut pas faire

| Peut faire | Ne peut pas faire |
|------------|-------------------|
| Déclencher des requêtes avec les cookies de la victime | Lire la réponse (CORS) |
| Effectuer des actions à la place de la victime | Lire les cookies HttpOnly |
| Utiliser GET, POST, PUT, DELETE | Contourner SameSite=Strict |

---

## 4. Le CSRF Token : comment ça marche

### Principe fondamental

Le serveur génère un token secret, imprévisible, unique par session (ou par requête). Ce token est inclus dans chaque formulaire HTML. Quand le formulaire est soumis, le serveur vérifie que le token est présent et valide.

L'attaquant ne peut pas obtenir ce token car :
- Il ne peut pas lire les pages du site cible (Same-Origin Policy)
- Il ne peut pas lire les cookies HttpOnly
- Il ne connaît pas la valeur du token

### Pattern 1 : Synchronizer Token Pattern

```python
# À la génération de la page (Django le fait automatiquement)
import secrets

def generate_csrf_token():
    return secrets.token_hex(32)

# Côté serveur : stocké en session
session['csrf_token'] = generate_csrf_token()

# Côté template HTML
"""
<form method="POST" action="/virement">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <input type="number" name="montant">
    <button type="submit">Virer</button>
</form>
"""

# Côté validation serveur
def virement_view(request):
    submitted_token = request.POST.get('csrf_token')
    session_token = request.session.get('csrf_token')

    if not submitted_token or submitted_token != session_token:
        return HttpResponse("CSRF validation échouée", status=403)

    # Traiter le virement...
```

L'attaquant ne peut pas mettre le bon token dans son formulaire piège car il ne le connaît pas.

### Pattern 2 : Double Submit Cookie

```
1. Serveur génère un token aléatoire
2. Token mis dans un cookie (pas HttpOnly)
3. Token mis aussi dans un champ caché du formulaire (ou header)
4. Lors de la soumission, le serveur vérifie que cookie == valeur du champ
```

```python
# Génération
csrf_token = secrets.token_hex(32)
response.set_cookie('csrftoken', csrf_token, samesite='Strict')

# Dans le formulaire
# <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}">

# Validation
def validate_csrf(request):
    cookie_token = request.COOKIES.get('csrftoken', '')
    form_token = request.POST.get('csrfmiddlewaretoken', '')

    if not cookie_token or not form_token:
        return False

    # Comparaison en temps constant (évite timing attacks)
    return hmac.compare_digest(cookie_token, form_token)
```

L'attaquant peut lire le cookie si SameSite n'est pas défini, mais sans HTTPS et sans HttpOnly, cette protection est affaiblie. En pratique, Django utilise une variante signée cryptographiquement.

### Pourquoi la comparaison en temps constant est importante

```python
import hmac

# MAUVAIS : vulnérable aux timing attacks
if submitted_token == session_token:  # Python court-circuite sur le premier caractère différent
    pass

# BON : temps constant quelle que soit la différence
if hmac.compare_digest(submitted_token, session_token):
    pass
```

Une timing attack mesure le temps de réponse pour deviner le token caractère par caractère.

---

## 5. L'attribut SameSite des cookies

SameSite est un attribut de cookie qui contrôle quand les cookies sont envoyés lors de requêtes cross-site.

### Valeurs possibles

#### `SameSite=Strict`

```
Set-Cookie: session_id=abc123; SameSite=Strict
```

Le cookie n'est **jamais** envoyé lors de requêtes cross-site. Même si vous cliquez sur un lien vers le site depuis un email.

- Protection CSRF : maximale
- Expérience utilisateur : dégradée (l'utilisateur semble déconnecté quand il arrive depuis un lien externe)

#### `SameSite=Lax` (défaut moderne)

```
Set-Cookie: session_id=abc123; SameSite=Lax
```

Le cookie est envoyé uniquement pour les navigations top-level GET (clic sur un lien). Pas envoyé pour les requêtes POST, PUT, DELETE cross-site, ni pour les iframes, images, fetch.

- Protection CSRF : bonne pour la plupart des attaques
- Expérience utilisateur : meilleure (connexion maintenue lors des clics de liens)

#### `SameSite=None`

```
Set-Cookie: session_id=abc123; SameSite=None; Secure
```

Cookie envoyé dans tous les contextes. Doit être accompagné de `Secure`.

- Protection CSRF : aucune
- Nécessaire pour les widgets embarqués dans des iframes cross-origin

### Tableau récapitulatif

| Type de requête | Strict | Lax | None |
|-----------------|--------|-----|------|
| Lien (`<a href>`) | Non | Oui | Oui |
| Form GET | Non | Oui | Oui |
| Form POST | Non | Non | Oui |
| iframe | Non | Non | Oui |
| fetch/XHR | Non | Non | Oui |
| Image `<img src>` | Non | Non | Oui |

---

## 6. Le middleware CSRF de Django

### Configuration

Dans `settings.py`, `CsrfViewMiddleware` est inclus par défaut :

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # <-- CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### Comment Django implémente le CSRF

Django utilise une variante du double submit cookie avec signature HMAC :

```python
# Simplifié — le vrai code est dans django/middleware/csrf.py

# 1. Génération du token
import secrets
import hmac
import hashlib

def _get_new_csrf_token():
    return secrets.token_hex(32)

def _mask_cipher_secret(secret):
    """Django masque le token pour éviter BREACH attack"""
    mask = secrets.token_hex(32)
    masked = hmac.new(mask.encode(), secret.encode(), hashlib.sha256).hexdigest()
    return f"{mask}:{masked}"

# 2. Django stocke un secret dans un cookie
# Cookie: csrftoken=<secret_non_masqué>

# 3. Le token dans le formulaire est masqué différemment à chaque fois
# Header/Form: csrfmiddlewaretoken=<token_masqué>

# 4. Validation : Django démasque le token du formulaire
# et vérifie qu'il correspond au secret du cookie
```

### Dans les templates Django

```html
<!-- Template Django classique -->
<form method="post">
    {% csrf_token %}
    <!-- Génère : <input type="hidden" name="csrfmiddlewaretoken" value="..."> -->
    <button type="submit">Soumettre</button>
</form>
```

```python
# Dans une vue basée sur fonction
from django.views.decorators.csrf import csrf_protect

@csrf_protect  # Explicitement protégé (redondant si middleware actif)
def ma_vue(request):
    if request.method == 'POST':
        # Django a déjà validé le token avant d'entrer ici
        pass
```

### Requêtes AJAX avec CSRF

```javascript
// Méthode 1 : Lire le cookie et mettre dans l'header
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

fetch('/api/action/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,  // Header que Django accepte
    },
    body: JSON.stringify({ data: 'valeur' }),
    credentials: 'same-origin',
});
```

```javascript
// Méthode 2 : Avec axios (configuration globale)
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';

// Méthode 3 : Lire depuis le template
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
```

### Comment Django valide l'header X-CSRFToken

```python
# Dans CsrfViewMiddleware.process_view() (simplifié)
def process_view(self, request, callback, callback_args, callback_kwargs):
    # 1. Ignorer les méthodes "safe" (GET, HEAD, OPTIONS, TRACE)
    if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
        return None  # Pas de vérification

    # 2. Récupérer le token du cookie
    csrf_cookie = request.COOKIES.get('csrftoken', '')

    # 3. Récupérer le token soumis (formulaire ou header)
    request_csrf_token = ''
    if request.method == 'POST':
        request_csrf_token = request.POST.get('csrfmiddlewaretoken', '')
    if not request_csrf_token:
        request_csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')

    # 4. Comparer
    if not hmac.compare_digest(csrf_cookie, request_csrf_token):
        return self._reject(request, REASON_BAD_TOKEN)
```

---

## 7. @csrf_exempt — quand l'utiliser

### Désactiver la protection sur une vue

```python
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def webhook_stripe(request):
    """
    Les webhooks Stripe arrivent depuis les serveurs Stripe,
    pas depuis un navigateur — pas de cookie à valider.
    On valide à la place avec la signature Stripe.
    """
    if request.method == 'POST':
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

        # Validation par signature cryptographique, pas par CSRF token
        import stripe
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            return JsonResponse({'error': 'Invalid signature'}, status=400)

        # Traiter l'événement...
        return JsonResponse({'status': 'ok'})
```

### Cas légitimes pour @csrf_exempt

1. **Webhooks externes** (Stripe, GitHub, Twilio) : authentifiés par signature
2. **APIs consommées par des apps mobiles** : utilisent Bearer token, pas de session cookie
3. **APIs machine-to-machine** : pas de navigateur impliqué
4. **Services de microarchitecture interne** : communication serveur-à-serveur

### Mauvaises raisons d'utiliser @csrf_exempt

```python
# MAUVAIS : "C'est trop compliqué à gérer"
@csrf_exempt
def mon_formulaire_de_paiement(request):  # DANGER !
    ...

# MAUVAIS : "L'API frontend n'envoie pas le token"
@csrf_exempt
def api_sensible(request):  # Corriger le frontend plutôt !
    ...
```

---

## 8. DRF et CSRF : session auth vs token auth

### Pourquoi la session auth nécessite le CSRF

Avec l'authentification par session (cookie) :

```python
# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
}
```

DRF applique la vérification CSRF car le navigateur envoie automatiquement le cookie de session. Sans CSRF, une page malveillante pourrait déclencher des appels API authentifiés.

```python
# SessionAuthentication dans DRF enforces CSRF
class SessionAuthentication(BaseAuthentication):
    def authenticate(self, request):
        user = get_user(request)
        if not user or not user.is_active:
            return None

        # CSRF check est fait ici !
        self.enforce_csrf(request)

        return (user, None)

    def enforce_csrf(self, request):
        check = CSRFCheck(request)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied('CSRF Failed: %s' % reason)
```

### Pourquoi la token auth ne nécessite pas le CSRF

Avec l'authentification par token (Bearer) :

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        # ou 'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
```

```python
# Requête API avec Bearer token
fetch('/api/resource/', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer eyJhbGc...',  // Token dans l'header
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
});
```

Un attaquant CSRF ne peut pas inclure le Bearer token dans sa page piège car :
- Il ne connaît pas le token (ce n'est pas un cookie automatiquement envoyé)
- JavaScript cross-origin ne peut pas lire les tokens stockés dans localStorage/mémoire

### Règle pratique

```
Session cookies → CSRF protection nécessaire
Bearer/API tokens dans headers → CSRF protection non nécessaire
```

### Configuration DRF avec CSRF désactivé pour les APIs token

```python
# views.py — API pure avec token auth
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class MonAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # CSRF n'est pas vérifié car TokenAuthentication ne l'exige pas
        return Response({'status': 'ok'})
```

```python
# Pour désactiver CSRF globalement pour les vues DRF
# (uniquement si vous n'utilisez PAS SessionAuthentication)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}
```

---

## 9. Résumé des protections CSRF

### Stratégie de défense en profondeur

```python
# settings.py — configuration CSRF complète

# 1. CSRF Middleware activé (par défaut)
MIDDLEWARE = [
    ...
    'django.middleware.csrf.CsrfViewMiddleware',
    ...
]

# 2. Cookie SameSite
SESSION_COOKIE_SAMESITE = 'Lax'   # ou 'Strict'
CSRF_COOKIE_SAMESITE = 'Lax'

# 3. Cookie Secure (HTTPS seulement)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 4. HttpOnly pour le cookie de session (pas le csrf cookie !)
SESSION_COOKIE_HTTPONLY = True
# CSRF_COOKIE_HTTPONLY = False  # Doit être False pour que JS puisse le lire

# 5. Durée du token CSRF
CSRF_COOKIE_AGE = 31449600  # 1 an (défaut Django)
```

### Checklist CSRF

- [ ] `CsrfViewMiddleware` dans `MIDDLEWARE`
- [ ] `{% csrf_token %}` dans tous les formulaires POST
- [ ] Header `X-CSRFToken` dans les requêtes AJAX
- [ ] `SameSite=Lax` ou `Strict` sur les cookies de session
- [ ] `@csrf_exempt` utilisé seulement là où c'est justifié
- [ ] Les APIs avec Bearer token n'ont pas besoin de CSRF

---

## 10. Outils de test

```bash
# Tester si une vue est protégée
curl -X POST https://monsite.com/action/ \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --cookie "sessionid=abc123" \
    --data "montant=100"
# Doit retourner 403 Forbidden sans le CSRF token

# Avec le bon token (obtenu depuis la page)
curl -X POST https://monsite.com/action/ \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --cookie "sessionid=abc123; csrftoken=LETOKEN" \
    --data "montant=100&csrfmiddlewaretoken=LETOKEN"
# Doit retourner 200

# Outils de test automatisé
# OWASP ZAP
# Burp Suite (onglet CSRF tester)
```

---

## Points clés à retenir

1. **CSRF exploite la confiance du serveur envers le navigateur** : les cookies sont envoyés automatiquement, même depuis d'autres domaines.

2. **La défense principale est le CSRF token** : un secret connu seulement du serveur légitime et du client, impossible à deviner pour l'attaquant.

3. **SameSite est une deuxième ligne de défense** : il empêche les requêtes cross-site d'envoyer les cookies, mais n'est pas suffisant seul (vieux navigateurs, exceptions Lax).

4. **@csrf_exempt est dangereux** : ne l'utiliser que pour des endpoints authentifiés par d'autres moyens (signatures, Bearer tokens).

5. **DRF avec TokenAuthentication ne nécessite pas CSRF** : le token n'est pas un cookie automatique, l'attaquant ne peut pas l'usurper.

6. **Django gère tout ça automatiquement** si vous utilisez le middleware et les templates correctement.
