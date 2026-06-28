"""
Jour 29 — Exercice : Serializers pour un Blog (Post, Author, Comment)

Objectifs :
1. PostSerializer simple (ModelSerializer de base)
2. PostDetailSerializer avec auteur imbriqué et comptage de commentaires
3. Validation custom (titre min 5 chars, mots interdits)
4. CommentCreateSerializer avec validation

Lance les tests : python -m pytest exercice.py -v
Ou : python exercice.py
"""

import django
import os
import sys

# ─────────────────────────────────────────────────────────────
# Configuration Django minimale (in-memory, pas de fichier settings)
# ─────────────────────────────────────────────────────────────
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
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
        },
    )

django.setup()

# ─────────────────────────────────────────────────────────────
# Modèles
# ─────────────────────────────────────────────────────────────
from django.db import models
from django.contrib.auth.models import User


class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
    bio = models.TextField(blank=True)
    website = models.URLField(blank=True)

    class Meta:
        app_label = 'auth'  # rattaché à l'app auth pour éviter les migrations

    def __str__(self):
        return self.user.username


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


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        app_label = 'auth'
        ordering = ['created_at']

    def __str__(self):
        return f"Commentaire de {self.author.username} sur '{self.post.title}'"


# ─────────────────────────────────────────────────────────────
# Serializers
# ─────────────────────────────────────────────────────────────
from rest_framework import serializers

MOTS_INTERDITS = ['spam', 'promo', 'click here', 'buy now', 'gratuit']


def validate_no_spam(value: str) -> str:
    """Validateur réutilisable : détecte les mots interdits."""
    valeur_lower = value.lower()
    for mot in MOTS_INTERDITS:
        if mot in valeur_lower:
            raise serializers.ValidationError(
                f"Contenu interdit détecté : '{mot}'. Reformule ton texte."
            )
    return value


# ── 1. PostSerializer simple ─────────────────────────────────

class PostSerializer(serializers.ModelSerializer):
    """
    Serializer de base pour Post.
    - Inclut les champs essentiels
    - author est exposé comme ID (PrimaryKeyRelatedField par défaut)
    - id, created_at, updated_at, views_count sont en lecture seule
    """

    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'content',
            'author',
            'status',
            'created_at',
            'updated_at',
            'views_count',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'views_count']

    def validate_title(self, value: str) -> str:
        """Titre : minimum 5 caractères, pas de mots interdits."""
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError(
                "Le titre doit faire au moins 5 caractères."
            )
        return validate_no_spam(value)

    def validate_content(self, value: str) -> str:
        """Contenu : pas de spam."""
        return validate_no_spam(value)

    def validate(self, attrs: dict) -> dict:
        """Règle croisée : un post publié doit avoir du contenu non vide."""
        if attrs.get('status') == Post.STATUS_PUBLISHED:
            content = attrs.get('content', '').strip()
            if not content:
                raise serializers.ValidationError({
                    'content': "Un post publié ne peut pas avoir un contenu vide."
                })
        return attrs


# ── 2. PostDetailSerializer avec auteur imbriqué ─────────────

class AuthorSummarySerializer(serializers.ModelSerializer):
    """Représentation légère d'un auteur pour l'imbrication."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name']

    def get_full_name(self, obj: User) -> str:
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.username


class CommentSummarySerializer(serializers.ModelSerializer):
    """Résumé d'un commentaire pour l'imbrication dans PostDetail."""
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'author_username', 'content', 'created_at', 'is_approved']
        read_only_fields = ['id', 'created_at']


class PostDetailSerializer(serializers.ModelSerializer):
    """
    Serializer détaillé pour un Post.
    - author imbriqué (objet complet, lecture seule)
    - comments imbriqués (les commentaires approuvés)
    - comment_count calculé via SerializerMethodField
    - est_auteur : indique si l'utilisateur courant est l'auteur (via context)
    """
    author = AuthorSummarySerializer(read_only=True)
    comments = CommentSummarySerializer(many=True, read_only=True, source='approved_comments')
    comment_count = serializers.SerializerMethodField()
    pending_comments_count = serializers.SerializerMethodField()
    est_auteur = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'content',
            'author',
            'status',
            'created_at',
            'updated_at',
            'views_count',
            'comment_count',
            'pending_comments_count',
            'comments',
            'est_auteur',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'views_count']

    def get_comment_count(self, obj: Post) -> int:
        """Nombre total de commentaires (approuvés et en attente)."""
        return obj.comments.count()

    def get_pending_comments_count(self, obj: Post) -> int:
        """Nombre de commentaires en attente de modération."""
        return obj.comments.filter(is_approved=False).count()

    def get_est_auteur(self, obj: Post) -> bool:
        """True si l'utilisateur courant est l'auteur du post."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.author == request.user
        return False


# ── 3. CommentCreateSerializer avec validation ───────────────

class CommentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer un commentaire.
    - author est injecté depuis request.user (via view.perform_create)
    - post est passé dans le contexte ou la vue
    - Validation : contenu min 10 chars, pas de spam
    """
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'author_username', 'content', 'created_at', 'is_approved']
        read_only_fields = ['id', 'author', 'author_username', 'created_at', 'is_approved']

    def validate_content(self, value: str) -> str:
        """Contenu : minimum 10 caractères, pas de spam."""
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError(
                "Le commentaire doit faire au moins 10 caractères."
            )
        return validate_no_spam(value)

    def validate_post(self, value: Post) -> Post:
        """Vérifier que le post est publié avant d'y commenter."""
        if value.status != Post.STATUS_PUBLISHED:
            raise serializers.ValidationError(
                "Impossible de commenter un brouillon."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """Règle croisée : vérifier depuis le contexte si nécessaire."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            post = attrs.get('post')
            # Exemple : un auteur ne peut pas commenter son propre post
            if post and post.author == request.user:
                raise serializers.ValidationError(
                    "L'auteur d'un post ne peut pas commenter son propre article."
                )
        return attrs


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────
import unittest
from django.test.utils import setup_test_environment
from django.test import TestCase


def create_tables():
    """Crée les tables nécessaires dans la base in-memory."""
    from django.db import connection
    with connection.schema_editor() as schema_editor:
        try:
            schema_editor.create_model(User)
        except Exception:
            pass
        try:
            schema_editor.create_model(Post)
        except Exception:
            pass
        try:
            schema_editor.create_model(Comment)
        except Exception:
            pass


# Simuler un objet Request DRF minimal pour les tests de contexte
class MockRequest:
    def __init__(self, user=None):
        self.user = user


class TestPostSerializer(TestCase):
    """Tests pour PostSerializer (sérialisation et validation)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='motdepasse123',
        )
        self.post = Post.objects.create(
            title='Mon premier article de blog',
            content='Ceci est le contenu de test de mon article de blog Django.',
            author=self.user,
            status=Post.STATUS_DRAFT,
        )

    # ── Sérialisation ──

    def test_serialisation_champs_basiques(self):
        """PostSerializer retourne les champs attendus."""
        serializer = PostSerializer(self.post)
        data = serializer.data

        self.assertEqual(data['id'], self.post.id)
        self.assertEqual(data['title'], 'Mon premier article de blog')
        self.assertEqual(data['author'], self.user.id)
        self.assertEqual(data['status'], Post.STATUS_DRAFT)
        self.assertIn('created_at', data)
        self.assertIn('views_count', data)

    def test_champs_read_only_non_modifiables(self):
        """Les champs read_only ne doivent pas être modifiés par des données entrantes."""
        data = {
            'title': 'Nouveau titre valide',
            'content': 'Contenu de remplacement avec beaucoup de mots.',
            'author': 99,         # doit être ignoré (read_only)
            'views_count': 9999,  # doit être ignoré (read_only)
        }
        serializer = PostSerializer(self.post, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # views_count ne doit pas apparaître dans validated_data
        self.assertNotIn('views_count', serializer.validated_data)

    # ── Validation titre ──

    def test_validation_titre_trop_court(self):
        """Titre de moins de 5 caractères → erreur de validation."""
        data = {
            'title': 'Hi',
            'content': 'Du contenu pour le test.',
            'author': self.user.id,
        }
        serializer = PostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        self.assertIn('5', str(serializer.errors['title']))

    def test_validation_titre_mot_interdit(self):
        """Titre avec mot interdit → erreur de validation."""
        data = {
            'title': 'Offre spam incroyable',
            'content': 'Du contenu pour le test.',
            'author': self.user.id,
        }
        serializer = PostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        self.assertIn('spam', str(serializer.errors['title']))

    def test_validation_titre_valide(self):
        """Titre valide (>= 5 chars, pas de mots interdits) → OK."""
        data = {
            'title': 'Guide complet Django',
            'content': 'Contenu complet et informatif sur Django REST Framework.',
            'author': self.user.id,
        }
        serializer = PostSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    # ── Validation croisée ──

    def test_validation_croisee_publie_sans_contenu(self):
        """Post publié avec contenu vide → erreur croisée."""
        data = {
            'title': 'Article publié sans contenu',
            'content': '',
            'author': self.user.id,
            'status': Post.STATUS_PUBLISHED,
        }
        serializer = PostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        # L'erreur peut être dans 'content' ou dans 'non_field_errors'
        errors_str = str(serializer.errors)
        self.assertIn('publié', errors_str.lower() + 'contenu vide')

    def test_contenu_spam(self):
        """Contenu avec mot interdit → erreur sur 'content'."""
        data = {
            'title': 'Article légitime',
            'content': 'Cliquez sur ce lien buy now pour des offres!',
            'author': self.user.id,
        }
        serializer = PostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

    # ── Création ──

    def test_creation_post(self):
        """Un serializer valide peut créer un Post."""
        data = {
            'title': 'Nouvel article créé',
            'content': 'Le contenu de mon nouvel article de test.',
            'author': self.user.id,
        }
        serializer = PostSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        post = serializer.save()
        self.assertIsInstance(post, Post)
        self.assertEqual(post.title, 'Nouvel article créé')
        self.assertEqual(post.author, self.user)


class TestPostDetailSerializer(TestCase):
    """Tests pour PostDetailSerializer (auteur imbriqué, commentaires)."""

    def setUp(self):
        self.auteur = User.objects.create_user(
            username='bob',
            first_name='Bob',
            last_name='Martin',
            email='bob@example.com',
            password='motdepasse123',
        )
        self.lecteur = User.objects.create_user(
            username='carol',
            email='carol@example.com',
            password='motdepasse123',
        )
        self.post = Post.objects.create(
            title='Article détaillé de test',
            content='Un contenu très détaillé pour tester le serializer.',
            author=self.auteur,
            status=Post.STATUS_PUBLISHED,
        )
        # Ajouter des commentaires
        self.comment1 = Comment.objects.create(
            post=self.post,
            author=self.lecteur,
            content='Super article, merci!',
            is_approved=True,
        )
        self.comment2 = Comment.objects.create(
            post=self.post,
            author=self.lecteur,
            content='Commentaire en attente de modération.',
            is_approved=False,
        )

    def _add_approved_comments_manager(self):
        """
        PostDetailSerializer accède à obj.approved_comments.
        On l'ajoute dynamiquement pour ce test (en prod, ce serait
        un related_manager filtré ou une propriété sur le modèle).
        """
        # Simuler le queryset approved_comments sur l'instance
        approved = self.post.comments.filter(is_approved=True)
        self.post.approved_comments = approved

    def test_auteur_imbrique(self):
        """L'auteur doit être un objet imbriqué avec username, email, full_name."""
        self._add_approved_comments_manager()
        serializer = PostDetailSerializer(self.post)
        data = serializer.data

        self.assertIsInstance(data['author'], dict)
        self.assertEqual(data['author']['username'], 'bob')
        self.assertEqual(data['author']['email'], 'bob@example.com')
        self.assertEqual(data['author']['full_name'], 'Bob Martin')

    def test_comment_count(self):
        """comment_count doit compter tous les commentaires (approuvés + en attente)."""
        self._add_approved_comments_manager()
        serializer = PostDetailSerializer(self.post)
        data = serializer.data

        self.assertEqual(data['comment_count'], 2)
        self.assertEqual(data['pending_comments_count'], 1)

    def test_est_auteur_true(self):
        """est_auteur = True si l'utilisateur de la requête est l'auteur."""
        self._add_approved_comments_manager()
        request = MockRequest(user=self.auteur)
        self.auteur.is_authenticated = True

        serializer = PostDetailSerializer(self.post, context={'request': request})
        data = serializer.data

        self.assertTrue(data['est_auteur'])

    def test_est_auteur_false(self):
        """est_auteur = False pour un autre utilisateur."""
        self._add_approved_comments_manager()
        request = MockRequest(user=self.lecteur)
        self.lecteur.is_authenticated = True

        serializer = PostDetailSerializer(self.post, context={'request': request})
        data = serializer.data

        self.assertFalse(data['est_auteur'])


class TestCommentCreateSerializer(TestCase):
    """Tests pour CommentCreateSerializer."""

    def setUp(self):
        self.auteur = User.objects.create_user(
            username='diana', email='diana@example.com', password='motdepasse123'
        )
        self.lecteur = User.objects.create_user(
            username='eric', email='eric@example.com', password='motdepasse123'
        )
        self.post_publie = Post.objects.create(
            title='Article publié pour les commentaires',
            content='Contenu de l article publié.',
            author=self.auteur,
            status=Post.STATUS_PUBLISHED,
        )
        self.post_brouillon = Post.objects.create(
            title='Brouillon non publié',
            content='Contenu du brouillon.',
            author=self.auteur,
            status=Post.STATUS_DRAFT,
        )

    def test_commentaire_valide(self):
        """Un commentaire valide sur un post publié → OK."""
        data = {
            'post': self.post_publie.id,
            'content': 'Excellent article, très instructif pour les débutants!',
        }
        request = MockRequest(user=self.lecteur)
        self.lecteur.is_authenticated = True

        serializer = CommentCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_commentaire_trop_court(self):
        """Commentaire de moins de 10 chars → erreur."""
        data = {
            'post': self.post_publie.id,
            'content': 'Court',
        }
        serializer = CommentCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)
        self.assertIn('10', str(serializer.errors['content']))

    def test_commentaire_sur_brouillon(self):
        """Commenter un brouillon → erreur sur 'post'."""
        data = {
            'post': self.post_brouillon.id,
            'content': 'Ce commentaire ne devrait pas passer.',
        }
        serializer = CommentCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('post', serializer.errors)
        self.assertIn('brouillon', str(serializer.errors['post']))

    def test_auteur_ne_peut_pas_commenter_son_post(self):
        """L'auteur d'un post ne peut pas le commenter lui-même."""
        data = {
            'post': self.post_publie.id,
            'content': "Je commente mon propre article, c'est interdit ici.",
        }
        request = MockRequest(user=self.auteur)
        self.auteur.is_authenticated = True

        serializer = CommentCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_commentaire_avec_spam(self):
        """Commentaire contenant un mot interdit → erreur."""
        data = {
            'post': self.post_publie.id,
            'content': 'Visitez notre site promo pour des offres incroyables!',
        }
        serializer = CommentCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)


# ─────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    from django.test.utils import setup_test_environment
    setup_test_environment()

    # Créer les tables
    from django.db import connection
    from django.contrib.auth.models import User as DjangoUser

    # Utiliser Django's create_all
    from django.test.runner import DiscoverRunner
    runner = DiscoverRunner(verbosity=0)
    old_config = runner.setup_databases()

    print("=" * 60)
    print("Tests Jour 29 — DRF Serializers")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPostSerializer))
    suite.addTests(loader.loadTestsFromTestCase(TestPostDetailSerializer))
    suite.addTests(loader.loadTestsFromTestCase(TestCommentCreateSerializer))

    runner_unittest = unittest.TextTestRunner(verbosity=2)
    result = runner_unittest.run(suite)

    runner.teardown_databases(old_config)

    sys.exit(0 if result.wasSuccessful() else 1)
