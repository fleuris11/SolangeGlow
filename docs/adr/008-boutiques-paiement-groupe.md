# ADR-008 — Boutiques : une commande par boutique, un paiement groupé

Date : 2026-10-15 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Module 4 du cahier des charges : chaque pro vérifiée a une boutique (produits avec
variantes et stock, remise au choix de la cliente, promotions), la cliente remplit un
panier de plusieurs boutiques et paie via le paiement sécurisé du module 5 (ADR-007).
Un paiement sécurisé n'a qu'une vendeuse : son code de réception, son délai d'envoi et
ses écritures lui sont propres. Payer chaque boutique l'une après l'autre ferait plusieurs
pages de paiement et plusieurs frais de prestataire.

## Décision

- **Une commande par boutique**, chacune avec son paiement sécurisé (`source_type =
  "order"`) : son code, ses délais, son litige éventuel.
- **Un paiement groupé** (`PaymentGroup`) réunit les paiements d'un même panier (même
  cliente, même devise, même prestataire) : une seule page chez le prestataire pour le
  total. À la réponse, chaque paiement du groupe passe « payé » avec sa propre écriture
  au grand livre ; les frais du prestataire sont répartis au prorata (le reste sur le
  dernier). Les remboursements se font par paiement, sur la même transaction
  (`provider_reference` du groupe recopiée). Le rapprochement additionne les paiements
  d'une même référence. Un paiement groupé ne se paie pas seul.
- **Délai d'envoi** : `escrow.ship_deadline_days` + le délai de préparation le plus long
  de la commande (`Payment.prep_days`), pour les articles faits sur commande.
- **Annulation** : le module propriétaire peut restreindre qui annule
  (`listen(..., may_cancel=)`). La boutique : la cliente seulement tant que la commande
  est « nouvelle », la vendeuse jusqu'à l'envoi.
- **Stock** pris à la création des commandes (mise à jour conditionnelle `stock >= n`),
  rendu une seule fois si le paiement n'arrive pas, si la commande est annulée ou
  remboursée avant l'envoi. Les ventes flash à quantité limitée suivent la même règle.
- **Produits interdits** : liste `ForbiddenTerm` dans l'admin (« bloquer » ou « à
  vérifier »), comparée sans accents ni majuscules, aussi écrite avec des points ou des
  tirets. Bloqué : publication refusée avec la raison. À vérifier : file de l'équipe
  (groupe « Shop review »), accepter ou refuser en un clic. La modération existante
  (`screen`) s'applique aussi.
- Une boutique livre seulement dans son pays ; le retrait est ouvert à toutes.
- Le numéro de la cliente n'est transmis à la vendeuse que pour une livraison, après le
  paiement.

## Conséquences

- Un panier de deux pays (deux devises) se paie en deux fois.
- La protection acheteur s'applique par commande (avec son minimum).
- Hors périmètre : ventes en live (V3), codes promo financés par la plateforme,
  rétractation de 14 jours pour la France (à prévoir avec les conditions de vente),
  suivi automatique des transporteurs.
