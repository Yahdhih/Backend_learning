"""
Jour 23 — Django ORM : QuerySets, filter, exclude, get
Exercice en Python pur : implémenter une mini classe QuerySet
sans Django ni base de données.

Objectif : comprendre ce que fait Django ORM "sous le capot"
en implémentant nous-mêmes les mécanismes de base.
"""


# ============================================================
# DONNÉES DE TEST (simulent une base de données)
# ============================================================

USERS_DATA = [
    {"id": 1, "name": "Alice Martin",   "email": "alice@example.com",   "is_active": True,  "score": 95},
    {"id": 2, "name": "Bob Dupont",     "email": "bob@example.com",     "is_active": True,  "score": 72},
    {"id": 3, "name": "Charlie Morin",  "email": "charlie@example.com", "is_active": True,  "score": 88},
    {"id": 4, "name": "Diana Prince",   "email": "diana@example.com",   "is_active": False, "score": 60},
    {"id": 5, "name": "Eve Lambert",    "email": "eve@example.com",     "is_active": True,  "score": 45},
    {"id": 6, "name": "Frank Leclerc",  "email": "frank@example.com",   "is_active": False, "score": 83},
    {"id": 7, "name": "Alice Dupont",   "email": "alice2@example.com",  "is_active": True,  "score": 91},
]

PRODUCTS_DATA = [
    {"id": 1, "name": "Laptop Pro",          "category": "Electronics", "price": 1299.99, "stock": 15},
    {"id": 2, "name": "Wireless Mouse",      "category": "Electronics", "price":   49.99, "stock": 50},
    {"id": 3, "name": "Mechanical Keyboard", "category": "Electronics", "price":  129.99, "stock": 30},
    {"id": 4, "name": "Python Book",         "category": "Books",       "price":   39.99, "stock": 100},
    {"id": 5, "name": "Django Book",         "category": "Books",       "price":   44.99, "stock": 80},
    {"id": 6, "name": "Standing Desk",       "category": "Furniture",   "price":  599.99, "stock":  8},
    {"id": 7, "name": "Office Chair",        "category": "Furniture",   "price":  349.99, "stock": 12},
    {"id": 8, "name": "USB Hub",             "category": "Electronics", "price":   29.99, "stock": 60},
]


# ============================================================
# PARTIE 1 : Mini QuerySet — À COMPLÉTER
# ============================================================

class MiniQuerySet:
    """
    Implémentation simplifiée d'un QuerySet Django.
    Supporte : filter(), exclude(), order_by(), count(),
               exists(), first(), last(), values(), values_list(),
               slicing, itération.
    """

    def __init__(self, data: list[dict]):
        """
        data : liste de dicts (simule les lignes d'une table).
        _filters et _excludes contiennent des conditions à appliquer.
        L'évaluation est LAZY : les filtres ne sont appliqués
        qu'au moment où on accède aux données.
        """
        self._data = data                  # données brutes
        self._filters: list[dict] = []     # conditions inclusives
        self._excludes: list[dict] = []    # conditions exclusives
        self._order_by_fields: list[str] = []
        self._fields: list[str] | None = None   # pour values()
        self._flat: bool = False           # pour values_list(flat=True)
        self._values_list_mode: bool = False
        self._limit: int | None = None
        self._offset: int = 0
        self._evaluated: list | None = None   # cache du résultat

    def _clone(self) -> "MiniQuerySet":
        """Crée une copie du QuerySet (pour préserver l'immuabilité)."""
        new = MiniQuerySet(self._data)
        new._filters = list(self._filters)
        new._excludes = list(self._excludes)
        new._order_by_fields = list(self._order_by_fields)
        new._fields = self._fields
        new._flat = self._flat
        new._values_list_mode = self._values_list_mode
        new._limit = self._limit
        new._offset = self._offset
        return new

    def _matches(self, row: dict, conditions: dict) -> bool:
        """
        Vérifie si une ligne satisfait toutes les conditions.
        Supporte les lookups Django : __gt, __lt, __gte, __lte,
        __contains, __icontains, __startswith, __endswith,
        __in, __isnull, __exact (défaut).
        """
        # TODO : Implémentez cette méthode
        # Pour chaque (key, value) dans conditions :
        #   1. Séparez le nom de champ du lookup (split("__", 1))
        #      ex: "name__icontains" -> field="name", lookup="icontains"
        #      ex: "score" -> field="score", lookup="exact"
        #   2. Appliquez le lookup approprié
        #   3. Retournez False si une condition échoue
        # Retournez True si toutes les conditions passent

        # SOLUTION :
        for key, value in conditions.items():
            parts = key.split("__", 1)
            field = parts[0]
            lookup = parts[1] if len(parts) > 1 else "exact"

            if field not in row:
                return False

            field_value = row[field]

            if lookup == "exact":
                if field_value != value:
                    return False
            elif lookup == "gt":
                if not (field_value > value):
                    return False
            elif lookup == "gte":
                if not (field_value >= value):
                    return False
            elif lookup == "lt":
                if not (field_value < value):
                    return False
            elif lookup == "lte":
                if not (field_value <= value):
                    return False
            elif lookup == "in":
                if field_value not in value:
                    return False
            elif lookup == "contains":
                if str(value) not in str(field_value):
                    return False
            elif lookup == "icontains":
                if str(value).lower() not in str(field_value).lower():
                    return False
            elif lookup == "startswith":
                if not str(field_value).startswith(str(value)):
                    return False
            elif lookup == "istartswith":
                if not str(field_value).lower().startswith(str(value).lower()):
                    return False
            elif lookup == "endswith":
                if not str(field_value).endswith(str(value)):
                    return False
            elif lookup == "iendswith":
                if not str(field_value).lower().endswith(str(value).lower()):
                    return False
            elif lookup == "isnull":
                if value and field_value is not None:
                    return False
                if not value and field_value is None:
                    return False
            elif lookup == "range":
                low, high = value
                if not (low <= field_value <= high):
                    return False

        return True

    def _evaluate(self) -> list:
        """
        Applique tous les filtres, tris et limites.
        C'est ici que le "SQL" s'exécute.
        """
        if self._evaluated is not None:
            return self._evaluated

        # TODO : Implémentez l'évaluation
        # 1. Parcourir self._data
        # 2. Garder les lignes qui passent tous les self._filters
        # 3. Exclure les lignes qui passent un des self._excludes
        # 4. Trier selon self._order_by_fields
        # 5. Appliquer offset et limit
        # 6. Mettre en cache dans self._evaluated

        # SOLUTION :
        result = []
        for row in self._data:
            # Appliquer les filtres inclusifs
            if not all(self._matches(row, cond) for cond in self._filters):
                continue
            # Appliquer les exclusions
            if any(self._matches(row, cond) for cond in self._excludes):
                continue
            result.append(row)

        # Tri
        for field in reversed(self._order_by_fields):
            reverse = field.startswith("-")
            actual_field = field.lstrip("-")
            result.sort(key=lambda r: r.get(actual_field, None) or 0, reverse=reverse)

        # Offset et limit
        result = result[self._offset:]
        if self._limit is not None:
            result = result[:self._limit]

        self._evaluated = result
        return result

    def filter(self, **kwargs) -> "MiniQuerySet":
        """
        TODO : Retourne un nouveau QuerySet avec les conditions ajoutées.
        Doit être immuable : ne pas modifier self.
        """
        # SOLUTION :
        clone = self._clone()
        clone._evaluated = None
        clone._filters.append(kwargs)
        return clone

    def exclude(self, **kwargs) -> "MiniQuerySet":
        """
        TODO : Retourne un nouveau QuerySet qui exclut les lignes
        correspondant aux conditions.
        """
        # SOLUTION :
        clone = self._clone()
        clone._evaluated = None
        clone._excludes.append(kwargs)
        return clone

    def order_by(self, *fields) -> "MiniQuerySet":
        """
        TODO : Trier par les champs donnés.
        Préfixe '-' pour ordre décroissant.
        """
        # SOLUTION :
        clone = self._clone()
        clone._evaluated = None
        clone._order_by_fields = list(fields)
        return clone

    def count(self) -> int:
        """
        TODO : Retourne le nombre de résultats.
        (Ne doit pas charger tous les objets en mémoire
         dans une vraie base de données — ici on simule.)
        """
        # SOLUTION :
        return len(self._evaluate())

    def exists(self) -> bool:
        """
        TODO : Retourne True si au moins un résultat existe.
        Doit être plus efficace que count() > 0.
        """
        # SOLUTION :
        # Dans une vraie BDD : LIMIT 1 — on s'arrête au premier
        for row in self._data:
            if all(self._matches(row, cond) for cond in self._filters):
                if not any(self._matches(row, cond) for cond in self._excludes):
                    return True
        return False

    def first(self) -> dict | None:
        """
        TODO : Retourne le premier objet ou None.
        """
        # SOLUTION :
        results = self._evaluate()
        return results[0] if results else None

    def last(self) -> dict | None:
        """
        TODO : Retourne le dernier objet ou None.
        """
        # SOLUTION :
        results = self._evaluate()
        return results[-1] if results else None

    def values(self, *fields) -> "MiniQuerySet":
        """
        Retourne un QuerySet qui retourne des dicts avec seulement
        les champs spécifiés.
        """
        clone = self._clone()
        clone._fields = list(fields) if fields else None
        clone._values_list_mode = False
        return clone

    def values_list(self, *fields, flat: bool = False) -> "MiniQuerySet":
        """
        Retourne un QuerySet qui retourne des tuples.
        Si flat=True et un seul champ, retourne une liste de valeurs.
        """
        clone = self._clone()
        clone._fields = list(fields) if fields else None
        clone._flat = flat
        clone._values_list_mode = True
        return clone

    def _format_row(self, row: dict):
        """Formate une ligne selon values() / values_list()."""
        if self._fields is None:
            return row
        if self._values_list_mode:
            values = tuple(row[f] for f in self._fields)
            if self._flat and len(self._fields) == 1:
                return values[0]
            return values
        else:
            return {f: row[f] for f in self._fields}

    def __iter__(self):
        """Itération — évalue le QuerySet."""
        return iter(self._format_row(row) for row in self._evaluate())

    def __len__(self):
        return self.count()

    def __getitem__(self, key):
        results = self._evaluate()
        if isinstance(key, slice):
            sliced = results[key]
            new_qs = self._clone()
            new_qs._evaluated = sliced
            return new_qs
        return self._format_row(results[key])

    def __repr__(self):
        results = self._evaluate()
        preview = results[:3]
        suffix = "..." if len(results) > 3 else ""
        return f"<MiniQuerySet [{', '.join(str(r) for r in preview)}{suffix}]>"


# ============================================================
# PARTIE 2 : Manager (simule User.objects)
# ============================================================

class Manager:
    """Simule le manager Django (User.objects)."""

    def __init__(self, data: list[dict]):
        self._data = data

    def all(self) -> MiniQuerySet:
        return MiniQuerySet(self._data)

    def filter(self, **kwargs) -> MiniQuerySet:
        return self.all().filter(**kwargs)

    def exclude(self, **kwargs) -> MiniQuerySet:
        return self.all().exclude(**kwargs)

    def get(self, **kwargs) -> dict:
        results = self.filter(**kwargs)._evaluate()
        if len(results) == 0:
            raise LookupError("DoesNotExist: aucun objet trouvé")
        if len(results) > 1:
            raise LookupError("MultipleObjectsReturned: plusieurs objets trouvés")
        return results[0]


# Simuler les "managers" Django
class UserObjects:
    objects = Manager(USERS_DATA)

class ProductObjects:
    objects = Manager(PRODUCTS_DATA)


# ============================================================
# EXERCICES
# ============================================================

def exercice_1_filter_basique():
    """
    TODO : Utilisez UserObjects.objects pour répondre aux questions.

    1a. Obtenez tous les utilisateurs actifs.
    1b. Obtenez les utilisateurs dont le score est supérieur à 80.
    1c. Obtenez les utilisateurs inactifs triés par nom.
    """
    print("\n--- EXERCICE 1 : filter() basique ---")

    # 1a. TODO : utilisateurs actifs
    # qs_1a = UserObjects.objects.filter(???)
    # SOLUTION :
    qs_1a = UserObjects.objects.filter(is_active=True)
    print(f"  1a : {qs_1a.count()} utilisateurs actifs")
    for u in qs_1a:
        print(f"       - {u['name']}")

    # 1b. TODO : score > 80
    # qs_1b = UserObjects.objects.filter(???)
    # SOLUTION :
    qs_1b = UserObjects.objects.filter(score__gt=80)
    print(f"\n  1b : {qs_1b.count()} utilisateurs avec score > 80")
    for u in qs_1b:
        print(f"       - {u['name']} (score: {u['score']})")

    # 1c. TODO : inactifs triés par nom
    # qs_1c = UserObjects.objects.filter(???).order_by(???)
    # SOLUTION :
    qs_1c = UserObjects.objects.filter(is_active=False).order_by("name")
    print(f"\n  1c : {qs_1c.count()} utilisateurs inactifs")
    for u in qs_1c:
        print(f"       - {u['name']}")


def exercice_2_exclude_et_lookups():
    """
    TODO : Utilisez exclude() et les lookups avancés.

    2a. Excluez les utilisateurs dont le nom contient "Alice".
    2b. Trouvez les produits dont le nom contient "Book" (icontains).
    2c. Trouvez les produits de catégorie "Electronics" ou "Books"
        avec price__in ou en combinant deux filter().
    2d. Produits dont le prix est dans l'intervalle 30-150.
    """
    print("\n--- EXERCICE 2 : exclude() et lookups ---")

    # 2a. TODO
    # SOLUTION :
    qs_2a = UserObjects.objects.exclude(name__icontains="Alice")
    print(f"  2a : {qs_2a.count()} utilisateurs sans 'Alice' dans le nom")

    # 2b. TODO
    # SOLUTION :
    qs_2b = ProductObjects.objects.filter(name__icontains="book")
    print(f"  2b : {qs_2b.count()} produits contenant 'book'")
    for p in qs_2b:
        print(f"       - {p['name']}")

    # 2c. TODO (hint: pour "ou", vous pouvez faire deux filter séparés
    #     et combiner manuellement les résultats, ou implémenter __in sur category)
    # SOLUTION :
    qs_2c = ProductObjects.objects.filter(category__in=["Electronics", "Books"])
    print(f"  2c : {qs_2c.count()} produits Electronics ou Books")

    # 2d. TODO
    # SOLUTION :
    qs_2d = ProductObjects.objects.filter(price__range=(30, 150))
    print(f"  2d : {qs_2d.count()} produits entre 30 et 150€")
    for p in qs_2d.order_by("price"):
        print(f"       - {p['name']} ({p['price']}€)")


def exercice_3_count_exists_first():
    """
    TODO : Utilisez count(), exists(), first(), last().

    3a. Vérifiez si un utilisateur avec l'email "alice@example.com" existe.
    3b. Comptez les produits avec un stock inférieur à 20.
    3c. Trouvez le produit le moins cher (first() après order_by).
    3d. Trouvez l'utilisateur avec le score le plus élevé.
    """
    print("\n--- EXERCICE 3 : count(), exists(), first(), last() ---")

    # 3a. TODO
    # SOLUTION :
    existe = UserObjects.objects.filter(email="alice@example.com").exists()
    print(f"  3a : alice@example.com existe ? {existe}")

    # 3b. TODO
    # SOLUTION :
    nb = ProductObjects.objects.filter(stock__lt=20).count()
    print(f"  3b : {nb} produits avec stock < 20")

    # 3c. TODO
    # SOLUTION :
    moins_cher = ProductObjects.objects.order_by("price").first()
    print(f"  3c : produit le moins cher = {moins_cher['name']} ({moins_cher['price']}€)")

    # 3d. TODO
    # SOLUTION :
    top_user = UserObjects.objects.filter(is_active=True).order_by("-score").first()
    print(f"  3d : meilleur score = {top_user['name']} ({top_user['score']})")


def exercice_4_values_et_values_list():
    """
    TODO : Utilisez values() et values_list().

    4a. Récupérez seulement les noms et emails des utilisateurs actifs
        (values).
    4b. Récupérez la liste des emails (values_list flat=True).
    4c. Récupérez les tuples (name, price) des 3 produits les plus chers.
    """
    print("\n--- EXERCICE 4 : values() et values_list() ---")

    # 4a. TODO
    # SOLUTION :
    qs_4a = UserObjects.objects.filter(is_active=True).values("name", "email")
    print("  4a : noms et emails des actifs :")
    for d in qs_4a:
        print(f"       {d}")

    # 4b. TODO
    # SOLUTION :
    emails = list(UserObjects.objects.all().values_list("email", flat=True))
    print(f"\n  4b : liste des emails : {emails}")

    # 4c. TODO
    # SOLUTION :
    top3 = list(
        ProductObjects.objects.order_by("-price")[:3]
        .values_list("name", "price")
    )
    print(f"\n  4c : top 3 produits les plus chers : {top3}")


def exercice_5_get():
    """
    TODO : Utilisez get() et gérez les exceptions.

    5a. Récupérez l'utilisateur avec id=3.
    5b. Essayez de récupérer un utilisateur avec id=999 et gérez l'exception.
    5c. Essayez de récupérer un utilisateur avec name__icontains="alice"
        (plusieurs résultats) et gérez l'exception MultipleObjectsReturned.
    """
    print("\n--- EXERCICE 5 : get() et exceptions ---")

    # 5a. TODO
    # SOLUTION :
    user = UserObjects.objects.get(id=3)
    print(f"  5a : utilisateur id=3 : {user['name']}")

    # 5b. TODO
    # SOLUTION :
    try:
        UserObjects.objects.get(id=999)
    except LookupError as e:
        print(f"  5b : Exception levée : {e}")

    # 5c. TODO
    # SOLUTION :
    try:
        UserObjects.objects.get(name__icontains="alice")
    except LookupError as e:
        print(f"  5c : Exception levée : {e}")


# ============================================================
# FONCTION TESTER
# ============================================================

def tester():
    print("\n" + "="*60)
    print("   JOUR 23 — Django ORM : Mini QuerySet")
    print("="*60)

    exercice_1_filter_basique()
    exercice_2_exclude_et_lookups()
    exercice_3_count_exists_first()
    exercice_4_values_et_values_list()
    exercice_5_get()

    # --- Tests automatiques ---
    print("\n" + "="*60)
    print("   TESTS AUTOMATIQUES")
    print("="*60)

    tests_passes = 0
    tests_total = 0

    def ok(description: str, condition: bool):
        nonlocal tests_passes, tests_total
        tests_total += 1
        if condition:
            print(f"  OK  {description}")
            tests_passes += 1
        else:
            print(f"  !!  {description}")

    qs = MiniQuerySet(USERS_DATA)

    # Test filter()
    ok("filter(is_active=True) retourne 5 utilisateurs",
       qs.filter(is_active=True).count() == 5)

    ok("filter(score__gt=80) retourne 4 utilisateurs",
       qs.filter(score__gt=80).count() == 4)

    ok("filter(score__gte=95) retourne 1 utilisateur",
       qs.filter(score__gte=95).count() == 1)

    # Test exclude()
    ok("exclude(is_active=False) retourne 5 utilisateurs",
       qs.exclude(is_active=False).count() == 5)

    ok("exclude(name__icontains='alice') exclut 2 Alice",
       qs.exclude(name__icontains="alice").count() == 5)

    # Test order_by()
    premier = qs.order_by("score").first()
    ok("order_by('score').first() retourne le score le plus bas",
       premier is not None and premier["score"] == 45)

    dernier = qs.order_by("score").last()
    ok("order_by('score').last() retourne le score le plus haut",
       dernier is not None and dernier["score"] == 95)

    # Test exists()
    ok("filter(id=1).exists() = True",
       qs.filter(id=1).exists())

    ok("filter(id=999).exists() = False",
       not qs.filter(id=999).exists())

    # Test count()
    ok("count() total = 7",
       qs.count() == 7)

    # Test slicing
    tranche = qs.order_by("id")[:3]
    ok("slice [:3] retourne 3 éléments",
       len(list(tranche)) == 3)

    # Test values()
    vals = list(qs.filter(id=1).values("name", "email"))
    ok("values('name', 'email') retourne un dict avec 2 clés",
       len(vals) == 1 and set(vals[0].keys()) == {"name", "email"})

    # Test values_list(flat=True)
    noms = list(qs.filter(is_active=True).values_list("name", flat=True))
    ok("values_list('name', flat=True) retourne une liste de strings",
       all(isinstance(n, str) for n in noms))

    # Test lookups
    ok("name__icontains='alice' trouve 2 utilisateurs",
       qs.filter(name__icontains="alice").count() == 2)

    ok("score__range=(60, 90) filtre correctement",
       qs.filter(score__range=(60, 90)).count() == 4)

    ok("name__startswith='Alice' trouve 2 Alice",
       qs.filter(name__startswith="Alice").count() == 2)

    ok("email__endswith='@example.com' trouve tous",
       qs.filter(email__endswith="@example.com").count() == 7)

    # Test immuabilité
    original = qs.filter(is_active=True)
    _ = original.filter(score__gt=80)
    ok("QuerySet est immuable (filter ne modifie pas l'original)",
       original.count() == 5)

    # Test get()
    manager = Manager(USERS_DATA)
    user1 = manager.get(id=1)
    ok("get(id=1) retourne Alice", user1["name"] == "Alice Martin")

    try:
        manager.get(id=999)
        ok("get(id=999) lève une exception", False)
    except LookupError:
        ok("get(id=999) lève LookupError (DoesNotExist)", True)

    try:
        manager.get(name__icontains="alice")
        ok("get avec plusieurs résultats lève une exception", False)
    except LookupError:
        ok("get avec plusieurs résultats lève LookupError (MultipleObjectsReturned)", True)

    print(f"\n  Résultat : {tests_passes}/{tests_total} tests passés")


if __name__ == "__main__":
    tester()
