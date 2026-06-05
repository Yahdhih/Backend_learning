# Module 04 — Django Fundamentals

> Now that you know what happens before Django runs, let's build with it.

---

## Learning Objectives

- Set up a Django project from scratch
- Understand the MTV pattern
- Route URLs to views
- Build function-based and class-based views
- Use Django's ORM to model data
- Write and run migrations

---

## 1. The MTV Pattern

Django uses MTV — Model, Template, View. (It's MVC in disguise — Django's "View" is the Controller.)

```
HTTP Request
     │
     ▼
 URLconf (urls.py)
     │  matches /users → views.list_users
     ▼
 View (views.py)  ←──────────→ Model (models.py)
     │  business logic              talk to the database
     │  builds context
     ▼
 Template (templates/)
     │  renders HTML (or skipped for APIs)
     ▼
HTTP Response
```

For APIs (what you'll build most of), Templates are skipped — views return JSON directly.

---

## 2. Project Setup

```bash
# Install Django
pip install django

# Create a project (the container)
django-admin startproject myproject .
# The . means "create in current directory, not a subdirectory"

# Create an app (a module inside the project)
python manage.py startapp api

# Run the dev server
python manage.py runserver
```

**Project vs App:**
- **Project** = the whole site (`settings.py`, root `urls.py`)
- **App** = a self-contained module (`models.py`, `views.py`, `urls.py`)

A project can have many apps. Apps are reusable across projects.

```
myproject/
├── manage.py              ← CLI tool
├── myproject/             ← project package
│   ├── settings.py        ← all configuration
│   ├── urls.py            ← root URL config
│   ├── wsgi.py            ← WSGI entry point
│   └── asgi.py            ← ASGI entry point (async)
└── api/                   ← your app
    ├── models.py          ← database models
    ├── views.py           ← request handlers
    ├── urls.py            ← app URL config
    ├── admin.py           ← admin site config
    ├── apps.py            ← app config
    └── migrations/        ← database schema versions
```

---

## 3. URL Routing

Root `urls.py` routes to each app. Each app has its own `urls.py`.

```python
# myproject/urls.py
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),        # delegate to api app
]

# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("users/", views.list_users),                  # /api/users/
    path("users/<int:pk>/", views.get_user),           # /api/users/42/
    path("users/<str:username>/", views.by_username),  # /api/users/alice/
]
```

URL converters:
- `<int:pk>` — matches digits, captured as integer named `pk`
- `<str:name>` — matches any path segment, as string
- `<slug:slug>` — letters, numbers, hyphens, underscores
- `<uuid:id>` — UUID format
- `<path:rest>` — matches anything including slashes

---

## 4. Views

A view receives a `HttpRequest` and must return an `HttpResponse`.

```python
# api/views.py
from django.http import HttpResponse, JsonResponse
from django.views import View

# Function-based view (FBV)
def list_users(request):
    if request.method == "GET":
        users = list(User.objects.values("id", "name", "email"))
        return JsonResponse({"users": users})

    elif request.method == "POST":
        import json
        data = json.loads(request.body)
        user = User.objects.create(name=data["name"], email=data["email"])
        return JsonResponse({"id": user.id}, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


# Class-based view (CBV)
class UserListView(View):
    def get(self, request):
        users = list(User.objects.values("id", "name", "email"))
        return JsonResponse({"users": users})

    def post(self, request):
        import json
        data = json.loads(request.body)
        user = User.objects.create(**data)
        return JsonResponse({"id": user.id}, status=201)
```

The `HttpRequest` object Django gives your view:

```python
request.method          # "GET", "POST", etc.
request.path            # "/api/users/"
request.GET             # QueryDict of ?query=params
request.POST            # QueryDict of form data
request.body            # raw bytes (use for JSON)
request.headers         # dict-like headers (lowercase)
request.user            # authenticated user (or AnonymousUser)
request.session         # session dict
request.COOKIES         # dict of cookies
request.META            # raw WSGI environ
```

---

## 5. Models

Models are Python classes that map to database tables.

```python
# api/models.py
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]           # default ordering
        db_table = "users"                   # custom table name

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,           # if user deleted, delete their posts
        related_name="posts",               # user.posts.all()
    )
    published_at = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField("Tag", blank=True)

    def __str__(self):
        return self.title
```

**Field types:**

| Field | Python type | SQL type |
|-------|-------------|----------|
| CharField | str | VARCHAR |
| TextField | str | TEXT |
| IntegerField | int | INTEGER |
| FloatField | float | REAL |
| BooleanField | bool | BOOLEAN |
| DateTimeField | datetime | TIMESTAMP |
| EmailField | str | VARCHAR with validation |
| JSONField | dict/list | JSONB (Postgres) |
| ForeignKey | Model | INTEGER + FK constraint |
| ManyToManyField | QuerySet | junction table |
| OneToOneField | Model | INTEGER + UNIQUE FK |

---

## 6. Migrations

Migrations are version-controlled database schema changes.

```bash
# After changing models.py, generate a migration
python manage.py makemigrations

# Apply all pending migrations to the database
python manage.py migrate

# See migration history
python manage.py showmigrations

# See the SQL a migration would run
python manage.py sqlmigrate api 0001
```

A migration file looks like:

```python
# api/migrations/0001_initial.py
class Migration(migrations.Migration):
    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
                ("email", models.EmailField(unique=True)),
            ],
        ),
    ]
```

Each migration is a list of operations. Django tracks which ones have run in a `django_migrations` table.

---

## 7. The Django ORM Basics

```python
# Create
user = User(name="Alice", email="alice@test.com")
user.save()

# Shortcut: create + save in one step
user = User.objects.create(name="Alice", email="alice@test.com")

# Read all
User.objects.all()

# Filter
User.objects.filter(is_active=True)
User.objects.filter(name__startswith="A")   # field lookups
User.objects.filter(age__gte=18)            # gte = greater than or equal

# Get one (raises if 0 or multiple)
User.objects.get(id=1)
User.objects.get(email="alice@test.com")

# Update
User.objects.filter(id=1).update(name="Alice Updated")

# Delete
User.objects.filter(is_active=False).delete()

# Count
User.objects.filter(is_active=True).count()

# Order
User.objects.order_by("name")
User.objects.order_by("-created_at")    # - = descending

# Limit
User.objects.all()[:10]         # first 10
User.objects.all()[10:20]       # 11th to 20th
```

---

## Exercises

Complete all exercises in the exercises/ directory.

1. [Exercise 01 — First Django Project](exercises/01_first_project.md)
2. [Exercise 02 — URL Routing & Views](exercises/02_routing_and_views.md)
3. [Exercise 03 — Models and ORM](exercises/03_models_and_orm.md)

---

## Next → [Module 05: Databases & The ORM](../05_databases_and_orm/README.md)
