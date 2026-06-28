# Plan Jour par Jour — 1h/jour

> Début : 27 juin 2026 · Fin estimée : ~31 août 2026
> Coche chaque jour dans [PROGRESS.md](PROGRESS.md) quand c'est fait.

---

## MODULE 00 — How the Web Works (3 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J1 | 27 juin | Lire la théorie complète | [README](modules/00_how_the_web_works/README.md) |
| J2 | 28 juin | Exercise 01 — curl exploration | [01_curl_exploration.md](modules/00_how_the_web_works/exercises/01_curl_exploration.md) |
| J3 | 29 juin | Exercise 02 — Raw socket server + Exercise 03 — DNS | [02_raw_socket_server.py](modules/00_how_the_web_works/exercises/02_raw_socket_server.py) · [03_dns_deep_dive.md](modules/00_how_the_web_works/exercises/03_dns_deep_dive.md) |

**Question de fin de module :** "Que se passe-t-il entre le moment où tu tapes une URL et l'affichage de la page ?"

---

## MODULE 01 — Python Crash Course (4 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J4 | 30 juin | Lire théorie sections 1–5 (syntax, types, fonctions, comprehensions, decorators) | [README](modules/01_python_crash_course/README.md) |
| J5 | 1 juil | Lire théorie sections 6–9 (classes, generators, context managers, types hints) + Exercise 01 | [01_python_basics.py](modules/01_python_crash_course/exercises/01_python_basics.py) |
| J6 | 2 juil | Exercise 02 — OOP Python | [02_oop_python.py](modules/01_python_crash_course/exercises/02_oop_python.py) |
| J7 | 3 juil | Exercise 03 — Decorators Lab + révision du module | [03_decorators_lab.py](modules/01_python_crash_course/exercises/03_decorators_lab.py) |

**Question de fin de module :** "C'est quoi un décorateur et comment Python l'exécute ?"

---

## MODULE 02 — HTTP In Depth (4 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J8 | 4 juil | Lire la théorie complète | [README](modules/02_http_in_depth/README.md) |
| J9 | 5 juil | Exercise 01 — HTTP methods lab | [01_http_methods_lab.md](modules/02_http_in_depth/exercises/01_http_methods_lab.md) |
| J10 | 6 juil | Exercise 02 — Headers deep dive | (dans le README module 02) |
| J11 | 7 juil | Exercise 03 — HTTP parser + révision | [03_http_parser.py](modules/02_http_in_depth/exercises/03_http_parser.py) |

**Question de fin de module :** "Quelle est la différence entre HTTP stateless et une session stateful ?"

---

## MODULE 03 — WSGI (3 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J12 | 8 juil | Lire la théorie complète | [README](modules/03_wsgi_first_server/README.md) |
| J13 | 9 juil | Exercise 01 — Minimal WSGI app | [01_minimal_wsgi.py](modules/03_wsgi_first_server/exercises/01_minimal_wsgi.py) |
| J14 | 10 juil | Exercise 02 — Router from scratch + révision | [02_wsgi_router.py](modules/03_wsgi_first_server/exercises/02_wsgi_router.py) |

**Question de fin de module :** "Pourquoi Django a besoin de Gunicorn en prod mais pas en dev ?"

---

## MODULE 04 — Django Fundamentals (6 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J15 | 11 juil | Lire la théorie complète | [README](modules/04_django_fundamentals/README.md) |
| J16 | 12 juil | Exercise 01 — Premier projet Django (setup + `startproject`) | [01_first_project.md](modules/04_django_fundamentals/exercises/01_first_project.md) |
| J17 | 13 juil | Exercise 01 suite — explorer la structure générée, settings, `runserver` | (suite du J16) |
| J18 | 14 juil | Exercise 02 — URL routing et views | [02_routing_and_views.md](modules/04_django_fundamentals/exercises/02_routing_and_views.md) |
| J19 | 15 juil | Exercise 03 — Models et ORM basics | [03_models_and_orm.md](modules/04_django_fundamentals/exercises/03_models_and_orm.md) |
| J20 | 16 juil | Révision du module + répondre à la question de fin | — |

**Question de fin de module :** "C'est quoi le pattern MTV et comment une requête traverse Django ?"

---

## MODULE 05 — Databases & ORM (7 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J21 | 17 juil | Lire la théorie complète | [README](modules/05_databases_and_orm/README.md) |
| J22 | 18 juil | Exercise 01 — Raw SQL (écrire des requêtes SQL à la main) | — |
| J23 | 19 juil | Exercise 02 — Django ORM queries (partie 1 : select, filter, exclude) | — |
| J24 | 20 juil | Exercise 02 — Django ORM queries (partie 2 : annotate, aggregate, Q objects) | — |
| J25 | 21 juil | Exercise 03 — Migrations | — |
| J26 | 22 juil | Exercise 04 — Le problème N+1 | — |
| J27 | 23 juil | Révision + optimisation de requêtes | — |

**Question de fin de module :** "Quelle SQL cette requête ORM génère-t-elle ?"

---

## MODULE 06 — REST APIs with DRF (6 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J28 | 24 juil | Lire la théorie complète | [README](modules/06_rest_apis_drf/README.md) |
| J29 | 25 juil | Exercise 01 — Premier serializer | — |
| J30 | 26 juil | Exercise 02 — ViewSets et Routers (partie 1) | — |
| J31 | 27 juil | Exercise 02 — ViewSets et Routers (partie 2) | — |
| J32 | 28 juil | Exercise 03 — Filtering et Pagination | — |
| J33 | 29 juil | Révision du module | — |

**Question de fin de module :** "Qu'est-ce qui rend une API RESTful plutôt que juste HTTP ?"

---

## PROJET 01 — Blog API (5 jours)

> À faire après Module 06. Tu appliques tout ce que tu sais.

| Jour | Date | Tâche |
|------|------|-------|
| J34 | 30 juil | Setup du projet + définir les models (Post, Category, Tag) |
| J35 | 31 juil | Serializers + views CRUD |
| J36 | 1 août | Intégration auth + permissions |
| J37 | 2 août | Pagination + filtering |
| J38 | 3 août | Tests + review final |

Référence : [projects/project_01_blog_api/](projects/project_01_blog_api/README.md)

---

## MODULE 07 — Auth & Sessions (5 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J39 | 4 août | Lire la théorie complète | [README](modules/07_auth_and_sessions/README.md) |
| J40 | 5 août | Exercise 01 — Session-based auth | — |
| J41 | 6 août | Exercise 02 — JWT from scratch | — |
| J42 | 7 août | Exercise 03 — Permissions et rôles | — |
| J43 | 8 août | Révision du module | — |

**Question de fin de module :** "Quand choisir JWT plutôt que sessions ?"

---

## MODULE 08 — Security (4 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J44 | 9 août | Lire la théorie complète | [README](modules/08_security/README.md) |
| J45 | 10 août | Exercise 01 — Simulation d'attaque CSRF | — |
| J46 | 11 août | Exercise 02 — SQL injection lab | — |
| J47 | 12 août | Exercise 03 — Django security audit + révision | — |

**Question de fin de module :** "Comment la protection CSRF fonctionne dans Django ?"

---

## PROJET 02 — Auth System (5 jours)

| Jour | Date | Tâche |
|------|------|-------|
| J48 | 13 août | Setup JWT auth |
| J49 | 14 août | Permissions + rôles |
| J50 | 15 août | Token rotation + refresh |
| J51 | 16 août | Hardening sécurité |
| J52 | 17 août | Tests + review final |

Référence : [projects/project_02_auth_system/](projects/project_02_auth_system/README.md)

---

## MODULE 09 — Caching & Performance (4 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J53 | 18 août | Lire la théorie complète | [README](modules/09_caching_and_performance/README.md) |
| J54 | 19 août | Exercise 01 — Redis basics | — |
| J55 | 20 août | Exercise 02 — Django cache framework | — |
| J56 | 21 août | Exercise 03 — Optimisation de requêtes + révision | — |

**Question de fin de module :** "C'est quoi la cache invalidation et pourquoi c'est difficile ?"

---

## MODULE 10 — Deployment (5 jours)

| Jour | Date | Tâche | Fichier |
|------|------|-------|---------|
| J57 | 22 août | Lire la théorie complète | [README](modules/10_deployment/README.md) |
| J58 | 23 août | Exercise 01 — Gunicorn + Nginx | — |
| J59 | 24 août | Exercise 02 — Docker | — |
| J60 | 25 août | Exercise 03 — Environment config | — |
| J61 | 26 août | Révision du module | — |

**Question de fin de module :** "Pourquoi on ne peut pas utiliser le serveur de dev Django en production ?"

---

## PROJET 03 — Production Ready (5 jours)

| Jour | Date | Tâche |
|------|------|-------|
| J62 | 27 août | Dockeriser l'app |
| J63 | 28 août | Nginx + Gunicorn setup |
| J64 | 29 août | Caching + performance |
| J65 | 30 août | Monitoring + health checks |
| J66 | 31 août | Review final + déploiement |

Référence : [projects/project_03_production_ready/](projects/project_03_production_ready/README.md)

---

## Résumé

| | |
|---|---|
| Début | 27 juin 2026 |
| Fin | 31 août 2026 |
| Total | 66 jours / 66 heures |
| Rythme | 1 heure par jour |

> Si tu rates un jour, continue le lendemain sans te rattraper — mieux vaut avancer lentement que de te surcharger et abandonner.
