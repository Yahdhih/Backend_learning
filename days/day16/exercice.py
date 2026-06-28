"""
Jour 16 — Exercice : Vues fonctionnelles Django testées avec RequestFactory

Objectif : implémenter 3 vues (liste, détail, créer) et les tester
sans lancer de serveur, grâce à RequestFactory et django.test.

Exécution :
    python exercice.py
"""

# ─── Setup Django minimal ─────────────────────────────────────────────────────
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='cle-secrete-pour-exercice-local',
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',  # base en RAM, pas de fichier
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',  # nécessaire pour User
        ],
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
        ROOT_URLCONF=__name__,  # ce fichier contient les urlpatterns
    )
    django.setup()

# ─── Création des tables ──────────────────────────────────────────────────────
from django.test.utils import setup_test_environment
from django.db import connection

setup_test_environment()

# On crée les tables manuellement pour cet exercice autonome
with connection.schema_editor() as schema_editor:
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType
    try:
        schema_editor.create_model(ContentType)
    except Exception:
        pass
    try:
        schema_editor.create_model(User)
    except Exception:
        pass

# ─── Modèle Article simple (en mémoire) ──────────────────────────────────────
# On simule le modèle avec un dictionnaire (pas de vraie DB pour garder
# l'exercice focalisé sur les vues, pas sur les models)
import json
from datetime import datetime

_articles_db = {}
_next_id = 1


def _article_suivant_id():
    global _next_id
    id_ = _next_id
    _next_id += 1
    return id_


def _serialiser(article: dict) -> dict:
    """Retourne une copie JSON-safe de l'article."""
    return {**article, 'date_creation': article['date_creation'].isoformat()}


# ─── Les 3 vues ───────────────────────────────────────────────────────────────
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


def liste_articles(request: HttpRequest) -> JsonResponse:
    """
    GET /articles/
    Retourne la liste de tous les articles sous forme JSON.
    Supporte un paramètre ?publie=true pour filtrer.
    """
    articles = list(_articles_db.values())

    # Filtrage optionnel par statut de publication
    filtre_publie = request.GET.get('publie')
    if filtre_publie is not None:
        publie = filtre_publie.lower() == 'true'
        articles = [a for a in articles if a['publie'] == publie]

    # Tri par date décroissante
    articles.sort(key=lambda a: a['date_creation'], reverse=True)

    return JsonResponse({
        'articles': [_serialiser(a) for a in articles],
        'total': len(articles),
    })


def detail_article(request: HttpRequest, pk: int) -> JsonResponse:
    """
    GET /articles/<pk>/
    Retourne le détail d'un article ou 404.
    """
    article = _articles_db.get(pk)
    if article is None:
        return JsonResponse(
            {'erreur': f"Article {pk} introuvable"},
            status=404,
        )
    return JsonResponse(_serialiser(article))


@csrf_exempt  # pour les tests sans token CSRF
def creer_article(request: HttpRequest) -> JsonResponse:
    """
    POST /articles/
    Corps JSON attendu : {"titre": "...", "contenu": "...", "publie": false}
    Retourne l'article créé avec status 201.
    """
    if request.method != 'POST':
        return JsonResponse(
            {'erreur': f"Méthode {request.method} non autorisée"},
            status=405,
        )

    # Désérialisation du corps JSON
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'erreur': 'Corps JSON invalide'}, status=400)

    # Validation
    erreurs = {}
    titre = str(data.get('titre', '')).strip()
    contenu = str(data.get('contenu', '')).strip()

    if not titre:
        erreurs['titre'] = 'Ce champ est requis.'
    elif len(titre) > 200:
        erreurs['titre'] = f'200 caractères max (reçu {len(titre)}).'

    if not contenu:
        erreurs['contenu'] = 'Ce champ est requis.'

    if erreurs:
        return JsonResponse({'erreurs': erreurs}, status=400)

    # Création en "base"
    pk = _article_suivant_id()
    article = {
        'id': pk,
        'titre': titre,
        'contenu': contenu,
        'publie': bool(data.get('publie', False)),
        'date_creation': datetime.now(),
    }
    _articles_db[pk] = article

    return JsonResponse(_serialiser(article), status=201)


# ─── URLs (requis par ROOT_URLCONF=__name__) ──────────────────────────────────
from django.urls import path

urlpatterns = [
    path('articles/', liste_articles),
    path('articles/<int:pk>/', detail_article),
    path('articles/nouveau/', creer_article),
]


# ─── Tests avec RequestFactory ────────────────────────────────────────────────
from django.test import RequestFactory, TestCase
import unittest


class TestListeArticles(unittest.TestCase):
    """Tests de la vue liste_articles."""

    def setUp(self):
        # Réinitialiser la "base" avant chaque test
        global _articles_db, _next_id
        _articles_db = {}
        _next_id = 1
        self.factory = RequestFactory()

    def test_liste_vide(self):
        """Renvoie une liste vide quand il n'y a pas d'articles."""
        request = self.factory.get('/articles/')
        response = liste_articles(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['articles'], [])
        self.assertEqual(data['total'], 0)

    def test_liste_avec_articles(self):
        """Renvoie les articles existants."""
        # Pré-remplir la base directement
        _articles_db[1] = {
            'id': 1, 'titre': 'Article A', 'contenu': 'Contenu A',
            'publie': True, 'date_creation': datetime(2026, 7, 12, 10, 0),
        }
        _articles_db[2] = {
            'id': 2, 'titre': 'Article B', 'contenu': 'Contenu B',
            'publie': False, 'date_creation': datetime(2026, 7, 12, 11, 0),
        }

        request = self.factory.get('/articles/')
        response = liste_articles(request)

        data = json.loads(response.content)
        self.assertEqual(data['total'], 2)
        # Tri décroissant : Article B (11h) avant Article A (10h)
        self.assertEqual(data['articles'][0]['titre'], 'Article B')

    def test_filtre_publie(self):
        """Le paramètre ?publie=true filtre correctement."""
        _articles_db[1] = {
            'id': 1, 'titre': 'Publié', 'contenu': 'X',
            'publie': True, 'date_creation': datetime.now(),
        }
        _articles_db[2] = {
            'id': 2, 'titre': 'Brouillon', 'contenu': 'Y',
            'publie': False, 'date_creation': datetime.now(),
        }

        request = self.factory.get('/articles/', {'publie': 'true'})
        response = liste_articles(request)

        data = json.loads(response.content)
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['articles'][0]['titre'], 'Publié')


class TestDetailArticle(unittest.TestCase):
    """Tests de la vue detail_article."""

    def setUp(self):
        global _articles_db, _next_id
        _articles_db = {
            1: {
                'id': 1, 'titre': 'Mon article', 'contenu': 'Super contenu',
                'publie': True, 'date_creation': datetime(2026, 7, 12, 9, 0),
            }
        }
        _next_id = 2
        self.factory = RequestFactory()

    def test_detail_existant(self):
        """Retourne l'article complet si le pk existe."""
        request = self.factory.get('/articles/1/')
        response = detail_article(request, pk=1)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['id'], 1)
        self.assertEqual(data['titre'], 'Mon article')
        self.assertIn('date_creation', data)

    def test_detail_inexistant(self):
        """Retourne 404 si le pk n'existe pas."""
        request = self.factory.get('/articles/999/')
        response = detail_article(request, pk=999)

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('erreur', data)

    def test_detail_contient_tous_les_champs(self):
        """La réponse contient bien tous les champs attendus."""
        request = self.factory.get('/articles/1/')
        response = detail_article(request, pk=1)
        data = json.loads(response.content)

        champs_attendus = {'id', 'titre', 'contenu', 'publie', 'date_creation'}
        self.assertTrue(champs_attendus.issubset(data.keys()))


class TestCreerArticle(unittest.TestCase):
    """Tests de la vue creer_article."""

    def setUp(self):
        global _articles_db, _next_id
        _articles_db = {}
        _next_id = 1
        self.factory = RequestFactory()

    def _post_json(self, data: dict):
        """Helper : envoie une requête POST JSON."""
        return self.factory.post(
            '/articles/nouveau/',
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_creer_succes(self):
        """Crée un article avec des données valides."""
        request = self._post_json({
            'titre': 'Nouvel article',
            'contenu': 'Contenu de l\'article.',
            'publie': True,
        })
        response = creer_article(request)

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data['titre'], 'Nouvel article')
        self.assertEqual(data['publie'], True)
        self.assertIn('id', data)
        # Vérifie que l'article est bien en base
        self.assertIn(data['id'], _articles_db)

    def test_creer_titre_manquant(self):
        """Retourne 400 si le titre est absent."""
        request = self._post_json({'contenu': 'Contenu sans titre.'})
        response = creer_article(request)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('titre', data['erreurs'])

    def test_creer_contenu_manquant(self):
        """Retourne 400 si le contenu est absent."""
        request = self._post_json({'titre': 'Titre sans contenu'})
        response = creer_article(request)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('contenu', data['erreurs'])

    def test_creer_json_invalide(self):
        """Retourne 400 si le corps n'est pas du JSON valide."""
        request = self.factory.post(
            '/articles/nouveau/',
            data='pas du json {{{',
            content_type='application/json',
        )
        response = creer_article(request)
        self.assertEqual(response.status_code, 400)

    def test_creer_methode_get_refusee(self):
        """Retourne 405 si la méthode est GET."""
        request = self.factory.get('/articles/nouveau/')
        response = creer_article(request)
        self.assertEqual(response.status_code, 405)

    def test_creer_publie_defaut_false(self):
        """Sans champ 'publie', l'article est en brouillon par défaut."""
        request = self._post_json({'titre': 'Brouillon', 'contenu': 'Contenu'})
        response = creer_article(request)

        data = json.loads(response.content)
        self.assertEqual(data['publie'], False)

    def test_creer_titre_trop_long(self):
        """Retourne 400 si le titre dépasse 200 caractères."""
        request = self._post_json({
            'titre': 'A' * 201,
            'contenu': 'Contenu valide.',
        })
        response = creer_article(request)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('titre', data['erreurs'])

    def test_creer_plusieurs_articles(self):
        """Les IDs sont incrémentaux."""
        for i in range(3):
            request = self._post_json({
                'titre': f'Article {i}',
                'contenu': f'Contenu {i}',
            })
            creer_article(request)

        self.assertEqual(len(_articles_db), 3)
        self.assertIn(1, _articles_db)
        self.assertIn(2, _articles_db)
        self.assertIn(3, _articles_db)


# ─── Point d'entrée ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("Jour 16 — Tests des vues fonctionnelles Django")
    print("=" * 60)
    print()

    # Lancer les tests avec un rapport détaillé
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for cls in [TestListeArticles, TestDetailArticle, TestCreerArticle]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    if result.wasSuccessful():
        print(f"Tous les tests passent ({result.testsRun} tests).")
    else:
        print(f"Échecs : {len(result.failures)}, Erreurs : {len(result.errors)}")
