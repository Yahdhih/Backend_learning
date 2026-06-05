"""
Exercise 02 — OOP in Python

Build a mini model system that mimics how Django's ORM works internally.
This will make Django's models feel familiar rather than magical.

Run with: python3 02_oop_python.py
"""

from datetime import datetime
from typing import Any, Optional


# ─── PART 1: Build a Field class ─────────────────────────────────────────────
#
# In Django, you write:
#   class User(Model):
#       name = CharField(max_length=100)
#       age  = IntegerField()
#
# Each "CharField" is a descriptor — an object that knows how to get/set
# a value on another object.
#
# Build a simplified Field class below.

class Field:
    """
    A descriptor that stores typed values.

    Usage:
        class Person:
            name = Field(str, required=True)
            age  = Field(int, default=0)

        p = Person()
        p.name = "Alice"
        p.age = 30
        p.name  # "Alice"
    """

    def __init__(self, field_type: type, required: bool = False, default=None):
        self.field_type = field_type
        self.required = required
        self.default = default
        self.name = None  # set by ModelMeta below

    def __set_name__(self, owner, name):
        # Python calls this when the class is defined
        # It gives the descriptor access to its own attribute name
        self.name = name
        self.storage_key = f"_field_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self  # accessing on class returns the Field itself
        return getattr(obj, self.storage_key, self.default)

    def __set__(self, obj, value):
        if value is not None and not isinstance(value, self.field_type):
            try:
                value = self.field_type(value)  # try to coerce the type
            except (ValueError, TypeError):
                raise TypeError(
                    f"Field '{self.name}' expects {self.field_type.__name__}, "
                    f"got {type(value).__name__}"
                )
        setattr(obj, self.storage_key, value)


# ─── PART 2: Build a Model base class ────────────────────────────────────────
#
# Django models inherit from Model and get features like:
#   - .save() — writes to database (we'll fake it with a list)
#   - .delete()
#   - Model.objects.all()
#   - Model.objects.filter(name="Alice")
#   - __repr__ and __str__
#
# Build a simplified version below.

class Manager:
    """Mimics Django's Model.objects"""

    def __init__(self):
        self._store: list = []

    def all(self) -> list:
        """Return all saved instances."""
        return list(self._store)

    def filter(self, **kwargs) -> list:
        """
        Return instances where all kwargs match.

        Manager().filter(name="Alice", active=True)
        """
        # YOUR CODE HERE
        pass

    def get(self, **kwargs):
        """
        Return exactly one matching instance.
        Raise ValueError if 0 or more than 1 found.
        """
        # YOUR CODE HERE
        pass

    def count(self) -> int:
        return len(self._store)

    def _add(self, instance):
        self._store.append(instance)

    def _remove(self, instance):
        self._store.remove(instance)


class Model:
    """Base class that all our models will inherit from."""

    objects: Manager  # each subclass gets its own Manager

    def __init_subclass__(cls, **kwargs):
        """Called when a subclass is defined. Give it its own Manager."""
        super().__init_subclass__(**kwargs)
        cls.objects = Manager()
        cls._next_id = 1

    def save(self):
        """
        'Save' to our fake in-memory database.
        If the object has no id, assign one and add to store.
        If it already has an id, it's already in the store (update in place).
        """
        if not hasattr(self, "_id") or self._id is None:
            self._id = self.__class__._next_id
            self.__class__._next_id += 1
            self.__class__.objects._add(self)
        # In a real ORM this would run an INSERT or UPDATE SQL query
        return self

    def delete(self):
        """Remove from the store."""
        self.__class__.objects._remove(self)
        self._id = None

    @property
    def id(self):
        return getattr(self, "_id", None)

    def __repr__(self):
        fields = {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_")
        }
        field_str = ", ".join(f"{k}={v!r}" for k, v in fields.items())
        return f"{self.__class__.__name__}(id={self.id}, {field_str})"


# ─── PART 3: Define some Models ──────────────────────────────────────────────
#
# Now use your Field and Model to define real models.

class User(Model):
    name = Field(str, required=True)
    email = Field(str, required=True)
    age = Field(int, default=0)
    is_active = Field(bool, default=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Post(Model):
    title = Field(str, required=True)
    content = Field(str, default="")
    published = Field(bool, default=False)
    # In a real ORM, this would be a ForeignKey
    author_id = Field(int)

    def author(self) -> Optional[User]:
        """Find the user who wrote this post."""
        if self.author_id is None:
            return None
        results = User.objects.filter(id=self.author_id)  # won't work yet — fix filter()
        return results[0] if results else None


# ─── PART 4: Validation ───────────────────────────────────────────────────────

class ValidationError(Exception):
    pass


def validate(instance: Model) -> None:
    """
    Check all required Fields on the instance have a value.
    Raise ValidationError listing which fields are missing.

    Hint: look through the class's __dict__ for Field instances,
    check if they're required, then check the instance's value.
    """
    # YOUR CODE HERE
    pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name}")
            print(f"    Expected: {expected!r}")
            print(f"    Got:      {actual!r}")
            failed += 1

    def check_raises(name, fn, exception_type):
        nonlocal passed, failed
        try:
            fn()
            print(f"  ✗ {name} (no exception raised)")
            failed += 1
        except exception_type:
            print(f"  ✓ {name}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {name} (wrong exception: {e})")
            failed += 1

    print("\n─── Part 1: Fields ───")
    u = User()
    u.name = "Alice"
    u.age = "30"  # should coerce to int
    check("field get", u.name, "Alice")
    check("field type coercion", u.age, 30)
    check("field default", u.is_active, True)
    check_raises("field wrong type", lambda: setattr(u, "age", "notanumber"), TypeError)

    print("\n─── Part 2: Manager ───")
    # Clear any leftover state
    User.objects._store.clear()
    User._next_id = 1

    alice = User()
    alice.name = "Alice"
    alice.email = "alice@test.com"
    alice.age = 30
    alice.save()

    bob = User()
    bob.name = "Bob"
    bob.email = "bob@test.com"
    bob.age = 25
    bob.save()

    carol = User()
    carol.name = "Carol"
    carol.email = "carol@test.com"
    carol.age = 30
    carol.save()

    check("auto-id alice", alice.id, 1)
    check("auto-id bob", bob.id, 2)
    check("all count", User.objects.count(), 3)
    check("filter by age", len(User.objects.filter(age=30)), 2)
    check("filter by name", User.objects.filter(name="Bob")[0].email, "bob@test.com")

    try:
        check("get by name", User.objects.get(name="Alice").id, 1)
    except Exception as e:
        print(f"  ✗ get by name (error: {e})")
        failed += 1
        passed -= 1

    check_raises("get too many", lambda: User.objects.get(age=30), ValueError)
    check_raises("get none", lambda: User.objects.get(name="Nobody"), ValueError)

    print("\n─── Part 3: Delete ───")
    bob.delete()
    check("after delete count", User.objects.count(), 2)
    check("deleted id is None", bob.id, None)

    print("\n─── Part 4: Validation ───")
    incomplete = User()
    incomplete.name = "Dan"
    # email is required but not set
    check_raises("validate missing field", lambda: validate(incomplete), ValidationError)

    complete = User()
    complete.name = "Eve"
    complete.email = "eve@test.com"
    try:
        validate(complete)
        print("  ✓ validate passes for complete model")
        passed += 1
    except ValidationError as e:
        print(f"  ✗ validate passes for complete model: {e}")
        failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")


if __name__ == "__main__":
    run_tests()
