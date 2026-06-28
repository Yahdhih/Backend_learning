"""
Exercice Jour 38 — Tests de l'API Blog
=======================================
Date : 3 août 2026

Objectif :
  Ce fichier présente la structure de tests à compléter.
  Les tests marqués TODO sont à implémenter.
  Lance `tester()` pour voir quels tests sont en place.

Utilisation :
  python manage.py test blog.tests
  pytest blog/tests.py -v
  python exercice.py  (pour voir la structure)
"""

# ─────────────────────────────────────────
# Structure complète de tests à copier dans blog/tests.py
# ─────────────────────────────────────────

FULL_TEST_STRUCTURE = """
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from blog.models import Category, Tag, Post, Comment


class BlogTestMixin:
    \"\"\"Helpers partagés entre tous les TestCases.\"\"\"

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
            content='Contenu de test pour cet article.',
            author=author,
            category=category,
            status=status,
        )

    def create_comment(self, post, author, content='Commentaire de test'):
        return Comment.objects.create(post=post, author=author, content=content)


class AuthAPITest(BlogTestMixin, APITestCase):
    \"\"\"Tests de register, login, logout, me.\"\"\"

    def test_register_success(self):
        # TODO: voir cours
        pass

    def test_register_password_mismatch(self):
        # TODO: voir cours
        pass

    def test_login_success(self):
        # TODO: voir cours
        pass

    def test_login_invalid_credentials(self):
        # TODO: voir cours
        pass

    def test_logout_invalidates_token(self):
        # TODO: voir cours
        pass

    def test_me_returns_current_user(self):
        # TODO: voir cours
        pass


class PostCRUDTest(BlogTestMixin, APITestCase):
    \"\"\"Tests CRUD des posts.\"\"\"

    def setUp(self):
        self.alice, self.alice_token = self.create_user('alice')
        self.bob, self.bob_token = self.create_user('bob')
        self.category = self.create_category()

    def test_list_shows_only_published_to_anonymous(self):
        # TODO
        pass

    def test_create_post_requires_auth(self):
        # TODO
        pass

    def test_create_post_success(self):
        # TODO
        pass

    def test_update_post_by_author(self):
        # TODO
        pass

    def test_update_post_forbidden_to_other_user(self):
        # TODO
        pass

    def test_delete_post_by_author(self):
        # TODO
        pass


class PostPermissionTest(BlogTestMixin, APITestCase):
    \"\"\"Tests de permission spécifiques.\"\"\"

    def setUp(self):
        self.alice, self.alice_token = self.create_user('alice')
        self.bob, self.bob_token = self.create_user('bob')

    def test_draft_not_visible_to_anonymous(self):
        # TODO
        pass

    def test_draft_visible_to_author(self):
        # TODO
        pass

    def test_draft_not_visible_to_other_user(self):
        # TODO
        pass

    def test_publish_action_by_author(self):
        # TODO
        pass

    def test_publish_action_forbidden_for_non_author(self):
        # TODO
        pass


class PaginationTest(BlogTestMixin, APITestCase):
    \"\"\"Tests de pagination.\"\"\"

    def setUp(self):
        self.alice, _ = self.create_user('alice')
        for i in range(15):
            self.create_post(self.alice, title=f'Post {i+1}', status='published')

    def test_paginated_response_format(self):
        # TODO : vérifier que 'pagination' et 'results' sont dans la réponse
        pass

    def test_default_page_size_is_10(self):
        # TODO
        pass

    def test_custom_page_size(self):
        # TODO
        pass

    def test_page_2_returns_remaining_items(self):
        # TODO
        pass


class FilterTest(BlogTestMixin, APITestCase):
    \"\"\"Tests de filtres et recherche.\"\"\"

    def setUp(self):
        self.alice, _ = self.create_user('alice')
        self.bob, _ = self.create_user('bob')
        self.tech = self.create_category('Technologie')
        self.dev = self.create_category('Developpement')
        self.python_tag = self.create_tag('Python')
        self.django_tag = Tag.objects.create(name='Django')

        p1 = self.create_post(self.alice, title='Python intro', status='published', category=self.tech)
        p1.tags.add(self.python_tag)
        p2 = self.create_post(self.alice, title='Django guide', status='published', category=self.dev)
        p2.tags.add(self.python_tag, self.django_tag)
        p3 = self.create_post(self.bob, title='Bob article', status='published', category=self.tech)

    def test_filter_by_category_slug(self):
        # TODO
        pass

    def test_filter_by_tag_slug(self):
        # TODO
        pass

    def test_filter_by_author(self):
        # TODO
        pass

    def test_search_in_title(self):
        # TODO
        pass

    def test_search_case_insensitive(self):
        # TODO
        pass

    def test_ordering_by_created_at(self):
        # TODO
        pass


class PostModelTest(APITestCase):
    \"\"\"Tests unitaires des modèles.\"\"\"

    def setUp(self):
        self.user = User.objects.create_user('alice', 'alice@example.com', 'pass')

    def test_slug_auto_generated(self):
        # TODO
        pass

    def test_slug_unique_for_duplicate_titles(self):
        # TODO
        pass

    def test_excerpt_auto_generated_from_content(self):
        # TODO
        pass

    def test_published_at_set_when_published(self):
        # TODO
        pass

    def test_comment_count_property(self):
        # TODO
        pass
"""


# ─────────────────────────────────────────
# Inventaire des tests
# ─────────────────────────────────────────

TESTS_INVENTORY = {
    "AuthAPITest": {
        "description": "Tests de register, login, logout, me",
        "tests": [
            ("test_register_success", "Un utilisateur peut s'inscrire avec des données valides"),
            ("test_register_password_mismatch", "L'inscription échoue si les mots de passe ne correspondent pas"),
            ("test_register_duplicate_username", "L'inscription échoue si le username existe déjà"),
            ("test_login_success", "Un utilisateur peut se connecter avec des identifiants valides"),
            ("test_login_invalid_credentials", "Le login échoue avec de mauvais identifiants"),
            ("test_logout_invalidates_token", "Après logout, le token ne fonctionne plus"),
            ("test_me_returns_current_user", "GET /auth/me/ retourne le profil de l'utilisateur connecté"),
            ("test_me_requires_auth", "GET /auth/me/ retourne 401 sans authentification"),
        ]
    },
    "PostCRUDTest": {
        "description": "Tests CRUD des posts",
        "tests": [
            ("test_list_posts_shows_only_published_to_anonymous", "Les non-authentifiés ne voient que les posts publiés"),
            ("test_list_posts_shows_own_drafts_to_author", "L'auteur voit ses propres drafts"),
            ("test_create_post_requires_auth", "Créer un post requiert d'être authentifié"),
            ("test_create_post_success", "Un utilisateur authentifié peut créer un post"),
            ("test_create_post_slug_auto_generated", "Le slug est auto-généré depuis le titre"),
            ("test_create_post_with_category_and_tags", "On peut créer un post avec catégorie et tags"),
            ("test_retrieve_published_post_anonymous", "N'importe qui peut voir un post publié"),
            ("test_retrieve_draft_forbidden_to_anonymous", "Un draft est interdit aux anonymes"),
            ("test_retrieve_draft_visible_to_author", "L'auteur peut voir son propre draft"),
            ("test_retrieve_draft_forbidden_to_other_user", "Un autre utilisateur ne peut pas voir le draft d'alice"),
            ("test_update_post_by_author", "L'auteur peut modifier son post"),
            ("test_update_post_forbidden_to_other_user", "Bob ne peut pas modifier le post d'alice"),
            ("test_delete_post_by_author", "L'auteur peut supprimer son post"),
            ("test_delete_post_forbidden_to_other_user", "Bob ne peut pas supprimer le post d'alice"),
        ]
    },
    "PostActionsTest": {
        "description": "Tests des actions personnalisées (publish, my_posts, comments)",
        "tests": [
            ("test_publish_action_by_author", "L'auteur peut publier son post"),
            ("test_publish_action_forbidden_for_non_author", "Bob ne peut pas publier le post d'alice"),
            ("test_publish_already_published_post", "Publier un post déjà publié retourne 400"),
            ("test_my_posts_requires_auth", "GET /posts/my_posts/ requiert d'être authentifié"),
            ("test_my_posts_returns_only_user_posts", "my_posts retourne seulement les posts de l'utilisateur"),
            ("test_get_comments_of_post", "GET /posts/{id}/comments/ retourne les commentaires"),
            ("test_add_comment_to_post", "Un utilisateur authentifié peut commenter"),
            ("test_add_comment_requires_auth", "Commenter requiert d'être authentifié"),
        ]
    },
    "PaginationTest": {
        "description": "Tests de pagination",
        "tests": [
            ("test_pagination_returns_paginated_response", "La réponse contient le format paginé personnalisé"),
            ("test_pagination_page_size", "La première page contient page_size résultats"),
            ("test_pagination_page_2", "La deuxième page contient les posts restants"),
            ("test_pagination_custom_page_size", "Le client peut définir page_size"),
            ("test_pagination_max_page_size", "page_size ne peut pas dépasser max_page_size"),
        ]
    },
    "FilterTest": {
        "description": "Tests de filtres et recherche",
        "tests": [
            ("test_filter_by_category_slug", "Filtrer par slug de catégorie"),
            ("test_filter_by_tag_slug", "Filtrer par slug de tag"),
            ("test_filter_by_author", "Filtrer par username d'auteur"),
            ("test_search_in_title", "La recherche trouve dans le titre"),
            ("test_search_case_insensitive", "La recherche est insensible à la casse"),
            ("test_ordering_by_created_at_desc", "Tri par date de création descendant"),
            ("test_ordering_by_title", "Tri par titre alphabétique"),
            ("test_combined_filters", "Combinaison de filtres"),
        ]
    },
    "PostModelTest": {
        "description": "Tests unitaires des modèles",
        "tests": [
            ("test_slug_auto_generated", "Le slug est généré automatiquement"),
            ("test_slug_unique", "Des posts avec le même titre ont des slugs différents"),
            ("test_excerpt_auto_generated", "L'extrait est généré depuis le contenu"),
            ("test_published_at_set_on_publish", "published_at est défini quand le post est publié"),
            ("test_is_published_property", "La propriété is_published retourne le bon statut"),
            ("test_comment_count_property", "comment_count retourne le bon nombre"),
        ]
    },
}

# Tests à compléter (TODOs)
TODO_TESTS = [
    {
        "class": "PostCRUDTest",
        "method": "test_create_post_validates_required_fields",
        "description": "La création échoue si title ou content est vide",
        "hint": "Envoie une requête POST sans 'title', vérifie le status 400 et le champ d'erreur",
    },
    {
        "class": "PostCRUDTest",
        "method": "test_create_post_sets_default_status_to_draft",
        "description": "Un post créé sans status explicite est en draft",
        "hint": "Crée un post sans le champ 'status', vérifie que post.status == 'draft'",
    },
    {
        "class": "FilterTest",
        "method": "test_filter_by_status",
        "description": "Filtrer par status (published/draft)",
        "hint": "?status=published ne doit retourner que les posts publiés",
    },
    {
        "class": "FilterTest",
        "method": "test_search_in_content",
        "description": "La recherche trouve dans le contenu aussi",
        "hint": "Crée un post avec 'unicorn' uniquement dans le contenu, cherche ?search=unicorn",
    },
    {
        "class": "PostActionsTest",
        "method": "test_comments_of_draft_forbidden_to_anonymous",
        "description": "On ne peut pas voir les commentaires d'un draft si on n'est pas l'auteur",
        "hint": "Crée un draft, accède à /posts/{id}/comments/ sans auth → 403",
    },
    {
        "class": "PostModelTest",
        "method": "test_category_set_null_on_category_delete",
        "description": "Quand une catégorie est supprimée, le post reste avec category=None",
        "hint": "Crée un post avec category, supprime la category, vérifie post.category is None",
    },
    {
        "class": "AuthAPITest",
        "method": "test_register_creates_token_automatically",
        "description": "L'inscription crée automatiquement un token pour l'utilisateur",
        "hint": "Après register, vérifie que Token.objects.filter(user=new_user).exists()",
    },
    {
        "class": "PaginationTest",
        "method": "test_pagination_invalid_page_returns_404",
        "description": "Demander une page qui n'existe pas retourne 404",
        "hint": "?page=9999 → 404 Not Found",
    },
]


# ─────────────────────────────────────────
# Fonction principale
# ─────────────────────────────────────────

def tester():
    """Affiche la structure de tests et les TODOs."""

    print("=" * 65)
    print("EXERCICE JOUR 38 — Tests de l'API Blog")
    print("=" * 65)
    print()

    # Compter les tests
    total_tests = sum(
        len(info["tests"]) for info in TESTS_INVENTORY.values()
    )
    print(f"Structure de tests : {len(TESTS_INVENTORY)} TestCases, {total_tests} tests au total")
    print()

    # Afficher les TestCases
    for class_name, info in TESTS_INVENTORY.items():
        print(f"  {class_name}")
        print(f"  {'─' * (len(class_name) + 2)}")
        print(f"  {info['description']}")
        print()
        for method, description in info["tests"]:
            print(f"    def {method}(self):")
            print(f"        # {description}")
        print()

    # Afficher les TODOs
    print("=" * 65)
    print(f"TODOs : {len(TODO_TESTS)} tests à implémenter toi-même")
    print("=" * 65)
    print()

    for i, todo in enumerate(TODO_TESTS, 1):
        print(f"  TODO {i} : {todo['class']}.{todo['method']}")
        print(f"  Objectif : {todo['description']}")
        print(f"  Indice   : {todo['hint']}")
        print()

    print("=" * 65)
    print("INSTRUCTIONS")
    print("=" * 65)
    print()
    print("1. Copie le code complet depuis le cours (blog/tests.py)")
    print("   → /Users/yahdhih/etudes/Juin-aout-26/backend_learning/")
    print("     Backend_learning/days/day38/cours.md")
    print()
    print("2. Lance tous les tests :")
    print("   python manage.py test blog -v 2")
    print()
    print("3. Implémente les TODOs ci-dessus (méthodes manquantes)")
    print()
    print("4. Vérifie que tous les tests passent :")
    print("   python manage.py test blog")
    print("   → Attendu : Ran N tests in X.Xs OK")
    print()
    print("5. BONUS : Lance avec pytest pour un meilleur affichage :")
    print("   pip install pytest pytest-django")
    print("   pytest blog/tests.py -v --tb=short")
    print()

    # Afficher le template des tests à copier
    print("=" * 65)
    print("TEMPLATE (structure vide — à compléter avec le cours)")
    print("=" * 65)
    print()
    print("Voir FULL_TEST_STRUCTURE en haut de ce fichier pour")
    print("la structure complète avec les méthodes TODO.")
    print()

    # Résumé des assertions utiles
    print("=" * 65)
    print("ASSERTIONS DRF UTILES")
    print("=" * 65)
    print()
    assertions = [
        ("assertEqual(response.status_code, status.HTTP_200_OK)", "Vérifier le code HTTP"),
        ("assertIn('token', response.data)", "Vérifier qu'une clé est dans la réponse"),
        ("assertEqual(len(response.data['results']), 10)", "Vérifier la taille de la liste"),
        ("assertFalse(Post.objects.filter(pk=post.pk).exists())", "Vérifier qu'un objet est supprimé"),
        ("post.refresh_from_db()", "Recharger l'objet depuis la DB après update"),
        ("self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')", "S'authentifier"),
        ("self.client.credentials()", "Se désauthentifier"),
        ("self.client.force_authenticate(user=user)", "Authentification forcée (bypass token)"),
    ]
    for assertion, description in assertions:
        print(f"  # {description}")
        print(f"  self.{assertion}")
        print()


# ─────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────

if __name__ == '__main__':
    tester()
