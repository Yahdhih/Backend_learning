# Exercice Jour 63 — Nginx + Gunicorn en production

## Objectif

Configurer Nginx comme reverse proxy devant Gunicorn, tester SSL et benchmarker les performances.

---

## Partie 1 : Configuration Gunicorn

### 1.1 — Créer gunicorn.conf.py
```bash
# À la racine du projet, créer gunicorn.conf.py
# Copier le contenu du cours (calcul automatique des workers)
```

### 1.2 — Tester Gunicorn localement
```bash
# Sans Docker, dans ton venv
pip install gunicorn

# Lancer manuellement
gunicorn blog_api.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --log-level info

# Tester
curl http://localhost:8000/api/posts/
```

### 1.3 — Vérifier les workers dans Docker
```bash
# Avec Docker
docker-compose -f docker-compose.prod.yml up -d web

# Voir les workers Gunicorn qui tournent
docker-compose exec web ps aux | grep gunicorn
# Tu dois voir : 1 master + N workers
```

---

## Partie 2 : Configuration Nginx de base (dev)

### 2.1 — Créer la config Nginx de dev
```bash
mkdir -p nginx
# Créer nginx/nginx.conf avec la config dev du cours
```

### 2.2 — Ajouter Nginx dans docker-compose.yml (dev)
```yaml
# Ajouter ce service dans docker-compose.yml
nginx:
  image: nginx:1.25-alpine
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    - dev_static:/var/www/static:ro
    - dev_media:/var/www/media:ro
  ports:
    - "80:80"
  depends_on:
    - web
```

### 2.3 — Tester la configuration
```bash
# Redémarrer avec Nginx
docker-compose up -d

# Vérifier que Nginx est OK
docker-compose exec nginx nginx -t
# Expected: nginx: configuration file /etc/nginx/nginx.conf test is successful

# Tester via Nginx (port 80, pas 8000)
curl http://localhost/api/posts/

# Vérifier que les fichiers statiques passent par Nginx
curl -I http://localhost/static/admin/css/base.css
# Le header Server doit indiquer nginx, pas gunicorn/django
```

---

## Partie 3 : Tester les headers de sécurité

### 3.1 — Vérifier les headers
```bash
# Avec la config de prod (simulée localement), vérifier les headers
curl -I http://localhost/api/posts/

# Headers attendus :
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Referrer-Policy: strict-origin-when-cross-origin
```

### 3.2 — Tester le rate limiting
```bash
# Envoyer 25 requêtes rapides
for i in {1..25}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/posts/)
    echo "Requête $i : $STATUS"
done

# Après 10-20 requêtes, tu dois voir des 429 (Too Many Requests)
```

### 3.3 — Tester la protection des fichiers sensibles
```bash
# Ces URLs doivent retourner 404
curl -I http://localhost/.env
curl -I http://localhost/.git/config
curl -I http://localhost/backup.sql
```

---

## Partie 4 : SSL avec Let's Encrypt (sur un vrai serveur)

> Si tu n'as pas encore de serveur, passe à la Partie 5.
> Si tu as un domaine et un serveur, suis ces étapes.

### 4.1 — Prérequis
```bash
# Ton domaine doit pointer vers l'IP de ton serveur
# Vérifier le DNS
dig votre-domaine.com +short   # Doit retourner ton IP
nslookup votre-domaine.com     # Alternativement
```

### 4.2 — Premier certificat
```bash
# Sur le serveur

# 1. Démarrer Nginx sans SSL (commenter les directives ssl_ temporairement)
docker-compose -f docker-compose.prod.yml up -d nginx

# 2. Vérifier que le challenge ACME fonctionne
curl http://votre-domaine.com/.well-known/acme-challenge/test

# 3. Obtenir le certificat
docker-compose -f docker-compose.prod.yml run --rm certbot \
    certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email ton@email.com \
    --agree-tos \
    --no-eff-email \
    -d votre-domaine.com \
    -d www.votre-domaine.com

# 4. Décommenter les directives SSL dans nginx.prod.conf

# 5. Recharger Nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### 4.3 — Vérifier SSL
```bash
# Vérifier le grade SSL (en ligne)
# https://www.ssllabs.com/ssltest/analyze.html?d=votre-domaine.com
# Objectif : Grade A ou A+

# Vérifier l'expiration du certificat
echo | openssl s_client -servername votre-domaine.com \
    -connect votre-domaine.com:443 2>/dev/null | \
    openssl x509 -noout -dates

# Tester HSTS
curl -I https://votre-domaine.com | grep Strict-Transport-Security
# Expected: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

---

## Partie 5 : Benchmark

### 5.1 — Benchmark avec curl (basique)
```bash
# Temps de réponse d'une requête
curl -w "\n\nDNS: %{time_namelookup}s\nConnexion: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" \
    -o /dev/null -s http://localhost/api/posts/
```

### 5.2 — Benchmark avec Apache Benchmark
```bash
# Installer ab
sudo apt-get install apache2-utils  # Linux
brew install wrk                     # macOS

# Test de base : liste des posts
ab -n 500 -c 10 http://localhost/api/posts/

# Résultats attendus et à noter :
# Requests per second: _____ [#/sec]
# Time per request: _____ [ms] (mean)
# 50th percentile: _____ [ms]
# 95th percentile: _____ [ms]
# 99th percentile: _____ [ms]
# Failed requests: _____
```

### 5.3 — Comparer avec et sans Nginx
```bash
# 1. Test direct sur Gunicorn (port 8000)
ab -n 500 -c 10 http://localhost:8000/api/posts/
# Note le résultat

# 2. Test via Nginx (port 80)
ab -n 500 -c 10 http://localhost:80/api/posts/
# Compare

# Nginx devrait être plus rapide pour les fichiers statiques
# et comparable pour l'API (légère surcharge de proxy)

# 3. Test des fichiers statiques (gros gain)
ab -n 1000 -c 20 http://localhost/static/admin/css/base.css
# Ces fichiers sont servis par Nginx directement — très rapide
```

### 5.4 — Benchmark avec wrk (si disponible)
```bash
# Installer wrk
# brew install wrk (macOS)
# https://github.com/wg/wrk (Linux)

# Test 30 secondes
wrk -t4 -c50 -d30s http://localhost/api/posts/

# Résultat typique :
# Thread Stats   Avg      Stdev     Max   +/- Stdev
#   Latency    45.23ms   15.67ms 189.34ms   78.45%
#   Req/Sec   278.45     42.31   400.00     68.00%
# 33414 requests in 30.05s, 12.34MB read
# Requests/sec:  1112.34
```

---

## Partie 6 : Optimisations supplémentaires

### 6.1 — Activer le cache Nginx pour l'API
```nginx
# Ajouter dans le bloc location /api/ (pour les GET seulement)
location /api/ {
    proxy_cache static_cache;
    proxy_cache_valid 200 60s;     # Cache les 200 pendant 60s
    proxy_cache_use_stale error timeout updating;
    proxy_cache_methods GET HEAD;  # Seulement pour GET/HEAD
    proxy_no_cache $http_authorization;  # Pas de cache si authentifié

    add_header X-Cache-Status $upstream_cache_status;  # HIT/MISS dans les headers

    limit_req zone=api burst=20 nodelay;
    proxy_pass http://django_app;
    include /etc/nginx/proxy_params;
}
```

### 6.2 — Vérifier le cache
```bash
curl -I http://localhost/api/posts/
# Chercher : X-Cache-Status: MISS (première fois)

curl -I http://localhost/api/posts/
# Chercher : X-Cache-Status: HIT (requêtes suivantes)
```

---

## Validation finale

Coche chaque point :

- [ ] Gunicorn démarre avec le bon nombre de workers (`ps aux | grep gunicorn`)
- [ ] Nginx est accessible sur le port 80
- [ ] `nginx -t` passe sans erreur
- [ ] Les requêtes API passent via Nginx vers Gunicorn
- [ ] Les fichiers statiques sont servis par Nginx directement
- [ ] Le rate limiting bloque les requêtes excessives (429)
- [ ] Les fichiers `.env` et `.git` retournent 404
- [ ] Le benchmark donne > 100 req/s sur l'API (objectif raisonnable)
- [ ] (Si serveur réel) SSL obtenu avec grade A sur ssllabs.com
- [ ] (Si serveur réel) HSTS header présent dans les réponses
