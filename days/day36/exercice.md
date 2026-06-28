# Exercice Jour 36 — Auth et Permissions sur le blog

## Objectif

Ajouter les permissions au projet et vérifier que chaque règle fonctionne correctement.

---

## Étape 1 : Créer permissions.py

Crée `blog/permissions.py` et copie le code complet du cours.

---

## Étape 2 : Mettre à jour views.py

Remplace le contenu de `blog/views.py` par le code du cours (version avec permissions).

Ajoute les imports manquants :

```python
from .permissions import IsAuthorOrReadOnly, IsAuthorOrAdmin, IsCommentAuthorOrPostAuthor
```

---

## Étape 3 : Mettre à jour urls.py

Ajoute les nouveaux endpoints dans `blog/urls.py` :

```python
path('auth/logout/', LogoutView.as_view(), name='logout'),
path('auth/me/', MeView.as_view(), name='me'),
```

---

## Étape 4 : Script de tests de permissions

Crée `test_permissions.sh` à la racine du projet :

```bash
#!/bin/bash
# test_permissions.sh
# Lance avec : bash test_permissions.sh

BASE="http://127.0.0.1:8000/api"
PASS=0
FAIL=0

check() {
    local description="$1"
    local expected_status="$2"
    local actual_status="$3"

    if [ "$actual_status" = "$expected_status" ]; then
        echo "PASS : $description (HTTP $actual_status)"
        ((PASS++))
    else
        echo "FAIL : $description (attendu $expected_status, obtenu $actual_status)"
        ((FAIL++))
    fi
}

echo "=== Inscription des utilisateurs ==="

# Alice
ALICE_RESP=$(curl -s -w "\n%{http_code}" -X POST $BASE/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice_perm", "email": "alice_p@example.com", "password": "password123", "password_confirm": "password123"}')
ALICE_TOKEN=$(echo "$ALICE_RESP" | head -1 | python -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
ALICE_STATUS=$(echo "$ALICE_RESP" | tail -1)
check "Inscription Alice" "201" "$ALICE_STATUS"

# Bob
BOB_RESP=$(curl -s -w "\n%{http_code}" -X POST $BASE/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "bob_perm", "email": "bob_p@example.com", "password": "password123", "password_confirm": "password123"}')
BOB_TOKEN=$(echo "$BOB_RESP" | head -1 | python -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

echo ""
echo "=== Création d'un post par Alice ==="

POST_RESP=$(curl -s -w "\n%{http_code}" -X POST $BASE/posts/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $ALICE_TOKEN" \
  -d '{"title": "Post permission test", "content": "Contenu de test...", "status": "draft"}')
POST_ID=$(echo "$POST_RESP" | head -1 | python -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
POST_STATUS=$(echo "$POST_RESP" | tail -1)
check "Alice crée un post" "201" "$POST_STATUS"

echo ""
echo "=== Tests de lecture ==="

# Anonymous voit la liste (posts publiés)
S=$(curl -s -o /dev/null -w "%{http_code}" $BASE/posts/)
check "Anonymous : liste des posts publiés" "200" "$S"

# Anonymous essaie de voir le draft d'Alice
S=$(curl -s -o /dev/null -w "%{http_code}" $BASE/posts/$POST_ID/)
check "Anonymous : voir le draft d'Alice (403 attendu)" "403" "$S"

# Alice voit son propre draft
S=$(curl -s -o /dev/null -w "%{http_code}" $BASE/posts/$POST_ID/ \
  -H "Authorization: Token $ALICE_TOKEN")
check "Alice : voir son propre draft" "200" "$S"

# Bob essaie de voir le draft d'Alice
S=$(curl -s -o /dev/null -w "%{http_code}" $BASE/posts/$POST_ID/ \
  -H "Authorization: Token $BOB_TOKEN")
check "Bob : voir le draft d'Alice (403 attendu)" "403" "$S"

echo ""
echo "=== Tests de modification ==="

# Bob essaie de modifier le post d'Alice
S=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH $BASE/posts/$POST_ID/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $BOB_TOKEN" \
  -d '{"title": "Modifié par Bob"}')
check "Bob : modifier le post d'Alice (403 attendu)" "403" "$S"

# Alice modifie son propre post
S=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH $BASE/posts/$POST_ID/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $ALICE_TOKEN" \
  -d '{"title": "Post modifié par Alice"}')
check "Alice : modifier son propre post" "200" "$S"

echo ""
echo "=== Tests de publication ==="

# Bob essaie de publier le post d'Alice
S=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/posts/$POST_ID/publish/ \
  -H "Authorization: Token $BOB_TOKEN")
check "Bob : publier le post d'Alice (403 attendu)" "403" "$S"

# Alice publie son post
S=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/posts/$POST_ID/publish/ \
  -H "Authorization: Token $ALICE_TOKEN")
check "Alice : publier son post" "200" "$S"

# Maintenant anonymous peut voir le post
S=$(curl -s -o /dev/null -w "%{http_code}" $BASE/posts/$POST_ID/)
check "Anonymous : voir le post publié" "200" "$S"

echo ""
echo "=== Tests de suppression ==="

# Bob essaie de supprimer le post d'Alice
S=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE $BASE/posts/$POST_ID/ \
  -H "Authorization: Token $BOB_TOKEN")
check "Bob : supprimer le post d'Alice (403 attendu)" "403" "$S"

# Alice supprime son propre post
S=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE $BASE/posts/$POST_ID/ \
  -H "Authorization: Token $ALICE_TOKEN")
check "Alice : supprimer son propre post" "204" "$S"

echo ""
echo "=== Tests d'authentification ==="

# Créer un post sans auth
S=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/posts/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Sans auth", "content": "..."}')
check "Anonymous : créer un post (401 attendu)" "401" "$S"

# Profil de l'utilisateur connecté
S=$(curl -s -o /dev/null -w "%{http_code}" $BASE/auth/me/ \
  -H "Authorization: Token $ALICE_TOKEN")
check "Alice : voir son profil" "200" "$S"

# Logout Alice
S=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/auth/logout/ \
  -H "Authorization: Token $ALICE_TOKEN")
check "Alice : logout" "200" "$S"

# Après logout, le token est invalide
S=$(curl -s -o /dev/null -w "%{http_code}" $BASE/auth/me/ \
  -H "Authorization: Token $ALICE_TOKEN")
check "Alice : token invalide après logout (401 attendu)" "401" "$S"

echo ""
echo "========================"
echo "Résultats : $PASS PASS, $FAIL FAIL"
echo "========================"
```

Lance avec :

```bash
bash test_permissions.sh
```

---

## Étape 5 : Tests manuels à compléter

En plus du script, teste manuellement ces scénarios :

**Scénario 1 — Commentaires**
1. Alice crée et publie un post
2. Bob commente le post
3. Alice essaie de modifier le commentaire de Bob → 403
4. Bob modifie son propre commentaire → 200
5. Alice (auteure du post) supprime le commentaire de Bob → 200

**Scénario 2 — my_posts**
1. Alice crée 2 posts (1 draft, 1 publié)
2. `GET /api/posts/my_posts/` avec token Alice → voit les 2 posts
3. `GET /api/posts/my_posts/` avec token Bob → voit seulement ses posts
4. `GET /api/posts/my_posts/` sans token → 401

---

## Questions de réflexion

1. Quelle est la différence entre `has_permission()` et `has_object_permission()` ?
   - Quand est appelé chacun ?
   - Peut-on avoir `has_permission = False` mais `has_object_permission = True` ?

2. Pourquoi retourne-t-on `False` dans `has_permission` pour les non-authentifiés plutôt que de lancer une exception ?

3. Que se passe-t-il si on met `permission_classes = []` sur un ViewSet ?

4. Comment testerait-on les permissions dans une suite de tests automatisés ?

---

## Bonus : Throttling (limitation du taux)

Ajoute dans `settings.py` pour limiter les requêtes d'abus :

```python
REST_FRAMEWORK = {
    # ... autres configs ...
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',    # 100 requêtes par jour pour les non-auth
        'user': '1000/day',   # 1000 requêtes par jour pour les auth
    }
}
```

Teste : lance 101 requêtes anonymes et observe la réponse 429 Too Many Requests.
