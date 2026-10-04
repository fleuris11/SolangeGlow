# ADR-003 — Fournisseurs externes derrière des interfaces

Date : 2026-10-05 — Statut : accepté

## Contexte

La plateforme dépend de services tiers : WhatsApp Business, SMS, e-mail, Web Push,
paiement (FedaPay, Stripe Connect), plus tard vidéo, IA et transporteurs. Le
développement et les tests doivent fonctionner sans clés ni réseau, et une clé manquante
en production doit être visible tout de suite, pas silencieuse.

## Décision

- Chaque fournisseur est utilisé à travers une interface du code (ex. `SmsClient`,
  `WhatsAppClient`, `OtpSender`, `NotificationChannel`, plus tard `PaymentProvider`).
- Chaque interface a une implémentation **Console** ou **Fake** pour le développement et
  les tests : elle écrit dans les journaux ou garde les envois en mémoire.
- Les vraies classes lèvent **`ProviderNotConfigured`** quand leurs clés manquent. Le code
  appelant décide : passer au canal suivant (codes, notifications) ou échouer clairement.
- Les implémentations Console/Fake sont désactivées en production par les réglages
  (`*_CONSOLE = False` forcé dans `config/settings/prod.py`).
- Les appels réseau ont un délai maximal et sont faits en tâche Celery quand c'est possible.

## Conséquences

- Aucun test n'appelle un service réel (respx et les Fake le garantissent).
- Brancher un fournisseur = renseigner ses variables d'environnement, sans changer le code.
- Ajouter un fournisseur = écrire une classe de plus derrière l'interface existante.
