# Jour 38 — Project Blog : Tests de l'API (3 août 2026)

## Objectif du jour

Écrire une suite de tests complète pour la Blog API. À la fin du jour, chaque endpoint, chaque règle de permission et chaque comportement de filtrage sera couvert par des tests automatisés.

---

## Pourquoi tester ?

Les tests automatisés permettent de :
1. **Détecter les régressions** : une modification ne casse pas ce qui fonctionnait
2. **Documenter le comportement** : les tests décrivent ce que l'API est censée faire
3. **Refactoriser en confiance** : tu peux changer le code interne sans peur

---

## Outils de test

### Django TestCase vs APITestCase

```python
# Django standard : pour les modèles, les vues HTML
from django.test import TestCase

# DRF : pour les APIs
from rest_framework.test import APITestCase, APIClient
```

`APITestCase` ajoute un `APIClient` pré-configuré qui comprend les formats JSON.

### Fixtures et setUp

```python
class PostAPITest(APITestCase):
    def setUp(self):
        """
        Appelé AVANT chaque test.
        Crée les données fraîches pour chaque test (isolation totale).
        """
        self.alice = User.objects.create_user('alice', 'alice@example.com', 'pass')
        self.token = Token.objects.create(user=self.alice)
```

### Authentification dans les tests

```python
# Méthode 1 : en-tête manuel
self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

# Méthode 2 : force_authenticate (bypass complet, utile pour les tests unitaires)
self.client.force_authenticate(user=self.alice)

# Méthode 3 : sans auth (réinitialiser)
self.client.credentials()
```

---

## tests.py — Suite complète

```python
# blog/tests.py

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token

from .models import Category, Tag, Post, Comment


# ─────────────────────────────────────────
# Helpers / Mixins
# ─────────────────────────────────────────

class BlogTestMixin:
    """
    Mixin avec des méthodes utilitaires partagées entre les TestCases.
    """

    def create_user(self, username, password='password123'):
        user = User.objects.create_user(username, f'{username}@example.com', password)
        token = Token.objects.create(user=user)
        return user, token

    def authenticate(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def unauthenticate(self):
        self.client.credentials()

    def create_category(self, name='Technologie'):
        return Category.objects.create(name=name)

    def create_tag(self, name='Python'):
        return Tag.objects.create(name=name)

    def create_post(self, author, title='Post de test', status='draft', category=None):
        return Post.objects.create(
            title=title,
            content='Contenu de test pour cet article de blog.',
            author=author,
            category=category,
            status=status,
        )

    def create_comment(self, post, author, content='Commentaire de test'):
        return Comment.objects.create(post=post, author=author, content=content)


# ─────────────────────────────────────────
# Tests d'authentification
# ─────────────────────────────────────────

class AuthAPITest(BlogTestMixin, APITestCase):

    def test_register_success(self):
        """Un utilisateur peut s'inscrire avec des données valides."""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_password_mismatch(self):
        """L'inscription échoue si les mots de passe ne correspondent pas."""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123',
            'password_confirm': 'differentpassword',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """L'inscription échoue si le username existe déjà."""
        self.create_user('existinguser')
        url = reverse('register')
        data = {
            'username': 'existinguser',
            'email': 'other@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        """Un utilisateur peut se connecter avec des identifiants valides."""
        self.create_user('alice')
        url = reverse('login')
        response = self.client.post(url, {'username': 'alice', 'password': 'password123'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_login_invalid_credentials(self):
        """Le login échoue avec de mauvais identifiants."""
        self.create_user('alice')
        url = reverse('login')
        response = self.client.post(url, {'username': 'alice', 'password': 'wrongpassword'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_invalidates_token(self):
        """Après logout, le token ne fonctionne plus."""
        user, token = self.create_user('alice')
        self.authenticate(token)

        # Logout
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Le token est supprimé
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    def test_me_returns_current_user(self):
        """GET /auth/me/ retourne le profil de l'utilisateur connecté."""
        user, token = self.create_user('alice')
        self.authenticate(token)

        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'alice')

    def test_me_requires_auth(self):
        """GET /auth/me/ retourne 401 sans authentification."""
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────
# Tests des catégories
# ─────────────────────────────────────────

class CategoryAPITest(BlogTestMixin, APITestCase):

    def setUp(self):
        self.alice, self.token = self.create_user('alice')
        self.category = self.create_category('Technologie')

    def test_list_categories_public(self):
        """N'importe qui peut lister les catégories."""
        response = self.client.get(reverse('category-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_slug_auto_generated(self):
        """Le slug est auto-généré depuis le nom."""
        self.authenticate(self.token)
        # Les catégories sont créées par admin, on teste directement le modèle
        cat = Category.objects.create(name='Data Science')
        self.assertEqual(cat.slug, 'data-science')

    def test_post_count_in_category(self):
        """post_count dans la réponse correspond aux posts publiés."""
        author, _ = self.create_user('bob')
        # 2 posts publiés, 1 draft
        self.create_post(author, category=self.category, status='published')
        self.create_post(author, category=self.category, status='published')
        self.create_post(author, category=self.category, status='draft')

        response = self.client.get(reverse('category-detail', kwargs={'pk': self.category.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['post_count'], 2)  # Seulement les publiés


# ─────────────────────────────────────────
# Tests des posts — CRUD
# ─────────────────────────────────────────

class PostCRUDTest(BlogTestMixin, APITestCase):

    def setUp(self):
        self.alice, self.alice_token = self.create_user('alice')
        self.bob, self.bob_token = self.create_user('bob')
        self.category = self.create_category()
        self.tag = self.create_tag()

    def test_list_posts_shows_only_published_to_anonymous(self):
        """Les non-authentifiés ne voient que les posts publiés."""
        self.create_post(self.alice, title='Draft', status='draft')
        self.create_post(self.alice, title='Publié', status='published')

        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Format paginé : results est dans data['results']
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('Publié', titles)
        self.assertNotIn('Draft', titles)

    def test_list_posts_shows_own_drafts_to_author(self):
        """L'auteur voit ses propres drafts + les posts publiés des autres."""
        self.create_post(self.alice, title='Mon draft', status='draft')
        self.create_post(self.bob, title='Post de Bob publié', status='published')

        self.authenticate(self.alice_token)
        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        titles = [p['title'] for p in response.data['results']]
        self.assertIn('Mon draft', titles)
        self.assertIn('Post de Bob publié', titles)

    def test_create_post_requires_auth(self):
        """Créer un post requiert d'être authentifié."""
        data = {'title': 'Test', 'content': 'Contenu'}
        response = self.client.post(reverse('post-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_post_success(self):
        """Un utilisateur authentifié peut créer un post."""
        self.authenticate(self.alice_token)
        data = {
            'title': 'Mon nouveau post',
            'content': 'Contenu détaillé du post.',
            'status': 'draft',
        }
        response = self.client.post(reverse('post-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # L'auteur est automatiquement alice
        post = Post.objects.get(id=response.data['id'])
        self.assertEqual(post.author, self.alice)

    def test_create_post_slug_auto_generated(self):
        """Le slug est auto-généré depuis le titre."""
        self.authenticate(self.alice_token)
        data = {
            'title': 'Mon Post Avec Accents Éàü',
            'content': 'Contenu...',
        }
        response = self.client.post(reverse('post-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = Post.objects.get(id=response.data['id'])
        self.assertTrue(len(post.slug) > 0)
        # Le slug ne doit pas contenir d'espaces
        self.assertNotIn(' ', post.slug)

    def test_create_post_with_category_and_tags(self):
        """On peut créer un post avec catégorie et tags."""
        self.authenticate(self.alice_token)
        data = {
            'title': 'Post avec meta',
            'content': 'Contenu...',
            'category': self.category.pk,
            'tags': [self.tag.pk],
        }
        response = self.client.post(reverse('post-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = Post.objects.get(id=response.data['id'])
        self.assertEqual(post.category, self.category)
        self.assertIn(self.tag, post.tags.all())

    def test_retrieve_published_post_anonymous(self):
        """N'importe qui peut voir un post publié."""
        post = self.create_post(self.alice, status='published')
        response = self.client.get(reverse('post-detail', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], post.title)

    def test_retrieve_draft_forbidden_to_anonymous(self):
        """Un draft est interdit aux anonymes."""
        post = self.create_post(self.alice, status='draft')
        response = self.client.get(reverse('post-detail', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_draft_visible_to_author(self):
        """L'auteur peut voir son propre draft."""
        post = self.create_post(self.alice, status='draft')
        self.authenticate(self.alice_token)
        response = self.client.get(reverse('post-detail', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_draft_forbidden_to_other_user(self):
        """Un autre utilisateur ne peut pas voir le draft d'alice."""
        post = self.create_post(self.alice, status='draft')
        self.authenticate(self.bob_token)
        response = self.client.get(reverse('post-detail', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_post_by_author(self):
        """L'auteur peut modifier son post."""
        post = self.create_post(self.alice)
        self.authenticate(self.alice_token)
        response = self.client.patch(
            reverse('post-detail', kwargs={'pk': post.pk}),
            {'title': 'Titre modifié'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.title, 'Titre modifié')

    def test_update_post_forbidden_to_other_user(self):
        """Bob ne peut pas modifier le post d'alice."""
        post = self.create_post(self.alice)
        self.authenticate(self.bob_token)
        response = self.client.patch(
            reverse('post-detail', kwargs={'pk': post.pk}),
            {'title': 'Modifié par Bob'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_post_by_author(self):
        """L'auteur peut supprimer son post."""
        post = self.create_post(self.alice)
        self.authenticate(self.alice_token)
        response = self.client.delete(reverse('post-detail', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_delete_post_forbidden_to_other_user(self):
        """Bob ne peut pas supprimer le post d'alice."""
        post = self.create_post(self.alice)
        self.authenticate(self.bob_token)
        response = self.client.delete(reverse('post-detail', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())


# ─────────────────────────────────────────
# Tests des actions personnalisées
# ─────────────────────────────────────────

class PostActionsTest(BlogTestMixin, APITestCase):

    def setUp(self):
        self.alice, self.alice_token = self.create_user('alice')
        self.bob, self.bob_token = self.create_user('bob')

    def test_publish_action_by_author(self):
        """L'auteur peut publier son post via l'action /publish/."""
        post = self.create_post(self.alice, status='draft')
        self.authenticate(self.alice_token)

        response = self.client.post(reverse('post-publish', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        post.refresh_from_db()
        self.assertEqual(post.status, Post.PUBLISHED)
        self.assertIsNotNone(post.published_at)

    def test_publish_action_forbidden_for_non_author(self):
        """Bob ne peut pas publier le post d'alice."""
        post = self.create_post(self.alice, status='draft')
        self.authenticate(self.bob_token)

        response = self.client.post(reverse('post-publish', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_publish_already_published_post(self):
        """Publier un post déjà publié retourne 400."""
        post = self.create_post(self.alice, status='published')
        self.authenticate(self.alice_token)

        response = self.client.post(reverse('post-publish', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_my_posts_requires_auth(self):
        """GET /posts/my_posts/ requiert d'être authentifié."""
        response = self.client.get(reverse('post-my-posts'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_posts_returns_only_user_posts(self):
        """my_posts retourne seulement les posts de l'utilisateur connecté."""
        # Alice a 2 posts, Bob en a 1
        self.create_post(self.alice, title='Post Alice 1', status='published')
        self.create_post(self.alice, title='Post Alice 2', status='draft')
        self.create_post(self.bob, title='Post Bob 1', status='published')

        self.authenticate(self.alice_token)
        response = self.client.get(reverse('post-my-posts'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        titles = [p['title'] for p in response.data['results']]
        self.assertIn('Post Alice 1', titles)
        self.assertIn('Post Alice 2', titles)
        self.assertNotIn('Post Bob 1', titles)

    def test_get_comments_of_post(self):
        """GET /posts/{id}/comments/ retourne les commentaires du post."""
        post = self.create_post(self.alice, status='published')
        self.create_comment(post, self.bob, 'Premier commentaire')
        self.create_comment(post, self.alice, 'Deuxième commentaire')

        response = self.client.get(reverse('post-comments', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_add_comment_to_post(self):
        """Un utilisateur authentifié peut commenter un post."""
        post = self.create_post(self.alice, status='published')
        self.authenticate(self.bob_token)

        response = self.client.post(
            reverse('post-comments', kwargs={'pk': post.pk}),
            {'content': 'Super article !'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(post.comments.count(), 1)

    def test_add_comment_requires_auth(self):
        """Commenter requiert d'être authentifié."""
        post = self.create_post(self.alice, status='published')
        response = self.client.post(
            reverse('post-comments', kwargs={'pk': post.pk}),
            {'content': 'Commentaire anonyme'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────
# Tests de pagination
# ─────────────────────────────────────────

class PaginationTest(BlogTestMixin, APITestCase):

    def setUp(self):
        self.alice, _ = self.create_user('alice')
        # Créer 15 posts publiés
        for i in range(15):
            self.create_post(self.alice, title=f'Post {i+1}', status='published')

    def test_pagination_returns_paginated_response(self):
        """La réponse contient le format paginé personnalisé."""
        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Notre format personnalisé
        self.assertIn('pagination', response.data)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data['pagination'])
        self.assertIn('page', response.data['pagination'])
        self.assertIn('pages', response.data['pagination'])

    def test_pagination_page_size(self):
        """La première page contient page_size résultats (défaut=10)."""
        response = self.client.get(reverse('post-list'))
        self.assertEqual(len(response.data['results']), 10)
        self.assertEqual(response.data['pagination']['count'], 15)

    def test_pagination_page_2(self):
        """La deuxième page contient les posts restants."""
        response = self.client.get(reverse('post-list') + '?page=2')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_pagination_custom_page_size(self):
        """Le client peut définir page_size."""
        response = self.client.get(reverse('post-list') + '?page_size=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_pagination_max_page_size(self):
        """page_size ne peut pas dépasser max_page_size (100)."""
        # Créer assez de posts
        for i in range(95):
            self.create_post(self.alice, title=f'Extra post {i}', status='published')

        response = self.client.get(reverse('post-list') + '?page_size=200')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # DRF restreint automatiquement à max_page_size
        self.assertLessEqual(len(response.data['results']), 100)


# ─────────────────────────────────────────
# Tests de filtres
# ─────────────────────────────────────────

class FilterTest(BlogTestMixin, APITestCase):

    def setUp(self):
        self.alice, _ = self.create_user('alice')
        self.bob, _ = self.create_user('bob')

        self.tech = self.create_category('Technologie')
        self.dev = self.create_category('Developpement')

        self.python_tag = self.create_tag('Python')
        self.django_tag = Tag.objects.create(name='Django')

        # Posts de test
        p1 = self.create_post(self.alice, title='Python intro', status='published', category=self.tech)
        p1.tags.add(self.python_tag)

        p2 = self.create_post(self.alice, title='Django guide', status='published', category=self.dev)
        p2.tags.add(self.python_tag, self.django_tag)

        p3 = self.create_post(self.bob, title='Bob article', status='published', category=self.tech)
        p3.tags.add(self.django_tag)

        self.create_post(self.alice, title='Draft privé', status='draft', category=self.tech)

    def test_filter_by_category_slug(self):
        """Filtrer par slug de catégorie."""
        response = self.client.get(reverse('post-list') + '?category_slug=technologie')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 2 posts publiés dans "technologie" (python intro + bob article)
        for post in response.data['results']:
            self.assertEqual(post['category']['slug'], 'technologie')

    def test_filter_by_tag_slug(self):
        """Filtrer par slug de tag."""
        response = self.client.get(reverse('post-list') + '?tag_slug=python')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 2 posts avec le tag python
        self.assertEqual(response.data['pagination']['count'], 2)

    def test_filter_by_author(self):
        """Filtrer par username d'auteur."""
        response = self.client.get(reverse('post-list') + '?author=alice')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Alice a 2 posts publiés (pas le draft)
        self.assertEqual(response.data['pagination']['count'], 2)

    def test_search_in_title(self):
        """La recherche trouve dans le titre."""
        response = self.client.get(reverse('post-list') + '?search=django')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pagination']['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Django guide')

    def test_search_case_insensitive(self):
        """La recherche est insensible à la casse."""
        response_lower = self.client.get(reverse('post-list') + '?search=python')
        response_upper = self.client.get(reverse('post-list') + '?search=PYTHON')
        self.assertEqual(
            response_lower.data['pagination']['count'],
            response_upper.data['pagination']['count']
        )

    def test_ordering_by_created_at_desc(self):
        """Tri par date de création descendant."""
        response = self.client.get(reverse('post-list') + '?ordering=-created_at')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dates = [p['created_at'] for p in response.data['results']]
        # Les dates doivent être dans l'ordre décroissant
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_ordering_by_title(self):
        """Tri par titre alphabétique."""
        response = self.client.get(reverse('post-list') + '?ordering=title')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertEqual(titles, sorted(titles))

    def test_combined_filters(self):
        """Combinaison de filtres."""
        response = self.client.get(
            reverse('post-list') + '?category_slug=technologie&search=python'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 1 post (python intro dans technologie)
        self.assertEqual(response.data['pagination']['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Python intro')


# ─────────────────────────────────────────
# Tests des modèles (unit tests)
# ─────────────────────────────────────────

class PostModelTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user('alice', 'alice@example.com', 'pass')

    def test_slug_auto_generated(self):
        """Le slug est généré automatiquement."""
        post = Post.objects.create(
            title='Mon Premier Article',
            content='Contenu...',
            author=self.user,
        )
        self.assertEqual(post.slug, 'mon-premier-article')

    def test_slug_unique(self):
        """Des posts avec le même titre ont des slugs différents."""
        post1 = Post.objects.create(title='Article Test', content='...', author=self.user)
        post2 = Post.objects.create(title='Article Test', content='...', author=self.user)
        self.assertNotEqual(post1.slug, post2.slug)
        # Le second a un suffixe numérique
        self.assertTrue(post2.slug.startswith('article-test-'))

    def test_excerpt_auto_generated(self):
        """L'extrait est généré depuis le contenu."""
        long_content = 'A' * 300
        post = Post.objects.create(title='Test', content=long_content, author=self.user)
        self.assertEqual(len(post.excerpt), 203)  # 200 + '...'
        self.assertTrue(post.excerpt.endswith('...'))

    def test_published_at_set_on_publish(self):
        """published_at est défini quand le post est publié."""
        post = Post.objects.create(title='Test', content='...', author=self.user)
        self.assertIsNone(post.published_at)

        post.status = Post.PUBLISHED
        post.save()
        self.assertIsNotNone(post.published_at)

    def test_is_published_property(self):
        """La propriété is_published retourne le bon statut."""
        post = Post.objects.create(title='Test', content='...', author=self.user, status='draft')
        self.assertFalse(post.is_published)

        post.status = Post.PUBLISHED
        post.save()
        self.assertTrue(post.is_published)

    def test_comment_count_property(self):
        """comment_count retourne le bon nombre."""
        post = Post.objects.create(title='Test', content='...', author=self.user, status='published')
        self.assertEqual(post.comment_count, 0)

        Comment.objects.create(post=post, author=self.user, content='Commentaire')
        self.assertEqual(post.comment_count, 1)
```

---

## Exécuter les tests

### Avec Django

```bash
# Tous les tests
python manage.py test blog

# Un TestCase spécifique
python manage.py test blog.tests.PostCRUDTest

# Un test spécifique
python manage.py test blog.tests.PostCRUDTest.test_create_post_success

# Avec verbosité
python manage.py test blog -v 2
```

### Avec pytest-django

```bash
pip install pytest pytest-django

# Créer pytest.ini
cat > pytest.ini << EOF
[pytest]
DJANGO_SETTINGS_MODULE = blog_api.settings
python_files = tests.py test_*.py
EOF

# Lancer
pytest blog/tests.py -v
pytest blog/tests.py -v --tb=short  # Traceback courte
pytest blog/tests.py -k "permission"  # Seulement les tests de permission
pytest blog/tests.py -v --no-header   # Sans l'en-tête pytest
```

---

## Résultats attendus

```
blog.tests.AuthAPITest
  test_login_invalid_credentials ... ok
  test_login_success ... ok
  test_logout_invalidates_token ... ok
  test_me_requires_auth ... ok
  test_me_returns_current_user ... ok
  test_register_duplicate_username ... ok
  test_register_password_mismatch ... ok
  test_register_success ... ok

blog.tests.PostCRUDTest
  test_create_post_requires_auth ... ok
  test_create_post_slug_auto_generated ... ok
  test_create_post_success ... ok
  test_create_post_with_category_and_tags ... ok
  test_delete_post_by_author ... ok
  test_delete_post_forbidden_to_other_user ... ok
  ...

----------------------------------------------------------------------
Ran 42 tests in 1.847s

OK
```

---

## Résumé du jour et du projet

Aujourd'hui tu as :
1. Écrit des tests unitaires pour les modèles (slug, excerpt, published_at)
2. Écrit des tests d'intégration pour l'API (CRUD, permissions, pagination, filtres)
3. Utilisé `APITestCase` et `APIClient` pour simuler des requêtes HTTP
4. Créé un mixin réutilisable pour les helpers de test
5. Organisé les tests par fonctionnalité (auth, CRUD, actions, pagination, filtres)

### Bilan du Project 01 — Blog API

| Jour | Sujet | Fichiers créés |
|------|-------|----------------|
| 34 | Modèles | models.py, admin.py |
| 35 | Serializers et ViewSets | serializers.py, views.py, urls.py |
| 36 | Permissions | permissions.py, views.py (update) |
| 37 | Pagination et filtres | pagination.py, filters.py, views.py (update) |
| 38 | Tests | tests.py |

L'API est maintenant complète et testée. Prochain projet : **E-commerce API** !
