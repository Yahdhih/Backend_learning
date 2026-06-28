# Jour 45 — XSS et injection SQL
📅 10 août 2026 · Module : Sécurité

---

## XSS — Cross-Site Scripting

XSS = injecter du JavaScript malveillant dans une page web que d'autres utilisateurs vont voir.

### Types de XSS

**Stored XSS (persistant) :** Le payload est stocké en DB et affiché à tous.
```
Attaquant poste un commentaire :
"Super article ! <script>document.cookie = 'vol_de_session'</script>"

→ Tous les visiteurs qui voient le commentaire exécutent le script.
```

**Reflected XSS :** Le payload est dans l'URL, reflété dans la page.
```
Lien piégé : https://site.com/search?q=<script>alert('XSS')</script>
→ Si le site affiche "Résultats pour <query>" sans échapper, le script s'exécute.
```

**DOM XSS :** Le payload manipule le DOM via JavaScript côté client.

### Protection côté serveur (Django)

Django échappe automatiquement dans les templates :

```html
<!-- templates/commentaires.html -->
{{ commentaire.texte }}
<!-- "Super <script>alert(1)</script>" devient :
     "Super &lt;script&gt;alert(1)&lt;/script&gt;" -->

<!-- DANGEREUX — ne jamais faire sans raison valide -->
{{ commentaire.texte|safe }}
```

```python
from django.utils.html import mark_safe, escape

# Correct : échapper manuellement
def ma_vue(request):
    texte_utilisateur = request.GET.get("q", "")
    texte_safe = escape(texte_utilisateur)  # '<' → '&lt;'
    return HttpResponse(f"<p>Résultats pour {texte_safe}</p>")

# DANGEREUX
texte_utilisateur = request.GET.get("q", "")
return HttpResponse(f"<p>Résultats pour {texte_utilisateur}</p>")  # XSS !
```

### Content Security Policy (CSP)

```python
# Middleware ou header response
response["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
# → Le navigateur refuse d'exécuter des scripts inline ou depuis d'autres domaines
```

---

## SQL Injection

L'attaquant injecte du SQL dans une requête pour lire/modifier/supprimer des données.

### L'attaque classique

```python
# CODE VULNÉRABLE — JAMAIS faire ça
username = request.POST["username"]
password = request.POST["password"]
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"

# Payload attaquant : username = "admin' --"
# Query résultante : SELECT * FROM users WHERE username='admin' --' AND password='...'
# Le -- commente le reste → authentification bypassée !
```

```python
# Autre payload : username = "'; DROP TABLE users; --"
# Query : SELECT * FROM users WHERE username=''; DROP TABLE users; --'
# Résultat : toute la table users est supprimée !
```

### Protection : requêtes paramétrées

```python
# Correct — Django ORM paramétrise automatiquement
User.objects.get(username=username, password=password)
# SQL généré : SELECT * FROM users WHERE username = ? AND password = ?
# Les ? sont remplacés par la DB, jamais interprétés comme SQL

# Correct — cursor.execute avec paramètres
with connection.cursor() as cursor:
    cursor.execute(
        "SELECT * FROM users WHERE username = %s AND password = %s",
        [username, password]   # jamais concaténer dans la string !
    )

# DANGEREUX — même avec cursor
cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")  # SQLi !
```

### L'ORM Django protège, SAUF

```python
# raw() avec concaténation → DANGEREUX
Article.objects.raw(f"SELECT * FROM articles WHERE titre = '{titre}'")

# raw() correct
Article.objects.raw("SELECT * FROM articles WHERE titre = %s", [titre])

# extra() avec concaténation → DANGEREUX (déprécié de toute façon)
Article.objects.extra(where=[f"titre = '{titre}'"])  # SQLi possible
```

---

## Autres injections

### Command injection

```python
# DANGEREUX
import subprocess
nom_fichier = request.GET["file"]
subprocess.run(f"cat {nom_fichier}", shell=True)  # ; rm -rf / fonctionne !

# Correct
subprocess.run(["cat", nom_fichier], shell=False)  # pas shell=True
```

### Path traversal

```python
# DANGEREUX
nom_fichier = request.GET["file"]
with open(f"/uploads/{nom_fichier}") as f:   # ../../../etc/passwd fonctionne !
    ...

# Correct
import os
nom_fichier = os.path.basename(request.GET["file"])  # retire les ../
chemin = os.path.join("/uploads", nom_fichier)
if not chemin.startswith("/uploads/"):  # double vérification
    return HttpResponse("Interdit", status=403)
```

---

## Résumé des protections

| Attaque | Protection Django |
|---------|-----------------|
| XSS dans templates | Auto-échappement (ne pas utiliser `\|safe`) |
| XSS dans JSON API | `JsonResponse` encode correctement |
| SQL injection | ORM, ou `cursor.execute` avec paramètres `%s` |
| Command injection | Ne jamais utiliser `shell=True` avec input utilisateur |
| Path traversal | `os.path.basename()` + validation du chemin résultant |
