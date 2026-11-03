# Tests de charge

Mesurés le 3 novembre 2026 avec k6 (`./loadtest/run.sh`), sur l'image de production (gunicorn + uvicorn,
3 processus) et les données de démo (50 pros, 48 publications).

**Ces chiffres sont des ordres de grandeur.** Le test tourne sur un ordinateur portable lent : le serveur,
la base, Redis, le stockage et k6 lui-même se partagent 4 cœurs et 8 Go. Caddy et Next ne sont pas dans
la boucle : on mesure Django. Et 48 publications, ce n'est pas une base réelle. Le test est à refaire
sur un serveur de la taille prévue (voir en bas).

## Le scénario

Une « personne » est un téléphone : elle ouvre le fil, cherche une pro, regarde les créneaux, lit environ
2 secondes entre chaque écran, et paie un tour sur cinq (prestataire de test). Chacune a sa propre adresse
IP : les limites de débit restent actives, comme en vrai.

Trois vagues de 60 secondes : 10, 30 et 60 personnes en même temps.

## Résultats (temps de réponse, en millisecondes)

| Personnes en même temps | 10 | 30 | 60 |
| --- | --- | --- | --- |
| Requêtes par seconde | 3,5 | 10,6 | 13,0 |
| Requêtes en échec | 0 | 0 | 0 |
| **Fil** : médiane / 95 % | 302 / 4 848 | 387 / 3 134 | 2 441 / 11 110 |
| **Recherche** : médiane / 95 % | 137 / 712 | 196 / 1 664 | 734 / 2 617 |
| **Disponibilités** : médiane / 95 % | 101 / 404 | 141 / 458 | 803 / 3 329 |
| **Paiement simulé** (chaque appel) : médiane / 95 % | 149 / 547 | 349 / 1 121 | 1 760 / 3 266 |
| **Du « payé » à l'argent bloqué** : médiane / 95 % | 1 305 / 1 764 | 2 448 / 3 714 | 7 587 / 12 493 |

« 95 % » veut dire que 95 requêtes sur 100 sont plus rapides que ce temps.

Le « payé » à l'argent bloqué compte une attente d'une seconde par vérification (le script regarde chaque
seconde) : le temps réel est un peu plus court.

## Ce qu'il faut en retenir

- **Jusqu'à 30 personnes en même temps** : les temps médians restent sous 0,4 seconde.
- **À 60 personnes**, la machine sature : tout ralentit, sans aucune erreur. Le débit plafonne autour de
  13 requêtes par seconde sur cet ordinateur.
- **Le 95 % du fil est élevé à toutes les charges.** Toutes les personnes commencent par le fil à la même
  seconde : c'est probablement ce départ groupé qui le tire vers le haut, car ces premières requêtes pèsent
  lourd sur un total court. Je ne l'ai pas démontré : à regarder sur un test plus long sur le vrai serveur.

## Ce que le test a trouvé et corrigé

| Problème | Effet | Correction |
| --- | --- | --- |
| Sous ASGI, chaque requête a son propre fil d'exécution, et chaque fil construisait son client S3 | 0,2 à 0,5 s de processeur par requête qui affiche un média : le fil à 6,6 s avec 10 personnes | Un seul client par processus pour signer les liens : 1 ms |
| Le code se chargeait à la première requête de chaque processus | Près de 2 s pour cette requête, et à chaque renouvellement de processus | Code chargé une fois avant le démarrage (`preload_app`) |
| Connexions à la base gardées d'une requête à l'autre sous ASGI | Risque d'épuiser les connexions de PostgreSQL (repéré à la relecture, pas au test) | `CONN_MAX_AGE = 0` en production |

Médiane du fil avant / après ces corrections :

| Personnes | 10 | 30 | 60 |
| --- | --- | --- | --- |
| Avant | 6 612 ms | 8 218 ms | 30 861 ms |
| Après | 302 ms | 387 ms | 2 441 ms |

## Requête par requête, sans charge

Pour séparer ce qui vient du code et ce qui vient de la machine (mesuré avant `preload_app`, 8 appels) :

| Écran | Temps habituel |
| --- | --- |
| Fil, connectée | 215 à 325 ms |
| Fil, visiteuse | 115 à 245 ms |
| Recherche | 140 à 540 ms |
| Disponibilités | 70 à 160 ms |

## Limites connues

- Pas encore de cache sur le fil : chaque page est recalculée (12 requêtes SQL). C'est le premier point à
  regarder si le vrai serveur sature.
- La recherche et le fil restent à mesurer avec beaucoup plus de données.
- Les envois de photos et de vidéos, le temps réel (WebSocket) et les lives ne sont pas dans ce test.

## Refaire le test

Sur un ordinateur ou un serveur de même taille que celui prévu, **jamais sur la base réelle** (le test a
besoin des données de démo et du prestataire de paiement de test) :

```
docker compose up -d
docker compose exec backend python manage.py seed_demo
./loadtest/run.sh
LOADS="50 100 200" DURATION=300s ./loadtest/run.sh
```

Les résultats sont dans `loadtest/results/`.
