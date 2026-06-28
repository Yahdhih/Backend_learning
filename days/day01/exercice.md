# Exercice Jour 01 — Observer le DNS en action

## Partie 1 — Inspecter le DNS (terminal)

Lance ces commandes et note ce que tu vois :

```bash
# Résoudre un domaine
dig google.com

# Voir le chemin complet de résolution DNS
dig +trace google.com

# Voir le TTL (combien de temps l'IP est cachée)
dig google.com | grep -A1 "ANSWER SECTION"

# Comparer les IPs de différents domaines
dig github.com
dig stackoverflow.com
```

**Questions à répondre dans `notes.md` :**
1. Quelle est l'IP de `google.com` ?
2. Quel est le TTL retourné ? En combien de temps expirera le cache ?
3. Combien d'IPs différentes `google.com` retourne-t-il ? Pourquoi plusieurs ?

---

## Partie 2 — Observer TCP avec netcat

```bash
# Ouvre une connexion TCP brute vers google.com port 80
nc google.com 80

# Ensuite tape exactement ça (puis appuie 2 fois sur Entrée) :
GET / HTTP/1.0
Host: google.com

```

Tu vas voir la réponse HTTP brute de Google. C'est exactement ce que ton navigateur reçoit.

**Questions :**
1. Quel code de statut tu reçois ? Pourquoi pas 200 ?
2. Que dit le header `Location` ?

---

## Partie 3 — Réfléchir

Dans `notes.md`, réponds à cette question **dans tes propres mots** (3-5 phrases) :

> "Décris ce qui se passe entre le moment où tu tapes `https://github.com` et le moment où la page s'affiche. Étape par étape."

Pas de copier-coller du cours. Reformule avec tes mots.
