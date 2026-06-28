# Exercice Jour 60 — Fichiers statiques et uploads

## Mise en place

```bash
mkdir -p monprojet/static/css monprojet/static/js monprojet/media/avatars
cd monprojet
python -m venv venv && source venv/bin/activate
pip install django pillow
django-admin startproject config .
python manage.py startapp utilisateurs
```

---

## Étape 1 : Configurer les fichiers statiques et médias

Dans [config/settings.py](config/settings.py), ajoute :

```python
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Crée un fichier CSS de test :
```css
/* static/css/style.css */
body { font-family: Arial, sans-serif; }
```

Lance `collectstatic` :
```bash
python manage.py collectstatic
ls staticfiles/css/  # doit contenir style.css
```

---

## Étape 2 : Modèle avec ImageField

Dans [utilisateurs/models.py](utilisateurs/models.py) :

```python
from django.contrib.auth.models import User
from django.db import models

class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return f"Profil de {self.user.username}"
```

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Étape 3 : Vue d'upload

Dans [utilisateurs/views.py](utilisateurs/views.py) :

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Profil

@login_required
def modifier_profil(request):
    profil, _ = Profil.objects.get_or_create(user=request.user)

    if request.method == "POST":
        bio = request.POST.get("bio", "")
        avatar = request.FILES.get("avatar")

        # TODO : Valider la taille (max 2MB) et le type (image seulement)
        if avatar:
            if avatar.size > 2 * 1024 * 1024:
                return render(request, "profil.html", {
                    "profil": profil,
                    "erreur": "Image trop grande (max 2MB)"
                })
            if not avatar.content_type.startswith("image/"):
                return render(request, "profil.html", {
                    "profil": profil,
                    "erreur": "Le fichier doit être une image"
                })
            profil.avatar = avatar

        profil.bio = bio
        profil.save()
        return redirect("profil")

    return render(request, "profil.html", {"profil": profil})
```

---

## Étape 4 : Template avec upload

Crée [utilisateurs/templates/profil.html](utilisateurs/templates/profil.html) :

```html
<!DOCTYPE html>
<html>
<head>
    {% load static %}
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
</head>
<body>
    <h1>Profil de {{ profil.user.username }}</h1>

    {% if profil.avatar %}
        <img src="{{ profil.avatar.url }}" alt="Avatar" width="150">
    {% endif %}

    {% if erreur %}
        <p style="color: red">{{ erreur }}</p>
    {% endif %}

    <form method="post" enctype="multipart/form-data">
        {% csrf_token %}
        <label>Bio : <textarea name="bio">{{ profil.bio }}</textarea></label><br>
        <label>Avatar : <input type="file" name="avatar" accept="image/*"></label><br>
        <button type="submit">Sauvegarder</button>
    </form>
</body>
</html>
```

---

## Étape 5 : URLs et médias en dev

Dans [config/urls.py](config/urls.py) :

```python
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from utilisateurs import views

urlpatterns = [
    path("profil/", views.modifier_profil, name="profil"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## Étape 6 : Test manuel

```bash
python manage.py createsuperuser
python manage.py runserver
```

1. Aller sur http://localhost:8000/profil/
2. Uploader une image
3. Vérifier que le fichier apparaît dans `media/avatars/`
4. Tester le rejet d'une image > 2MB
5. Tester le rejet d'un PDF (type non autorisé)

---

## Questions pour `notes.md`

1. Pourquoi ne jamais servir les médias avec Django en production ?
2. Quelle est la différence entre `STATIC_ROOT` et `STATICFILES_DIRS` ?
3. Que se passe-t-il si on utilise `ALLOWED_HOSTS = ["*"]` et qu'un attaquant peut uploader des fichiers exécutables ?
4. Pourquoi vérifier le MIME type avec `python-magic` plutôt que l'extension ?
