# ADR-017 — Back-office : tout piloter depuis /admin

Date : 2026-10-30 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Le module 12 du cahier des charges demande que la propriétaire pilote seule la plateforme,
sans toucher au code :

- un tableau de bord ;
- des consoles : modération, litiges, finance, Sélection France, vérification des pros ;
- une équipe avec des rôles, une double authentification obligatoire et « se connecter à la
  place de » ;
- un journal d'audit et des exports CSV ;
- des contenus traduits et versionnés ;
- des traductions modifiables sans redéploiement ;
- les fonctionnalités à la carte, la prospection des pros et un centre d'aide.

ADR-001 garde une seule interface d'administration : Django admin + Unfold, complété de pages
personnalisées.

## Décision

- **Deux apps** : `backoffice` (équipe, sécurité, outils) et `content` (pages, bannières, FAQ,
  demandes d'aide).
- **Tableau de bord** :
  - c'est la page d'accueil de l'admin (`DASHBOARD_CALLBACK` d'Unfold) ;
  - chiffres par période (7, 30, 90 jours, mois en cours) et par pays : inscriptions, personnes
    actives, commandes, rendez-vous, chiffre d'affaires et commission, argent bloqué, litiges
    ouverts, file de modération ;
  - graphiques Chart.js fournis par Unfold : aucun script ajouté ;
  - réservé à `backoffice.view_dashboard` (et aux superutilisatrices).
- **Consoles** : pages de l'admin qui regroupent ce qui est à faire.
  - **Modération** : actions en un clic, celles du prompt 7.
  - **Litiges** :
    - chronologie (paiement, preuves, journal) ;
    - lien vers la salle de discussion et « Appel à trois » ;
    - décision depuis la fiche du litige.
  - **Sélection France** : commandes à passer, lots, colis à remettre.
  - La finance et la vérification des pros gardent leurs écrans des prompts 8 et 6.
- **Rôles** :
  - sept groupes Django sont créés après chaque migration : Moderation, Support, Disputes, Ads,
    Finance, Verification, Selection. Les groupes déjà existants sont réutilisés ;
  - la page « Équipe » crée un compte staff, choisit ses rôles ou le retire ;
  - les permissions fines sont celles de Django, plus des permissions propres
    (`view_dashboard`, `use_*_console`, `manage_team`, `manage_flags`, `edit_translations`,
    `impersonate_user`, `export_csv`).
- **Double authentification** :
  - TOTP fait maison (RFC 6238, HMAC-SHA1, 30 s, 6 chiffres) : aucune nouvelle dépendance ;
  - le secret est chiffré (`core.crypto`) ;
  - un code n'est accepté qu'une fois (dernier pas retenu) ;
  - 5 essais, puis blocage de 15 minutes ;
  - 10 codes de secours hachés ;
  - un middleware renvoie tout compte staff vers `/admin/2fa/` tant que la vérification n'est
    pas faite pour la session (`backoffice.two_factor_hours`) ;
  - mise en place à la première connexion (QR code SVG dessiné par `segno`) ;
  - `BACKOFFICE_REQUIRE_2FA` (vrai par défaut) n'est coupé qu'en test.
- **« Se connecter à la place de »** :
  - action sur la fiche d'une personne, avec un motif obligatoire ;
  - jamais sur un compte staff ;
  - le jeton porte `imp` (identifiant de la session d'aide) et expire après
    `backoffice.impersonation_minutes` (30) ;
  - chaque requête vérifie que la session vit encore ;
  - les paiements, les codes de réception, les versements et la suppression du compte sont
    refusés (`backoffice.impersonation_blocked`) ;
  - chaque écriture est notée dans le journal, avec `impersonated_by` ;
  - le web affiche une bannière rouge « Arrêter », lue dans un cookie sans secret et chargée à
    la demande.
- **Journal et exports** :
  - le journal d'audit se filtre par action, personne, pays et staff ;
  - l'action « Exporter en CSV » est ajoutée à toutes les listes de l'admin : colonnes de la
    liste, `;`, BOM pour Excel, `backoffice.export_max_rows` lignes au plus ;
  - chaque export est journalisé.
- **Contenus** :
  - `Page` : aide, conditions, confidentialité, mentions légales, règles des jeux, retours ;
  - `Banner` : bannière éditoriale de l'accueil, en plus de la bannière pub ;
  - `FaqItem` ;
  - tous sont traduits (fr/en/sk) par modeltranslation ;
  - chaque enregistrement crée une `ContentVersion` (copie des champs), qu'on peut remettre en
    un clic ;
  - les gabarits de notifications (e-mail, WhatsApp, SMS) sont versionnés de la même façon ;
  - les pages légales fournies sont des brouillons à faire valider par un juriste.
- **Traductions modifiables** :
  - `TranslationOverride` (web ou serveur, langue, clé, texte) ;
  - côté Django, un middleware remet les textes corrigés dans les catalogues gettext dès que
    la version (cache) change ;
  - côté web, `getRequestConfig` fusionne `/api/v1/i18n/overrides`, gardé 60 s ;
  - la page « Traductions » cherche par clé ou par texte dans les deux catalogues. Le web
    expose les siens sur `/i18n-catalog/<langue>`.
- **Fonctionnalités à la carte** : une grille des feature flags avec activé, pays et rôles,
  modifiée en un clic et journalisée.
- **Prospection** :
  - `Prospect` (statut, notes, responsable), importé depuis un CSV (`,` ou `;`, en-têtes
    français ou anglais, doublons ignorés) ;
  - l'invitation part par WhatsApp ou SMS (gabarit `prospects.invitation`) avec un lien suivi
    `/pro/start?invite=CODE` ;
  - le code est gardé par le navigateur et rattaché quand la vitrine est créée ;
  - une tâche quotidienne passe en « active » les prospects devenues pros.
- **Centre d'aide** :
  - FAQ par thème sur `/aide` ;
  - avant l'envoi, l'interface `HelpAssistant` propose des réponses.
    `SearchAssistant` compare les mots de la question à la FAQ. `AiHelpAssistant` est prêt
    pour `HELP_AI_URL` / `HELP_AI_KEY`, qui restent vides ;
  - le formulaire crée un `Ticket` (référence T-XXXXXX) ;
  - l'équipe répond depuis l'admin : la réponse part par notification, ou par e-mail pour une
    visiteuse.

## Conséquences

- Les textes corrigés s'affichent sur le web au plus tard une minute après l'enregistrement.
  Côté Django, ils s'affichent à la requête suivante de chaque processus.
- Une clé web inconnue est ignorée : une faute de frappe dans l'admin ne casse aucun écran.
- La double authentification est obligatoire pour tout compte staff, superutilisatrices
  comprises. En cas de téléphone perdu, une superutilisatrice remet l'appareil à zéro depuis
  la page « Équipe ».
- Hors périmètre :
  - les clés matérielles (WebAuthn) ;
  - un vrai assistant IA ;
  - l'envoi groupé d'invitations à des milliers de prospects (une campagne WhatsApp payante
    devra être validée d'abord).
