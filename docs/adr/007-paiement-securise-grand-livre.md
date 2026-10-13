# ADR-007 — Paiement sécurisé et grand livre en partie double

Date : 2026-10-13 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Module 5 du cahier des charges : l'argent de la cliente est bloqué jusqu'à ce qu'elle
confirme la réception (code à 6 chiffres) ; la vendeuse voit le montant « en attente »
sans pouvoir le retirer ; délais automatiques (annulation sans envoi, relances, versement
automatique, litige automatique) ; litiges à trois ; commissions (0 % au lancement) et
frais de « protection acheteur ». Les mêmes règles serviront aux acomptes de
rendez-vous. Prestataires : FedaPay au Bénin, Stripe Connect en France. Ni la boutique ni
les rendez-vous n'existent encore.

## Décision

**Grand livre en partie double** (`apps/payments/ledger.py`) :

- Comptes par devise : trésorerie chez chaque prestataire ; vendeuse en attente et
  vendeuse disponible (une par vendeuse) ; frais en attente ; versements en cours ;
  remboursements en cours ; revenus commissions ; revenus protection acheteur ; charges
  frais de paiement. Le **séquestre** affiché = vendeuses en attente + frais en attente.
- Une écriture = des lignes au débit ou au crédit, **équilibrées**, d'**une seule devise**
  (aucune conversion implicite), en entiers de la plus petite unité.
- **Immuables** : refus dans le code, et déclencheur PostgreSQL qui interdit UPDATE et
  DELETE sur les tables du grand livre. Une correction est une nouvelle écriture.
- **Idempotentes** : chaque écriture a une clé unique (« payment:<id>:released ») ;
  rejouer un événement ne l'écrit pas deux fois.
- Les soldes sont calculés depuis les lignes.

**Écritures** (exemple : articles 10 000 + livraison 1 000 FCFA, protection 3 % = 330,
commission 5 % = 500 sur les articles) :

| Événement | Débit | Crédit |
|---|---|---|
| Paiement confirmé | Trésorerie 11 330 | Vendeuse en attente 11 000, Frais en attente 330 |
| Code saisi / versement auto | Vendeuse en attente 11 000, Frais en attente 330 | Vendeuse disponible 10 500, Commissions 500, Protection 330 |
| Remboursement total | Vendeuse en attente 11 000, Frais en attente 330 | Remboursements en cours 11 330 |
| Remboursement confirmé | Remboursements en cours | Trésorerie |
| Remboursement partiel (4 000) | Vendeuse en attente 11 000, Frais en attente 330 | Remboursements en cours 4 000, Vendeuse disponible 6 700, Commissions 300, Protection 330 |
| Demande de versement | Vendeuse disponible | Versements en cours |
| Versement confirmé / échoué | Versements en cours | Trésorerie / Vendeuse disponible |
| Frais du prestataire | Charges frais de paiement | Trésorerie |

**Machine à états** : PENDING_PAYMENT → HELD → SHIPPED → RELEASED, ou REFUNDED, ou
DISPUTED → RELEASED / REFUNDED / PARTIALLY_REFUNDED ; plus CANCELLED (jamais payé) et
CANCELLED → REFUNDED (paiement arrivé trop tard). Une fonction de service par
transition, sous verrou de ligne ; chaque transition écrit au grand livre et au journal
d'audit, prévient les deux parties et le module propriétaire (`listen(source_type, …)`).

**Choix du propriétaire (2026-10-13)** : protection acheteur 3 % (minimum 100 FCFA /
0,30 €), remboursée seulement en cas de remboursement total ; frais des prestataires à la
charge de la plateforme ; annulation possible par la cliente avant l'envoi ; « livré »
déclaré par la vendeuse avec photo obligatoire ; décisions de litige toujours humaines ;
code haché pour la vérification + copie chiffrée pour l'affichage à la cliente ;
suspension après 3 litiges perdus en 90 jours ; versement minimum 5 000 FCFA / 10 € ;
commission calculée sur les articles seulement.

**Prestataires** derrière `PaymentProvider` (`create_checkout`, `refund`, `payout`,
`parse_webhook`, `transactions`) : FakeProvider complet (page de paiement de test,
webhooks signés simulés), FedaPayProvider et StripeConnectProvider écrits selon leurs
API, inactifs sans clés. Webhooks : signature vérifiée (horodatage, HMAC-SHA256), chaque
événement enregistré une fois (`WebhookEvent`, unique par prestataire et identifiant).
FedaPay n'a pas d'API de remboursement : ses remboursements sont marqués « à faire à la
main » et clos dans l'admin. Bénin : la plateforme encaisse puis reverse (à valider avec
FedaPay et un juriste avant l'activation).

## Conséquences

- La boutique, les rendez-vous et les formations appellent seulement les services
  (`create_payment`, `ship`, `confirm_receipt`, `release`, `refund_full`…), enregistrent
  leur écoute (`listen`) et la confiance de la messagerie (`fraud.register_trust_check`
  déjà branché).
- Couverture de tests de 100 % exigée par la CI sur les services, le grand livre et les
  règles de prix.
- Rapprochement quotidien des relevés des prestataires ; écarts visibles dans l'admin.
- Export CSV DAC7 annuel (revenus par vendeuse et par trimestre) ; la déclaration
  officielle (XML) reste à faire.
