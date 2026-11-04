# Pages publiques : ce qu'une visiteuse doit trouver

Règle du propriétaire : une personne qui arrive sans rien connaître comprend ce que fait la plateforme,
qu'elle peut créer un compte, se connecter, venir comme cliente ou comme pro, ce qu'elle peut faire
sans compte. Les belles images ne remplacent jamais cette explication.

## Les pages

| Adresse | Pour qui | Contenu |
| --- | --- | --- |
| `/` | Toute visiteuse | Ouverture, « Par où commencer ? », tout ce qu'on peut faire, photos, code de réception, rendez-vous, pros, Sélection, Académie, Offrir, questions, fil des pros |
| `/pour-les-pros` | Pros sans compte | Pour qui, lien et QR code, vitrine, agenda, boutique, formations, réseau, gratuit ou Premium, trois étapes pour commencer |
| `/comment-ca-marche` | Toute visiteuse | Types de compte, création de compte, chaque service étape par étape, audio et langues |

Une personne connectée arrive sur son fil. `/pour-les-pros` et `/comment-ca-marche` restent ouvertes, avec « Mon compte » au lieu de « Me connecter ».

## Entrées de compte

| Bouton | Adresse | Suite du parcours |
| --- | --- | --- |
| Me connecter | `/auth` | Numéro ou e-mail, code |
| Créer un compte, Créer mon compte | `/auth?as=client` | Code, puis accueil cliente |
| Créer ma vitrine | `/auth?as=pro` | Code, puis accueil pro et création de la vitrine |
| Je suis une pro | `/pour-les-pros` | Explications, puis « Créer ma vitrine » |
| Trouver une pro | `/explore` | Réservation possible sans compte |

## Chaque module du cahier des charges et sa place

| Module | Accueil | Page détaillée |
| --- | --- | --- |
| Comptes et inscription | Par où commencer, questions | `/comment-ca-marche#comptes` |
| 1. Profils, localisation, lien court, QR code | Tout ce que tu peux faire, section pros | `/pour-les-pros` |
| 2. Réseau social | Tout ce que tu peux faire, fil des pros | `/pour-les-pros` |
| 3. Messagerie et appels | Tout ce que tu peux faire | `/comment-ca-marche#comptes` |
| 4. Boutiques et ventes en live | Tout ce que tu peux faire | `/pour-les-pros`, `/comment-ca-marche#payer` |
| 5. Paiement sécurisé et litiges | Code de réception, questions | `/comment-ca-marche#payer` |
| 6. Sélection France | Tout ce que tu peux faire, section photo | `/comment-ca-marche#france` |
| 7. Académie et lives | Tout ce que tu peux faire, section photo | `/comment-ca-marche#academie`, `/pour-les-pros` |
| 8. Rendez-vous et Glow Pro | Rendez-vous, section pros | `/comment-ca-marche#rendez-vous`, `/pour-les-pros` |
| 9. Offrir au pays | Section Offrir, questions | `/comment-ca-marche#offrir` |
| 10. Côté ludique | Tout ce que tu peux faire | `/comment-ca-marche#jeux` |
| 11. Langues, audio, accessibilité | Tout ce que tu peux faire, bouton audio | `/comment-ca-marche#audio` |
| 12. Back-office | Sans objet : réservé au propriétaire et à son équipe | Sans objet |

## Les deux QR codes

- **Celui de la pro** : lien de réservation, affiche A4, stickers, carte pour les réseaux. Il existait déjà.
- **Celui de la cliente** : affiché quand un rendez-vous est confirmé, avec ou sans compte. La pro le scanne,
  voit le rendez-vous et note l'arrivée. Il n'ouvre rien pour une autre personne. Une cliente arrivée ne peut
  plus être marquée absente.

## Ce qui n'est pas annoncé

Ces fonctions du cahier des charges ne sont pas promises sur les pages publiques, car elles ne sont pas actives :
paiement sur place par téléphone, facture électronique, caisse certifiée, langues locales, traduction automatique
des contenus. Aucun prix n'est écrit en dur : les offres et les tarifs se règlent dans l'admin. Aucun concurrent n'est nommé.
