# Jour 28 — Principes REST : Ressources, Représentations et Contraintes (24 juillet 2026)

## Introduction

REST (Representational State Transfer) est aujourd'hui l'architecture dominante pour la conception d'APIs web. Comprendre ses principes fondamentaux — pas seulement les conventions superficielles — est indispensable pour tout développeur backend. Ce cours explore l'histoire, les contraintes formelles, et les bonnes pratiques de conception REST.

---

## 1. Histoire et Origine de REST

### Roy Fielding et sa thèse de doctorat

En l'an 2000, Roy Fielding, l'un des auteurs principaux de la spécification HTTP/1.1, publie sa thèse de doctorat intitulée **"Architectural Styles and the Design of Network-based Software Architectures"** à l'Université de Californie à Irvine.

Dans cette thèse, Fielding décrit REST non pas comme un protocole ou un standard, mais comme un **style architectural** — un ensemble de contraintes qui, lorsqu'elles sont appliquées à un système distribué, produisent des propriétés désirables : évolutivité, fiabilité, et interopérabilité.

REST a été conçu pour décrire et guider l'architecture du **World Wide Web** lui-même. Autrement dit, le Web tel que nous le connaissons est la plus grande implémentation REST qui existe.

### Ce que REST N'est PAS

Beaucoup d'APIs se disent "RESTful" sans respecter les contraintes REST. Fielding lui-même a critiqué cette tendance dans un article de blog en 2008 :

> "I am getting frustrated by the number of people calling any HTTP-based interface a REST API."

Un simple fait : utiliser HTTP ne fait pas une API RESTful. REST est un ensemble de contraintes architecturales, pas une technologie.

---

## 2. Les 6 Contraintes de REST

Fielding définit 6 contraintes. Le respect de ces contraintes produit un système dit "RESTful".

### Contrainte 1 : Client-Server (Client-Serveur)

**Principe** : Séparation des préoccupations entre l'interface utilisateur (client) et le stockage des données (serveur).

- Le client ne se préoccupe pas du stockage des données
- Le serveur ne se préoccupe pas de l'interface utilisateur
- Les deux évoluent indépendamment

**Avantages** :
- Portabilité du client (web, mobile, CLI)
- Scalabilité du serveur indépendamment du client
- Développement en parallèle des deux couches

```
[Client Web]  ←→  [API REST]  ←→  [Base de données]
[Client iOS]  ←→  [API REST]
[Client CLI]  ←→  [API REST]
```

### Contrainte 2 : Stateless (Sans état)

**Principe** : Chaque requête du client vers le serveur doit contenir **toutes les informations nécessaires** pour comprendre et traiter la requête. Le serveur ne stocke aucun contexte de session.

```
# Mauvais (avec état) :
# Requête 1 : POST /login   → serveur se souvient de l'utilisateur
# Requête 2 : GET /profile  → serveur utilise la session stockée

# Bon (sans état) :
# Requête 1 : GET /profile  Authorization: Bearer eyJhbGci...
# Requête 2 : GET /orders   Authorization: Bearer eyJhbGci...
# Chaque requête est auto-suffisante
```

**Avantages** :
- Visibilité : chaque requête peut être analysée indépendamment
- Fiabilité : plus simple de reprendre après une panne
- Scalabilité : n'importe quel serveur peut traiter n'importe quelle requête (load balancing facile)

**Trade-off** : Légère augmentation de la taille des requêtes (token envoyé à chaque fois).

### Contrainte 3 : Cacheable (Mise en cache)

**Principe** : Les réponses doivent se définir elles-mêmes comme pouvant être mises en cache ou non, pour éviter que les clients réutilisent des données périmées.

```http
HTTP/1.1 200 OK
Cache-Control: max-age=3600, public
ETag: "abc123"
Last-Modified: Fri, 24 Jul 2026 08:00:00 GMT

{"id": 1, "title": "Django for Professionals"}
```

```http
HTTP/1.1 200 OK
Cache-Control: no-store
# Cette réponse ne doit jamais être mise en cache
```

**Avantages** :
- Réduction de la latence
- Réduction de la charge serveur
- Amélioration de la scalabilité

### Contrainte 4 : Uniform Interface (Interface Uniforme)

C'est la contrainte centrale de REST. Elle se décompose en 4 sous-contraintes :

**4a. Identification des ressources**
Chaque ressource est identifiée par un URI stable.
```
/api/v1/books/42        # La ressource "livre avec ID 42"
/api/v1/users/17        # La ressource "utilisateur avec ID 17"
```

**4b. Manipulation des ressources via des représentations**
Le client manipule des ressources via des représentations (JSON, XML). La représentation contient suffisamment d'informations pour modifier ou supprimer la ressource.

**4c. Messages auto-descriptifs**
Chaque message contient suffisamment d'informations pour décrire comment le traiter :
```http
POST /api/v1/books
Content-Type: application/json
Accept: application/json

{"title": "Clean Code", "author": "Robert Martin"}
```

**4d. HATEOAS** (voir section dédiée ci-dessous)

### Contrainte 5 : Layered System (Système en couches)

**Principe** : Le client ne sait pas s'il communique directement avec le serveur final ou avec un intermédiaire (proxy, load balancer, gateway, cache).

```
[Client]
    ↓
[CDN / Cache Layer]
    ↓
[Load Balancer]
    ↓
[API Gateway]
    ↓
[Service 1]  [Service 2]  [Service 3]
```

**Avantages** :
- Sécurité : les intermédiaires peuvent filtrer les requêtes
- Scalabilité : ajout de couches transparent pour le client
- Flexibilité d'architecture

### Contrainte 6 : Code on Demand (Code à la demande) — Optionnelle

**Principe** : Le serveur peut étendre les fonctionnalités du client en envoyant du code exécutable (JavaScript, applets).

Cette contrainte est **optionnelle** — un système peut être RESTful sans l'implémenter.

```html
<!-- Le serveur envoie du JavaScript que le client exécute -->
<script src="https://api.example.com/widget.js"></script>
```

---

## 3. Ressources vs Représentations

C'est une distinction fondamentale souvent mal comprise.

### La Ressource

Une **ressource** est un concept abstrait — n'importe quelle information qui peut être nommée :
- Un livre, un utilisateur, une commande
- Une collection de livres
- La météo actuelle à Paris

La ressource est identifiée par son **URI** (Uniform Resource Identifier).

### La Représentation

Une **représentation** est l'état courant de la ressource encodé dans un format spécifique pour être transféré.

```
Ressource : "Livre avec ID 42"
URI       : /api/v1/books/42

Représentation JSON :
{
    "id": 42,
    "title": "The Pragmatic Programmer",
    "author": "David Thomas",
    "isbn": "978-0135957059"
}

Représentation XML :
<book>
    <id>42</id>
    <title>The Pragmatic Programmer</title>
    <author>David Thomas</author>
</book>
```

La même ressource peut avoir plusieurs représentations. Le client indique sa préférence via le header `Accept` :

```http
GET /api/v1/books/42
Accept: application/json       # Je veux du JSON
Accept: application/xml        # Je veux du XML
Accept: text/html              # Je veux du HTML
```

---

## 4. Conception des URIs — Bonnes Pratiques

### Noms au pluriel pour les collections

```
# Bon
GET /api/v1/books           # Collection de livres
GET /api/v1/books/42        # Livre spécifique
GET /api/v1/users           # Collection d'utilisateurs

# Mauvais
GET /api/v1/book            # Singulier incohérent
GET /api/v1/getBook         # Verbe dans l'URI
GET /api/v1/BookList        # CamelCase
```

### Hiérarchie et relations

```
GET /api/v1/users/17/orders           # Commandes de l'utilisateur 17
GET /api/v1/users/17/orders/5         # Commande 5 de l'utilisateur 17
GET /api/v1/books/42/reviews          # Avis du livre 42
GET /api/v1/books/42/reviews/8        # Avis 8 du livre 42
```

### Versioning

```
# Dans l'URI (recommandé pour la visibilité)
GET /api/v1/books
GET /api/v2/books

# Dans le header (plus "pur" REST mais moins pratique)
GET /api/books
Accept: application/vnd.myapi.v2+json

# Sous-domaine
GET https://v2.api.example.com/books
```

### Paramètres de requête pour filtrage, tri, pagination

```
# Filtrage
GET /api/v1/books?genre=fiction&available=true

# Tri
GET /api/v1/books?ordering=-published_date    # Décroissant

# Pagination
GET /api/v1/books?page=2&page_size=20

# Recherche
GET /api/v1/books?search=django

# Combiné
GET /api/v1/books?genre=tech&ordering=title&page=1&page_size=10
```

### Ce qu'il faut éviter

```
# Eviter les verbes dans les URIs
POST /api/v1/createBook        # Mauvais
POST /api/v1/books             # Bon (le verbe est dans la méthode HTTP)

# Eviter les extensions de fichier
GET /api/v1/books.json         # Mauvais
GET /api/v1/books              # Bon (utiliser Accept header)

# Eviter les mots d'action dans l'URI
POST /api/v1/books/42/delete   # Mauvais
DELETE /api/v1/books/42        # Bon
```

---

## 5. Méthodes HTTP Mappées aux Opérations CRUD

| Méthode HTTP | Opération CRUD | Idempotent | Safe | Exemple               |
|-------------|----------------|------------|------|-----------------------|
| GET         | Read           | Oui        | Oui  | GET /books/42         |
| POST        | Create         | Non        | Non  | POST /books           |
| PUT         | Update (total) | Oui        | Non  | PUT /books/42         |
| PATCH       | Update (partiel)| Non*      | Non  | PATCH /books/42       |
| DELETE      | Delete         | Oui        | Non  | DELETE /books/42      |
| HEAD        | Métadonnées    | Oui        | Oui  | HEAD /books/42        |
| OPTIONS     | Capacités      | Oui        | Oui  | OPTIONS /books        |

**Idempotent** : Plusieurs requêtes identiques produisent le même résultat.
**Safe** : La requête ne modifie pas l'état du serveur.

### PUT vs PATCH

```json
// Ressource actuelle : GET /api/v1/books/42
{
    "id": 42,
    "title": "Clean Code",
    "author": "Robert Martin",
    "isbn": "978-0132350884",
    "available": true
}

// PUT /api/v1/books/42 — remplacement TOTAL
// Corps de la requête doit contenir TOUS les champs
{
    "title": "Clean Code",
    "author": "Robert Martin",
    "isbn": "978-0132350884",
    "available": false          // Seul champ modifié
}

// PATCH /api/v1/books/42 — modification PARTIELLE
// Corps de la requête contient uniquement les champs à modifier
{
    "available": false
}
```

### Codes de statut HTTP appropriés

```
200 OK              — GET réussi, PUT réussi
201 Created         — POST réussi (avec Location header)
204 No Content      — DELETE réussi, PUT sans corps de réponse
400 Bad Request     — Données invalides
401 Unauthorized    — Non authentifié
403 Forbidden       — Authentifié mais non autorisé
404 Not Found       — Ressource inexistante
405 Method Not Allowed — Méthode non supportée
409 Conflict        — Conflit (ex: email déjà utilisé)
422 Unprocessable Entity — Validation échouée
429 Too Many Requests — Rate limit atteint
500 Internal Server Error — Erreur serveur
```

---

## 6. REST vs SOAP vs GraphQL

### SOAP (Simple Object Access Protocol)

```xml
<!-- Requête SOAP -->
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <getBook>
            <bookId>42</bookId>
        </getBook>
    </soap:Body>
</soap:Envelope>
```

**Caractéristiques SOAP** :
- Protocole strict, basé sur XML
- WSDL (Web Services Description Language) pour décrire le service
- Supporte les transactions, WS-Security
- Très verbeux
- Populaire dans les entreprises (systèmes bancaires, santé)

### GraphQL

```graphql
# Requête GraphQL
query {
    book(id: 42) {
        title
        author {
            name
            nationality
        }
        reviews(limit: 3) {
            rating
            comment
        }
    }
}
```

**Caractéristiques GraphQL** :
- Un seul endpoint (`/graphql`)
- Le client spécifie exactement les données qu'il veut
- Élimine l'over-fetching et l'under-fetching
- Type system fort
- Excellent pour des UIs complexes avec des besoins de données variables

### Tableau comparatif

| Critère              | REST          | SOAP          | GraphQL       |
|---------------------|---------------|---------------|---------------|
| Format              | JSON/XML      | XML           | JSON          |
| Endpoints           | Multiple      | Multiple      | Un seul       |
| Typage              | Faible        | Fort (WSDL)   | Fort (Schema) |
| Flexibilité client  | Moyenne       | Faible        | Très forte    |
| Caching             | Facile        | Difficile     | Complexe      |
| Courbe apprentissage| Faible        | Élevée        | Moyenne       |
| Cas d'usage         | APIs générales| Entreprise    | UIs complexes |

---

## 7. Qu'est-ce qui Rend une API Véritablement RESTful ?

### API "REST-like" (très commune)

```
- Utilise HTTP
- JSON pour les données
- URIs pour les ressources
- GET/POST/PUT/DELETE
```

La plupart des "REST APIs" s'arrêtent ici. C'est acceptable en pratique, mais ce n'est pas strictement RESTful.

### API Vraiment RESTful

En plus des points ci-dessus :
1. Toutes les 6 contraintes respectées
2. HATEOAS implémenté
3. Content negotiation (Accept headers)
4. Messages auto-descriptifs
5. Pas d'état de session côté serveur

Richardson Maturity Model mesure le niveau de maturité REST :

```
Niveau 0 : HTTP comme tunnel (RPC via HTTP)
Niveau 1 : Ressources (URIs différents par ressource)
Niveau 2 : HTTP Verbs (GET/POST/PUT/DELETE)
Niveau 3 : HATEOAS (hypermedia controls)
```

---

## 8. HATEOAS — Hypermedia As The Engine Of Application State

HATEOAS est la contrainte la plus avancée et la moins implémentée de REST.

**Principe** : Les réponses incluent des liens hypermédia qui guident le client vers les prochaines actions possibles. Le client n'a pas besoin de connaître les URIs à l'avance — il les découvre dynamiquement.

### Exemple sans HATEOAS (niveau 2)

```json
// GET /api/v1/books/42
{
    "id": 42,
    "title": "Clean Code",
    "available": true
}
// Le client doit savoir "de mémoire" quels endpoints existent
```

### Exemple avec HATEOAS (niveau 3)

```json
// GET /api/v1/books/42
{
    "id": 42,
    "title": "Clean Code",
    "available": true,
    "_links": {
        "self": {
            "href": "/api/v1/books/42",
            "method": "GET"
        },
        "update": {
            "href": "/api/v1/books/42",
            "method": "PUT"
        },
        "delete": {
            "href": "/api/v1/books/42",
            "method": "DELETE"
        },
        "borrow": {
            "href": "/api/v1/books/42/borrow",
            "method": "POST"
        },
        "reviews": {
            "href": "/api/v1/books/42/reviews",
            "method": "GET"
        },
        "collection": {
            "href": "/api/v1/books",
            "method": "GET"
        }
    }
}
```

### HATEOAS dans les collections

```json
// GET /api/v1/books?page=2
{
    "count": 150,
    "results": [
        {"id": 21, "title": "Refactoring"},
        {"id": 22, "title": "The Pragmatic Programmer"}
    ],
    "_links": {
        "self":     {"href": "/api/v1/books?page=2"},
        "first":    {"href": "/api/v1/books?page=1"},
        "prev":     {"href": "/api/v1/books?page=1"},
        "next":     {"href": "/api/v1/books?page=3"},
        "last":     {"href": "/api/v1/books?page=8"}
    }
}
```

---

## 9. Exemples de Conception d'API Réelle

### Système de bibliothèque

```
# Livres
GET    /api/v1/books                    # Liste tous les livres
POST   /api/v1/books                    # Crée un nouveau livre
GET    /api/v1/books/{id}               # Récupère un livre
PUT    /api/v1/books/{id}               # Met à jour un livre (total)
PATCH  /api/v1/books/{id}               # Met à jour un livre (partiel)
DELETE /api/v1/books/{id}               # Supprime un livre

# Avis sur les livres
GET    /api/v1/books/{id}/reviews       # Avis du livre
POST   /api/v1/books/{id}/reviews       # Ajoute un avis
GET    /api/v1/books/{id}/reviews/{rid} # Avis spécifique
DELETE /api/v1/books/{id}/reviews/{rid} # Supprime un avis

# Membres
GET    /api/v1/members                  # Liste les membres
POST   /api/v1/members                  # Inscrit un membre
GET    /api/v1/members/{id}             # Profil d'un membre
PATCH  /api/v1/members/{id}             # Met à jour un profil
GET    /api/v1/members/{id}/loans       # Emprunts d'un membre

# Emprunts
GET    /api/v1/loans                    # Tous les emprunts actifs
POST   /api/v1/loans                    # Crée un emprunt
GET    /api/v1/loans/{id}               # Détails d'un emprunt
PATCH  /api/v1/loans/{id}/return        # Retourne un livre
```

### Format de réponse cohérent

```json
// Succès — Objet unique
// GET /api/v1/books/42
// HTTP 200 OK
{
    "id": 42,
    "title": "Clean Code",
    "author": "Robert Martin",
    "isbn": "978-0132350884",
    "available": true,
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-07-20T08:15:00Z"
}

// Succès — Collection paginée
// GET /api/v1/books
// HTTP 200 OK
{
    "count": 150,
    "next": "/api/v1/books?page=2",
    "previous": null,
    "results": [
        {"id": 1, "title": "Clean Code", "author": "Robert Martin"},
        {"id": 2, "title": "Refactoring", "author": "Martin Fowler"}
    ]
}

// Erreur de validation
// POST /api/v1/books  (avec données manquantes)
// HTTP 400 Bad Request
{
    "errors": {
        "title": ["Ce champ est obligatoire."],
        "isbn": ["Numéro ISBN invalide."]
    }
}

// Ressource créée
// POST /api/v1/books
// HTTP 201 Created
// Location: /api/v1/books/43
{
    "id": 43,
    "title": "The Clean Coder",
    "author": "Robert Martin"
}
```

---

## 10. Anti-patterns à Éviter

### Verbes dans les URIs

```
# Mauvais
POST /api/v1/createUser
POST /api/v1/deleteBook/42
GET  /api/v1/fetchAllOrders

# Bon
POST   /api/v1/users
DELETE /api/v1/books/42
GET    /api/v1/orders
```

### Ignorer les codes de statut HTTP

```python
# Mauvais — tout renvoie 200, même les erreurs
def get_book(request, book_id):
    try:
        book = Book.objects.get(id=book_id)
        return JsonResponse({"data": book_data})
    except Book.DoesNotExist:
        return JsonResponse({"error": "Not found"})  # Status 200 !

# Bon — codes appropriés
def get_book(request, book_id):
    try:
        book = Book.objects.get(id=book_id)
        return JsonResponse(book_data, status=200)
    except Book.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
```

### Mettre des informations sensibles dans les URIs

```
# Mauvais (token dans l'URI — apparaît dans les logs)
GET /api/v1/users?token=secret123

# Bon (token dans le header)
GET /api/v1/users
Authorization: Bearer secret123
```

### Sessions côté serveur

```python
# Mauvais — REST avec sessions = violation de Stateless
def get_user_data(request):
    user_id = request.session.get('user_id')  # Etat côté serveur !
    ...

# Bon — JWT sans état
def get_user_data(request):
    token = request.headers.get('Authorization')
    user_id = decode_jwt(token)['user_id']  # Tout dans le token
    ...
```

---

## 11. Documentation d'API avec OpenAPI / Swagger

Une bonne API REST est bien documentée. OpenAPI (anciennement Swagger) est le standard :

```yaml
# openapi.yaml
openapi: "3.0.3"
info:
  title: "Library API"
  version: "1.0.0"

paths:
  /api/v1/books:
    get:
      summary: "Liste tous les livres"
      parameters:
        - name: genre
          in: query
          schema:
            type: string
        - name: page
          in: query
          schema:
            type: integer
      responses:
        "200":
          description: "Succès"
          content:
            application/json:
              schema:
                type: object
                properties:
                  count:
                    type: integer
                  results:
                    type: array
                    items:
                      $ref: "#/components/schemas/Book"

    post:
      summary: "Crée un livre"
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/BookCreate"
      responses:
        "201":
          description: "Créé avec succès"
        "400":
          description: "Données invalides"

components:
  schemas:
    Book:
      type: object
      properties:
        id:
          type: integer
        title:
          type: string
        author:
          type: string
        available:
          type: boolean
```

---

## 12. Résumé : Les Règles d'Or d'une API REST

1. **Utilisez des noms (pas des verbes) dans vos URIs**
2. **Utilisez les méthodes HTTP correctement** : GET lit, POST crée, PUT remplace, PATCH modifie, DELETE supprime
3. **Utilisez les codes de statut HTTP appropriés** — ne retournez pas 200 pour les erreurs
4. **Soyez sans état** — aucune session serveur, utilisez JWT
5. **Versionnez votre API** — préfixez avec `/api/v1/`
6. **Paginéz vos collections** — ne retournez jamais des milliers d'éléments d'un coup
7. **Utilisez JSON** comme format par défaut
8. **Documentez votre API** avec OpenAPI/Swagger
9. **Respectez la hiérarchie des ressources** pour les relations
10. **Retournez toujours un format d'erreur cohérent**

---

## Pour Aller Plus Loin

- **Thèse de Roy Fielding** : https://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm
- **Richardson Maturity Model** : https://martinfowler.com/articles/richardsonMaturityModel.html
- **RFC 7231** : Sémantique HTTP
- **JSON:API** : Standard de format pour les APIs JSON (https://jsonapi.org)
- **OpenAPI Specification** : https://swagger.io/specification/
