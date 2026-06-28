# Exercice Jour 28 — Conception d'API REST et Exploration (24 juillet 2026)

## Objectifs

- Concevoir une API RESTful complète pour un système réel
- Critiquer et améliorer une mauvaise API
- Explorer une vraie API REST avec `curl`
- Pratiquer la lecture et l'écriture de documentation d'API

---

## Exercice 1 — Concevoir l'API d'une Bibliothèque

Vous devez concevoir une API REST complète pour un système de gestion de bibliothèque. Le système doit gérer :

- Des **livres** (titre, auteur, ISBN, genre, disponibilité, date de publication)
- Des **membres** (nom, email, date d'inscription, statut)
- Des **emprunts** (qui a emprunté quoi, quand, date de retour prévue)
- Des **avis** (note, commentaire, auteur, livre)
- Des **catégories/genres** (nom, description)

### 1a — Listez tous les endpoints

Pour chaque ressource, définissez les endpoints avec :
- La méthode HTTP
- L'URI
- Une description courte

**Exemple de format :**
```
GET    /api/v1/books            — Liste les livres (paginé, filtrable)
POST   /api/v1/books            — Crée un nouveau livre
GET    /api/v1/books/{id}       — Récupère un livre par ID
...
```

Votre réponse doit couvrir les 5 ressources ci-dessus avec toutes les opérations pertinentes (au moins 20 endpoints au total).

---

### 1b — Définissez les formats de requête et réponse

Pour chacun des endpoints suivants, écrivez le corps de la requête et la réponse attendue :

**POST /api/v1/books** — Création d'un livre

Requête :
```json
// Écrivez le corps JSON ici
```

Réponse succès (201) :
```json
// Écrivez la réponse ici
```

Réponse erreur (400) :
```json
// Exemple d'erreur de validation
```

---

**POST /api/v1/loans** — Emprunter un livre

Requête :
```json
// Quelles informations faut-il envoyer ?
```

Réponse succès (201) :
```json
// Réponse attendue
```

Réponse si le livre n'est pas disponible (409 Conflict) :
```json
// Message d'erreur approprié
```

---

**PATCH /api/v1/loans/{id}/return** — Retourner un livre

Requête : (corps vide ou JSON minimal)

Réponse succès (200) :
```json
// Que renvoie-t-on après le retour ?
```

---

### 1c — Paramètres de filtrage et tri

Définissez les paramètres de query string pour `GET /api/v1/books` :

| Paramètre     | Type    | Description                        | Exemple                    |
|---------------|---------|------------------------------------|----------------------------|
| `search`      | string  | Recherche dans titre et auteur     | `?search=martin`           |
| `genre`       | string  | Filtrer par genre                  | `?genre=fiction`           |
| `available`   | boolean | Filtrer par disponibilité          | `?available=true`          |
| ...           | ...     | Complétez le tableau               | ...                        |

---

## Exercice 2 — Critique d'une Mauvaise API

Voici une API "REST" mal conçue. Identifiez tous les problèmes et proposez des corrections.

### API originale (à corriger)

```
POST   /api/getAllBooks
POST   /api/getBook?bookId=42
POST   /api/createNewBook
POST   /api/updateBook?id=42
POST   /api/deleteBook
POST   /api/searchBooks?q=python&token=secret123abc
POST   /api/getUserLoans?userId=17
POST   /api/returnBook
```

Toutes ces routes retournent toujours HTTP 200, même en cas d'erreur :

```json
// Réponse d'erreur "typique" de cette API
{
    "status": "error",
    "code": 404,
    "message": "Book not found"
}
// Mais le code HTTP est toujours 200 !
```

### 2a — Listez les problèmes

Pour chaque endpoint, identifiez ce qui ne va pas. Utilisez ce format :

```
Problème 1 : POST /api/getAllBooks
  - Problème : [décrivez le problème]
  - Correction : [proposez la bonne version]

Problème 2 : ...
```

### 2b — Réécrivez l'API correctement

Réécrivez tous les endpoints en respectant les conventions REST.

### 2c — Sécurité

Dans la route `POST /api/searchBooks?q=python&token=secret123abc`, il y a un problème de sécurité critique. Identifiez-le et expliquez comment le corriger.

---

## Exercice 3 — Exploration de l'API JSONPlaceholder avec curl

JSONPlaceholder (https://jsonplaceholder.typicode.com) est une fausse API REST pour les tests. Elle expose des ressources `/posts`, `/users`, `/comments`, `/todos`, `/albums`, `/photos`.

Exécutez les commandes curl suivantes dans votre terminal et analysez les réponses.

### 3a — Exploration basique

```bash
# 1. Récupérer tous les posts
curl -s https://jsonplaceholder.typicode.com/posts | head -50

# 2. Récupérer un post spécifique
curl -s https://jsonplaceholder.typicode.com/posts/1

# 3. Récupérer les posts d'un utilisateur spécifique (filtrage)
curl -s "https://jsonplaceholder.typicode.com/posts?userId=1"

# 4. Voir les headers de réponse
curl -s -I https://jsonplaceholder.typicode.com/posts/1

# 5. Récupérer un utilisateur
curl -s https://jsonplaceholder.typicode.com/users/1
```

**Questions :**
- Quel code de statut HTTP retourne `GET /posts/1` ?
- Y a-t-il des headers de cache dans la réponse ?
- Quelle est la structure du JSON retourné pour un post ?
- Comment l'API gère-t-elle le filtrage par userId ?

### 3b — Opérations d'écriture

```bash
# 6. Créer un nouveau post (POST)
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "Mon titre", "body": "Mon contenu", "userId": 1}' \
  https://jsonplaceholder.typicode.com/posts

# 7. Mettre à jour un post (PUT)
curl -s -X PUT \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "title": "Titre modifié", "body": "Contenu modifié", "userId": 1}' \
  https://jsonplaceholder.typicode.com/posts/1

# 8. Mise à jour partielle (PATCH)
curl -s -X PATCH \
  -H "Content-Type: application/json" \
  -d '{"title": "Seulement le titre modifié"}' \
  https://jsonplaceholder.typicode.com/posts/1

# 9. Supprimer un post (DELETE)
curl -s -X DELETE https://jsonplaceholder.typicode.com/posts/1
echo "Code retour: $?"
```

**Questions :**
- Quel code HTTP retourne un POST réussi ? (201 ou 200 ?)
- Quelle est la réponse d'un DELETE réussi ?
- JSONPlaceholder simule-t-il vraiment les opérations ou fait-il semblant ?

### 3c — Navigation des relations

```bash
# 10. Récupérer les commentaires d'un post (relation imbriquée)
curl -s "https://jsonplaceholder.typicode.com/posts/1/comments"

# 11. Alternative : via paramètre de filtrage
curl -s "https://jsonplaceholder.typicode.com/comments?postId=1"

# 12. Les albums d'un utilisateur
curl -s "https://jsonplaceholder.typicode.com/users/1/albums"

# 13. Les todos d'un utilisateur
curl -s "https://jsonplaceholder.typicode.com/users/1/todos"
```

**Questions :**
- Les deux approches en 10 et 11 retournent-elles les mêmes données ?
- Laquelle préférez-vous ? Pourquoi ?

### 3d — Analyse des headers HTTP

```bash
# 14. Afficher tous les headers de réponse
curl -s -D - https://jsonplaceholder.typicode.com/posts/1 -o /dev/null

# 15. Voir le type de contenu
curl -s -I https://jsonplaceholder.typicode.com/posts \
  | grep -i "content-type"

# 16. Tester la négociation de contenu
curl -s -H "Accept: application/xml" \
  https://jsonplaceholder.typicode.com/posts/1
# Que se passe-t-il quand on demande du XML ?
```

### 3e — Commandes avancées

```bash
# 17. Requête avec affichage formaté (nécessite jq)
curl -s https://jsonplaceholder.typicode.com/users/1 | python3 -m json.tool

# 18. Chronomètre de la requête
curl -s -w "\nTemps: %{time_total}s\nCode: %{http_code}\n" \
  -o /dev/null \
  https://jsonplaceholder.typicode.com/posts

# 19. Simuler un mauvais Accept header
curl -s -I -H "Accept: text/plain" \
  https://jsonplaceholder.typicode.com/posts/1

# 20. Tester une ressource inexistante
curl -s -w "\nHTTP Status: %{http_code}\n" \
  https://jsonplaceholder.typicode.com/posts/99999
```

---

## Exercice 4 — Conception HATEOAS

Reprenez le livre de l'exercice 1 et ajoutez des liens HATEOAS à la réponse.

Contexte : Le livre est disponible. L'utilisateur connecté est un membre normal (pas un admin).

```json
// GET /api/v1/books/42
// Répondez en ajoutant les liens _links appropriés
{
    "id": 42,
    "title": "The Pragmatic Programmer",
    "author": "David Thomas",
    "isbn": "978-0135957059",
    "available": true,
    "genre": "technology",

    "_links": {
        // Complétez avec tous les liens pertinents
        // Pour chaque lien : href, method, description
    }
}
```

**Quels liens inclure ?**
- Le lien vers soi-même
- Les liens vers les opérations possibles (selon la disponibilité du livre)
- Le lien vers la collection
- Le lien vers les avis
- Le lien vers l'auteur (si vous avez un endpoint /authors)

---

## Exercice 5 — Versionning et Évolution d'API

Vous avez une API v1 avec ce modèle de réponse :

```json
// GET /api/v1/books/42
{
    "id": 42,
    "name": "Clean Code",          // "name" dans v1
    "author_name": "Robert Martin", // prénom+nom concatené dans v1
    "isbn": "978-0132350884"
}
```

Dans la v2, vous voulez changer :
- `name` → `title` (meilleure sémantique)
- `author_name` → un objet `author` avec `first_name`, `last_name`, `id`
- Ajouter un champ `categories` (tableau)
- Ajouter la pagination sur les collections

**Questions :**
1. Pourquoi ne peut-on pas simplement modifier la v1 ?
2. Écrivez le format de réponse de la v2 pour le même livre
3. Comment gérer la transition ? Les clients v1 doivent continuer à fonctionner.
4. Pendant combien de temps maintenir la v1 ? Quelle stratégie de déprécation ?

---

## Solutions et Corrections

*(À compléter après avoir fait les exercices vous-même)*

### Réponse indicative pour l'exercice 2 — Problèmes identifiés

```
Problème 1 : POST /api/getAllBooks
  - Problème : Utilisation de POST pour une lecture ; verbe "getAllBooks" dans l'URI
  - Correction : GET /api/v1/books

Problème 2 : POST /api/getBook?bookId=42
  - Problème : POST pour une lecture ; identifiant dans query string au lieu du chemin
  - Correction : GET /api/v1/books/42

Problème 3 : POST /api/createNewBook
  - Problème : Verbe "createNew" dans l'URI ; c'est redondant avec POST
  - Correction : POST /api/v1/books

Problème 4 : POST /api/updateBook?id=42
  - Problème : POST au lieu de PUT/PATCH ; verbe dans l'URI
  - Correction : PUT /api/v1/books/42 ou PATCH /api/v1/books/42

Problème 5 : POST /api/deleteBook
  - Problème : POST au lieu de DELETE ; pas d'ID dans l'URI
  - Correction : DELETE /api/v1/books/42

Problème 6 : token=secret123abc dans l'URL
  - PROBLÈME DE SÉCURITÉ : les tokens dans les URLs apparaissent dans
    les logs serveur, l'historique du navigateur, les headers Referer
  - Correction : Authorization: Bearer secret123abc dans les headers HTTP

Problème 7 : Toujours retourner HTTP 200
  - Problème : Les clients ne peuvent pas distinguer succès/erreur par code HTTP
  - Correction : Utiliser 200, 201, 204, 400, 401, 403, 404, 409, 500 correctement
```
