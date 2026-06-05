# Exercise 01 — Your First Django Project

Build a Django project from scratch, step by step. Every command explained.

---

## Step 1: Environment Setup

```bash
# Create a virtual environment (isolates dependencies from your system Python)
python3 -m venv venv

# Activate it
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

# Your prompt should now show (venv)
# All packages installed here stay in this project

# Install Django
pip install django psycopg2-binary

# Verify
python -c "import django; print(django.__version__)"
```

---

## Step 2: Create the Project

```bash
# Navigate to the exercises folder
cd modules/04_django_fundamentals/exercises/

# Create the project (the . keeps it flat, not nested)
django-admin startproject blog_project .

# You now have:
# manage.py
# blog_project/
#   __init__.py
#   settings.py
#   urls.py
#   wsgi.py
#   asgi.py

# Create an app inside the project
python manage.py startapp posts
```

---

## Step 3: Understand settings.py

Open `blog_project/settings.py`. Find these and understand them:

```python
SECRET_KEY = "..."        # Used for cryptographic signing. NEVER commit this to git.
DEBUG = True              # Shows error pages with stack traces. Set False in production.
ALLOWED_HOSTS = []        # Which domains can serve this app. Add "localhost" etc.

INSTALLED_APPS = [        # Which apps are active. ADD YOUR APP HERE.
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "posts",              # ← add this
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

**Task:** Add "posts" to INSTALLED_APPS.

---

## Step 4: Run Initial Migrations

Django comes with built-in apps (auth, sessions, etc.) that need database tables.

```bash
# See what migrations haven't been applied yet
python manage.py showmigrations

# Apply them
python manage.py migrate

# See the database file created
ls *.sqlite3
```

---

## Step 5: Start the Server

```bash
python manage.py runserver

# Visit http://127.0.0.1:8000/
# You should see Django's welcome page
```

Open a second terminal (keep the server running) and use curl:
```bash
curl -v http://127.0.0.1:8000/
```

**Questions:**
1. What HTTP status code does `GET /` return?
2. Look at the response headers. What is the `Server` header?
3. What does `X-Frame-Options` do? (Research this)

---

## Step 6: Create a Superuser and Explore Admin

```bash
python manage.py createsuperuser
# Follow the prompts

# Visit http://127.0.0.1:8000/admin/
# Login with your credentials
```

The Django admin is a full CRUD interface, auto-generated from your models. You'll use it to manage data during development.

---

## Step 7: Your First Model

In `posts/models.py`:

```python
from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
```

```bash
# Generate migration
python manage.py makemigrations posts

# See the SQL it will run
python manage.py sqlmigrate posts 0001

# Apply it
python manage.py migrate

# Open the Django shell
python manage.py shell
```

In the shell:
```python
from posts.models import Post

# Create posts
p1 = Post.objects.create(title="Hello World", content="My first post!", published=True)
p2 = Post.objects.create(title="Draft Post", content="Not ready yet")

# Query
Post.objects.all()
Post.objects.filter(published=True)
Post.objects.get(id=1)

# Update
p2.published = True
p2.save()

# Count
Post.objects.count()

# Exit shell
exit()
```

---

## Step 8: Register in Admin

In `posts/admin.py`:

```python
from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "published", "created_at"]
    list_filter = ["published"]
    search_fields = ["title", "content"]
```

Restart the server and go to `/admin/`. You can now create, edit, delete posts from a GUI.

---

## Checkpoint Questions

Before moving to the next exercise, answer these:

1. What is `manage.py`? What does it do differently from running Django directly?
2. What is the difference between `makemigrations` and `migrate`?
3. What does `auto_now_add=True` do on a DateTimeField? What about `auto_now=True`?
4. Django's dev server auto-reloads when you change Python files. Why doesn't this work for migrations?
5. Where is the SQLite database stored? What tool can you use to open and inspect it?
