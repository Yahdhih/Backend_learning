# Jour 06 — Python : classes et OOP
📅 2 juillet 2026 · Module : Python

---

## Les classes en Python

Une classe est un modèle pour créer des objets. En Python, tout est objet.

```python
class Utilisateur:
    # Variable de classe (partagée par toutes les instances)
    nombre_total = 0

    def __init__(self, nom: str, email: str):
        # Variables d'instance (propres à chaque objet)
        self.nom = nom
        self.email = email
        self.actif = True
        Utilisateur.nombre_total += 1

    # Méthode d'instance (reçoit self = l'objet lui-même)
    def desactiver(self):
        self.actif = False

    # Méthode de classe (reçoit cls = la classe, pas l'instance)
    @classmethod
    def depuis_dict(cls, data: dict) -> "Utilisateur":
        return cls(data["nom"], data["email"])

    # Méthode statique (pas d'accès à l'instance ni à la classe)
    @staticmethod
    def est_email_valide(email: str) -> bool:
        return "@" in email and "." in email

    # Représentation en chaîne (pour print() et debug)
    def __repr__(self) -> str:
        return f"Utilisateur(nom={self.nom!r}, email={self.email!r})"


# Créer des instances
alice = Utilisateur("Alice", "alice@exemple.com")
bob = Utilisateur.depuis_dict({"nom": "Bob", "email": "bob@exemple.com"})

print(alice)                          # Utilisateur(nom='Alice', email='alice@exemple.com')
print(Utilisateur.nombre_total)       # 2
print(Utilisateur.est_email_valide("test@test.com"))  # True
```

---

## Héritage

```python
class Administrateur(Utilisateur):
    def __init__(self, nom, email, permissions):
        super().__init__(nom, email)      # appel au __init__ parent
        self.permissions = permissions

    def a_permission(self, perm: str) -> bool:
        return perm in self.permissions

    def __repr__(self) -> str:
        return f"Administrateur(nom={self.nom!r}, permissions={self.permissions})"


admin = Administrateur("Admin", "admin@exemple.com", ["lire", "écrire", "supprimer"])
print(admin.a_permission("supprimer"))  # True
print(isinstance(admin, Utilisateur))   # True — un Admin EST un Utilisateur
```

---

## Les méthodes dunder (magic methods)

Les méthodes `__nom__` permettent de définir comment tes objets se comportent avec les opérateurs Python.

```python
class Vecteur:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):                          # repr(v) ou print(v)
        return f"Vecteur({self.x}, {self.y})"

    def __add__(self, autre):                    # v1 + v2
        return Vecteur(self.x + autre.x, self.y + autre.y)

    def __sub__(self, autre):                    # v1 - v2
        return Vecteur(self.x - autre.x, self.y - autre.y)

    def __mul__(self, scalaire):                 # v * 3
        return Vecteur(self.x * scalaire, self.y * scalaire)

    def __eq__(self, autre):                     # v1 == v2
        return self.x == autre.x and self.y == autre.y

    def __len__(self):                           # len(v)
        return 2

    def __getitem__(self, index):                # v[0], v[1]
        return (self.x, self.y)[index]

    def __iter__(self):                          # for coord in v:
        yield self.x
        yield self.y

    def __bool__(self):                          # if v:
        return self.x != 0 or self.y != 0

    def __abs__(self):                           # abs(v) — longueur
        return (self.x ** 2 + self.y ** 2) ** 0.5


v1 = Vecteur(1, 2)
v2 = Vecteur(3, 4)
print(v1 + v2)          # Vecteur(4, 6)
print(v1 * 3)           # Vecteur(3, 6)
print(list(v1))         # [1, 2]
print(abs(v2))          # 5.0
```

---

## Propriétés avec @property

`@property` permet de définir des attributs calculés avec validation :

```python
class Cercle:
    def __init__(self, rayon: float):
        self._rayon = rayon    # convention: _ = "privé"

    @property
    def rayon(self) -> float:
        return self._rayon

    @rayon.setter
    def rayon(self, valeur: float):
        if valeur < 0:
            raise ValueError("Le rayon doit être positif")
        self._rayon = valeur

    @property
    def aire(self) -> float:           # propriété calculée (pas de setter)
        import math
        return math.pi * self._rayon ** 2


c = Cercle(5)
print(c.rayon)    # 5    — appelle le getter
print(c.aire)     # 78.5 — calculé à la volée
c.rayon = 10      # appelle le setter
c.rayon = -1      # ValueError !
```

---

## Dataclasses (Python 3.7+)

Pour les classes qui stockent principalement des données :

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class Produit:
    nom: str
    prix: float
    tags: List[str] = field(default_factory=list)

    def prix_ttc(self, taux=0.20) -> float:
        return self.prix * (1 + taux)


p = Produit("Livre Python", 29.99, ["programmation", "python"])
print(p)              # Produit(nom='Livre Python', prix=29.99, tags=[...])
print(p.prix_ttc())   # 35.99
```

`@dataclass` génère automatiquement `__init__`, `__repr__`, et `__eq__`.

---

## Pourquoi c'est important pour Django

Django Models ressemblent exactement à des classes Python avec des dunder methods :

```python
# Ce que tu écriras en Django
class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):    # utilisé dans l'admin Django
        return self.titre

    class Meta:           # configuration de la classe
        ordering = ["-date_creation"]
```
