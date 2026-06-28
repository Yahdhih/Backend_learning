# Jour 05 — Python : décorateurs
📅 1 juillet 2026 · Module : Python

---

## Le problème que les décorateurs résolvent

Imagine que tu veux logger chaque appel à tes fonctions :

```python
# Sans décorateur — code dupliqué partout
def get_user(user_id):
    print("Appel de get_user")    # dupliqué
    user = db.find(user_id)
    print("Fin de get_user")      # dupliqué
    return user

def delete_user(user_id):
    print("Appel de delete_user") # dupliqué encore
    db.delete(user_id)
    print("Fin de delete_user")   # dupliqué encore
```

Les décorateurs permettent d'**envelopper** une fonction pour ajouter un comportement, sans toucher à la fonction originale.

---

## Un décorateur = une fonction qui prend une fonction et retourne une fonction

```python
def logger(func):                        # reçoit la fonction à décorer
    def wrapper(*args, **kwargs):        # la nouvelle fonction
        print(f"Appel de {func.__name__}")
        result = func(*args, **kwargs)   # appelle la fonction originale
        print(f"Fin de {func.__name__}")
        return result
    return wrapper                       # retourne la nouvelle fonction
```

**Utilisation avec `@` :**
```python
@logger
def get_user(user_id):
    return {"id": user_id, "nom": "Alice"}

# @logger est exactement équivalent à :
# get_user = logger(get_user)
```

**Ce qui se passe quand tu appelles `get_user(42)` :**
1. Python exécute `wrapper(42)` (pas `get_user` directement)
2. `wrapper` affiche "Appel de get_user"
3. `wrapper` appelle la vraie `get_user(42)`
4. `wrapper` affiche "Fin de get_user"
5. `wrapper` retourne le résultat

---

## `functools.wraps` — préserver les métadonnées

Sans `@wraps`, la fonction décorée "perd" son nom et sa docstring :

```python
print(get_user.__name__)   # "wrapper" ← mauvais !
print(get_user.__doc__)    # None ← mauvais !
```

La solution :

```python
from functools import wraps

def logger(func):
    @wraps(func)              # copie __name__, __doc__, etc.
    def wrapper(*args, **kwargs):
        print(f"Appel de {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Fin de {func.__name__}")
        return result
    return wrapper

@logger
def get_user(user_id):
    """Retourne un utilisateur par son ID."""
    return {"id": user_id}

print(get_user.__name__)   # "get_user" ✓
print(get_user.__doc__)    # "Retourne un utilisateur par son ID." ✓
```

---

## Décorateurs avec arguments

`@cache_page(60)` — comment passer un argument à un décorateur ?
Il faut une **couche supplémentaire** :

```python
def repeter(n):                          # couche 1 : prend l'argument
    def decorateur(func):                # couche 2 : prend la fonction
        @wraps(func)
        def wrapper(*args, **kwargs):    # couche 3 : le vrai wrapper
            for _ in range(n):
                func(*args, **kwargs)
        return wrapper
    return decorateur

@repeter(3)
def dire_bonjour():
    print("Bonjour !")

dire_bonjour()
# Bonjour !
# Bonjour !
# Bonjour !
```

`@repeter(3)` = d'abord `repeter(3)` est appelé (retourne `decorateur`), puis `decorateur(dire_bonjour)` est appelé.

---

## Décorateurs courants dans Django

```python
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

@login_required                     # redirige si pas connecté
@cache_page(60 * 15)                # met en cache 15 minutes
@require_http_methods(["GET"])      # refuse les autres méthodes
def ma_vue(request):
    return HttpResponse("OK")
```

L'ordre des décorateurs compte : ils s'appliquent de bas en haut.

---

## Pattern réel : décorateur de validation

```python
from functools import wraps
from django.http import JsonResponse

def require_json(func):
    """Vérifie que la requête contient du JSON valide."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.content_type != "application/json":
            return JsonResponse({"error": "JSON requis"}, status=400)
        try:
            import json
            request.json = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON invalide"}, status=400)
        return func(request, *args, **kwargs)
    return wrapper

@require_json
def creer_utilisateur(request):
    nom = request.json["nom"]   # on peut utiliser request.json directement
    ...
```

---

## Décorateurs empilés

```python
@decorateur_a
@decorateur_b
@decorateur_c
def ma_fonction():
    pass

# Équivaut à :
ma_fonction = decorateur_a(decorateur_b(decorateur_c(ma_fonction)))
# c est appliqué en premier, puis b, puis a
```
