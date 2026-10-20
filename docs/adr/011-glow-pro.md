# ADR-011 — Glow Pro : offres, gestion du salon et factures

Date : 2026-10-20 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Module 8 du cahier des charges, tableau « Gratuit ou Premium » : le cœur des rendez-vous
est gratuit (prompt 11) ; Premium ajoute l'équipe au-delà de 2 personnes, le fichier
client complet (paiements échelonnés, forfaits, anniversaires), les stocks, le tableau de
bord complet, les campagnes, le widget en marque blanche et la facture électronique. Les
cartes cadeaux sont gratuites avec commission, l'encaissement sur place a des frais de
paiement, la caisse certifiée NF525 passe par un partenaire (hors périmètre).

## Décision

- **Trois apps** : `glowpro` (offres, abonnement, droits, tableau de bord, widget),
  `salon` (forfaits, échéances, cartes cadeaux, stock, encaissement sur place,
  consentements et campagnes), `invoicing` (factures, reçus, avoirs).
- **Offres modifiables dans l'admin** (`Plan` : fonctions débloquées, limites
  `{"staff": 2, "campaigns_per_month": 4}`, essai ; `PlanPrice` par pays : 9 900 FCFA et
  29,00 € par mois au lancement, essai de 30 jours une fois). Toute fonction payante passe
  par `glowpro.selectors.require(pro, feature)` (erreur `premium_required`) ; la limite
  d'équipe est vérifiée en ajoutant une personne à l'agenda.
- **Abonnement par le paiement sécurisé** (`purpose = "subscription"`) : la vendeuse est un
  compte de la plateforme par pays (`glowpro.house_email`), sans protection ni commission,
  argent versé dès le paiement, facture émise par la plateforme. Renouvellement : le
  paiement du mois suivant est créé 3 jours avant l'échéance (pas de prélèvement
  automatique tant que Stripe n'est pas branché) ; 7 jours de grâce ; puis retour au
  gratuit : rien n'est supprimé, les personnes en trop sont mises en pause, le widget
  s'éteint.
- **Forfaits et échéances** (`purpose = "package"`) : argent bloqué jusqu'à la première
  séance, puis versé ; les échéances suivantes sont versées dès leur paiement. Une séance
  est décomptée toute seule quand un rendez-vous de la prestation est terminé (crochet
  `booking.common.on_completed`).
- **Cartes cadeaux** (`purpose = "gift_card"`, commission 5 %) : argent bloqué jusqu'à la
  première utilisation, puis versé ; à l'expiration (12 mois par défaut), versé à la pro.
  Utilisables seulement chez la pro qui les a vendues : au salon (la pro tape le code) ou
  en ligne pour payer l'acompte (crochet `booking.common.deposit_cover`).
- **Stock** : articles vendus ou utilisés en cabine, code EAN vérifié (chiffre de
  contrôle), mouvements immuables, consommation par prestation décomptée à la fin du
  rendez-vous, alerte une fois par jour, inventaire. Un article relié à un produit de la
  boutique partage son stock. Lecture du code-barres : celle du navigateur
  (`BarcodeDetector`), sinon la bibliothèque `barcode-detector` chargée à l'ouverture.
- **Encaissement sur place** : un simple relevé (`OnSitePayment`), hors du grand livre (cet
  argent ne passe pas par la plateforme), pour le tableau de bord et les reçus. Espèces et
  Mobile Money seulement dans les pays de `salon.cash_countries` (Bénin) : en France, un
  logiciel qui enregistre des espèces doit être certifié NF525. Carte : interface
  `TerminalProvider` (Stripe Terminal), inactive tant que `TERMINAL_PROVIDER` est vide.
- **Factures** : numérotation continue sans trou par émetteur, par type et par année
  (F-, R-, A-2026-000001), verrou de ligne sur la série ; un document émis ne change plus
  (modèle et admin en lecture seule), une erreur s'annule par un avoir. PDF en texte
  (fpdf2, polices de la marque instanciées en statique). Facture électronique : interface
  `EInvoiceProvider`, aucune plateforme branchée (`EINVOICE_PROVIDER` vide).
- **Campagnes** : segments (pas venue depuis X jours, anniversaire sous 7 jours, forfait
  presque fini, toutes) ; seulement les clientes qui ont dit oui sur le canal
  (`MarketingConsent` avec date et origine) ; lien de désinscription signé dans chaque
  message (et en-tête `List-Unsubscribe`) ; envoi direct par le hub de notifications
  (e-mail, WhatsApp — non configuré en production : compté « pas envoyé ») ;
  statistiques : envoyés, échoués, désinscrites, revenues sous 30 jours.
- **Widget** : script `widget.js` qui ouvre `/[langue]/embed/<vitrine>` dans un cadre aux
  couleurs du salon ; `Content-Security-Policy: frame-ancestors` limite l'affichage aux
  domaines déclarés, et toutes les autres pages du site refusent d'être affichées dans un
  cadre étranger. Dans le cadre, réservation en invitée ; connexion et paiement s'ouvrent
  dans un nouvel onglet.

## Conséquences

- Les abonnements ne se renouvellent pas tout seuls : la pro paie chaque mois par un lien
  (rappel 3 jours avant). Le prélèvement viendra avec Stripe Billing.
- L'encaissement sur place n'est pas une caisse : avant de l'ouvrir en France, il faut un
  partenaire certifié NF525.
- Le tableau de bord est calculé à la demande (mis en cache 10 minutes, invalidé à chaque
  changement de l'agenda) ; au-delà de 92 jours, la période est coupée.
