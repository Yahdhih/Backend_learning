# Module 01 — Python Crash Course

> You already know how to program. This module teaches you Python's unique patterns — the ones you'll see everywhere in Django.

---

## Learning Objectives

- Read and write Python fluently
- Understand decorators (Django uses them constantly)
- Use list/dict comprehensions
- Understand Python's type system (dynamic but not loose)
- Use generators and `yield`
- Understand `*args` and `**kwargs`
- Grasp basic async/await

---

## 1. Python Syntax at a Glance

If you know C/Java/JavaScript, here's what's different:

```python
# No semicolons, no braces — indentation IS the structure
def greet(name: str) -> str:
    if name:
        return f"Hello, {name}!"
    else:
        return "Hello, stranger!"

# Calling it
result = greet("Alice")  # "Hello, Alice!"

# f-strings (like template literals in JS)
age = 30
print(f"Alice is {age} years old")         # "Alice is 30 years old"
print(f"In 10 years: {age + 10}")          # "In 10 years: 40"
print(f"Uppercase: {name.upper()!r}")      # Expressions work inside {}
```

---

## 2. Python's Core Data Types

```python
# Strings — immutable
s = "hello"
s.upper()    # "HELLO" — returns new string, s unchanged
s[0]         # "h"
s[-1]        # "o" — negative indexing
s[1:3]       # "el" — slicing

# Lists — mutable, ordered
numbers = [1, 2, 3, 4, 5]
numbers.append(6)       # [1, 2, 3, 4, 5, 6]
numbers.pop()           # removes and returns 6
numbers[0]              # 1
numbers[-1]             # 5
numbers[1:3]            # [2, 3]

# Tuples — immutable lists (use for coordinates, RGB, records)
point = (10, 20)
x, y = point            # unpacking

# Dicts — key-value pairs (like objects in JS, HashMaps in Java)
user = {"id": 1, "name": "Alice", "active": True}
user["name"]            # "Alice"
user.get("email")       # None (no KeyError)
user.get("email", "")   # "" (default)
user.keys()             # dict_keys(['id', 'name', 'active'])
user.items()            # dict_items([('id', 1), ('name', 'Alice'), ...])

# Sets — unordered, unique values
tags = {"python", "django", "python"}  # {"python", "django"}

# None (Python's null/nil/undefined)
x = None
if x is None:           # use "is None", not "== None"
    print("empty")
```

---

## 3. Functions

```python
# Basic function
def add(a, b):
    return a + b

# Default arguments
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"

greet("Alice")           # "Hello, Alice!"
greet("Alice", "Hi")     # "Hi, Alice!"

# *args — variable positional arguments (tuple)
def sum_all(*numbers):
    return sum(numbers)

sum_all(1, 2, 3, 4)      # 10

# **kwargs — variable keyword arguments (dict)
def build_url(host, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{host}?{query}" if query else host

build_url("api.com/users", page=2, limit=10)
# "api.com/users?page=2&limit=10"

# Combining all
def everything(required, *args, default="x", **kwargs):
    print(required, args, default, kwargs)

everything("a", "b", "c", default="y", key="val")
# "a" ("b", "c") "y" {"key": "val"}
```

---

## 4. List & Dict Comprehensions

These are extremely common in Django views and serializers.

```python
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# List comprehension: [expression for item in iterable if condition]
squares = [n ** 2 for n in numbers]
# [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]

evens = [n for n in numbers if n % 2 == 0]
# [2, 4, 6, 8, 10]

even_squares = [n ** 2 for n in numbers if n % 2 == 0]
# [4, 16, 36, 64, 100]

# Dict comprehension
users = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
user_map = {u["id"]: u["name"] for u in users}
# {1: "Alice", 2: "Bob"}

# In Django you'll see patterns like:
data = {field: getattr(obj, field) for field in ["id", "name", "email"]}
```

---

## 5. Decorators — The Most Important Python Concept for Django

Decorators are functions that **wrap** other functions to add behavior. Django uses them everywhere:

```python
# @login_required   — check user is logged in
# @permission_required("admin")
# @cache_page(60)   — cache this view for 60 seconds
# @csrf_exempt      — skip CSRF check
```

Here's how they work from first principles:

```python
# A decorator is just a function that takes a function and returns a function

def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before the function runs")
        result = func(*args, **kwargs)          # call the original function
        print("After the function runs")
        return result
    return wrapper

# The @ syntax is just shorthand for: greet = my_decorator(greet)
@my_decorator
def greet(name):
    print(f"Hello, {name}!")

greet("Alice")
# Before the function runs
# Hello, Alice!
# After the function runs
```

**Decorators with arguments** (like `@cache_page(60)`) need an extra layer:

```python
def repeat(n):                          # outer: takes the argument
    def decorator(func):                # middle: takes the function
        def wrapper(*args, **kwargs):   # inner: the actual wrapper
            for _ in range(n):
                func(*args, **kwargs)
        return wrapper
    return decorator

@repeat(3)
def say_hi():
    print("Hi!")

say_hi()   # prints "Hi!" three times
```

**Real-world Django decorator pattern:**

```python
from functools import wraps
from django.http import JsonResponse

def require_auth(func):
    @wraps(func)    # preserves the original function's name/docs
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)
        return func(request, *args, **kwargs)
    return wrapper

@require_auth
def my_view(request):
    return JsonResponse({"user": request.user.username})
```

---

## 6. Classes

```python
class User:
    # Class variable (shared by all instances)
    count = 0

    def __init__(self, name: str, email: str):
        # Instance variables
        self.name = name
        self.email = email
        self.is_active = True
        User.count += 1

    # Instance method (receives self)
    def deactivate(self):
        self.is_active = False

    # String representation (like toString() in Java)
    def __repr__(self):
        return f"User(name={self.name!r}, email={self.email!r})"

    # Class method (receives cls, not instance)
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(data["name"], data["email"])

    # Static method (no access to class or instance)
    @staticmethod
    def is_valid_email(email: str) -> bool:
        return "@" in email


# Inheritance
class AdminUser(User):
    def __init__(self, name, email, permissions):
        super().__init__(name, email)           # call parent __init__
        self.permissions = permissions

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions
```

**Python's special (dunder) methods** — these are how Django models work:

```python
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):       # v1 + v2
        return Vector(self.x + other.x, self.y + other.y)

    def __eq__(self, other):        # v1 == v2
        return self.x == other.x and self.y == other.y

    def __len__(self):              # len(v)
        return 2

    def __getitem__(self, key):     # v[0], v[1]
        return (self.x, self.y)[key]

    def __iter__(self):             # for item in v:
        yield self.x
        yield self.y
```

---

## 7. Generators and `yield`

A generator is a function that returns values **lazily** — one at a time, on demand.

```python
# Without generator — loads everything into memory
def get_all_ids():
    return [i for i in range(1_000_000)]  # 1M items in memory at once

# With generator — yields one at a time
def get_all_ids_lazy():
    for i in range(1_000_000):
        yield i                           # pauses here, resumes on next()

# Usage
gen = get_all_ids_lazy()
next(gen)   # 0
next(gen)   # 1

# In a for loop (most common)
for id in get_all_ids_lazy():
    process(id)   # never more than 1 in memory
```

Django's QuerySets use lazy evaluation — the query doesn't run until you iterate.

---

## 8. Context Managers (`with` statement)

```python
# You've seen this with files:
with open("file.txt") as f:
    data = f.read()
# file is automatically closed here, even if an exception occurs

# In Django/databases:
with transaction.atomic():
    order = Order.objects.create(user=user)
    OrderItem.objects.create(order=order, ...)
# transaction commits on exit, rolls back if exception

# Building your own context manager
from contextlib import contextmanager

@contextmanager
def timer(label):
    import time
    start = time.time()
    yield                       # the "with" block runs here
    elapsed = time.time() - start
    print(f"{label}: {elapsed:.3f}s")

with timer("database query"):
    results = MyModel.objects.all()
```

---

## 9. Type Hints

Python is dynamically typed but supports hints. Django REST Framework uses these heavily.

```python
from typing import Optional, List, Dict, Any, Union

def get_user(user_id: int) -> Optional[dict]:
    # Returns a dict or None
    ...

def process_users(users: List[dict]) -> Dict[str, Any]:
    ...

# Python 3.10+ (preferred modern style)
def process(value: int | str | None) -> list[dict]:
    ...
```

---

## Exercises

1. [Exercise 01 — Python Basics](exercises/01_python_basics.py)
2. [Exercise 02 — Classes and OOP](exercises/02_oop_python.py)
3. [Exercise 03 — Decorators Lab](exercises/03_decorators_lab.py)

---

## Next → [Module 02: HTTP In Depth](../02_http_in_depth/README.md)
