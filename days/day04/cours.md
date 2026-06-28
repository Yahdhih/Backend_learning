# Jour 04 — Python : syntaxe, types, fonctions
📅 30 juin 2026 · Module : Python

---

## Pourquoi Python ?

Python a une syntaxe minimaliste : pas de `{}`, pas de `;`, l'indentation EST la structure du code.

```python
# Java
if (x > 0) {
    System.out.println("positif");
}

# Python — même chose
if x > 0:
    print("positif")
```

---

## Les types de base

```python
# Entier
age = 30
annee = 2_026      # underscore autorisé pour la lisibilité

# Flottant
pi = 3.14159
temperature = -5.5

# Chaîne de caractères (immutable)
nom = "Alice"
message = f"Bonjour {nom}, tu as {age} ans"  # f-string

# Booléen
actif = True
connecte = False

# None (l'absence de valeur, comme null en Java/JS)
resultat = None
```

**f-strings** (Python 3.6+) : tu peux mettre n'importe quelle expression Python entre `{}` :

```python
prix = 19.99
print(f"Prix TTC : {prix * 1.2:.2f} €")  # 23.99 €
```

---

## Les collections

```python
# Liste (mutable, ordonnée, doublons OK)
nombres = [1, 2, 3, 4, 5]
nombres.append(6)       # [1, 2, 3, 4, 5, 6]
nombres[0]              # 1
nombres[-1]             # 6  (dernier élément)
nombres[1:3]            # [2, 3]  (slice)
len(nombres)            # 6

# Tuple (immutable, ordonnée)
coordonnees = (48.8566, 2.3522)
lat, lon = coordonnees  # déstructuration

# Dict (clé-valeur, mutable)
utilisateur = {
    "id": 1,
    "nom": "Alice",
    "actif": True
}
utilisateur["nom"]              # "Alice"
utilisateur.get("email")        # None (pas d'erreur)
utilisateur.get("email", "")    # "" (valeur par défaut)
utilisateur.keys()              # dict_keys(["id", "nom", "actif"])
utilisateur.items()             # paires (clé, valeur)

# Set (non ordonné, pas de doublons)
tags = {"python", "django", "python"}   # {"python", "django"}
tags.add("api")
"python" in tags                # True
```

---

## Fonctions

```python
# Fonction de base
def additionner(a, b):
    return a + b

# Arguments par défaut
def saluer(nom, salutation="Bonjour"):
    return f"{salutation}, {nom} !"

saluer("Alice")           # "Bonjour, Alice !"
saluer("Bob", "Salut")    # "Salut, Bob !"

# Arguments positionnels variables (*args → tuple)
def somme(*nombres):
    return sum(nombres)

somme(1, 2, 3, 4)         # 10

# Arguments nommés variables (**kwargs → dict)
def construire_url(host, **params):
    if not params:
        return host
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{host}?{query}"

construire_url("api.com/users", page=2, limit=10)
# "api.com/users?page=2&limit=10"

# Combiner tout
def tout(*args, separateur=", ", **kwargs):
    print(args, separateur, kwargs)
```

---

## Comprehensions — filtrer et transformer en une ligne

```python
nombres = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# List comprehension : [expression for element in iterable if condition]
carres = [n ** 2 for n in nombres]
# [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]

pairs = [n for n in nombres if n % 2 == 0]
# [2, 4, 6, 8, 10]

carres_des_pairs = [n ** 2 for n in nombres if n % 2 == 0]
# [4, 16, 36, 64, 100]

# Dict comprehension
utilisateurs = [{"id": 1, "nom": "Alice"}, {"id": 2, "nom": "Bob"}]
index = {u["id"]: u["nom"] for u in utilisateurs}
# {1: "Alice", 2: "Bob"}

# Set comprehension
lettres_uniques = {lettre.lower() for lettre in "Hello World"}
# {'h', 'e', 'l', 'o', ' ', 'w', 'r', 'd'}
```

---

## Contrôle de flux

```python
# if / elif / else
score = 75
if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
else:
    grade = "F"

# for avec enumerate (index + valeur)
fruits = ["pomme", "banane", "cerise"]
for i, fruit in enumerate(fruits):
    print(f"{i}: {fruit}")

# for avec zip (parallèle)
noms = ["Alice", "Bob"]
ages = [30, 25]
for nom, age in zip(noms, ages):
    print(f"{nom} a {age} ans")

# while
compteur = 0
while compteur < 5:
    print(compteur)
    compteur += 1
```

---

## Gestion d'erreurs

```python
try:
    resultat = 10 / 0
except ZeroDivisionError as e:
    print(f"Erreur : {e}")
except (ValueError, TypeError) as e:
    print(f"Erreur de valeur ou de type : {e}")
else:
    print("Pas d'erreur")        # exécuté si pas d'exception
finally:
    print("Toujours exécuté")    # nettoyage

# Lever une exception
def diviser(a, b):
    if b == 0:
        raise ValueError("Impossible de diviser par zéro")
    return a / b
```
