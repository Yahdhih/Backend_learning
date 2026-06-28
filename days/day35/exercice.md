# Exercice Jour 35 — Serializers et vues CRUD du blog

## Objectif

Ajouter les serializers et ViewSets au projet blog, puis tester tous les endpoints avec curl.

---

## Étape 1 : Copier le code

Copie le code complet depuis le cours dans les fichiers correspondants :

- `blog/serializers.py` — copie le code de serializers.py
- `blog/views.py` — copie le code de views.py
- `blog/urls.py` — copie la configuration du routeur

---

## Étape 2 : Appliquer les migrations

Si tu as modifié des modèles, relance :

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Étape 3 : Script de données de test

Crée `seed.py` à la racine du projet :

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_api.settings')
django.setup()

from django.contrib.auth.models import User
from blog.models import Category, Tag, Post, Comment

# Nettoyer les données existantes
Comment.objects.all().delete()
Post.objects.all().delete()
Tag.objects.all().delete()
Category.objects.all().delete()
User.objects.filter(is_superuser=False).delete()

# Utilisateurs
alice = User.objects.create_user('alice', 'alice@example.com', 'password123')
bob = User.objects.create_user('bob', 'bob@example.com', 'password123')

# Catégories
tech = Category.objects.create(name='Technologie', description='Articles sur la tech')
dev = Category.objects.create(name='Développement', description='Dev web et logiciel')

# Tags
python_tag = Tag.objects.create(name='Python')
django_tag = Tag.objects.create(name='Django')
api_tag = Tag.objects.create(name='API')
rest_tag = Tag.objects.create(name='REST')

# Posts
p1 = Post.objects.create(
    title='Introduction à Python',
    content='Python est un langage de programmation polyvalent et lisible...',
    author=alice,
    category=tech,
    status='published',
)
p1.tags.add(python_tag)

p2 = Post.objects.create(
    title='Django REST Framework — Guide complet',
    content='DRF est la bibliothèque de référence pour créer des APIs avec Django...',
    author=alice,
    category=dev,
    status='published',
)
p2.tags.add(django_tag, api_tag, rest_tag)

p3 = Post.objects.create(
    title='Mon brouillon privé',
    content='Ce post est en cours de rédaction...',
    author=alice,
    category=dev,
    status='draft',
)

p4 = Post.objects.create(
    title='Post de Bob',
    content='Bob partage ses expériences avec les APIs REST...',
    author=bob,
    category=tech,
    status='published',
)
p4.tags.add(api_tag)

# Commentaires
Comment.objects.create(post=p1, author=bob, content='Super article Alice !')
Comment.objects.create(post=p2, author=bob, content='Très complet, merci !')
Comment.objects.create(post=p1, author=alice, content='Merci Bob !')

print("Données créées :")
print(f"  {User.objects.count()} utilisateurs")
print(f"  {Category.objects.count()} catégories")
print(f"  {Tag.objects.count()} tags")
print(f"  {Post.objects.count()} posts ({Post.objects.filter(status='published').count()} publiés)")
print(f"  {Comment.objects.count()} commentaires")
```

Lance : `python seed.py`

---

## Étape 4 : Tests curl

Lance le serveur (`python manage.py runserver`) et exécute ces commandes dans un autre terminal.

### 4.1 — Inscription et login

```bash
# S'inscrire
curl -s -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "charlie", "email": "charlie@example.com", "password": "password123", "password_confirm": "password123"}' | python -m json.tool

# Se connecter avec alice (créée par seed.py)
curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}' | python -m json.tool

# Sauvegarde le token (remplace TOKEN par la valeur reçue)
TOKEN="votre_token_ici"
```

### 4.2 — Lire les posts (sans auth)

```bash
# Liste des posts publiés
curl -s http://127.0.0.1:8000/api/posts/ | python -m json.tool

# Détail d'un post
curl -s http://127.0.0.1:8000/api/posts/1/ | python -m json.tool

# Posts publiés seulement
curl -s http://127.0.0.1:8000/api/posts/published/ | python -m json.tool
```

### 4.3 — Créer des données (avec auth)

```bash
# Créer une catégorie
curl -s -X POST http://127.0.0.1:8000/api/categories/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"name": "Data Science"}' | python -m json.tool

# Créer un tag
curl -s -X POST http://127.0.0.1:8000/api/tags/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"name": "Machine Learning"}' | python -m json.tool

# Créer un post
curl -s -X POST http://127.0.0.1:8000/api/posts/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"title": "Mon nouveau post", "content": "Contenu du post...", "status": "draft"}' | python -m json.tool
```

### 4.4 — Actions personnalisées

```bash
# Mes posts (auth requise)
curl -s http://127.0.0.1:8000/api/posts/my_posts/ \
  -H "Authorization: Token $TOKEN" | python -m json.tool

# Publier un post (remplace {ID} par l'ID du post créé)
curl -s -X POST http://127.0.0.1:8000/api/posts/{ID}/publish/ \
  -H "Authorization: Token $TOKEN" | python -m json.tool

# Commentaires d'un post
curl -s http://127.0.0.1:8000/api/posts/1/comments/ | python -m json.tool

# Ajouter un commentaire
curl -s -X POST http://127.0.0.1:8000/api/posts/1/comments/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"content": "Excellent article !"}' | python -m json.tool
```

### 4.5 — Modifier et supprimer

```bash
# Modifier un post (PATCH = mise à jour partielle)
curl -s -X PATCH http://127.0.0.1:8000/api/posts/{ID}/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"title": "Titre modifié"}' | python -m json.tool

# Supprimer un post
curl -s -X DELETE http://127.0.0.1:8000/api/posts/{ID}/ \
  -H "Authorization: Token $TOKEN"
# → 204 No Content si succès
```

---

## Vérifications attendues

| Test | Résultat attendu |
|------|-----------------|
| `GET /api/posts/` sans auth | Seulement les posts publiés |
| `GET /api/posts/my_posts/` sans auth | 401 Unauthorized |
| `POST /api/posts/` sans auth | 403 Forbidden |
| `POST /api/auth/login/` | Retourne un token |
| `GET /api/posts/` avec auth (alice) | Posts publiés + drafts d'alice |

---

## Questions de réflexion

1. Pourquoi utilise-t-on `PostListSerializer` (sans `content`) pour la liste et `PostDetailSerializer` (avec `content`) pour le détail ?

2. Que fait `select_related('author', 'category')` dans `get_queryset()` ? Pourquoi c'est important ?

3. Comment fonctionne l'injection de l'auteur dans `perform_create` ?

4. Quelle est la différence entre `PUT` et `PATCH` ?

---

## Bonus : Explorer l'API navigable

DRF fournit une interface web pour tester l'API. Ouvre dans ton navigateur :

```
http://127.0.0.1:8000/api/
http://127.0.0.1:8000/api/posts/
http://127.0.0.1:8000/api/categories/
```

Tu peux interagir avec l'API directement depuis le navigateur !
