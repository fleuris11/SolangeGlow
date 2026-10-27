# ADR-012 — Académie : formations vidéo, pass, certificats et lives

Date : 2026-10-27 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Module 7 du cahier des charges : les pros et la plateforme publient des formations en
leçons courtes (3 à 10 min), avec un mode « faible connexion » et un téléchargement pour
regarder hors ligne ; prix gratuit, à l'unité ou inclus dans un pass mensuel (plancher et
plafond réglables) ; progression, quiz, certificat avec QR code ; badge « Formée sur
Solange Glow » qui fait monter dans la recherche ; lives de formation (la diffusion vient
au prompt 14). Obligation légale : droit de rétractation de 14 jours pour la vente à
distance, sauf renonciation expresse au moment de l'accès immédiat.

## Décision

- **Une app `academy`** : `Course` (une pro, ou la plateforme quand `pro` est vide),
  `Module`, `Lesson` (vidéo `MediaAsset` privée, aperçu gratuit possible), `Resource`
  (PDF), `Question` (quiz de fin de module), `Enrollment`, `LessonProgress`,
  `QuizAttempt`, `Certificate`, `AcademyPass` (+ `PassPeriod`), `LiveSession`,
  `LiveRegistration`.
- **Médias** : nouveau type `document` (PDF vérifié par sa signature `%PDF-`, gardé tel
  quel) ; usages `course_cover`, `lesson_video` (3 à 10 min, 500 Mo au plus, réglables :
  `academy.lesson_*`) et `course_resource`. Une taille limite peut maintenant être propre
  à un usage. Les liens signés d'une leçon durent une heure
  (`academy.video_url_ttl_seconds`) ; le lecteur en redemande un s'il expire.
- **Revue avant publication** : une formation de pro passe brouillon → en vérification →
  publiée ou renvoyée avec une remarque (file « Formations à vérifier », groupe « Academy
  review », permission `review_course`) ; une formation publiée modifiée reste en ligne et
  revient dans la file (`needs_recheck`). Les formations de la plateforme sont écrites par
  l'équipe avec le même écran et publiées tout de suite.
- **Achat à l'unité** (`purpose = "training"`, commission de 15 %, pas de protection
  acheteur) : la case de renonciation est obligatoire ; on garde la date, le texte exact
  et l'adresse IP chiffrée (HMAC). L'argent est bloqué jusqu'à l'ouverture de la première
  leçon, puis versé à la formatrice ; avant, l'élève peut se faire rembourser elle-même
  pendant 14 jours (`academy.refund_days`) ; après ce délai sans ouverture, l'argent est
  versé quand même (tâche quotidienne). Une facture est émise au nom de la vendeuse.
- **Pass mensuel** (`purpose = "academy_pass"`) : vendu par un compte de la plateforme par
  pays (`academy.house_email`), comme l'abonnement Glow Pro : versé tout de suite, facture
  plateforme, paiement du mois suivant proposé 3 jours avant la fin, rien n'est prélevé
  tout seul ; sans paiement, le pass s'arrête (les progrès restent). Prix par pays
  (`academy.pass_price_minor`, 0 = pas de pass). Seules les formations de la plateforme
  peuvent être « incluses dans le pass » pour l'instant.
- **Progression** : position enregistrée toutes les 15 s, à la pause et en quittant ;
  leçon vue à 90 % (`academy.watched_percent`) ; quiz réussi à 70 %
  (`academy.quiz_pass_percent`), réponses justes montrées après l'essai. Fin = toutes
  les leçons vues et tous les quiz réussis → certificat (code de 12 caractères sans
  caractères ambigus, PDF fpdf2 avec QR code segno vers `/certificat/<code>`, page
  publique rendue par le serveur ; l'équipe peut l'annuler).
- **Badge** : une pro qui termine une formation marquée « compte pour le badge » reçoit
  `ProProfile.trained_at` ; la recherche le montre, le filtre « Formée sur Solange Glow »
  existe, et à égalité les pros formées passent devant.
- **Hors ligne** : la qualité basse d'une leçon est enregistrée par la page dans un cache
  à part (`sg-lessons-v1`, Cache API) sous une adresse stable ; le service worker ne vide
  jamais ce cache ; le lecteur lit la copie quand le réseau manque ; « Mes formations »
  montre la place prise et permet de supprimer.
- **Lives** : programmation, invitations aux élèves de la formation liée, inscriptions
  avec nombre de places, rappels la veille et 15 min avant, salle ouverte 10 min avant ;
  la diffusion passe par l'interface `LiveProvider` (`LIVE_PROVIDER`, vide : « bientôt
  disponible »). Interrupteurs par pays « academy » et « lives ».

## Conséquences

- Les vidéos de leçon peuvent être lourdes : en production, le proxy doit accepter des
  envois de 500 Mo (et un délai suffisant) sur `/api/v1/media`.
- Un fichier téléchargé reste sur le téléphone même si l'accès s'arrête (pass non payé) :
  acceptable pour la qualité basse ; une protection anti-copie (DRM) est hors périmètre.
- Hors périmètre : diffusion, questions écrites, main levée et replay des lives
  (prompt 14), lives payants, formations contre Glow Points (module 10), partage des
  revenus du pass avec les pros, reprise d'un envoi interrompu.
