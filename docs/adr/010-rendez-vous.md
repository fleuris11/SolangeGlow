# ADR-010 — Rendez-vous : un moteur de disponibilités par étapes

Date : 2026-10-20 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Module 8 du cahier des charges : prise de rendez-vous gratuite « façon Planity » pour les
salons et les indépendantes, au Bénin et en France. Une prestation peut avoir des étapes
(travail, temps de pose, rinçage), demander du matériel (bac, cabine) et être faite par
plusieurs personnes. Les clientes réservent avec ou sans compte ; certaines pros veulent
confirmer chaque demande ; les lapins coûtent cher aux pros.

## Décision

- **Une app `booking`** : `StaffMember` (chaque pro a une fiche « propriétaire », les
  collaboratrices ont le rôle `collaborator` et voient leur agenda en se connectant avec
  leur numéro), horaires propres, pauses, absences et créneaux bloqués (`TimeOff`),
  matériel (`Resource`, attaché à une étape par `StepResource`), `Appointment` et ses
  `AppointmentStep`.
- **Le moteur** (`booking/availability.py`) travaille en secondes, dans le fuseau de la
  pro (heure d'été comprise) : temps libre = horaires − fermetures − pauses − absences −
  étapes de *travail* des rendez-vous. Le temps de pose libère la personne ; le matériel
  est tenu toute l'étape. Une heure de départ est possible si chaque étape, à la suite,
  trouve sa personne (la même, ou une autre si l'étape le permet ; « peu importe » prend
  la moins chargée) et son matériel, sans dépasser la limite par jour.
- **Cache** : les créneaux bruts d'un jour sont gardés 15 minutes dans Redis, sous une
  clé qui contient un numéro de version par pro ; tout changement (réservation, horaire,
  absence, réglage) incrémente la version. Le délai minimum et l'horizon s'appliquent
  après le cache.
- **Pas de double réservation** : verrou sur les réglages de la pro pendant la
  réservation, puis contrainte d'exclusion PostgreSQL (`btree_gist`) sur
  (personne, plage horaire) des étapes qui bloquent.
- **Statuts** : en attente de la pro, acompte à payer, confirmé, autre créneau proposé,
  place gardée (liste d'attente), refusé, annulé, terminé, absente, expiré.
- **Acompte** par le paiement sécurisé du module 5 (`purpose = "deposit"`, livraison
  « service ») : annulation gratuite jusqu'à 24 h avant, ensuite la pro garde l'acompte ;
  si la pro annule, la cliente est toujours remboursée ; terminé ou absente : l'acompte
  est versé à la pro. Après 2 lapins en 12 mois (toutes pros, reconnus au numéro), un
  acompte de 30 % devient obligatoire ; une invitée doit alors créer un compte.
- **Confirmation manuelle** : sans réponse en 24 h, annulation et remboursement ; un
  autre créneau proposé est valable 24 h.
- **Invitées** : prénom + numéro (`GuestIdentity`), messages WhatsApp puis SMS
  (`notify_contact`), lien secret `/rdv/<jeton>` pour gérer. Si elle crée un compte avec
  le même numéro (vérifié), ses rendez-vous la suivent et elle peut laisser un avis.
- **Liste d'attente** : une place libérée est gardée 30 min pour la première inscrite qui
  convient, puis passe à la suivante. **Groupe** : chaque participante paie sa part dans
  les 24 h (sinon l'organisatrice paie, ou les places sont libérées). **Dernière
  minute** : réduction sur les créneaux proches, alerte aux abonnées et anciennes
  clientes de la ville, une par jour au plus.
- **Agenda** : vues jour (par personne) et semaine, glisser-déposer (vérifié par le
  moteur), création rapide, blocage, temps réel par Channels (`ws/agenda/`, signal
  « quelque chose a changé »), export iCal par adresse secrète.
- **Avis vérifiés** : `BookingEligibility` enregistrée dans le registre du module social.
- Tous les délais et seuils sont des réglages `booking.*` (pays ou plateforme) ; une pro
  peut remplacer les siens dans « Réglages de l'agenda ».

## Conséquences

- Le moteur relit la journée à chaque réservation (sans cache) : quelques requêtes,
  testées sur un salon de 10 personnes.
- Un rendez-vous garde ses étapes calculées : changer une prestation n'affecte pas les
  rendez-vous déjà pris.
- Hors périmètre : abonnement premium des pros, synchronisation dans l'autre sens avec
  Google Agenda, appels vidéo, rendez-vous récurrents.
