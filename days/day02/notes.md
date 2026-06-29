# Le protocole du web

## Partie 1 - Voir une requête/réponse complète

**Question :** Quel header indique le format du body reçu ?

**Reponse :**  Le header qui indique le format du body est "content-type" 

## Partie 2 - Les méthodes HTTP

**NB :** la commande curl lance par défaut la commande GET et renvoie le body json

On va se concentré un peu sur le cours pour le bien maitriser: 
http est un protocole (HypperText Transfert Protocole) qui permet d'envoie des requête et recevoir les reponses sous forme de text, ce text peux avoir plusieurs format, html, json.... 
IL y a 5 grand type de requêtes à savoir par coeur et maitriser qui sont:
GET : permet de recupérer des données du serveur solicité, la commande curl envoie par défaut le body sous format json.
POST : permet de créer une source, c'est quoi la signification de ça? c'est créer un nouveau élement dans le database, un utilisateur par exemple.
PUT : permet remplacer entièrement, c'est un PATCH globale.
PATCH : permet de modifier les données à l'aide du terminale, par exemple si on veut modifier nos données sur une site les modification et les click qu'on fait ne sont rien d'autres que des rquêtes POST
DELETE : comme son nom l'indique celui-ci permet de supprimer du contenu.

**Question :** Dans la réponse de httpbin, que contient le champ `json` ?

**Reponse :** le champ `json`contient les données ajoutées ou modifiées, on remarque que ce est `null` pour les requêtes `DELETE` et `PATCH`. 

## Partie 3 - Les codes de statut

En lançant les commandes, j'ai deux remarques. La première est que la commande 
# 404 Not Found
curl -s -o /dev/null -w "%{http_code}" https://httpbin.org/status/404

qui est sensé retourné une erreur de 404(not found) retourne une erreur de 503(erreur de serveur?)

Expectation : 
il y a 4 types de status des reponses des requêtes http : 
200 : succes, la requête est bien passé et la reponse a été bien reçu. Pas d'erreurs ni de la part du seveur ni de la part du client!
300 : Rédirection, la site est ancienne, donc on redirige l'utilisateur vers la nouvelle site par exemple.
400 : Erreur de la part du client, la requête du client n'existe pas ou le serveur au quel il demande l'accès n'est pas trouvé.
500 : Erreur du niveau du serveur, le serveur existe mais il ne repond pas!

Cool, tu as bien fait tout ça, il manque quels que détails les voici dans le tableau suivant: 

| Plage | Signification | Exemples |
|-------|--------------|---------|
| 2xx | Succès | 200 OK, 201 Created, 204 No Content |
| 3xx | Redirection | 301 Moved Permanently, 302 Found |
| 4xx | Erreur client | 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found |
| 5xx | Erreur serveur | 500 Internal Server Error, 503 Service Unavailable |

**Question :** Que fait curl face à une redirection ? Suit-il automatiquement ?
(Indice : essaie avec `-L` pour voir la différence)

**Reponse :** Non curl ne suit pas directement la redirection, en fait elle nous indique où aller mais elle n'envoie pas de requête à la nouvelle destination trouvée. Mais si on ajoute le tag -L, curl suit bien la redirection. 
La reponse de curl sans le flag -L est la suivante(évidement juste la partie consernant le host au quel on est redirigé!) 
```bash
* Request completely sent off
< HTTP/1.1 301 Moved Permanently
< Content-Length: 0
< Location: https://github.com/
< 
* Connection #0 to host github.com left intact
```
## Partie 4 - Headers personnalilsés

httpbin.org est tombé donc j'ai pas pu lancer la requête. J'ai dans un autre temps si j'aurais l'occasion 

## Partie 5 - Réflexion

1. Quelle est la différence entre `401 Unauthorized` et `403 Forbidden` ?

La différence est claire : 
`401 Unauthorized` : signifie que l'utilisateur ne s'est pas authentifié. 
`403 Forbidden` : signifie que l'utilisateur est authentifié mais il n'est pas autorisé.

2. Pourquoi dit-on qu'HTTP est "stateless" ?
HTTP est stateless car les requêtes sont indépendantes. Le serveur ne se souvient pas de la requête précédente. On dit aussi que HTTP est sans mémoire.
3. À quoi sert le header `Content-Type` et pourquoi est-il important ?
`Content-Type` est le header qui contient le contenu du réponse demandé quand il est dans la requête envoyée et il contient le type de reponse lorsqu'il est dans la réponse envoyée par le serveur.

