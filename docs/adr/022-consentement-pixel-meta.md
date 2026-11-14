# ADR-022 — Consentement aux cookies et pixel Meta

Date : 2026-11-14 — Statut : proposé (à valider par le propriétaire avant mise en production)

## Contexte

Les publicités Meta (Instagram, Facebook) deviennent le premier canal d'acquisition. Pour mesurer
les inscriptions, rendez-vous et commandes venus des pubs, et pour recibler les visiteuses, il faut
le pixel Meta. C'est un traceur publicitaire : en France (CNIL, article 82 de la loi
Informatique et Libertés), rien ne doit se charger avant un accord libre et explicite. Le bandeau
actuel n'est qu'une information (« Aucun cookie publicitaire »), ce qui deviendrait faux.

Contraintes : budget JS des pages publiques (ADR-004), pas de fichier JS supplémentaire pour le
bandeau, et Umami (sans cookie) reste exempté de consentement.

## Options

1. Plateforme de consentement du marché (Axeptio, Didomi, Cookiebot) : payante au-delà d'un
   seuil, script tiers lourd, contraire à ADR-004.
2. Bandeau maison en script inline, pixel chargé seulement après « Accepter ».
3. API de conversions Meta côté serveur seulement : utile plus tard, mais ne remplace pas le
   reciblage et demande aussi le consentement pour les données de navigation.

## Décision

Option 2.

- `NEXT_PUBLIC_META_PIXEL_ID` vide : rien ne change (simple information, aucune donnée à Meta).
- Renseigné : le bandeau devient un bandeau de consentement avec « Refuser » et « Accepter » de
  même poids, un lien vers la politique de confidentialité, aucune case pré-cochée.
- Le choix est gardé dans le stockage du navigateur (`sg.consent`) et redemandé après 6 mois.
- « Gérer mes cookies » en pied de page rouvre le bandeau ; un retrait recharge la page pour
  décharger le pixel.
- Événements standard envoyés seulement si le pixel est chargé : `CompleteRegistration`
  (inscription), `Schedule` (rendez-vous), `Purchase` avec montant et devise (commande payée),
  `InitiateCheckout` (cadeau, au départ vers le paiement).
- AdSense, prévu comme bouche-trou (ADR-016), est lui aussi conditionné à ce même accord.
- CSP : ajout de `https://connect.facebook.net` dans `script-src` (le reste est déjà couvert).

## Conséquences

- La politique de confidentialité (page `confidentialite`, éditable dans le back-office) doit
  mentionner Meta Platforms Ireland comme destinataire, la finalité « mesure et ciblage
  publicitaire », la durée (13 mois max pour les cookies Meta, choix redemandé à 6 mois) et le
  retrait via « Gérer mes cookies ».
- Une partie des visiteuses refusera : les chiffres Meta seront sous-estimés. Umami reste la
  référence d'audience.
- Évolution possible : API de conversions côté serveur pour les paiements, toujours sous
  consentement.
