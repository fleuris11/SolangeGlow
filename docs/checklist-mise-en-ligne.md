# Checklist de mise en ligne

Tout ce qu'il faut brancher avant d'ouvrir au public. Le serveur lui-même est décrit dans
`docs/deploiement.md`.

**Comment brancher un service :**
1. Ouvre le compte chez le fournisseur et récupère les clés.
2. Mets-les dans `.env.prod` sur le serveur (`nano .env.prod`).
3. Lance `./deploy/update.sh --force-build`.
4. Regarde l'accueil de l'admin : le service disparaît du bandeau « À configurer ».

Le bandeau montre seulement que les clés sont présentes. **Il ne prouve pas qu'elles marchent : fais à
chaque fois l'essai indiqué.**

## À brancher avant d'ouvrir

### 1. Au moins un moyen de connexion

Sans WhatsApp, SMS ni e-mail, personne ne reçoit de code, donc personne ne peut se connecter.

**E-mail (SMTP).** Le plus simple pour commencer (Brevo, Mailjet, ou l'e-mail OVH).

| Variable | Contenu |
| --- | --- |
| `EMAIL_HOST` | Serveur SMTP du fournisseur |
| `EMAIL_PORT` | Souvent `587` |
| `EMAIL_HOST_USER` | Identifiant SMTP |
| `EMAIL_HOST_PASSWORD` | Mot de passe SMTP |
| `EMAIL_USE_TLS` | `true` |
| `DEFAULT_FROM_EMAIL` | `Solange Glow <no-reply@solangeglow.com>` |

Déclare aussi SPF et DKIM dans le DNS (le fournisseur donne les lignes), sinon les e-mails finissent
en indésirables.
Essai : inscris-toi avec une adresse e-mail et vérifie que le code arrive, sans passer par les
indésirables.

**WhatsApp Business** (Meta Cloud API). C'est le canal principal prévu au Bénin.

| Variable | Contenu |
| --- | --- |
| `WHATSAPP_ACCESS_TOKEN` | Jeton permanent de l'utilisateur système Meta |
| `WHATSAPP_PHONE_NUMBER_ID` | Identifiant du numéro (pas le numéro lui-même) |
| `WHATSAPP_TEMPLATE_NAME` | Nom du modèle de code : `solange_glow_code` |

À faire chez Meta, **compte plusieurs jours** :
- faire vérifier l'entreprise ;
- faire approuver le modèle « authentification », en fr, en et sk ;
- faire approuver les modèles des autres messages : rappels de rendez-vous, invitées, cadeaux,
  campagnes. Leurs textes sont dans l'admin (« Messages et e-mails »). Ils sont désactivés sur
  WhatsApp par défaut, car chaque message est payant : active ceux que tu veux après approbation.

Essai : connecte-toi avec un numéro béninois.

**SMS** (Twilio). Sert de secours quand WhatsApp échoue.

| Variable | Contenu |
| --- | --- |
| `TWILIO_ACCOUNT_SID` | Identifiant du compte |
| `TWILIO_AUTH_TOKEN` | Jeton du compte |
| `TWILIO_FROM` | Numéro ou nom d'expéditeur autorisé dans le pays |

Vérifie chez Twilio ce qui est autorisé au Bénin, et le prix du message. Fixe une limite de dépenses.
Essai : avec WhatsApp coupé ou un numéro sans WhatsApp, le code arrive par SMS.

### 2. Paiement au Bénin : FedaPay

| Variable | Contenu |
| --- | --- |
| `FEDAPAY_SECRET_KEY` | Clé secrète |
| `FEDAPAY_WEBHOOK_SECRET` | Secret du webhook |
| `FEDAPAY_ENVIRONMENT` | `sandbox` pour les essais, puis `live` |

Adresse du webhook à déclarer : `https://solangeglow.com/api/v1/payments/webhooks/fedapay`

**Avant d'activer, à valider :**
- **Avec FedaPay et un juriste :** le montage « la plateforme encaisse, garde l'argent jusqu'au code,
  puis reverse ». C'est le cœur du paiement sécurisé.
- **Signature des webhooks :** elle a été codée d'après une documentation incomplète et n'a jamais été
  essayée avec une vraie clé. À vérifier en premier, en `sandbox`. Si elle est fausse, les paiements
  restent « en attente » alors que le client a payé.
- **Remboursements :** FedaPay n'a pas d'API de remboursement. Ils se font à la main dans son tableau
  de bord, puis se notent dans l'admin.
- **Change euros vers FCFA :** les cadeaux de la diaspora sont payés en euros, mais utilisés en FCFA. Il
  faut organiser l'alimentation du compte FedaPay.

Essai en `sandbox` : payer une commande, voir l'argent bloqué, valider le code, retirer l'argent,
rembourser une commande. Fais ensuite un vrai paiement de 100 FCFA en `live`.

**KKiaPay ?** Il n'est **pas codé** aujourd'hui. Si tu le préfères à FedaPay, ou en complément, il faut
d'abord le développer (une nouvelle classe de prestataire et ses tests d'argent). Il n'y a pas de
variable à remplir pour l'instant. Le choix du prestataire par pays se règle ensuite dans le réglage
`payments.providers` de l'admin.

### 3. Paiement en France : Stripe Connect

| Variable | Contenu |
| --- | --- |
| `STRIPE_SECRET_KEY` | Clé secrète (`sk_test_…` puis `sk_live_…`) |
| `STRIPE_WEBHOOK_SECRET` | Secret du webhook (`whsec_…`) |

Adresse du webhook à déclarer : `https://solangeglow.com/api/v1/payments/webhooks/stripe`

**Avant d'activer :**
- activer Connect sur le compte Stripe et faire valider le dossier de l'entreprise ;
- **rétrofacturations** (une cliente conteste auprès de sa banque après le versement) : **pas encore
  gérées dans le code**. À prévoir avant un vrai volume en France ;
- **rapprochement bancaire :** les références sont à affiner avec les premiers vrais paiements ;
- droit de rétractation de 14 jours pour la vente à distance par une professionnelle : pas géré dans
  les boutiques, à prévoir avec les conditions de vente ;
- DAC7 : l'export CSV est prêt, la déclaration officielle reste à produire.

Essai avec les clés `test` : payer, bloquer, valider le code, verser à une pro, offrir un cadeau.

### 4. Les pages légales et les documents

- [ ] Faire relire par un juriste les 5 pages (admin, « Pages ») : ce sont des brouillons.
- [ ] Compléter les mentions légales : société, adresse, hébergeur.
- [ ] Comparer la liste des produits interdits (admin, « Mots interdits ») à la liste officielle ABMed.
- [ ] Vérifier l'import au Bénin pour la Sélection France : cosmétiques autorisés et droits de douane.
      Les droits du calcul sont une estimation.
- [ ] Déclarer le traitement des données selon le pays (CNIL, APDP au Bénin).
- [ ] Vérifier les règles de la facture électronique en France (`EINVOICE_PROVIDER`, non branché).

### 5. Les données de départ, dans l'admin

Il n'y a aucune donnée de démonstration sur le serveur. Il faut créer :
- [ ] l'équipe (« Équipe »), chaque personne avec sa double authentification ;
- [ ] les points de retrait de la Sélection France (« Points de retrait ») ;
- [ ] les produits de la Sélection France (« Produits de la Sélection ») ;
- [ ] les premières formations de l'Académie, si tu en veux à l'ouverture ;
- [ ] les quiz, sondages et lots de la roue, selon les réglages que tu souhaites ;
- [ ] les prospects à inviter : les pros à inscrire en premier (« Prospects »).

Relis aussi les commissions, délais et limites (« Réglages » et « Commissions et frais ») : les valeurs
sont celles de départ.

## Déjà prêt, à vérifier une fois en ligne

### 6. Appels et lives (LiveKit)

Le serveur tourne avec le site. `LIVEKIT_API_SECRET` est créée par `generate-secrets.sh`.

Essai **sur un vrai réseau mobile béninois**, pas seulement en Wi-Fi : certains réseaux bloquent ce type
de trafic. Si les appels échouent, il faudra activer un relais TURN (réglage du serveur LiveKit).

Les replays des lives sont en option, car le service d'enregistrement est lourd (image de 1,5 Go) et
n'a jamais été essayé en vrai :
```
LIVEKIT_EGRESS=true
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile replay up -d egress
```

### 7. Notifications push

`VAPID_PUBLIC_KEY` et `VAPID_PRIVATE_KEY` sont créées par `first-run.sh`. Ne les change plus : les
abonnements existants seraient perdus. `VAPID_SUBJECT` : une adresse de contact.
Essai : autorise les notifications sur un téléphone, puis envoie-toi un message.

### 8. Fond de carte

Il ne demande aucune clé : c'est OpenFreeMap, gratuit. Le réglage est dans l'admin : `maps.style_url`,
et `maps.attribution` pour la mention. Vérifie que ses conditions te conviennent pour un usage
commercial, et prévois un autre fournisseur si besoin (MapTiler, Stadia).
Essai : ouvre Explorer, puis la vue carte.

### 9. Audience et erreurs

| Variable | Contenu |
| --- | --- |
| `NEXT_PUBLIC_UMAMI_WEBSITE_ID` | Identifiant du site, créé sur `stats.<domaine>` |
| `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN` | DSN du projet, créé sur `erreurs.<domaine>` |
| `GLITCHTIP_REGISTRATION` | `false` une fois ton compte créé |
| `GLITCHTIP_EMAIL_URL` | SMTP pour recevoir les alertes (`smtp://…`) |

Change le mot de passe `admin` / `umami` dès la première connexion.

### 10. Sauvegardes

- [ ] Copier `BACKUP_PASSPHRASE`, `IDENTITY_VAULT_KEY` et `.env.prod` hors du serveur.
- [ ] Faire une vraie restauration avant d'ouvrir au public : `./deploy/restore.sh latest --media`.
- [ ] Regarder `./deploy/status.sh` le lendemain : une sauvegarde de la nuit doit apparaître.

## En option : peut attendre l'ouverture

| Service | Variables | Sans lui |
| --- | --- | --- |
| IA de modération | `MODERATION_AI_URL`, `MODERATION_AI_KEY` | Listes de mots et règles seulement, et la file de modération |
| IA des quiz | `QUIZ_AI_URL`, `QUIZ_AI_KEY` | L'équipe écrit les quiz |
| IA du centre d'aide | `HELP_AI_URL`, `HELP_AI_KEY` | Le centre d'aide propose les réponses de la FAQ |
| Stripe Terminal (Tap to Pay) | `TERMINAL_PROVIDER` | Pas de paiement par carte sur le téléphone de la pro |
| Facture électronique | `EINVOICE_PROVIDER` | Factures gardées, mais pas transmises |
| Liens courts sur un autre domaine | `SHORT_LINK_BASE_URL` | Les QR codes utilisent le domaine du site |
| AdSense | Réglage dans l'admin | Seulement la régie maison. **Un bandeau de consentement aux cookies sera nécessaire en France avant de l'activer** |

**Pour l'IA de modération :** aucun fournisseur n'a été choisi. Le code envoie `{"input": texte,
"language": langue}` et attend une réponse `{"flagged": vrai ou faux, "categories": {...}}`, sur le
modèle d'une API de modération. Il faudra peut-être un petit adaptateur selon le service retenu. Vérifie
aussi où partent les données : ce sont des contenus de tes utilisatrices.

## Le dernier contrôle, le jour J

- [ ] Le bandeau « À configurer » ne contient plus aucune ligne « indispensable pour ouvrir ».
- [ ] `./deploy/status.sh` : tout est `healthy`, et une sauvegarde date de moins de 24 heures.
- [ ] `FEDAPAY_ENVIRONMENT=live` et clés Stripe `sk_live_…`.
- [ ] Un vrai parcours complet de bout en bout, avec de l'argent réel en petite somme : inscription,
      réservation, commande, paiement, code de réception, versement à la pro.
- [ ] Un vrai remboursement.
- [ ] Lighthouse mesuré sur le vrai site (voir le README).
