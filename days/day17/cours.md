# Jour 17 — Django : Vues basées sur les classes (CBV)
📅 13 juillet 2026 · Module : Django

---

## 1. Pourquoi les CBV ?

Les vues fonctionnelles (FBV) du jour 16 sont claires et directes. Mais quand on écrit beaucoup de vues CRUD, on répète les mêmes patterns : vérifier la méthode, récupérer l'objet, valider les données, renvoyer la réponse. Les CBV encapsulent ces patterns dans des classes réutilisables via l'héritage et les mixins.

**Avantages des CBV :**
- Réutilisation par héritage (surcharger une seule méthode change tout le comportement)
- Mixins composables (ajouter une fonctionnalité sans toucher à la logique principale)
- Les generic views éliminent le boilerplate pour les opérations CRUD standard
- Meilleure organisation du code quand la vue est complexe

**Inconvénients :**
- Courbe d'apprentissage plus raide (MRO, `super()`, `dispatch()`)
- Moins évident à lire d'un coup d'œil pour un débutant
- Pour des vues simples, c'est souvent trop

---

## 2. Comment un CBV est en réalité une FBV

C'est la clé pour comprendre les CBV. Django n'appelle pas la classe directement — il appelle une **fonction** générée par `as_view()`.

```python
# Ce qu'on écrit dans urls.py :
path('articles/', ArticleListView.as_view(), name='liste'),

# Ce que as_view() génère (simplifié) :
def vue_generee(request, *args, **kwargs):
    instance = ArticleListView()          # crée une instance de la classe
    instance.request = request
    instance.args = args
    instance.kwargs = kwargs
    return instance.dispatch(request, *args, **kwargs)
```

`dispatch()` regarde `request.method`, le transforme en minuscules, et appelle la méthode correspondante :

```python
# Dans View.dispatch() (code réel Django simplifié) :
def dispatch(self, request, *args, **kwargs):
    method = request.method.lower()
    if method in self.http_method_names:
        handler = getattr(self, method, self.http_method_not_allowed)
    else:
        handler = self.http_method_not_allowed
    return handler(request, *args, **kwargs)
```

Donc si `request.method == 'GET'`, Django appelle `self.get(request, ...)`. Si `POST`, il appelle `self.post(...)`. C'est tout.

---

## 3. `View` — la classe de base

```python
from django.views import View
from django.http import JsonResponse
import json


class ArticleView(View):
    """Vue de base : implémente get() et post() explicitement."""

    def get(self, request, pk=None):
        if pk:
            # Détail
            article = _articles_db.get(pk)
            if not article:
                return JsonResponse({'erreur': 'Non trouvé'}, status=404)
            return JsonResponse(article)
        # Liste
        return JsonResponse({'articles': list(_articles_db.values())})

    def post(self, request):
        data = json.loads(request.body)
        # créer l'article...
        return JsonResponse(nouvel_article, status=201)

    def delete(self, request, pk):
        article = _articles_db.pop(pk, None)
        if not article:
            return JsonResponse({'erreur': 'Non trouvé'}, status=404)
        return JsonResponse({}, status=204)
```

```python
# urls.py
urlpatterns = [
    path('articles/', ArticleView.as_view()),
    path('articles/<int:pk>/', ArticleView.as_view()),
]
```

**Attributs de classe configurables :**

```python
class ArticleView(View):
    http_method_names = ['get', 'post', 'delete']  # autorise seulement ces méthodes
    # Si une autre méthode arrive, dispatch() appellera http_method_not_allowed()
    # qui renvoie automatiquement un 405
```

---

## 4. Les Generic Views

Django fournit des CBV prêtes à l'emploi pour les patterns les plus courants.

### `TemplateView` — afficher un template

```python
from django.views.generic import TemplateView

class AccueilView(TemplateView):
    template_name = 'accueil.html'

    def get_context_data(self, **kwargs):
        # Surcharger pour ajouter des variables au template
        context = super().get_context_data(**kwargs)
        context['titre'] = "Bienvenue sur mon blog"
        context['nb_articles'] = Article.objects.filter(publie=True).count()
        return context
```

### `ListView` — liste d'objets

```python
from django.views.generic import ListView

class ArticleListView(ListView):
    model = Article
    template_name = 'articles/liste.html'
    context_object_name = 'articles'  # variable dans le template (défaut: object_list)
    paginate_by = 10  # pagination automatique !
    ordering = ['-date_creation']

    def get_queryset(self):
        # Surcharger pour filtrer
        qs = super().get_queryset()
        return qs.filter(publie=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context
```

### `DetailView` — détail d'un objet

```python
from django.views.generic import DetailView

class ArticleDetailView(DetailView):
    model = Article
    template_name = 'articles/detail.html'
    context_object_name = 'article'
    # Par défaut, cherche l'objet par 'pk' dans l'URL
    # On peut changer avec : pk_url_kwarg = 'article_id'
    # Ou utiliser : slug_field = 'slug'; slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Article.objects.filter(publie=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Incrémenter un compteur de vues, par exemple
        obj.nb_vues += 1
        obj.save(update_fields=['nb_vues'])
        return obj
```

### `CreateView` — créer un objet

```python
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy

class ArticleCreateView(CreateView):
    model = Article
    fields = ['titre', 'contenu', 'categorie', 'publie']
    template_name = 'articles/formulaire.html'
    success_url = reverse_lazy('articles:liste')

    def form_valid(self, form):
        # Avant de sauvegarder, assigner l'auteur
        form.instance.auteur = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form):
        # Appelé si le formulaire est invalide
        # super() renvoie la page avec les erreurs
        return super().form_invalid(form)
```

### `UpdateView` — modifier un objet

```python
from django.views.generic.edit import UpdateView

class ArticleUpdateView(UpdateView):
    model = Article
    fields = ['titre', 'contenu', 'publie']
    template_name = 'articles/formulaire.html'

    def get_success_url(self):
        # URL dynamique après succès
        return reverse('articles:detail', kwargs={'pk': self.object.pk})

    def get_queryset(self):
        # Seul l'auteur peut modifier
        return Article.objects.filter(auteur=self.request.user)
```

### `DeleteView` — supprimer un objet

```python
from django.views.generic.edit import DeleteView

class ArticleDeleteView(DeleteView):
    model = Article
    template_name = 'articles/confirmer_suppression.html'
    success_url = reverse_lazy('articles:liste')

    def get_queryset(self):
        return Article.objects.filter(auteur=self.request.user)
```

---

## 5. Les Mixins

Un mixin est une classe conçue pour être héritée en combinaison avec d'autres classes, pour ajouter une fonctionnalité spécifique. Avec Python, on peut hériter de plusieurs classes (MRO).

### `LoginRequiredMixin`

```python
from django.contrib.auth.mixins import LoginRequiredMixin

class ArticleCreateView(LoginRequiredMixin, CreateView):
    model = Article
    fields = ['titre', 'contenu']
    login_url = '/connexion/'        # Optionnel, sinon settings.LOGIN_URL
    redirect_field_name = 'next'     # Paramètre GET dans l'URL de redirection
```

**Ordre des mixins** : toujours mettre les mixins **avant** la classe de base.

```python
# Correct
class MaVue(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    ...

# Incorrect — LoginRequiredMixin ne sera jamais consulté
class MaVue(CreateView, LoginRequiredMixin):
    ...
```

### `PermissionRequiredMixin`

```python
from django.contrib.auth.mixins import PermissionRequiredMixin

class ArticleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Article
    permission_required = 'articles.delete_article'
    # Ou plusieurs permissions :
    # permission_required = ['articles.change_article', 'articles.delete_article']
    raise_exception = True  # 403 au lieu de redirection
```

### `UserPassesTestMixin`

```python
from django.contrib.auth.mixins import UserPassesTestMixin

class ArticleModifierView(UserPassesTestMixin, UpdateView):
    model = Article
    fields = ['titre', 'contenu']

    def test_func(self):
        # Renvoyer True si l'accès est autorisé
        article = self.get_object()
        return self.request.user == article.auteur or self.request.user.is_staff
```

---

## 6. Mixin custom — `JSONResponseMixin`

C'est l'exemple clé pour comprendre comment créer ses propres mixins.

```python
import json
from django.http import JsonResponse


class JSONResponseMixin:
    """
    Mixin qui remplace le rendu de template par une réponse JSON.
    Compatible avec les generic views.
    """

    def render_to_response(self, context, **response_kwargs):
        """Surcharge la méthode de rendu pour retourner du JSON."""
        return JsonResponse(self.get_data(context), **response_kwargs)

    def get_data(self, context):
        """
        Convertit le contexte en dict JSON-sérialisable.
        Surcharger dans la sous-classe pour contrôler la sérialisation.
        """
        # Par défaut, on enlève les clés non-sérialisables
        return {
            k: v for k, v in context.items()
            if isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }


class JSONListView(JSONResponseMixin, ListView):
    """ListView qui retourne du JSON au lieu d'un template."""

    def get_data(self, context):
        articles = context.get(self.context_object_name, context.get('object_list', []))
        return {
            'articles': [self.serialiser(a) for a in articles],
            'total': self.get_queryset().count(),
        }

    def serialiser(self, obj):
        raise NotImplementedError("Implémenter serialiser() dans la sous-classe")
```

---

## 7. FBV vs CBV — quand utiliser quoi ?

| Situation | FBV | CBV |
|-----------|-----|-----|
| Vue simple, logique spécifique | Oui | Non |
| CRUD standard avec templates | Non | Oui (generic views) |
| API JSON simple | Oui | Parfois (`View`) |
| Comportement réutilisable via héritage | Non | Oui |
| Logique complexe, conditions multiples | Oui | Peut devenir confus |
| Débutant Django | Oui | Apprendre après |

**Règle pratique :** si vous vous retrouvez à écrire le même code dans plusieurs FBV, c'est le signe de passer à un CBV avec mixin.

---

## 8. `as_view()` et les paramètres de classe

On peut passer des arguments à `as_view()` pour configurer la vue depuis l'URLconf :

```python
# urls.py
urlpatterns = [
    # Passer template_name directement dans l'URL
    path('', TemplateView.as_view(template_name='index.html'), name='index'),

    # Configurer une ListView sans créer de sous-classe
    path('articles/', ListView.as_view(
        model=Article,
        template_name='articles/liste.html',
        context_object_name='articles',
        paginate_by=10,
    ), name='liste'),
]
```

---

## Points clés à retenir

- `as_view()` crée une FBV classique qui instancie la classe à chaque requête
- `dispatch()` route vers `get()`, `post()`, `delete()`, etc. selon la méthode HTTP
- Les **generic views** (ListView, DetailView, CreateView...) font le CRUD avec très peu de code
- Les **mixins** s'héritent **avant** la classe principale (ordre du MRO)
- `LoginRequiredMixin` remplace le décorateur `@login_required` des FBV
- `get_queryset()` est la méthode clé à surcharger pour filtrer/restreindre les données
- `get_context_data()` est la méthode clé pour ajouter des variables au template
