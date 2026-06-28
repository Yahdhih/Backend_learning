# Jour 29 — DRF Serializers (25 juillet 2026)

## Introduction

Les **serializers** sont le cœur de Django REST Framework. Ils font deux choses symétriques :

1. **Sérialisation** : convertir un objet Python (instance de modèle, queryset) en données primitives (dict) → JSON
2. **Désérialisation** : valider des données entrantes (JSON → dict → objet Python) et créer ou mettre à jour des instances

Sans serializers, tu devrais écrire manuellement la validation, la conversion en JSON, et la gestion des erreurs. Les serializers encapsulent tout ça.

---

## 1. `Serializer` vs `ModelSerializer`

### `Serializer` : la base

```python
from rest_framework import serializers

class PostSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=200)
    content = serializers.CharField()
    published_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        return Post.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance
```

**Avantages** : contrôle total, explicite, pas lié à un modèle.
**Inconvénient** : verbeux — tu redéclares ce qui est déjà dans ton modèle.

### `ModelSerializer` : le raccourci

```python
class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'published_at']
        read_only_fields = ['id', 'published_at']
```

`ModelSerializer` génère automatiquement les champs à partir du modèle. Il implémente aussi `create()` et `update()` pour toi.

**Règle pratique** : commence toujours par `ModelSerializer`. Passe à `Serializer` seulement si tu as des besoins très spécifiques non liés à un modèle.

### Ce que `ModelSerializer` génère automatiquement

| Champ Django | Champ DRF généré |
|---|---|
| `CharField` | `CharField` |
| `IntegerField` | `IntegerField` |
| `BooleanField` | `BooleanField` |
| `DateTimeField` | `DateTimeField` |
| `ForeignKey` | `PrimaryKeyRelatedField` |
| `ManyToManyField` | `PrimaryKeyRelatedField(many=True)` |

---

## 2. Les champs courants

### Champs de base

```python
class ExempleSerializer(serializers.ModelSerializer):
    # CharField — options importantes
    title = serializers.CharField(
        max_length=200,
        min_length=5,
        allow_blank=False,  # "" interdit
        trim_whitespace=True,
    )

    # IntegerField — avec bornes
    views_count = serializers.IntegerField(
        min_value=0,
        max_value=1_000_000,
        read_only=True,
    )

    # EmailField — valide le format email
    email = serializers.EmailField()

    # URLField — valide le format URL
    website = serializers.URLField(required=False, allow_blank=True)

    # BooleanField
    is_published = serializers.BooleanField(default=False)

    # DateTimeField — format personnalisable
    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M",
        read_only=True,
    )

    # ChoiceField
    STATUS_CHOICES = [('draft', 'Brouillon'), ('published', 'Publié')]
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
```

### `SerializerMethodField` : champs calculés en lecture seule

```python
class PostSerializer(serializers.ModelSerializer):
    comment_count = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()

    def get_comment_count(self, obj):
        # obj = instance du modèle Post
        return obj.comments.count()

    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}".strip()

    class Meta:
        model = Post
        fields = ['id', 'title', 'comment_count', 'author_name']
```

**Important** : `SerializerMethodField` est toujours `read_only=True`. La convention de nommage est `get_<field_name>`.

---

## 3. Validation

La validation DRF se fait en plusieurs niveaux, dans cet ordre :

```
Données brutes (JSON)
      ↓
Validation de type (CharField, IntegerField, etc.)
      ↓
validate_<field>() — validation par champ
      ↓
validate() — validation croisée entre champs
      ↓
validated_data — données propres prêtes à l'emploi
```

### Validation par champ : `validate_<field_name>()`

```python
class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['title', 'content', 'status']

    def validate_title(self, value):
        """
        'value' est déjà nettoyé (type correct, etc.)
        Lève serializers.ValidationError si invalide.
        Retourne la valeur (éventuellement modifiée).
        """
        if len(value) < 5:
            raise serializers.ValidationError(
                "Le titre doit faire au moins 5 caractères."
            )

        mots_interdits = ['spam', 'promo', 'pub']
        for mot in mots_interdits:
            if mot.lower() in value.lower():
                raise serializers.ValidationError(
                    f"Le titre contient un mot interdit : '{mot}'."
                )

        # Normaliser : première lettre majuscule
        return value.capitalize()

    def validate_content(self, value):
        if len(value.split()) < 10:
            raise serializers.ValidationError(
                "Le contenu doit faire au moins 10 mots."
            )
        return value
```

### Validation croisée : `validate()`

```python
    def validate(self, attrs):
        """
        'attrs' = dict de toutes les valeurs validées individuellement.
        Idéal pour les règles qui impliquent plusieurs champs.
        """
        if attrs.get('status') == 'published' and not attrs.get('content'):
            raise serializers.ValidationError(
                "Un post publié doit avoir du contenu."
            )

        if attrs.get('published_at') and attrs.get('status') == 'draft':
            raise serializers.ValidationError({
                'published_at': "Un brouillon ne peut pas avoir de date de publication."
            })

        return attrs  # toujours retourner attrs !
```

### Validateurs au niveau du champ (réutilisables)

```python
def validate_no_profanity(value):
    """Validateur standalone réutilisable."""
    bad_words = ['spam', 'click here', 'buy now']
    for word in bad_words:
        if word.lower() in value.lower():
            raise serializers.ValidationError(
                f"Contenu inapproprié détecté : '{word}'"
            )
    return value

class PostSerializer(serializers.ModelSerializer):
    title = serializers.CharField(validators=[validate_no_profanity])
```

---

## 4. `create()` et `update()`

### `create()` dans `ModelSerializer`

`ModelSerializer` génère automatiquement :

```python
def create(self, validated_data):
    return ModelClass.objects.create(**validated_data)
```

Tu override quand tu dois faire quelque chose de spécial :

```python
class PostSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        # Extraire les M2M avant create() (Django ne les accepte pas directement)
        tags = validated_data.pop('tags', [])

        # Créer l'instance
        post = Post.objects.create(**validated_data)

        # Ajouter les M2M après
        post.tags.set(tags)

        return post
```

### `update()` dans `ModelSerializer`

```python
def update(self, instance, validated_data):
    # validated_data contient seulement les champs envoyés
    tags = validated_data.pop('tags', None)

    # Mettre à jour les champs scalaires
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()

    # Mettre à jour les M2M si fournis
    if tags is not None:
        instance.tags.set(tags)

    return instance
```

### Sauvegarder : `.save()`

```python
# Lors d'une création (pas d'instance)
serializer = PostSerializer(data=request.data)
if serializer.is_valid():
    post = serializer.save()  # appelle create()

# Lors d'une mise à jour (instance fournie)
serializer = PostSerializer(instance=post, data=request.data, partial=True)
if serializer.is_valid():
    post = serializer.save()  # appelle update()

# Passer des données supplémentaires à save()
serializer.save(author=request.user)  # kwargs → merged dans validated_data
```

---

## 5. `read_only_fields`

### Approche 1 : dans Meta

```python
class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'author', 'created_at', 'views_count']
        read_only_fields = ['id', 'author', 'created_at', 'views_count']
```

### Approche 2 : sur le champ directement

```python
class PostSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    views_count = serializers.IntegerField(read_only=True)
```

### Différence importante

`read_only_fields` dans `Meta` s'applique aux champs générés automatiquement. Pour les champs que tu déclares explicitement, utilise `read_only=True` sur le champ.

---

## 6. Serializers imbriqués (nested)

### Imbrication simple : afficher l'auteur complet

```python
class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class PostSerializer(serializers.ModelSerializer):
    # Remplace le PrimaryKeyRelatedField par un serializer complet
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'author']
```

**Résultat JSON** :
```json
{
    "id": 1,
    "title": "Mon article",
    "author": {
        "id": 5,
        "username": "alice",
        "email": "alice@example.com"
    }
}
```

### Écriture avec serializer imbriqué

Les serializers imbriqués sont `read_only=True` par défaut. Pour l'écriture, la pratique courante est d'avoir deux serializers distincts :

```python
class PostListSerializer(serializers.ModelSerializer):
    """Pour la liste — auteur comme ID (écriture possible)."""
    class Meta:
        model = Post
        fields = ['id', 'title', 'author', 'created_at']

class PostDetailSerializer(serializers.ModelSerializer):
    """Pour le détail — auteur imbriqué (lecture seule)."""
    author = AuthorSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'author', 'comments', 'created_at']
```

---

## 7. `many=True`

Pour sérialiser plusieurs objets (un queryset) :

```python
# Côté vue
posts = Post.objects.all()
serializer = PostSerializer(posts, many=True)
data = serializer.data  # list de dicts

# DRF crée automatiquement un ListSerializer en interne
```

### `many=True` sur les champs imbriqués

```python
class PostSerializer(serializers.ModelSerializer):
    # Un post peut avoir plusieurs commentaires
    comments = CommentSerializer(many=True, read_only=True)
    # Un post peut avoir plusieurs tags
    tags = TagSerializer(many=True, read_only=True)
```

---

## 8. `context` : passer la requête au serializer

Le `context` est un dict transmis au serializer. DRF y met automatiquement `request`, `view`, et `format` quand le serializer est créé depuis une vue.

### Accéder au contexte dans le serializer

```python
class PostSerializer(serializers.ModelSerializer):
    url_absolue = serializers.SerializerMethodField()
    est_auteur = serializers.SerializerMethodField()

    def get_url_absolue(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/posts/{obj.id}/')
        return f'/api/posts/{obj.id}/'

    def get_est_auteur(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.author == request.user
        return False

    class Meta:
        model = Post
        fields = ['id', 'title', 'url_absolue', 'est_auteur']
```

### Passer le contexte manuellement

```python
# Dans une vue
serializer = PostSerializer(
    post,
    context={'request': request, 'extra_data': 'valeur'}
)

# Dans un test
serializer = PostSerializer(
    post,
    context={'request': None}  # ou créer un mock request
)
```

---

## 9. Résumé : choisir le bon pattern

```
Besoin                          → Solution
─────────────────────────────────────────────────────────
Modèle simple, CRUD standard    → ModelSerializer basique
Champ calculé (lecture seule)   → SerializerMethodField
Afficher relation complète      → Nested serializer (read_only)
Deux représentations (list/detail) → Deux serializers distincts
Logique de création complexe    → Override create()
Validation d'un champ           → validate_<field>()
Validation croisée              → validate()
Accès à la requête              → self.context['request']
```

---

## Points clés à retenir

1. `ModelSerializer` génère les champs automatiquement — utilise-le par défaut
2. `validate_<field>()` pour valider un champ, `validate()` pour les règles croisées
3. Les nested serializers affichent les relations complètes en lecture
4. `many=True` pour sérialiser des querysets ou des listes
5. Le `context` permet d'accéder à la requête depuis n'importe quel serializer
6. `read_only_fields` pour protéger les champs auto-générés (id, timestamps)
7. Override `create()` quand tu as des ManyToMany à gérer
