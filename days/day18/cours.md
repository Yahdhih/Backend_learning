# Jour 18 — Django : Models
📅 14 juillet 2026 · Module : Django

---

## Un Model = une table en base de données

Chaque classe qui hérite de `models.Model` devient une table. Chaque attribut devient une colonne.

```python
from django.db import models

class Article(models.Model):
    titre = models.CharField(max_length=200)     # VARCHAR(200)
    contenu = models.TextField()                  # TEXT
    publie = models.BooleanField(default=False)  # BOOLEAN
    date_creation = models.DateTimeField(auto_now_add=True)  # TIMESTAMP
    date_modification = models.DateTimeField(auto_now=True)
```

Django génère automatiquement une colonne `id` (clé primaire, auto-incrément).

---

## Les types de champs principaux

```python
# Texte
models.CharField(max_length=200)       # texte court, obligatoire max_length
models.TextField()                      # texte long
models.SlugField()                      # "mon-article-de-blog"
models.EmailField()                     # validation email incluse
models.URLField()                       # validation URL

# Nombres
models.IntegerField()
models.FloatField()
models.DecimalField(max_digits=10, decimal_places=2)  # pour l'argent !

# Dates
models.DateField()                      # seulement la date
models.DateTimeField()                  # date + heure
models.DateTimeField(auto_now_add=True) # définit à la création, jamais modifié
models.DateTimeField(auto_now=True)     # mis à jour à chaque save()

# Booléen
models.BooleanField(default=False)

# Fichiers
models.FileField(upload_to='uploads/')
models.ImageField(upload_to='images/')
```

---

## Options des champs

```python
models.CharField(
    max_length=200,
    null=True,       # permet NULL en DB (évite pour les CharField, utilise blank)
    blank=True,      # permet la chaîne vide dans les formulaires
    default="",      # valeur par défaut
    unique=True,     # contrainte UNIQUE en DB
    db_index=True,   # crée un index sur cette colonne
    choices=[        # liste de valeurs autorisées
        ("brouillon", "Brouillon"),
        ("publie", "Publié"),
        ("archive", "Archivé"),
    ],
    verbose_name="titre de l'article",  # pour l'admin Django
)
```

**Règle importante :** Pour les `CharField` et `TextField`, utilise `blank=True` (pas `null=True`). Django stocke `""` pour vide, pas `NULL`.

---

## Relations entre models

```python
from django.contrib.auth.models import User

class Categorie(models.Model):
    nom = models.CharField(max_length=100)

class Article(models.Model):
    auteur = models.ForeignKey(          # Many-to-One : un auteur, plusieurs articles
        User,
        on_delete=models.CASCADE,        # si User supprimé → articles supprimés
        related_name="articles",         # user.articles.all()
    )
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.SET_NULL,       # si Categorie supprimée → categorie=NULL
        null=True,
        blank=True,
    )
    tags = models.ManyToManyField(       # Many-to-Many : table de jointure auto
        "Tag",
        blank=True,
    )

class Profil(models.Model):
    utilisateur = models.OneToOneField(  # One-to-One : un profil par user
        User,
        on_delete=models.CASCADE,
        related_name="profil",
    )
    bio = models.TextField(blank=True)

class Tag(models.Model):
    nom = models.CharField(max_length=50)
```

**`on_delete` options :**
- `CASCADE` : supprime en cascade
- `SET_NULL` : met NULL (nécessite `null=True`)
- `SET_DEFAULT` : met la valeur par défaut
- `PROTECT` : interdit la suppression (lève une erreur)
- `DO_NOTHING` : ne fait rien (dangereux)

---

## La classe Meta

```python
class Article(models.Model):
    titre = models.CharField(max_length=200)
    date_creation = models.DateTimeField(auto_now_add=True)
    vues = models.IntegerField(default=0)

    class Meta:
        ordering = ["-date_creation"]              # tri par défaut (- = décroissant)
        verbose_name = "article"
        verbose_name_plural = "articles"
        db_table = "blog_articles"                 # nom de table custom
        indexes = [
            models.Index(fields=["titre"]),        # index sur titre
            models.Index(fields=["-date_creation", "auteur"]),  # index composite
        ]
        constraints = [
            models.UniqueConstraint(               # combinaison unique
                fields=["titre", "auteur"],
                name="unique_titre_par_auteur"
            ),
            models.CheckConstraint(                # contrainte CHECK SQL
                check=models.Q(vues__gte=0),
                name="vues_positives"
            ),
        ]
```

---

## Méthodes sur un Model

```python
class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    publie = models.BooleanField(default=False)

    def __str__(self):
        """Utilisé dans l'admin et les repr."""
        return self.titre

    def __repr__(self):
        return f"Article(id={self.pk}, titre={self.titre!r})"

    @property
    def est_recent(self):
        """Publié dans les 7 derniers jours."""
        from django.utils import timezone
        delta = timezone.now() - self.date_creation
        return delta.days <= 7

    @property
    def extrait(self):
        """Les 200 premiers caractères du contenu."""
        return self.contenu[:200]

    def publier(self):
        """Publie l'article."""
        self.publie = True
        self.save(update_fields=["publie"])  # UPDATE seulement ce champ

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("articles:detail", kwargs={"pk": self.pk})
```

---

## Managers personnalisés

```python
class ArticleManager(models.Manager):
    """Manager avec des méthodes de requête custom."""

    def publies(self):
        return self.filter(publie=True)

    def recents(self, jours=7):
        from django.utils import timezone
        from datetime import timedelta
        depuis = timezone.now() - timedelta(days=jours)
        return self.filter(date_creation__gte=depuis)

    def populaires(self, min_vues=100):
        return self.filter(vues__gte=min_vues).order_by("-vues")


class Article(models.Model):
    ...
    objects = ArticleManager()   # remplace le manager par défaut

# Utilisation
Article.objects.publies()
Article.objects.recents(jours=3)
Article.objects.publies().recents()   # chaînage
```

---

## Signaux

```python
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=User)
def creer_profil(sender, instance, created, **kwargs):
    """Crée automatiquement un profil quand un User est créé."""
    if created:
        Profil.objects.create(utilisateur=instance)

@receiver(pre_delete, sender=Article)
def nettoyer_fichiers(sender, instance, **kwargs):
    """Supprime les fichiers associés avant suppression."""
    if instance.image:
        instance.image.delete(save=False)
```
