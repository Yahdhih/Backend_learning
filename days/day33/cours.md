# Jour 33 — DRF : Révision et bonnes pratiques
📅 29 juillet 2026 · Module : DRF

---

## Ce que tu sais maintenant sur DRF

```
REST Request
    │
    ▼
Router → ViewSet → get_permissions() → authenticate()
                        │
                        ├── list()     → get_queryset() → filter → paginate → serialize
                        ├── create()   → deserialize → validate → perform_create
                        ├── retrieve() → get_object() → check_object_permissions → serialize
                        ├── update()   → get_object() → deserialize → validate → perform_update
                        └── destroy()  → get_object() → check_object_permissions → perform_destroy
```

---

## Structure d'un projet DRF bien organisé

```
myapp/
  models.py
  serializers.py      ← serializers uniquement
  views.py            ← viewsets/APIViews
  urls.py             ← router + urlpatterns
  permissions.py      ← permission classes custom
  filters.py          ← FilterSets custom
  pagination.py       ← classes de pagination
```

---

## Versionning d'API

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1", "v2"],
}

# urls.py
urlpatterns = [
    path("api/v1/", include("api.v1.urls")),
    path("api/v2/", include("api.v2.urls")),
]

# Dans la vue :
def get_serializer_class(self):
    if self.request.version == "v2":
        return ArticleV2Serializer
    return ArticleSerializer
```

---

## Throttling (limitation de débit)

```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
    }
}

# Throttle custom par vue
class ArticleViewSet(viewsets.ModelViewSet):
    throttle_classes = [UserRateThrottle]
```

---

## Gestion d'exceptions custom

```python
# exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "erreur": True,
            "message": str(exc),
            "detail": response.data,
            "code": response.status_code,
        }
    return response

# settings.py
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "myapp.exceptions.custom_exception_handler"
}
```

---

## Erreurs courantes et solutions

**1. `is_valid()` sans `raise_exception=True`**
```python
# Mauvais : ne lève pas d'exception si invalide
serializer.is_valid()
serializer.save()  # plante silencieusement ou sauvegarde des données invalides

# Bon
serializer.is_valid(raise_exception=True)
serializer.save()
```

**2. N+1 dans les serializers**
```python
# Mauvais : accède à article.auteur pour chaque article
class ArticleSerializer(ModelSerializer):
    auteur_nom = SerializerMethodField()
    def get_auteur_nom(self, obj):
        return obj.auteur.nom  # N+1 !

# Bon : select_related dans get_queryset()
def get_queryset(self):
    return Article.objects.select_related("auteur")
```

**3. `context` manquant dans les serializers imbriqués**
```python
# Mauvais
ArticleSerializer(articles, many=True)

# Bon : passe le contexte (contient request, view, format)
ArticleSerializer(articles, many=True, context={"request": request})
# Permet aux serializers imbriqués d'accéder à request.user, request.build_absolute_uri...
```

**4. Queryset non filtré pour les objets privés**
```python
# Mauvais : un user peut voir les brouillons des autres
def get_queryset(self):
    return Article.objects.all()

# Bon
def get_queryset(self):
    if self.request.user.is_authenticated:
        return Article.objects.filter(
            models.Q(statut="publie") | models.Q(auteur=self.request.user)
        )
    return Article.objects.filter(statut="publie")
```

---

## Checklist avant de pousser une API

- [ ] Pagination activée sur les listes
- [ ] `select_related` / `prefetch_related` dans `get_queryset`
- [ ] Permissions définies (pas `AllowAny` par défaut en prod)
- [ ] Validation des données dans le serializer
- [ ] Tests pour : 200, 201, 400, 401, 403, 404
- [ ] Throttling configuré
- [ ] Pas de données sensibles dans la réponse (mots de passe, tokens...)
- [ ] `perform_create` pour les champs auto (auteur, organisation...)
