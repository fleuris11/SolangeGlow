# ADR-014 — Cadeaux de la diaspora : euros payés en France, FCFA utilisés au Bénin

Date : 2026-10-28 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Module 9 du cahier des charges (« Offrir au pays ») :
- offrir depuis la France une prestation, un produit d'une boutique béninoise ou de la
  Sélection France, ou une carte cadeau Glow d'un montant libre ;
- payer en euros ;
- la bénéficiaire reçoit un bon (lien et code), réserve ou reçoit son produit, avec ou
  sans compte ;
- la pro est payée en FCFA après la prestation ;
- occasions, message vocal ou vidéo, envoi programmé ;
- « preuve de plaisir » : une photo du résultat, avec l'accord de la bénéficiaire.

Le grand livre (ADR-007) n'accepte qu'une devise par écriture.

## Décision

- **App `gifts`** : `Gift` (type, statut, personne qui offre, bénéficiaire, occasion,
  message et média, date d'envoi, lien secret `token`, code de 10 caractères, valeur et
  solde en FCFA, prix en euros et taux utilisé), `GiftUse` (un paiement en FCFA payé par
  le cadeau), `GiftCredit` (un remboursement revenu sur le cadeau, une seule fois par
  remboursement), `GiftPhoto` (photo envoyée par la bénéficiaire).
- **Deux paiements, chacun dans sa devise** :
  1. **Paiement en euros** (purpose `gift`). Le vendeur est le compte de la plateforme
     en France (`gifts.house_email`). Les frais de 6 % (règle de prix modifiable,
     type « protection acheteur », pays FR) sont à la charge de la personne qui offre.
     L'argent reste bloqué jusqu'à la première utilisation, puis il est versé à la
     plateforme. À l'expiration, il est aussi versé. En cas d'annulation (cadeau non
     utilisé, sous `gifts.cancel_days`), il est remboursé.
  2. **Paiement en FCFA**, créé à chaque utilisation (rendez-vous, commande, Sélection
     France, achat avec la carte). Il est payé par le fournisseur interne `gift`
     (`payments/providers/gift.py`), sans page de paiement : écriture « payé » au débit de
     `provider_cash` du fournisseur `gift`. Ensuite, argent bloqué, code de réception,
     versement à la pro, litiges : tout suit le paiement sécurisé habituel. Un
     remboursement passe par `GiftProvider.refund`, qui recrédite le cadeau
     (`gifts.services.credit_back`, idempotent).
- **Trésorerie** : le solde du compte `provider_cash` (fournisseur `gift`) représente ce
  que la plateforme doit couvrir en FCFA avec les euros reçus chez Stripe. L'admin des
  cadeaux affiche ce montant pour le mois et depuis le début. Le change se fait hors de
  l'appli, au taux fixe `gifts.eur_xof_rate` (655,957).
- **Conversions** :
  - prix en euros = valeur en FCFA ÷ taux, arrondi au centime supérieur ;
  - carte Glow : FCFA = euros × taux, arrondi au franc inférieur ;
  - le prix est garanti : la pro honore le prix payé, même si elle le change ensuite.
- **Utilisations** :
  - **Prestation** : `booking.book(..., prepaid_minor=, prepay=)` crée un rendez-vous
    déjà payé en entier, même pour une invitée sans compte. La personne qui offre peut
    aussi réserver au nom de la bénéficiaire.
  - **Produit de boutique** : `shop.checkout.place_gift_order` crée une commande dont la
    cliente est la personne qui offre, livrée à l'adresse que la bénéficiaire confirme à
    l'ouverture du cadeau. Le code de réception s'affiche sur la page du cadeau.
  - **Sélection France** : `selection_france.services.place_gift_order`, retrait au point
    choisi par la bénéficiaire.
  - **Produit plus disponible** : le cadeau devient une carte Glow de même valeur.
  - **Carte Glow** : elle paie un paiement ou un panier entier en FCFA
    (`pay_from_gift`, `pay_group_from_gift`), sur toute la plateforme au Bénin.
    Elle s'utilise aussi pour l'acompte d'un rendez-vous, par le crochet `deposit_cover`.
  - Ces paiements n'ont pas de frais de protection (`with_buyer_fee=False`) : les frais
    de 6 % les remplacent. La personne qui offre ne reçoit ni le code ni les messages de
    paiement de ces paiements (`tell_buyer=False`, purpose `gift`).
- **Envoi** :
  - par le hub de notifications : WhatsApp, sinon SMS (`notify_contact`), le compte de la
    bénéficiaire si elle en a un, et un e-mail si une adresse est donnée ;
  - la personne qui offre a aussi le lien à partager (bouton « Envoyer sur WhatsApp »,
    lien `wa.me`) ;
  - une tâche Beat toutes les 5 min envoie les cadeaux du jour, fait un rappel après
    `gifts.remind_after_days` et clôt les cadeaux expirés ;
  - avant la date choisie, la page du cadeau reste fermée.
- **Preuve de plaisir** : les photos possibles sont les photos du résultat prises par la
  pro (`AppointmentPhoto`) et celles envoyées par la bénéficiaire. Rien ne part sans son
  « Oui ». La photo reste privée (URL signée), visible par la personne qui offre
  seulement.

## Conséquences

- La réconciliation et les webhooks ignorent le fournisseur interne (`INTERNAL`).
- Une carte Glow doit couvrir tout l'achat : pas de complément par Mobile Money pour
  l'instant.
- En production : prévoir le change euros → FCFA pour alimenter FedaPay (versements aux
  pros), et activer les modèles WhatsApp des événements `gifts.*`.
