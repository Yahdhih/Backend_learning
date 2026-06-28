"""
Jour 30 — Exercice : APIView et Response

Réécriture des vues du day20 (mini API blog) en utilisant DRF APIView.
- PostListView(APIView)  — GET (liste) + POST (créer)
- PostDetailView(APIView) — GET + PUT + DELETE

Avec serializers du day29 et tests avec DRF's APIClient.

Lance : python exercice.py
"""

import django
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '__main__')

from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'rest_framework',
        ],
        ROOT_URLCONF='__main__',
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
            ],
        },
    )

django.setup()

# ─────────────────────────────────────────────────────────────
# Modèles
# ─────────────────────────────────────────────────────────────
from django.db import models
from django.contrib.auth.models import User


class Post(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Brouillon'),
        (STATUS_PUBLISHED, 'Publié'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'auth'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# ─────────────────────────────────────────────────────────────
# Serializers (version simplifiée du day29)
# ─────────────────────────────────────────────────────────────
from rest_framework import serializers


class PostSerializer(serializers.ModelSerializer):
    """Serializer de base pour Post."""
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'content',
            'author',
            'author_username',
            'status',
            'created_at',
            'updated_at',
            'views_count',
        ]
        read_only_fields = ['id', 'author', 'author_username', 'created_at', 'updated_at', 'views_count']

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("Le titre doit faire au moins 5 caractères.")
        return value

    def validate_content(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Le contenu ne peut pas être vide.")
        return value


class PostUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour — tous les champs éditables.
    On sépare create et update pour plus de clarté.
    """

    class Meta:
        model = Post
        fields = ['title', 'content', 'status']

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("Le titre doit faire au moins 5 caractères.")
        return value


# ─────────────────────────────────────────────────────────────
# Vues : APIView
# ─────────────────────────────────────────────────────────────
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import NotFound, PermissionDenied
from django.shortcuts import get_object_or_404


class PostListView(APIView):
    """
    GET  /api/posts/   → liste des posts publiés (+ filtres par query params)
    POST /api/posts/   → créer un post (authentification requise)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        """
        Retourne la liste des posts.
        Query params supportés :
        - ?status=published|draft  (défaut : published)
        - ?search=mot              (recherche dans le titre)
        - ?author=<user_id>        (filtrer par auteur)
        """
        queryset = Post.objects.all()

        # Filtre par statut
        status_filter = request.query_params.get('status', 'published')
        if status_filter in [Post.STATUS_DRAFT, Post.STATUS_PUBLISHED]:
            queryset = queryset.filter(status=status_filter)

        # Recherche dans le titre
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(title__icontains=search)

        # Filtre par auteur
        author_id = request.query_params.get('author')
        if author_id:
            try:
                queryset = queryset.filter(author_id=int(author_id))
            except (ValueError, TypeError):
                pass

        serializer = PostSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
        })

    def post(self, request):
        """
        Crée un nouveau post.
        L'auteur est automatiquement l'utilisateur authentifié.
        """
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            # Injecter l'auteur depuis request.user
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    """
    GET    /api/posts/<pk>/  → détail d'un post
    PUT    /api/posts/<pk>/  → mise à jour complète (auteur seulement)
    PATCH  /api/posts/<pk>/  → mise à jour partielle (auteur seulement)
    DELETE /api/posts/<pk>/  → suppression (auteur seulement)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, pk: int) -> Post:
        """Récupère le post ou lève 404."""
        return get_object_or_404(Post, pk=pk)

    def check_author(self, post: Post, user) -> None:
        """Vérifie que l'utilisateur est l'auteur. Lève 403 sinon."""
        if post.author != user:
            raise PermissionDenied(
                "Seul l'auteur peut modifier ou supprimer ce post."
            )

    def get(self, request, pk: int):
        """Retourne le détail d'un post. Incrémente le compteur de vues."""
        post = self.get_object(pk)
        # Incrémenter le compteur de vues (update() évite de déclencher auto_now)
        Post.objects.filter(pk=pk).update(views_count=models.F('views_count') + 1)
        post.refresh_from_db()

        serializer = PostSerializer(post, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk: int):
        """Mise à jour complète d'un post (tous les champs requis)."""
        post = self.get_object(pk)
        self.check_author(post, request.user)

        serializer = PostUpdateSerializer(post, data=request.data)
        if serializer.is_valid():
            serializer.save()
            # Retourner avec le serializer complet
            return Response(PostSerializer(post).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk: int):
        """Mise à jour partielle d'un post (seuls les champs fournis sont modifiés)."""
        post = self.get_object(pk)
        self.check_author(post, request.user)

        serializer = PostUpdateSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(PostSerializer(post).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk: int):
        """Supprime un post. Retourne 204 No Content."""
        post = self.get_object(pk)
        self.check_author(post, request.user)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────
# URLs
# ─────────────────────────────────────────────────────────────
from django.urls import path

urlpatterns = [
    path('api/posts/', PostListView.as_view(), name='post-list'),
    path('api/posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
]


# ─────────────────────────────────────────────────────────────
# Tests avec APIClient
# ─────────────────────────────────────────────────────────────
import unittest
from django.test import TestCase
from rest_framework.test import APIClient


class TestPostListView(TestCase):
    """Tests pour GET /api/posts/ et POST /api/posts/."""

    def setUp(self):
        self.client = APIClient()
        self.auteur = User.objects.create_user(
            username='alice', email='alice@example.com', password='pass123'
        )
        self.autre_user = User.objects.create_user(
            username='bob', email='bob@example.com', password='pass123'
        )
        # Créer quelques posts
        self.post1 = Post.objects.create(
            title='Premier article Python',
            content='Contenu sur Python et ses applications.',
            author=self.auteur,
            status=Post.STATUS_PUBLISHED,
        )
        self.post2 = Post.objects.create(
            title='Second article Django',
            content='Contenu sur Django REST Framework.',
            author=self.auteur,
            status=Post.STATUS_PUBLISHED,
        )
        self.post_brouillon = Post.objects.create(
            title='Brouillon en cours',
            content='Contenu non terminé.',
            author=self.auteur,
            status=Post.STATUS_DRAFT,
        )

    # ── GET ──

    def test_get_liste_posts_publies(self):
        """GET /api/posts/ retourne seulement les posts publiés."""
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('results', data)
        self.assertEqual(data['count'], 2)  # seulement les publiés

    def test_get_liste_sans_authentification(self):
        """GET /api/posts/ est accessible sans authentification."""
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 200)

    def test_get_filtre_par_statut_brouillon(self):
        """GET /api/posts/?status=draft retourne les brouillons."""
        response = self.client.get('/api/posts/?status=draft')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['status'], 'draft')

    def test_get_recherche_dans_titre(self):
        """GET /api/posts/?search=Python retourne les posts contenant 'Python'."""
        response = self.client.get('/api/posts/?search=Python')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertIn('Python', data['results'][0]['title'])

    def test_get_recherche_insensible_casse(self):
        """La recherche est insensible à la casse."""
        response = self.client.get('/api/posts/?search=python')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)

    def test_get_filtre_par_auteur(self):
        """GET /api/posts/?author=<id> filtre par auteur."""
        response = self.client.get(f'/api/posts/?author={self.auteur.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 2)  # publiés de cet auteur

    # ── POST ──

    def test_post_cree_post_authentifie(self):
        """POST /api/posts/ crée un post avec l'auteur = user authentifié."""
        self.client.force_authenticate(user=self.auteur)
        data = {
            'title': 'Nouvel article de test',
            'content': 'Contenu de mon nouvel article créé via API.',
        }
        response = self.client.post('/api/posts/', data, format='json')
        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertEqual(response_data['title'], 'Nouvel article de test')
        self.assertEqual(response_data['author_username'], 'alice')
        self.assertEqual(response_data['author'], self.auteur.id)

    def test_post_sans_authentification(self):
        """POST /api/posts/ sans auth → 403."""
        data = {'title': 'Article sans auth', 'content': 'Contenu quelconque.'}
        response = self.client.post('/api/posts/', data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_post_titre_trop_court(self):
        """POST avec titre trop court → 400 avec erreur sur 'title'."""
        self.client.force_authenticate(user=self.auteur)
        data = {'title': 'Hi', 'content': 'Contenu valide.'}
        response = self.client.post('/api/posts/', data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('title', response.json())

    def test_post_champs_manquants(self):
        """POST sans champs requis → 400."""
        self.client.force_authenticate(user=self.auteur)
        response = self.client.post('/api/posts/', {}, format='json')
        self.assertEqual(response.status_code, 400)


class TestPostDetailView(TestCase):
    """Tests pour GET/PUT/PATCH/DELETE /api/posts/<pk>/."""

    def setUp(self):
        self.client = APIClient()
        self.auteur = User.objects.create_user(
            username='claire', email='claire@example.com', password='pass123'
        )
        self.autre_user = User.objects.create_user(
            username='dave', email='dave@example.com', password='pass123'
        )
        self.post = Post.objects.create(
            title='Article détaillé',
            content='Contenu complet pour les tests de détail.',
            author=self.auteur,
            status=Post.STATUS_PUBLISHED,
        )

    # ── GET ──

    def test_get_detail_post(self):
        """GET /api/posts/<pk>/ retourne le détail du post."""
        response = self.client.get(f'/api/posts/{self.post.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['title'], 'Article détaillé')
        self.assertEqual(data['id'], self.post.id)

    def test_get_incremente_views_count(self):
        """GET /api/posts/<pk>/ incrémente views_count."""
        initial_views = self.post.views_count
        self.client.get(f'/api/posts/{self.post.id}/')
        self.post.refresh_from_db()
        self.assertEqual(self.post.views_count, initial_views + 1)

    def test_get_post_inexistant(self):
        """GET sur un post inexistant → 404."""
        response = self.client.get('/api/posts/99999/')
        self.assertEqual(response.status_code, 404)

    # ── PUT ──

    def test_put_mise_a_jour_complete(self):
        """PUT par l'auteur → mise à jour complète."""
        self.client.force_authenticate(user=self.auteur)
        data = {
            'title': 'Titre mis à jour complet',
            'content': 'Contenu entièrement réécrit.',
            'status': 'published',
        }
        response = self.client.put(f'/api/posts/{self.post.id}/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'Titre mis à jour complet')

    def test_put_par_autre_user(self):
        """PUT par un autre utilisateur → 403."""
        self.client.force_authenticate(user=self.autre_user)
        data = {
            'title': 'Tentative de modification',
            'content': 'Cela ne devrait pas passer.',
            'status': 'draft',
        }
        response = self.client.put(f'/api/posts/{self.post.id}/', data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_put_sans_authentification(self):
        """PUT sans auth → 403."""
        data = {'title': 'Sans auth', 'content': 'Contenu.', 'status': 'draft'}
        response = self.client.put(f'/api/posts/{self.post.id}/', data, format='json')
        self.assertEqual(response.status_code, 403)

    # ── PATCH ──

    def test_patch_mise_a_jour_partielle(self):
        """PATCH par l'auteur → seul le titre change."""
        self.client.force_authenticate(user=self.auteur)
        response = self.client.patch(
            f'/api/posts/{self.post.id}/',
            {'title': 'Nouveau titre uniquement'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'Nouveau titre uniquement')
        # Le contenu ne change pas
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, 'Contenu complet pour les tests de détail.')

    # ── DELETE ──

    def test_delete_par_auteur(self):
        """DELETE par l'auteur → 204, post supprimé."""
        self.client.force_authenticate(user=self.auteur)
        response = self.client.delete(f'/api/posts/{self.post.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.filter(pk=self.post.id).exists())

    def test_delete_par_autre_user(self):
        """DELETE par un autre utilisateur → 403."""
        self.client.force_authenticate(user=self.autre_user)
        response = self.client.delete(f'/api/posts/{self.post.id}/')
        self.assertEqual(response.status_code, 403)
        # Le post existe toujours
        self.assertTrue(Post.objects.filter(pk=self.post.id).exists())

    def test_delete_sans_authentification(self):
        """DELETE sans auth → 403."""
        response = self.client.delete(f'/api/posts/{self.post.id}/')
        self.assertEqual(response.status_code, 403)


# ─────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    from django.test.runner import DiscoverRunner
    runner = DiscoverRunner(verbosity=0)
    old_config = runner.setup_databases()

    print("=" * 60)
    print("Tests Jour 30 — DRF APIView et Response")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPostListView))
    suite.addTests(loader.loadTestsFromTestCase(TestPostDetailView))

    result = unittest.TextTestRunner(verbosity=2).run(suite)

    runner.teardown_databases(old_config)
    sys.exit(0 if result.wasSuccessful() else 1)
