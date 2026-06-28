# Jour 60 — Fichiers statiques et médias
📅 25 août 2026 · Module : Déploiement

---

## Statiques vs Médias

| | Fichiers statiques | Fichiers médias |
|---|---|---|
| Quoi | CSS, JS, images du site | Fichiers uploadés par les users |
| Quand | Connus à l'avance | Générés à l'exécution |
| Command Django | `collectstatic` | — |
| Setting | `STATIC_ROOT` / `STATICFILES_DIRS` | `MEDIA_ROOT` / `MEDIA_URL` |

---

## Configuration Django

```python
# settings.py
import os

# Statiques
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"      # où collectstatic les copie
STATICFILES_DIRS = [BASE_DIR / "static"]    # où chercher les statiques

# Médias
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

```python
# urls.py — servir les médias en développement seulement
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    ...
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# ↑ Ne JAMAIS utiliser en prod — utiliser Nginx à la place
```

---

## Collectstatic

```bash
# Copie tous les fichiers statiques dans STATIC_ROOT
python manage.py collectstatic

# Ce qu'il fait :
# 1. Parcourt STATICFILES_DIRS et INSTALLED_APPS/static/
# 2. Copie tout dans STATIC_ROOT
# 3. Nginx servira /static/ → STATIC_ROOT/
```

---

## Uploader des fichiers

```python
class ProfilUtilisateur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    cv = models.FileField(upload_to="cvs/%Y/%m/", blank=True)
    # upload_to peut être une function
```

```python
# serializers.py
class ProfilSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False)

    def validate_avatar(self, value):
        if value.size > 2 * 1024 * 1024:  # 2 MB max
            raise serializers.ValidationError("Image trop grande (max 2MB)")
        if not value.content_type.startswith("image/"):
            raise serializers.ValidationError("Le fichier doit être une image")
        return value

    class Meta:
        model = ProfilUtilisateur
        fields = ["avatar", "cv"]
```

```python
# views.py
class UploadAvatarView(UpdateAPIView):
    serializer_class = ProfilSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user.profil
```

---

## Servir les fichiers avec Nginx

```nginx
# /etc/nginx/sites-available/monsite

server {
    listen 80;
    server_name monsite.com;

    # Fichiers statiques — directement par Nginx (Django n'est pas appelé)
    location /static/ {
        alias /home/ubuntu/monsite/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Fichiers médias
    location /media/ {
        alias /home/ubuntu/monsite/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Tout le reste → Gunicorn/Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Stockage cloud (S3, Cloudinary)

```bash
pip install django-storages boto3
```

```python
# settings.py
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"

AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_STORAGE_BUCKET_NAME = "mon-bucket"
AWS_S3_REGION_NAME = "eu-west-3"
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
```

---

## Sécurité des uploads

```python
import magic  # python-magic

def valider_fichier_strict(fichier):
    # Lire les premiers bytes pour détecter le vrai type (pas juste l'extension)
    header = fichier.read(1024)
    fichier.seek(0)
    mime = magic.from_buffer(header, mime=True)

    TYPES_AUTORISES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if mime not in TYPES_AUTORISES:
        raise ValidationError(f"Type de fichier non autorisé : {mime}")

    # Extension cohérente avec le MIME
    ext = os.path.splitext(fichier.name)[1].lower()
    EXT_PAR_MIME = {
        "image/jpeg": [".jpg", ".jpeg"],
        "image/png": [".png"],
        "image/webp": [".webp"],
    }
    if ext not in EXT_PAR_MIME.get(mime, []):
        raise ValidationError("Extension et type MIME incohérents")
```
