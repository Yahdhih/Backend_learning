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
