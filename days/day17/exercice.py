"""
Jour 17 — Exercice : Vues basées sur les classes (CBV)

Objectif : réécrire les 3 vues du jour 16 en CBV, comparer le volume
de code, et ajouter un JSONResponseMixin custom.

Exécution :
    python exercice.py
"""

# ─── Setup Django minimal ─────────────────────────────────────────────────────
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='cle-secrete-jour-17',
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
        ],
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
        ROOT_URLCONF=__name__,
    )
    django.setup()

# ─── Simulation de la "base de données" ──────────────────────────────────────
import json
from datetime import datetime

_articles_db: dict = {}
_next_id = 1


def _reset_db():
    """Réinitialise la base entre les tests."""
    global _articles_db, _next_id
    _articles_db = {}
    _next_id = 1


def _new_id() -> int:
    global _next_id
    id_ = _next_id
    _next_id += 1
    return id_


def _serialiser(article: dict) -> dict:
    return {**article, 'date_creation': article['date_creation'].isoformat()}


# ─── Mixin custom : JSONResponseMixin ────────────────────────────────────────
from django.http import JsonResponse


class JSONResponseMixin:
    """
    Mixin qui donne à n'importe quel CBV la capacité de répondre en JSON.

    Usage :
        class MaVue(JSONResponseMixin, View):
            def get(self, request):
                return self.json_response({'cle': 'valeur'})
    """

    def json_response(self, data: dict | list, status: int = 200) -> JsonResponse:
        """Raccourci pour créer une JsonResponse."""
        return JsonResponse(data, status=status, safe=isinstance(data, dict))

    def json_error(self, message: str, status: int = 400) -> JsonResponse:
        """Raccourci pour les réponses d'erreur."""
        return JsonResponse({'erreur': message}, status=status)

    def json_errors(self, erreurs: dict, status: int = 400) -> JsonResponse:
        """Raccourci pour les erreurs de validation multiples."""
        return JsonResponse({'erreurs': erreurs}, status=status)


# ─── Comparaison : FBV du jour 16 (rappel condensé) ─────────────────────────
# FBV — liste_articles : ~15 lignes
# FBV — detail_article : ~10 lignes
# FBV — creer_article  : ~30 lignes
# TOTAL FBV            : ~55 lignes de logique métier

# Les CBV ci-dessous font la même chose.
# Comparez vous-mêmes la différence de structure.


# ─── CBV version 1 : avec View de base ───────────────────────────────────────
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name='dispatch')
class ArticleListeView(JSONResponseMixin, View):
    """
    GET  /articles/     → liste des articles
    POST /articles/     → créer un article

    Équivalent CBV des fonctions liste_articles() et creer_article() du jour 16.

    Différence clé avec FBV :
    - Plus besoin de if/elif sur request.method
    - Chaque méthode HTTP a sa propre méthode Python
    - Le mixin ajoute json_response() sans if/else répété
    """

    def get(self, request):
        """Liste tous les articles, avec filtre optionnel ?publie=true."""
        articles = list(_articles_db.values())

        filtre = request.GET.get('publie')
        if filtre is not None:
            publie = filtre.lower() == 'true'
            articles = [a for a in articles if a['publie'] == publie]

        articles.sort(key=lambda a: a['date_creation'], reverse=True)

        return self.json_response({
            'articles': [_serialiser(a) for a in articles],
            'total': len(articles),
        })

    def post(self, request):
        """Crée un nouvel article."""
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.json_error('Corps JSON invalide')

        erreurs = self._valider(data)
        if erreurs:
            return self.json_errors(erreurs)

        pk = _new_id()
        article = {
            'id': pk,
            'titre': data['titre'].strip(),
            'contenu': data['contenu'].strip(),
            'publie': bool(data.get('publie', False)),
            'date_creation': datetime.now(),
        }
        _articles_db[pk] = article
        return self.json_response(_serialiser(article), status=201)

    def _valider(self, data: dict) -> dict:
        """Validation centralisée des données d'un article."""
        erreurs = {}
        titre = str(data.get('titre', '')).strip()
        contenu = str(data.get('contenu', '')).strip()

        if not titre:
            erreurs['titre'] = 'Ce champ est requis.'
        elif len(titre) > 200:
            erreurs['titre'] = f'200 caractères max (reçu {len(titre)}).'

        if not contenu:
            erreurs['contenu'] = 'Ce champ est requis.'

        return erreurs


@method_decorator(csrf_exempt, name='dispatch')
class ArticleDetailView(JSONResponseMixin, View):
    """
    GET    /articles/<pk>/  → détail d'un article
    PUT    /articles/<pk>/  → modifier un article
    DELETE /articles/<pk>/  → supprimer un article

    Notez que get_object() est factorisé dans la classe :
    plus besoin de répéter la logique dans get(), put(), delete().
    """

    def get_object(self, pk: int) -> dict | None:
        """Récupère l'article ou None. Factorisé pour éviter la répétition."""
        return _articles_db.get(pk)

    def get(self, request, pk: int):
        article = self.get_object(pk)
        if article is None:
            return self.json_error(f'Article {pk} introuvable', status=404)
        return self.json_response(_serialiser(article))

    def put(self, request, pk: int):
        article = self.get_object(pk)
        if article is None:
            return self.json_error(f'Article {pk} introuvable', status=404)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return self.json_error('Corps JSON invalide')

        # Mise à jour partielle (PATCH-like dans PUT)
        if 'titre' in data:
            article['titre'] = str(data['titre']).strip()
        if 'contenu' in data:
            article['contenu'] = str(data['contenu']).strip()
        if 'publie' in data:
            article['publie'] = bool(data['publie'])

        return self.json_response(_serialiser(article))

    def delete(self, request, pk: int):
        article = _articles_db.pop(pk, None)
        if article is None:
            return self.json_error(f'Article {pk} introuvable', status=404)
        return JsonResponse({}, status=204)


# ─── CBV version 2 : mixin avancé avec validation intégrée ──────────────────
class ValidatedArticleMixin(JSONResponseMixin):
    """
    Mixin qui centralise la validation des données d'un article.
    Peut être combiné avec n'importe quel View.

    Démontre la puissance de la composition de mixins.
    """

    required_fields_for_create = ['titre', 'contenu']

    def parse_json_body(self, request):
        """Parse le corps JSON et retourne (data, erreur)."""
        try:
            return json.loads(request.body), None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None, 'Corps JSON invalide'

    def validate_article(self, data: dict, partial: bool = False) -> dict:
        """
        Valide les données d'un article.
        partial=True : seuls les champs présents sont validés (pour PUT/PATCH).
        Retourne un dict d'erreurs (vide si valide).
        """
        erreurs = {}

        if 'titre' in data or not partial:
            titre = str(data.get('titre', '')).strip()
            if not titre and not partial:
                erreurs['titre'] = 'Ce champ est requis.'
            elif titre and len(titre) > 200:
                erreurs['titre'] = f'200 caractères max.'

        if 'contenu' in data or not partial:
            contenu = str(data.get('contenu', '')).strip()
            if not contenu and not partial:
                erreurs['contenu'] = 'Ce champ est requis.'

        return erreurs


@method_decorator(csrf_exempt, name='dispatch')
class ArticleAPIView(ValidatedArticleMixin, View):
    """
    Vue complète qui gère liste + détail + création + modification + suppression.
    Utilise ValidatedArticleMixin + JSONResponseMixin.

    C'est l'équivalent CBV complet de toutes les FBV du jour 16
    en une seule classe de ~60 lignes.
    """

    def get(self, request, pk: int = None):
        if pk is not None:
            article = _articles_db.get(pk)
            if not article:
                return self.json_error(f'Article {pk} introuvable', status=404)
            return self.json_response(_serialiser(article))

        # Liste
        articles = sorted(
            _articles_db.values(),
            key=lambda a: a['date_creation'],
            reverse=True,
        )
        return self.json_response({
            'articles': [_serialiser(a) for a in articles],
            'total': len(articles),
        })

    def post(self, request, pk: int = None):
        data, err = self.parse_json_body(request)
        if err:
            return self.json_error(err)

        erreurs = self.validate_article(data)
        if erreurs:
            return self.json_errors(erreurs)

        new_pk = _new_id()
        article = {
            'id': new_pk,
            'titre': data['titre'].strip(),
            'contenu': data['contenu'].strip(),
            'publie': bool(data.get('publie', False)),
            'date_creation': datetime.now(),
        }
        _articles_db[new_pk] = article
        return self.json_response(_serialiser(article), status=201)

    def put(self, request, pk: int):
        if pk not in _articles_db:
            return self.json_error(f'Article {pk} introuvable', status=404)

        data, err = self.parse_json_body(request)
        if err:
            return self.json_error(err)

        erreurs = self.validate_article(data, partial=True)
        if erreurs:
            return self.json_errors(erreurs)

        article = _articles_db[pk]
        for champ in ('titre', 'contenu', 'publie'):
            if champ in data:
                article[champ] = data[champ]

        return self.json_response(_serialiser(article))

    def delete(self, request, pk: int):
        article = _articles_db.pop(pk, None)
        if not article:
            return self.json_error(f'Article {pk} introuvable', status=404)
        return JsonResponse({}, status=204)


# ─── URLs ─────────────────────────────────────────────────────────────────────
from django.urls import path

urlpatterns = [
    path('articles/', ArticleListeView.as_view()),
    path('articles/<int:pk>/', ArticleDetailView.as_view()),
    path('api/articles/', ArticleAPIView.as_view()),
    path('api/articles/<int:pk>/', ArticleAPIView.as_view()),
]


# ─── Tests ────────────────────────────────────────────────────────────────────
import unittest
from django.test import RequestFactory


class TestArticleListeView(unittest.TestCase):
    """Tests de la CBV ArticleListeView (GET + POST)."""

    def setUp(self):
        _reset_db()
        self.factory = RequestFactory()
        self.view = ArticleListeView.as_view()

    def test_get_liste_vide(self):
        request = self.factory.get('/articles/')
        response = self.view(request)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['total'], 0)

    def test_post_creer_succes(self):
        payload = {'titre': 'CBV Test', 'contenu': 'Contenu via CBV', 'publie': True}
        request = self.factory.post(
            '/articles/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        response = self.view(request)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['titre'], 'CBV Test')

    def test_post_validation_echec(self):
        request = self.factory.post(
            '/articles/',
            data=json.dumps({'titre': ''}),
            content_type='application/json',
        )
        response = self.view(request)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertIn('titre', data['erreurs'])
        self.assertIn('contenu', data['erreurs'])

    def test_methode_inconnue_retourne_405(self):
        """PATCH n'est pas défini → 405."""
        request = self.factory.patch('/articles/')
        response = self.view(request)
        self.assertEqual(response.status_code, 405)


class TestArticleDetailView(unittest.TestCase):
    """Tests de la CBV ArticleDetailView (GET + PUT + DELETE)."""

    def setUp(self):
        _reset_db()
        _articles_db[1] = {
            'id': 1, 'titre': 'Article initial', 'contenu': 'Contenu initial',
            'publie': True, 'date_creation': datetime.now(),
        }
        self.factory = RequestFactory()
        self.view = ArticleDetailView.as_view()

    def test_get_existant(self):
        request = self.factory.get('/articles/1/')
        response = self.view(request, pk=1)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['titre'], 'Article initial')

    def test_get_inexistant(self):
        request = self.factory.get('/articles/999/')
        response = self.view(request, pk=999)
        self.assertEqual(response.status_code, 404)

    def test_put_modifier(self):
        payload = {'titre': 'Titre modifié'}
        request = self.factory.put(
            '/articles/1/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        response = self.view(request, pk=1)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['titre'], 'Titre modifié')
        # Le contenu n'a pas changé (PUT partiel)
        self.assertEqual(data['contenu'], 'Contenu initial')

    def test_delete_succes(self):
        request = self.factory.delete('/articles/1/')
        response = self.view(request, pk=1)
        self.assertEqual(response.status_code, 204)
        self.assertNotIn(1, _articles_db)

    def test_delete_inexistant(self):
        request = self.factory.delete('/articles/999/')
        response = self.view(request, pk=999)
        self.assertEqual(response.status_code, 404)


class TestJSONResponseMixin(unittest.TestCase):
    """Tests unitaires du JSONResponseMixin."""

    def setUp(self):
        self.mixin = JSONResponseMixin()

    def test_json_response_status_200(self):
        resp = self.mixin.json_response({'cle': 'valeur'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['cle'], 'valeur')

    def test_json_response_status_custom(self):
        resp = self.mixin.json_response({'ok': True}, status=201)
        self.assertEqual(resp.status_code, 201)

    def test_json_error(self):
        resp = self.mixin.json_error('Quelque chose a planté', status=500)
        data = json.loads(resp.content)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(data['erreur'], 'Quelque chose a planté')

    def test_json_errors_multiple(self):
        resp = self.mixin.json_errors({'champ1': 'Requis', 'champ2': 'Trop long'})
        data = json.loads(resp.content)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('champ1', data['erreurs'])
        self.assertIn('champ2', data['erreurs'])


class TestValidatedArticleMixin(unittest.TestCase):
    """Tests du mixin de validation."""

    def setUp(self):
        self.mixin = ValidatedArticleMixin()

    def test_valide_creation_complete(self):
        data = {'titre': 'Titre valide', 'contenu': 'Contenu valide'}
        erreurs = self.mixin.validate_article(data)
        self.assertEqual(erreurs, {})

    def test_invalide_titre_manquant(self):
        data = {'contenu': 'Contenu sans titre'}
        erreurs = self.mixin.validate_article(data)
        self.assertIn('titre', erreurs)

    def test_invalide_titre_trop_long(self):
        data = {'titre': 'X' * 201, 'contenu': 'OK'}
        erreurs = self.mixin.validate_article(data)
        self.assertIn('titre', erreurs)

    def test_partiel_ignore_manquants(self):
        # En mode partial, les champs absents ne génèrent pas d'erreur
        data = {'titre': 'Nouveau titre'}
        erreurs = self.mixin.validate_article(data, partial=True)
        self.assertEqual(erreurs, {})

    def test_parse_json_body_valide(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post(
            '/',
            data=json.dumps({'cle': 'valeur'}),
            content_type='application/json',
        )
        data, err = self.mixin.parse_json_body(request)
        self.assertIsNone(err)
        self.assertEqual(data['cle'], 'valeur')

    def test_parse_json_body_invalide(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post(
            '/',
            data=b'pas du json',
            content_type='application/json',
        )
        data, err = self.mixin.parse_json_body(request)
        self.assertIsNone(data)
        self.assertIsNotNone(err)


class TestComparaisonFBVvsCBV(unittest.TestCase):
    """
    Test de régression : les CBV se comportent exactement comme les FBV du jour 16.
    """

    def setUp(self):
        _reset_db()
        self.factory = RequestFactory()
        self.liste_view = ArticleListeView.as_view()
        self.detail_view = ArticleDetailView.as_view()

    def test_workflow_complet(self):
        """Crée → Liste → Détail → Modifier → Supprimer."""
        # 1. Créer
        request = self.factory.post(
            '/articles/',
            data=json.dumps({'titre': 'Workflow test', 'contenu': 'Contenu test'}),
            content_type='application/json',
        )
        response = self.liste_view(request)
        self.assertEqual(response.status_code, 201)
        article = json.loads(response.content)
        pk = article['id']

        # 2. Lister
        request = self.factory.get('/articles/')
        response = self.liste_view(request)
        data = json.loads(response.content)
        self.assertEqual(data['total'], 1)

        # 3. Détail
        request = self.factory.get(f'/articles/{pk}/')
        response = self.detail_view(request, pk=pk)
        self.assertEqual(response.status_code, 200)

        # 4. Modifier
        request = self.factory.put(
            f'/articles/{pk}/',
            data=json.dumps({'titre': 'Titre modifié'}),
            content_type='application/json',
        )
        response = self.detail_view(request, pk=pk)
        self.assertEqual(response.status_code, 200)

        # 5. Supprimer
        request = self.factory.delete(f'/articles/{pk}/')
        response = self.detail_view(request, pk=pk)
        self.assertEqual(response.status_code, 204)

        # 6. Vérifier que la liste est vide
        request = self.factory.get('/articles/')
        response = self.liste_view(request)
        data = json.loads(response.content)
        self.assertEqual(data['total'], 0)


# ─── Bilan de la comparaison ──────────────────────────────────────────────────
BILAN = """
╔══════════════════════════════════════════════════════╗
║         Comparaison FBV (Jour 16) vs CBV (Jour 17)  ║
╚══════════════════════════════════════════════════════╝

FBV — Jour 16 :
  liste_articles()  ─ ~25 lignes  (logique de filtre + tri)
  detail_article()  ─ ~12 lignes
  creer_article()   ─ ~35 lignes  (validation + création)
  TOTAL : ~72 lignes

CBV — Jour 17 :
  ArticleListeView  ─ ~35 lignes  (GET + POST + _valider dans la classe)
  ArticleDetailView ─ ~30 lignes  (GET + PUT + DELETE + get_object())
  JSONResponseMixin ─ ~12 lignes  (réutilisable partout)
  TOTAL : ~77 lignes

Verdict : en lignes pures, CBV vs FBV c'est similaire ici.
L'avantage CBV apparaît quand :
  - On a 10+ vues CRUD (get_object() factorisé une fois)
  - On ajoute LoginRequiredMixin partout sans toucher la logique
  - On hérite pour créer des variantes (ArticleAPIView hérite de View + 2 mixins)
"""


# ─── Point d'entrée ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("Jour 17 — Tests des CBV Django")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for cls in [
        TestArticleListeView,
        TestArticleDetailView,
        TestJSONResponseMixin,
        TestValidatedArticleMixin,
        TestComparaisonFBVvsCBV,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(BILAN)

    if result.wasSuccessful():
        print(f"Tous les tests passent ({result.testsRun} tests).")
    else:
        print(f"Échecs : {len(result.failures)}, Erreurs : {len(result.errors)}")
