# Reponses aux Questions

## Partie 1 - Inspecterle DNS

1. Quelle est l'IP de `google.com` ?
L'IP obtenu après la requete "dig google.com" est 192.168.100.1
2. Quel est le TTL retourné ? En combien le temps expirera le cache?
En regardant la sortie de la requete 'dig google.com | grep -A1 "ANSWER SECTION"' on voit que le TTL(Time To Live) est de 237s, c'est le temps au bout du quel le cache expirera.
3. Après avoir attendre le fin de TTL(Time To Live), chaque lancement de la requete dig google.com donne une adresse IP différent. Ceci c'explique par le fait que le géant Google a des serveurs partout dans le monde pour rendre les reponses aux utilisateurs plus rapide selon leurs zones.

## Partie 2 - Observer TCP avec netcat

1. la commande netcat n'a pas marché! on y revient aprés.


## Partie 3 - Réflechir

> "Décris ce qui se passe entre le moment où tu tapes `https://github.com` et le moment où la page s'affiche. Étape par étape."

Entre le moment ou je tapes `https://github.com` le nevigateur passe par 4 étapes : 
La première consiste à la resolution du lien écrit pour le divser an 4 parties, la protocole(https) le domaine(github.com), un éventuel chemin( comme /search ) et des éventuels (paramètres). 
La seconde consiste à la resolution du DNS(Domaine name service) pour trouver l'adresse IP correspondant. 
La troisième consiste à la 3 way handshake( SYNC, ACK, and SYNC+ACK).
La quatrième est le lancement des requete http et les transfert de données. 
