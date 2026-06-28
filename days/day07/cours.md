# Jour 07 — Python : générateurs et context managers
📅 3 juillet 2026 · Module : Python

---

## Générateurs : produire des valeurs à la demande

Un générateur est une fonction qui **pause** son exécution avec `yield` et reprend là où elle s'est arrêtée.

```python
# Fonction normale : charge tout en mémoire
def cent_mille_nombres():
    return list(range(100_000))   # 100 000 entiers en mémoire d'un coup

# Générateur : produit un nombre à la fois
def cent_mille_nombres_lazy():
    for i in range(100_000):
        yield i                   # pause ici, reprend au prochain appel
```

**Comment ça marche en interne :**

```python
gen = cent_mille_nombres_lazy()   # crée le générateur (ne calcule rien)

next(gen)   # 0  — avance jusqu'au premier yield
next(gen)   # 1  — avance jusqu'au deuxième yield
next(gen)   # 2
# ...
next(gen)   # StopIteration — plus rien à générer
```

En pratique, on utilise un `for` :

```python
for nombre in cent_mille_nombres_lazy():
    if nombre > 5:
        break                     # on peut arrêter quand on veut
```

---

## Cas d'usage concrets

```python
# Lire un fichier CSV ligne par ligne (sans charger tout en mémoire)
def lire_csv(chemin):
    with open(chemin) as f:
        for ligne in f:
            colonnes = ligne.strip().split(",")
            yield colonnes

# Générer une suite infinie de IDs
def generer_ids(debut=1):
    n = debut
    while True:
        yield n
        n += 1

id_gen = generer_ids()
print(next(id_gen))   # 1
print(next(id_gen))   # 2

# Pipeline de traitement de données
def lire_logs(fichier):
    with open(fichier) as f:
        yield from f              # déléguer à un autre itérable

def filtrer_erreurs(logs):
    for ligne in logs:
        if "ERROR" in ligne:
            yield ligne

def parser_ligne(logs):
    for ligne in logs:
        yield {"message": ligne.strip(), "niveau": "ERROR"}

# Combiner en pipeline :
# logs = lire_logs("app.log")
# erreurs = filtrer_erreurs(logs)
# parsed = parser_ligne(erreurs)
```

---

## Generator expressions

Comme les list comprehensions mais sans créer toute la liste :

```python
# List comprehension — crée la liste entière en mémoire
carres_liste = [n ** 2 for n in range(1_000_000)]

# Generator expression — calcule à la demande (parenthèses au lieu de [])
carres_gen = (n ** 2 for n in range(1_000_000))

# Utilisation directe dans sum() — jamais de liste complète en mémoire
somme = sum(n ** 2 for n in range(1_000_000))
```

---

## Context Managers : gérer les ressources proprement

Le `with` garantit que les ressources sont libérées, même si une exception se produit.

```python
# Sans context manager — dangereux
f = open("fichier.txt")
data = f.read()           # si ça plante ici...
f.close()                 # ... cette ligne n'est jamais exécutée !

# Avec context manager — toujours fermé
with open("fichier.txt") as f:
    data = f.read()
# f.close() est appelé automatiquement ici, même en cas d'exception
```

**Comment Python gère `with` :**
```python
# with expr as var: bloc
# est équivalent à :
var = expr.__enter__()
try:
    bloc
finally:
    expr.__exit__(...)    # toujours appelé
```

---

## Créer son propre context manager

**Méthode 1 : classe avec `__enter__` et `__exit__`**

```python
class Chronometre:
    def __enter__(self):
        import time
        self._debut = time.time()
        return self            # accessible via "as"

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        self.duree = time.time() - self._debut
        print(f"Durée : {self.duree:.3f}s")
        return False           # False = ne pas supprimer les exceptions

with Chronometre() as c:
    time.sleep(0.1)
# Affiche : "Durée : 0.100s"
print(c.duree)   # accessible après
```

**Méthode 2 : `@contextmanager` (plus simple)**

```python
from contextlib import contextmanager
import time

@contextmanager
def chronometre(label):
    debut = time.time()
    yield                          # ← le bloc "with" s'exécute ici
    print(f"{label}: {time.time() - debut:.3f}s")

with chronometre("requête DB"):
    time.sleep(0.05)
# Affiche : "requête DB: 0.050s"
```

---

## Dans Django : transactions

Le context manager le plus important en Django :

```python
from django.db import transaction

with transaction.atomic():
    commande = Commande.objects.create(utilisateur=user, total=99.99)
    for item in panier:
        ArticleCommande.objects.create(commande=commande, produit=item)
    # Si une exception se produit n'importe où ici :
    # → toutes les opérations DB sont annulées (rollback)
    # → la commande ET les articles sont supprimés
```

---

## `yield from` — déléguer à un sous-générateur

```python
def premiers():
    yield 2
    yield 3
    yield 5

def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

def sequences_combinees():
    yield from premiers()       # délègue à premiers()
    yield from fibonacci()      # puis délègue à fibonacci()

gen = sequences_combinees()
print(next(gen))   # 2
print(next(gen))   # 3
print(next(gen))   # 5
print(next(gen))   # 0  (fibonacci commence)
```
