# Exercice Jour 37 — Pagination et Filtres du blog

## Objectif

Ajouter la pagination et les filtres au projet blog, puis les tester avec des données réalistes.

---

## Étape 1 : Créer les fichiers

Crée `blog/pagination.py` et `blog/filters.py` avec le code du cours.

---

## Étape 2 : Mettre à jour settings.py

```python
# Dans REST_FRAMEWORK, ajoute/modifie :
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'blog.pagination.BlogPagination',
    'PAGE_SIZE': 10,
}
```

---

## Étape 3 : Mettre à jour views.py

Ajoute les imports et attributs de filtres dans les ViewSets comme montré dans le cours.

---

## Étape 4 : Script de données de masse

Crée `seed_big.py` pour générer 50+ posts :

```python
import os
import django
import random
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_api.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from blog.models import Category, Tag, Post, Comment

# Nettoyage
Comment.objects.all().delete()
Post.objects.all().delete()
Tag.objects.all().delete()
Category.objects.all().delete()
User.objects.filter(is_superuser=False).delete()

# Utilisateurs
users = []
for name in ['alice', 'bob', 'charlie', 'diana']:
    u = User.objects.create_user(name, f'{name}@example.com', 'password123')
    users.append(u)

# Catégories
categories = []
for name in ['Technologie', 'Développement', 'Data Science', 'DevOps', 'Design']:
    c = Category.objects.create(name=name)
    categories.append(c)

# Tags
tag_names = ['Python', 'Django', 'API', 'REST', 'JavaScript', 'SQL', 'Docker', 'Linux', 'Git', 'Testing']
tags = [Tag.objects.create(name=name) for name in tag_names]

# Posts (60 posts)
statuses = ['draft', 'draft', 'published', 'published', 'published']  # 40% draft, 60% published

titles = [
    "Introduction à {}", "Guide avancé de {}", "Meilleures pratiques {}",
    "Tutorial {} pour débutants", "Comprendre {} en profondeur",
    "{} : ce que vous devez savoir", "Optimiser {} pour la production",
    "Sécuriser votre {} application", "{} vs les alternatives",
    "Déployer avec {} sur AWS",
]

topics = ['Python', 'Django', 'l\'API REST', 'Docker', 'PostgreSQL',
          'Redis', 'Nginx', 'JWT', 'OAuth2', 'GraphQL']

posts = []
for i in range(60):
    title_template = random.choice(titles)
    topic = random.choice(topics)
    title = title_template.format(topic)
    content = f"Cet article explore en détail {topic}. " * 20
    author = random.choice(users)
    category = random.choice(categories)
    status = random.choice(statuses)

    # Date de création dans les 6 derniers mois
    days_ago = random.randint(0, 180)
    created_at = timezone.now() - timedelta(days=days_ago)

    post = Post(
        title=f"{title} — Partie {i+1}",
        content=content,
        author=author,
        category=category,
        status=status,
    )
    post.save()

    # Forcer la date de création (bypass auto_now_add)
    Post.objects.filter(pk=post.pk).update(created_at=created_at)

    # Ajouter 1-3 tags aléatoires
    selected_tags = random.sample(tags, random.randint(1, 3))
    post.tags.set(selected_tags)
    posts.append(post)

# Commentaires (100 commentaires)
for _ in range(100):
    published_posts = [p for p in posts if p.status == 'published']
    if published_posts:
        post = random.choice(published_posts)
        author = random.choice(users)
        Comment.objects.create(
            post=post,
            author=author,
            content=f"Commentaire de test sur ce post. Très intéressant !"
        )

print(f"Données créées :")
print(f"  {User.objects.count()} utilisateurs")
print(f"  {Category.objects.count()} catégories")
print(f"  {Tag.objects.count()} tags")
print(f"  {Post.objects.count()} posts ({Post.objects.filter(status='published').count()} publiés)")
print(f"  {Comment.objects.count()} commentaires")
```

Lance : `python seed_big.py`

---

## Étape 5 : Tests des filtres

```bash
# Lance le serveur
python manage.py runserver

# Dans un autre terminal :

# 1. PAGINATION
echo "=== Test pagination ==="
# Voir le format de réponse avec pagination
curl -s "http://127.0.0.1:8000/api/posts/" | python -m json.tool | head -20

# Vérifier que 'pagination' est dans la réponse
curl -s "http://127.0.0.1:8000/api/posts/" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Champs de réponse :', list(data.keys()))
print('Nombre total de posts :', data['pagination']['count'])
print('Posts dans cette page :', len(data['results']))
print('Nombre de pages :', data['pagination']['pages'])
"

# Aller à la page 2
curl -s "http://127.0.0.1:8000/api/posts/?page=2" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Page actuelle :', data['pagination']['page'])
print('Page suivante :', data['pagination']['next'])
"

# 2. FILTRES PAR CATÉGORIE
echo ""
echo "=== Test filtres catégorie ==="

# Obtenir les catégories disponibles
curl -s "http://127.0.0.1:8000/api/categories/" | python -m json.tool

# Filtrer par slug de catégorie
curl -s "http://127.0.0.1:8000/api/posts/?category_slug=technologie" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Posts tech :', data['pagination']['count'])
"

# 3. FILTRES PAR TAG
echo ""
echo "=== Test filtres tag ==="
curl -s "http://127.0.0.1:8000/api/posts/?tag_slug=python" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Posts Python :', data['pagination']['count'])
"

# 4. RECHERCHE
echo ""
echo "=== Test recherche ==="
curl -s "http://127.0.0.1:8000/api/posts/?search=docker" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Posts avec \"docker\" :', data['pagination']['count'])
"

# 5. TRI
echo ""
echo "=== Test tri ==="

# Plus récent d'abord
curl -s "http://127.0.0.1:8000/api/posts/?ordering=-created_at&page_size=3" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Tri par -created_at :')
for p in data['results']:
    print(f'  {p[\"created_at\"][:10]} — {p[\"title\"][:40]}')
"

# Plus ancien d'abord
curl -s "http://127.0.0.1:8000/api/posts/?ordering=created_at&page_size=3" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Tri par created_at :')
for p in data['results']:
    print(f'  {p[\"created_at\"][:10]} — {p[\"title\"][:40]}')
"

# 6. COMBINAISONS
echo ""
echo "=== Test combinaisons ==="
curl -s "http://127.0.0.1:8000/api/posts/?category_slug=developpement&search=api&ordering=-created_at&page_size=5" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Dev + api + tri date :', data['pagination']['count'], 'posts')
"

# 7. PAGINATION PETITE
echo ""
echo "=== Test page_size personnalisé ==="
curl -s "http://127.0.0.1:8000/api/posts/?page_size=3" | python -c "
import sys, json
data = json.load(sys.stdin)
print('page_size=3 :', len(data['results']), 'posts par page')
print('Total pages :', data['pagination']['pages'])
"

# Essayer de dépasser le max (100)
curl -s "http://127.0.0.1:8000/api/posts/?page_size=200" | python -c "
import sys, json
data = json.load(sys.stdin)
print('page_size=200 → restreint à :', len(data['results']))
"
```

---

## Étape 6 : Tests par auteur

```bash
# Login avec alice
ALICE_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}' | \
  python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Filtrer les posts d'alice
curl -s "http://127.0.0.1:8000/api/posts/?author=alice" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Posts publiés d\'alice :', data['pagination']['count'])
"

# Mes posts (draft inclus)
curl -s "http://127.0.0.1:8000/api/posts/my_posts/" \
  -H "Authorization: Token $ALICE_TOKEN" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Mes posts (draft inclus) :', data['pagination']['count'])
"
```

---

## Questions de réflexion

1. Quelle est la différence entre `PageNumberPagination` et `CursorPagination` ? Dans quel cas utilise-t-on chacun ?

2. Pourquoi combine-t-on `DjangoFilterBackend` ET `SearchFilter` ? Pourquoi pas un seul ?

3. Que se passe-t-il si on met `ordering=-comments_count` mais que `comments_count` n'est pas dans `ordering_fields` ?

4. Comment fonctionne `paginate_queryset` dans les actions personnalisées ?

---

## Bonus : Filtre de date avancé

Ajoute dans `PostFilter` un filtre pour les posts de la semaine dernière :

```python
# Dans blog/filters.py

class PostFilter(filters.FilterSet):
    # ... autres filtres ...

    this_week = filters.BooleanFilter(method='filter_this_week')
    this_month = filters.BooleanFilter(method='filter_this_month')

    def filter_this_week(self, queryset, name, value):
        if value:
            from django.utils import timezone
            from datetime import timedelta
            week_ago = timezone.now() - timedelta(days=7)
            return queryset.filter(created_at__gte=week_ago)
        return queryset

    def filter_this_month(self, queryset, name, value):
        if value:
            from django.utils import timezone
            now = timezone.now()
            return queryset.filter(
                created_at__year=now.year,
                created_at__month=now.month
            )
        return queryset
```

Test : `?this_week=true` et `?this_month=true`
