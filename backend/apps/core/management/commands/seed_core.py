"""Create the reference data the platform needs to start.

Safe to run several times: existing rows are never overwritten, so values edited in
the admin are kept.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Country, Currency, PlatformSetting

CURRENCIES = [
    {
        "code": "XOF",
        "symbol": "FCFA",
        "decimal_places": 0,
        "name_fr": "Franc CFA (BCEAO)",
        "name_en": "West African CFA franc",
        "name_sk": "Západoafrický frank CFA",
    },
    {
        "code": "EUR",
        "symbol": "€",
        "decimal_places": 2,
        "name_fr": "Euro",
        "name_en": "Euro",
        "name_sk": "Euro",
    },
]

COUNTRIES = [
    {
        "code": "BJ",
        "phone_prefix": "+229",
        "currency": "XOF",
        "default_language": "fr",
        "timezone": "Africa/Porto-Novo",
        "name_fr": "Bénin",
        "name_en": "Benin",
        "name_sk": "Benin",
    },
    {
        "code": "FR",
        "phone_prefix": "+33",
        "currency": "EUR",
        "default_language": "fr",
        "timezone": "Europe/Paris",
        "name_fr": "France",
        "name_en": "France",
        "name_sk": "Francúzsko",
    },
]

INT = PlatformSetting.ValueType.INTEGER

# Secure payment (escrow) deadlines, from module 5 of the specification (v2).
# They are edited in the admin, never in the code.
SETTINGS = [
    {
        "key": "escrow.ship_deadline_days",
        "country": None,
        "value_type": INT,
        "value": "3",
        "description_fr": "Jours laissés à la vendeuse pour expédier ou remettre la commande. "
        "Passé ce délai, la commande est annulée et la cliente remboursée.",
        "description_en": "Days the seller has to ship or hand over the order. After "
        "that, the order is cancelled and the client refunded.",
    },
    {
        "key": "escrow.auto_release_days",
        "country": None,
        "value_type": INT,
        "value": "7",
        "description_fr": "Jours après un suivi transporteur « livré » sans code de réception : "
        "relances à la cliente, puis argent versé à la vendeuse si elle ne dit rien.",
        "description_en": "Days after a carrier 'delivered' status without receipt code: "
        "the client is reminded, then the money is released to the seller.",
    },
    {
        "key": "escrow.auto_dispute_days",
        "country": None,
        "value_type": INT,
        "value": "7",
        "description_fr": "Jours après la date de livraison prévue, sans code ni preuve de "
        "livraison, au bout desquels un litige s'ouvre automatiquement.",
        "description_en": "Days after the expected delivery date, without code or proof of "
        "delivery, after which a dispute opens automatically.",
    },
    {
        "key": "escrow.dispute_response_hours",
        "country": None,
        "value_type": INT,
        "value": "48",
        "description_fr": "Heures laissées à chaque partie pour répondre et déposer ses "
        "preuves dans un litige.",
        "description_en": "Hours each party has to answer and upload evidence in a dispute.",
    },
    {
        "key": "escrow.receipt_code_max_attempts",
        "country": None,
        "value_type": INT,
        "value": "5",
        "description_fr": "Nombre d'essais autorisés pour saisir le code de réception.",
        "description_en": "Number of attempts allowed to enter the receipt code.",
    },
    {
        "key": "escrow.payment_timeout_minutes",
        "country": None,
        "value_type": INT,
        "value": "30",
        "description_fr": "Minutes laissées à la cliente pour finaliser un paiement "
        "avant l'annulation de la commande.",
        "description_en": "Minutes the client has to complete a payment before the "
        "order is cancelled.",
    },
]


STR = PlatformSetting.ValueType.STRING
JSON = PlatformSetting.ValueType.JSON

# Sign-in with one-time codes and request limits.
SETTINGS += [
    {
        "key": "otp.code_ttl_seconds",
        "country": None,
        "value_type": INT,
        "value": "600",
        "description_fr": "Durée de validité d'un code de connexion, en secondes.",
        "description_en": "How long a sign-in code stays valid, in seconds.",
    },
    {
        "key": "otp.max_attempts",
        "country": None,
        "value_type": INT,
        "value": "5",
        "description_fr": "Essais autorisés pour taper un code avant d'en demander un nouveau.",
        "description_en": "Attempts allowed to type a code before asking for a new one.",
    },
    {
        "key": "otp.resend_cooldown_seconds",
        "country": None,
        "value_type": INT,
        "value": "60",
        "description_fr": "Secondes à attendre avant de pouvoir redemander un code.",
        "description_en": "Seconds to wait before a new code can be asked.",
    },
    {
        "key": "otp.max_requests_per_destination_per_hour",
        "country": None,
        "value_type": INT,
        "value": "5",
        "description_fr": "Codes envoyés au maximum par heure à un même numéro ou e-mail.",
        "description_en": "Maximum codes sent per hour to the same number or e-mail.",
    },
    {
        "key": "otp.max_requests_per_ip_per_hour",
        "country": None,
        "value_type": INT,
        "value": "20",
        "description_fr": "Codes demandés au maximum par heure depuis une même adresse IP.",
        "description_en": "Maximum codes asked per hour from the same IP address.",
    },
    {
        "key": "otp.phone_channels",
        "country": None,
        "value_type": JSON,
        "value": '["whatsapp", "sms"]',
        "description_fr": "Canaux d'envoi des codes vers un téléphone, dans l'ordre : le "
        "suivant sert de secours. Valeurs : whatsapp, sms.",
        "description_en": "Channels used to send codes to a phone, in order: the next one is "
        "the fallback. Values: whatsapp, sms.",
    },
    {
        "key": "otp.email_channels",
        "country": None,
        "value_type": JSON,
        "value": '["email"]',
        "description_fr": "Canaux d'envoi des codes vers une adresse e-mail.",
        "description_en": "Channels used to send codes to an e-mail address.",
    },
    {
        "key": "accounts.avatar_max_bytes",
        "country": None,
        "value_type": INT,
        "value": str(5 * 1024 * 1024),
        "description_fr": "Taille maximale d'une photo de profil, en octets.",
        "description_en": "Maximum size of a profile photo, in bytes.",
    },
    {
        "key": "throttle.auth",
        "country": None,
        "value_type": STR,
        "value": "30/minute",
        "description_fr": "Limite de connexions par adresse IP (format : 30/minute).",
        "description_en": "Sign-in limit per IP address (format: 30/minute).",
    },
    {
        "key": "throttle.otp_request",
        "country": None,
        "value_type": STR,
        "value": "10/minute",
        "description_fr": "Limite de demandes de code par adresse IP (format : 10/minute).",
        "description_en": "Code request limit per IP address (format: 10/minute).",
    },
    {
        "key": "throttle.guest",
        "country": None,
        "value_type": STR,
        "value": "10/hour",
        "description_fr": "Limite de créations d'identité invitée par adresse IP.",
        "description_en": "Guest identity creation limit per IP address.",
    },
    {
        "key": "throttle.profile",
        "country": None,
        "value_type": STR,
        "value": "60/minute",
        "description_fr": "Limite de modifications du profil par adresse IP.",
        "description_en": "Profile update limit per IP address.",
    },
]


BOOL = PlatformSetting.ValueType.BOOLEAN
MB = 1024 * 1024


def _s(key, value_type, value, fr, en):
    return {
        "key": key,
        "country": None,
        "value_type": value_type,
        "value": value,
        "description_fr": fr,
        "description_en": en,
    }


# Accounts: ages, minors, deletion grace period.
SETTINGS += [
    _s(
        "accounts.minimum_age",
        INT,
        "16",
        "Âge minimum pour créer un compte (en années).",
        "Minimum age to create an account (years).",
    ),
    _s(
        "accounts.adult_age",
        INT,
        "18",
        "Âge à partir duquel un compte n'est plus limité (achats, messages).",
        "Age from which an account is no longer limited (purchases, messages).",
    ),
    _s(
        "accounts.minors_can_purchase",
        BOOL,
        "false",
        "Les comptes mineurs peuvent-ils acheter ? (true ou false)",
        "Can minor accounts buy? (true or false)",
    ),
    _s(
        "accounts.minors_receive_messages_from_strangers",
        BOOL,
        "false",
        "Les comptes mineurs peuvent-ils recevoir des messages de personnes "
        "qu'ils ne suivent pas ?",
        "Can minor accounts get messages from people they do not follow?",
    ),
    _s(
        "accounts.deletion_grace_days",
        INT,
        "30",
        "Jours entre la demande de suppression et l'effacement. Se reconnecter annule.",
        "Days between the deletion request and erasure. Signing in again cancels it.",
    ),
]

# Media: sizes, durations, quality, signed links.
SETTINGS += [
    _s(
        "media.image_max_bytes",
        INT,
        str(15 * MB),
        "Taille maximale d'une photo envoyée, en octets.",
        "Maximum size of a picture, in bytes.",
    ),
    _s(
        "media.video_max_bytes",
        INT,
        str(200 * MB),
        "Taille maximale d'une vidéo envoyée, en octets.",
        "Maximum size of a video, in bytes.",
    ),
    _s(
        "media.audio_max_bytes",
        INT,
        str(10 * MB),
        "Taille maximale d'une note vocale, en octets.",
        "Maximum size of a voice note, in bytes.",
    ),
    _s(
        "media.video_max_seconds",
        INT,
        "600",
        "Durée maximale d'une vidéo, en secondes.",
        "Maximum length of a video, in seconds.",
    ),
    _s(
        "media.audio_max_seconds",
        INT,
        "120",
        "Durée maximale d'une note vocale, en secondes.",
        "Maximum length of a voice note, in seconds.",
    ),
    _s(
        "media.image_sizes",
        JSON,
        '{"thumb": 160, "medium": 640, "large": 1280}',
        "Tailles des photos produites (plus grand côté, en pixels).",
        "Sizes of the pictures produced (longest side, in pixels).",
    ),
    _s(
        "media.webp_quality",
        INT,
        "80",
        "Qualité des photos WebP (0 à 100).",
        "Quality of WebP pictures (0 to 100).",
    ),
    _s(
        "media.video_qualities",
        JSON,
        '{"low": {"height": 360, "crf": 30, "audio": "64k"}, '
        '"medium": {"height": 720, "crf": 26, "audio": "96k"}}',
        "Qualités vidéo produites : « low » sert à l'économie de données.",
        'Video qualities produced: "low" is used by the data saver.',
    ),
    _s(
        "media.audio_bitrate",
        STR,
        "32k",
        "Débit des notes vocales (Opus).",
        "Bitrate of voice notes (Opus).",
    ),
    _s(
        "media.signed_url_ttl_seconds",
        INT,
        "600",
        "Durée de validité d'un lien vers un fichier privé, en secondes.",
        "How long a link to a private file stays valid, in seconds.",
    ),
    _s(
        "media.ffmpeg_timeout_seconds",
        INT,
        "600",
        "Temps maximal de conversion d'une vidéo, en secondes.",
        "Maximum time to convert a video, in seconds.",
    ),
    _s(
        "throttle.media_upload",
        STR,
        "30/hour",
        "Limite d'envois de fichiers par adresse IP.",
        "File upload limit per IP address.",
    ),
]

# Notifications.
SETTINGS += [
    _s(
        "notifications.quiet_hours",
        JSON,
        '{"start": "22:00", "end": "07:00"}',
        "Heures de silence par défaut (heure du pays) : pas d'alerte sur le téléphone, "
        "ni WhatsApp, ni SMS. Chaque personne peut les changer.",
        "Default quiet hours (country time): no phone alert, WhatsApp or SMS. "
        "Everyone can change them.",
    ),
    _s(
        "throttle.notification_test",
        STR,
        "10/hour",
        "Limite de notifications de test par adresse IP.",
        "Test notification limit per IP address.",
    ),
]


def _c(key, country, value_type, value, fr, en):
    return {**_s(key, value_type, value, fr, en), "country": country}


# Pros (module 1): showcases, search, map, verification.
SETTINGS += [
    _s(
        "pros.max_services",
        INT,
        "100",
        "Nombre maximum de prestations par pro.",
        "Maximum number of services per pro.",
    ),
    _s(
        "pros.max_categories",
        INT,
        "20",
        "Nombre maximum de catégories de prestations par pro.",
        "Maximum number of service categories per pro.",
    ),
    _s(
        "pros.max_options_per_service",
        INT,
        "10",
        "Nombre maximum d'options par prestation.",
        "Maximum number of options per service.",
    ),
    _s(
        "pros.max_service_photos",
        INT,
        "6",
        "Nombre maximum de photos par prestation.",
        "Maximum number of pictures per service.",
    ),
    _s(
        "pros.max_portfolio_items",
        INT,
        "60",
        "Nombre maximum de réalisations dans le portfolio.",
        "Maximum number of portfolio items.",
    ),
    _s(
        "pros.service_area_max_radius_km",
        INT,
        "30",
        "Rayon maximum de déplacement à domicile (km).",
        "Maximum home-visit radius (km).",
    ),
    _s(
        "pros.area_max_points",
        INT,
        "50",
        "Nombre maximum de points d'une zone de déplacement dessinée.",
        "Maximum number of points of a drawn travel area.",
    ),
    _s(
        "pros.itinerary_video_min_seconds",
        INT,
        "30",
        "Durée minimum de la vidéo d'itinéraire (secondes).",
        "Minimum length of the itinerary video (seconds).",
    ),
    _s(
        "pros.itinerary_video_max_seconds",
        INT,
        "60",
        "Durée maximum de la vidéo d'itinéraire (secondes).",
        "Maximum length of the itinerary video (seconds).",
    ),
    _s(
        "pros.voice_note_max_seconds",
        INT,
        "120",
        "Durée maximum des notes vocales de la vitrine (bio, repères), en secondes.",
        "Maximum length of the showcase voice notes (bio, landmarks), in seconds.",
    ),
    _s(
        "pros.arrival_cooldown_minutes",
        INT,
        "5",
        "Délai entre deux « Je suis devant » d'une même cliente (minutes).",
        "Delay between two « I am outside » of the same client (minutes).",
    ),
    _s(
        "pros.verification_required_to_collect",
        BOOL,
        "true",
        "Une pro doit être vérifiée (pièce d'identité + selfie) pour encaisser.",
        "A pro must be verified (identity document + selfie) to cash in.",
    ),
    _s(
        "search.page_size",
        INT,
        "20",
        "Nombre de pros par page de résultats.",
        "Number of pros per results page.",
    ),
    _s(
        "search.default_radius_km",
        INT,
        "10",
        "Rayon de recherche par défaut autour de la cliente (km).",
        "Default search radius around the client (km).",
    ),
    _s(
        "search.max_radius_km",
        INT,
        "50",
        "Rayon de recherche maximum (km).",
        "Maximum search radius (km).",
    ),
    _s(
        "search.map_max_points",
        INT,
        "500",
        "Nombre maximum de pros envoyés à la carte en une fois.",
        "Maximum number of pros sent to the map at once.",
    ),
    _s(
        "maps.style_url",
        STR,
        "https://tiles.openfreemap.org/styles/liberty",
        "Adresse du style du fond de carte (MapLibre).",
        "Address of the map style (MapLibre).",
    ),
    _s(
        "maps.attribution",
        STR,
        "© OpenStreetMap, OpenFreeMap",
        "Mention des sources de la carte, affichée sous chaque carte.",
        "Credits of the map, shown under every map.",
    ),
    _s(
        "maps.default_center",
        JSON,
        '{"latitude": 6.3654, "longitude": 2.4183, "zoom": 12}',
        "Vue de départ de la carte (Cotonou).",
        "Starting view of the map (Cotonou).",
    ),
    _c(
        "maps.default_center",
        "FR",
        JSON,
        '{"latitude": 48.8566, "longitude": 2.3522, "zoom": 12}',
        "Vue de départ de la carte en France (Paris).",
        "Starting view of the map in France (Paris).",
    ),
    _s(
        "throttle.search",
        STR,
        "120/minute",
        "Limite de recherches par adresse IP.",
        "Search limit per IP address.",
    ),
    _s(
        "throttle.printable",
        STR,
        "30/minute",
        "Limite de téléchargements de QR codes et affiches par adresse IP.",
        "QR code and poster download limit per IP address.",
    ),
    _s(
        "throttle.arrival",
        STR,
        "20/hour",
        "Limite de « Je suis devant » par adresse IP.",
        "« I am outside » limit per IP address.",
    ),
    _s(
        "throttle.verification",
        STR,
        "5/hour",
        "Limite d'envois de pièces d'identité par adresse IP.",
        "Identity document upload limit per IP address.",
    ),
]


# Social network, reviews and moderation (modules 2 and 12).
SETTINGS += [
    _s(
        "social.carousel_max",
        INT,
        "10",
        "Nombre maximum de photos ou vidéos dans un carrousel.",
        "Maximum number of pictures or videos in a carousel.",
    ),
    _s(
        "social.video_max_seconds",
        INT,
        "90",
        "Durée maximum d'une vidéo courte publiée (secondes).",
        "Maximum length of a short video post (seconds).",
    ),
    _s(
        "social.story_video_max_seconds",
        INT,
        "30",
        "Durée maximum d'une vidéo en story (secondes).",
        "Maximum length of a story video (seconds).",
    ),
    _s(
        "social.story_hours",
        INT,
        "24",
        "Durée de vie d'une story (heures).",
        "Life of a story (hours).",
    ),
    _s(
        "social.schedule_max_days",
        INT,
        "30",
        "Délai maximum pour programmer une publication (jours).",
        "Maximum delay to schedule a post (days).",
    ),
    _s(
        "social.feed_page_size",
        INT,
        "12",
        "Nombre de publications par page du fil.",
        "Number of posts per feed page.",
    ),
    _s(
        "social.feed_window_days",
        INT,
        "60",
        "Âge maximum des publications du fil (jours).",
        "Maximum age of the posts of the feed (days).",
    ),
    _s(
        "social.feed_weights",
        JSON,
        '{"recency": 1.0, "interactions": 0.4, "distance": 0.3, "half_life_hours": 36}',
        "Score du fil : poids de la récence, des interactions (j'aime, commentaires, enregistrements) et de la proximité ; demi-vie de la récence en heures.",
        "Feed score: weights of recency, interactions (likes, comments, saves) and closeness; half-life of recency in hours.",
    ),
    _s(
        "reviews.window_days",
        INT,
        "30",
        "Délai pour laisser un avis après un rendez-vous ou une commande (jours).",
        "Delay to leave a review after a booking or an order (days).",
    ),
    _s(
        "reviews.voice_max_seconds",
        INT,
        "120",
        "Durée maximum de la note vocale d'un avis (secondes).",
        "Maximum length of the voice note of a review (seconds).",
    ),
    _s(
        "moderation.blocked_words",
        JSON,
        '["salope", "pute", "connasse", "encule", "bitch", "whore"]',
        "Mots interdits : le contenu est masqué jusqu'à la décision de l'équipe.",
        "Forbidden words: the content is hidden until the team decides.",
    ),
    _s(
        "moderation.review_words",
        JSON,
        '["arnaque", "escroc", "scam", "nude", "nudes", "sexe"]',
        "Mots sensibles : le contenu reste visible mais arrive dans la file de modération.",
        "Sensitive words: the content stays visible but goes to the moderation queue.",
    ),
    _s(
        "moderation.banned_product_words",
        JSON,
        '["contrefacon", "replique", "fake"]',
        "Produits interdits (boutiques, à venir) : mots qui envoient un produit en modération.",
        "Forbidden products (shops, coming): words that send a product to moderation.",
    ),
    _s(
        "moderation.flag_phone_numbers",
        BOOL,
        "true",
        "Mettre en file les textes qui contiennent un numéro de téléphone.",
        "Queue texts that contain a phone number.",
    ),
    _s(
        "moderation.auto_hide_reports",
        INT,
        "3",
        "Nombre de signalements qui masque un contenu en attendant la décision.",
        "Number of reports that hides a content until the decision.",
    ),
    _s(
        "moderation.sanction_ladder",
        JSON,
        '[{"level": "warning"}, {"level": "mute", "days": 3}, {"level": "suspension", "days": 7}, {"level": "ban"}]',
        "Sanctions graduées, dans l'ordre : avertissement, interdiction de publier (jours), suspension (jours), bannissement.",
        "Graduated sanctions, in order: warning, no posting (days), suspension (days), ban.",
    ),
    _s(
        "moderation.sanction_window_days",
        INT,
        "180",
        "Période prise en compte pour passer à la sanction suivante (jours).",
        "Period counted to move to the next sanction (days).",
    ),
    _s(
        "moderation.ai_block_categories",
        JSON,
        '["sexual/minors"]',
        "Catégories de l'IA de modération qui masquent tout de suite un contenu.",
        "Categories of the moderation AI that hide a content at once.",
    ),
    _s(
        "throttle.social_write",
        STR,
        "120/hour",
        "Limite de publications, commentaires et j'aime par adresse IP.",
        "Limit of posts, comments and likes per IP address.",
    ),
    _s(
        "throttle.report",
        STR,
        "30/hour",
        "Limite de signalements par adresse IP.",
        "Report limit per IP address.",
    ),
    # Messaging.
    _s(
        "messaging.page_size",
        INT,
        "30",
        "Nombre de conversations ou de messages chargés à la fois.",
        "Number of conversations or messages loaded at once.",
    ),
    _s(
        "messaging.max_text_length",
        INT,
        "2000",
        "Longueur maximum d'un message (caractères).",
        "Maximum length of a message (characters).",
    ),
    _s(
        "messaging.voice_max_seconds",
        INT,
        "180",
        "Durée maximum d'une note vocale dans la messagerie (secondes).",
        "Maximum length of a voice note in messages (seconds).",
    ),
    _s(
        "messaging.request_max_messages",
        INT,
        "1",
        "Messages qu'une pro peut envoyer à une inconnue avant que la demande soit acceptée.",
        "Messages a pro can send to a stranger before the request is accepted.",
    ),
    _s(
        "messaging.group_max_members",
        INT,
        "10",
        "Nombre maximum de personnes dans une conversation de groupe.",
        "Maximum number of people in a group conversation.",
    ),
    _s(
        "messaging.notify_delay_seconds",
        INT,
        "60",
        "Délai avant l'alerte d'un nouveau message (les messages arrivés entre-temps sont regroupés).",
        "Delay before the alert of a new message (messages arriving meanwhile are grouped).",
    ),
    _s(
        "messaging.away_cooldown_hours",
        INT,
        "12",
        "Délai minimum entre deux messages d'absence dans la même conversation (heures).",
        "Minimum delay between two away messages in the same conversation (hours).",
    ),
    _s(
        "messaging.quick_replies_max",
        INT,
        "20",
        "Nombre maximum de réponses rapides d'une pro.",
        "Maximum number of quick replies of a pro.",
    ),
    _s(
        "messaging.fraud_keywords",
        JSON,
        '["western union", "moneygram", "mobile money", "momo", "orange money", "paypal", "virement", "iban", "lydia", "payer en dehors", "paie en dehors", "hors de l\'appli"]',
        "Mots qui déclenchent l'avertissement « Paie dans l'appli » avant une commande.",
        "Words that show the « Pay in the app » warning before an order.",
    ),
    _s(
        "messaging.payment_link_domains",
        JSON,
        '["paypal.me", "paypal.com", "lydia-app.com", "pay.wave.com", "wise.com", "revolut.me", "buy.stripe.com", "me.fedapay.com"]',
        "Sites de paiement dont les liens déclenchent l'avertissement « Paie dans l'appli ».",
        "Payment sites whose links show the « Pay in the app » warning.",
    ),
    # Secure payment (module 5), besides the escrow deadlines at the top of this file.
    _s(
        "escrow.ship_reminder_hours",
        INT,
        "24",
        "Heures avant la date limite d'envoi où la vendeuse reçoit un rappel.",
        "Hours before the shipping deadline when the seller gets a reminder.",
    ),
    _s(
        "escrow.expected_delivery_days",
        INT,
        "5",
        "Jours de livraison prévus quand la vendeuse n'indique pas de date.",
        "Expected delivery days when the seller gives no date.",
    ),
    _s(
        "escrow.release_reminder_days",
        JSON,
        "[2, 5]",
        "Jours après « livré » où la cliente est relancée (sans code ni contestation).",
        "Days after « delivered » when the client is reminded (no code, no complaint).",
    ),
    _s(
        "escrow.receipt_code_renewals_max",
        INT,
        "3",
        "Nombre de nouveaux codes de réception qu'une cliente peut demander.",
        "Number of new receipt codes a client can ask for.",
    ),
    _s(
        "escrow.courier_link_hours",
        INT,
        "72",
        "Durée de validité du lien livreur pour saisir le code (heures).",
        "How long the courier link to type the code stays valid (hours).",
    ),
    _s(
        "payments.providers",
        JSON,
        '{"BJ": "fedapay", "FR": "stripe"}',
        "Prestataire de paiement par pays (fedapay, stripe).",
        "Payment provider per country (fedapay, stripe).",
    ),
    _s(
        "payments.payout_minimum",
        JSON,
        '{"XOF": 5000, "EUR": 1000}',
        "Versement minimum par devise, dans la plus petite unité (FCFA, centimes d'euro).",
        "Minimum payout per currency, in the smallest unit (FCFA, euro cents).",
    ),
    _s(
        "payments.lost_disputes_threshold",
        INT,
        "3",
        "Litiges perdus au-delà desquels la vitrine est suspendue automatiquement.",
        "Lost disputes after which the showcase is suspended automatically.",
    ),
    _s(
        "payments.lost_disputes_window_days",
        INT,
        "90",
        "Période (jours) sur laquelle on compte les litiges perdus.",
        "Period (days) over which lost disputes are counted.",
    ),
    _s(
        "throttle.payments",
        STR,
        "60/minute",
        "Limite des actions de paiement par adresse IP.",
        "Payment actions limit per IP address.",
    ),
    _s(
        "throttle.receipt_code",
        STR,
        "20/hour",
        "Limite de saisies du code de réception par adresse IP.",
        "Receipt code attempts limit per IP address.",
    ),
    _s(
        "throttle.message_send",
        STR,
        "120/minute",
        "Limite d'envoi de messages par adresse IP.",
        "Message sending limit per IP address.",
    ),
]


# Shops of the pros (module 4).
SETTINGS += [
    _s(
        "shop.max_photos",
        INT,
        "8",
        "Nombre maximum de photos d'un produit.",
        "Maximum number of pictures of a product.",
    ),
    _s(
        "shop.video_max_seconds",
        INT,
        "60",
        "Durée maximum de la vidéo d'un produit (secondes).",
        "Maximum length of a product video (seconds).",
    ),
    _s(
        "shop.prep_days_max",
        INT,
        "60",
        "Délai de préparation maximum qu'une pro peut annoncer (jours).",
        "Longest preparation time a pro can announce (days).",
    ),
    _s(
        "shop.cart_max_lines",
        INT,
        "30",
        "Nombre maximum de lignes dans un panier.",
        "Maximum number of lines in a cart.",
    ),
    _s(
        "shop.max_quantity_per_line",
        INT,
        "20",
        "Quantité maximum d'un même produit dans une commande.",
        "Maximum quantity of one product in an order.",
    ),
    _s(
        "shop.promo_max_percent",
        INT,
        "70",
        "Remise maximum d'un code promo (pourcentage).",
        "Highest discount of a promo code (percent).",
    ),
    _s(
        "shop.flash_sale_max_days",
        INT,
        "7",
        "Durée maximum d'une vente flash (jours).",
        "Longest flash sale (days).",
    ),
    _s(
        "shop.price_drop_min_percent",
        INT,
        "10",
        "Baisse de prix (pourcentage) qui déclenche une alerte pour la liste d'envies.",
        "Price drop (percent) that alerts the wishlists.",
    ),
    _s(
        "shop.price_alert_cooldown_days",
        INT,
        "7",
        "Jours minimum entre deux alertes de baisse de prix pour un même produit.",
        "Minimum days between two price drop alerts for the same product.",
    ),
    _s(
        "shop.low_stock_threshold",
        INT,
        "3",
        "Stock à partir duquel « Ma boutique » signale une rupture proche.",
        "Stock under which « My shop » warns that a product runs out.",
    ),
    _s(
        "throttle.shop",
        STR,
        "120/minute",
        "Limite des actions de boutique (panier, commandes) par adresse IP.",
        "Shop actions limit (cart, orders) per IP address.",
    ),
]


# France Selection (module 6): the price formula, delays, quotes, air restrictions.
SETTINGS += [
    _s(
        "selection.eur_xof_rate",
        STR,
        "655.957",
        "Taux euro → FCFA de la formule de prix (parité fixe).",
        "Euro to FCFA rate of the price formula (fixed parity).",
    ),
    _s(
        "selection.rounding_xof",
        INT,
        "100",
        "Arrondi du prix de vente (à la centaine de FCFA supérieure).",
        "Rounding of the sale price (up to the next hundred FCFA).",
    ),
    _s(
        "selection.pricing_defaults",
        JSON,
        '{"transport_per_kg_cents": 1200, "express_per_kg_cents": 2500, "packaging_cents": 150, "customs_bps": 2000, "margin_bps": 2500, "payment_fee_cents": 80}',
        "Paramètres de prix par défaut (une catégorie peut les remplacer) : transport groupé et express par kg et emballage en centimes d'euro, douane et marge en centièmes de pourcent (2000 = 20 %), frais de paiement en centimes.",
        "Default price parameters (a category can replace them): grouped and express transport per kg and packaging in euro cents, customs and margin in hundredths of a percent (2000 = 20 %), payment fees in cents.",
    ),
    _s(
        "selection.delays",
        JSON,
        '{"purchase_days": [3, 6], "grouped_transit_days": [7, 12], "express_transit_days": [3, 5], "departure_weekday": 4}',
        "Délais affichés : achat en France, transport groupé, transport express (jours, mini et maxi) ; jour du départ groupé (0 = lundi, 4 = vendredi).",
        "Delays shown: purchase in France, grouped transport, express transport (days, min and max); day of the grouped departure (0 = Monday, 4 = Friday).",
    ),
    _s(
        "selection.countries",
        JSON,
        '["BJ"]',
        "Pays dont les clientes peuvent commander (retrait au Bénin, prix en FCFA).",
        "Countries whose clients can order (pick-up in Benin, prices in FCFA).",
    ),
    _s(
        "selection.max_quantity",
        INT,
        "5",
        "Quantité maximum d'un produit dans une commande.",
        "Maximum quantity of a product in an order.",
    ),
    _s(
        "selection.quote_valid_days",
        INT,
        "7",
        "Durée de validité d'un devis de demande spéciale (jours).",
        "How long a special request quote stays valid (days).",
    ),
    _s(
        "selection.block_air_restricted",
        BOOL,
        "true",
        "Bloquer les catégories interdites en avion (parfums, aérosols).",
        "Block the categories forbidden by air (perfumes, aerosols).",
    ),
    _s(
        "selection.house_email",
        STR,
        "selection@solangeglow.com",
        "Compte qui encaisse les ventes de la Sélection France (la plateforme).",
        "Account that receives the France Selection sales (the platform).",
    ),
    _s(
        "throttle.selection",
        STR,
        "60/minute",
        "Limite des actions de la Sélection France par adresse IP.",
        "France Selection actions limit per IP address.",
    ),
]


# Appointments (module 8): engine, answers, cancellation, no-shows, waiting list, groups.
SETTINGS += [
    _s(
        "booking.min_notice_minutes",
        INT,
        "120",
        "Délai minimum avant un rendez-vous réservé en ligne (minutes ; une pro peut le changer).",
        "Minimum notice before an appointment booked online (minutes; a pro can change it).",
    ),
    _s(
        "booking.horizon_days",
        INT,
        "60",
        "Jusqu'à combien de jours à l'avance on peut réserver (une pro peut le changer).",
        "How many days ahead clients can book (a pro can change it).",
    ),
    _s(
        "booking.pro_answer_hours",
        INT,
        "24",
        "Temps laissé pour répondre à une demande ou à un autre créneau proposé (heures) ; sans réponse, le rendez-vous est annulé et l'acompte rendu.",
        "Time to answer a request or a proposed time (hours); without answer the appointment is cancelled and the deposit refunded.",
    ),
    _s(
        "booking.free_cancel_hours",
        INT,
        "24",
        "Annulation gratuite par la cliente jusqu'à ce nombre d'heures avant ; ensuite la pro garde l'acompte.",
        "Free cancellation by the client up to this many hours before; then the pro keeps the deposit.",
    ),
    _s(
        "booking.late_tolerance_minutes",
        INT,
        "15",
        "Retard toléré avant que la pro puisse marquer la cliente absente (minutes).",
        "Lateness allowed before the pro can mark the client as a no-show (minutes).",
    ),
    _s(
        "booking.no_show_threshold",
        INT,
        "2",
        "Nombre de lapins (toutes pros confondues) qui rendent un acompte obligatoire. 0 = jamais.",
        "Number of no-shows (all pros) that make a deposit compulsory. 0 = never.",
    ),
    _s(
        "booking.no_show_window_months",
        INT,
        "12",
        "Période pendant laquelle les lapins comptent (mois).",
        "Period during which no-shows count (months).",
    ),
    _s(
        "booking.no_show_deposit_percent",
        INT,
        "30",
        "Acompte imposé après trop de lapins (pourcentage du prix).",
        "Deposit imposed after too many no-shows (percent of the price).",
    ),
    _s(
        "booking.reminder_hours",
        JSON,
        "[24, 2]",
        "Rappels envoyés avant le rendez-vous (heures avant).",
        "Reminders sent before the appointment (hours before).",
    ),
    _s(
        "booking.waitlist_answer_minutes",
        INT,
        "30",
        "Temps pendant lequel une place libérée est gardée pour la cliente de la liste d'attente (minutes).",
        "How long a freed place is kept for the waiting-list client (minutes).",
    ),
    _s(
        "booking.group_max",
        INT,
        "8",
        "Nombre maximum de personnes dans une réservation de groupe.",
        "Maximum number of people in a group booking.",
    ),
    _s(
        "booking.group_pay_hours",
        INT,
        "24",
        "Temps laissé aux participantes d'un groupe pour payer leur part (heures).",
        "Time for the members of a group to pay their share (hours).",
    ),
    _s(
        "throttle.booking",
        STR,
        "60/minute",
        "Limite des réservations et actions de rendez-vous par adresse IP.",
        "Booking actions limit per IP address.",
    ),
]


# Glow Pro offers and salon management (prompt 12).
SETTINGS += [
    _s(
        "glowpro.renewal_notice_days",
        INT,
        "3",
        "Jours avant la fin du mois où la pro reçoit le paiement du mois suivant (ou la fin de l'essai).",
        "Days before the end of the month when the pro gets the payment of next month (or the end of the trial).",
    ),
    _s(
        "glowpro.grace_days",
        INT,
        "7",
        "Jours de grâce après un mois non payé avant le retour à l'offre gratuite.",
        "Days of grace after an unpaid month before going back to the free plan.",
    ),
    {
        **_s(
            "glowpro.house_email",
            STR,
            "glowpro.bj@solangeglow.com",
            "Compte de la plateforme qui vend les abonnements au Bénin.",
            "Platform account that sells the subscriptions in Benin.",
        ),
        "country": "BJ",
    },
    {
        **_s(
            "glowpro.house_email",
            STR,
            "glowpro.fr@solangeglow.com",
            "Compte de la plateforme qui vend les abonnements en France.",
            "Platform account that sells the subscriptions in France.",
        ),
        "country": "FR",
    },
    _s(
        "salon.cash_countries",
        JSON,
        '["BJ"]',
        "Pays où la pro peut enregistrer des paiements en espèces ou Mobile Money (pas une caisse certifiée NF525 : à ne pas ouvrir en France sans avis).",
        "Countries where the pro can record cash or Mobile Money payments (not a certified NF525 till: do not open in France without advice).",
    ),
    _s(
        "salon.gift_card_validity_days",
        INT,
        "365",
        "Durée de validité d'une carte cadeau (jours).",
        "How long a gift card can be used (days).",
    ),
    {
        **_s(
            "salon.gift_card_limits",
            JSON,
            "[5000, 500000]",
            "Montant minimum et maximum d'une carte cadeau (FCFA).",
            "Minimum and maximum amount of a gift card (FCFA).",
        ),
        "country": "BJ",
    },
    {
        **_s(
            "salon.gift_card_limits",
            JSON,
            "[1000, 50000]",
            "Montant minimum et maximum d'une carte cadeau (centimes d'euro).",
            "Minimum and maximum amount of a gift card (euro cents).",
        ),
        "country": "FR",
    },
    _s(
        "throttle.salon",
        STR,
        "120/minute",
        "Limite des actions de gestion du salon par adresse IP.",
        "Salon management actions limit per IP address.",
    ),
    _s(
        "throttle.widget",
        STR,
        "120/minute",
        "Limite des appels du widget de réservation par adresse IP.",
        "Booking widget calls limit per IP address.",
    ),
]

# Academy (prompt 13): prices of the courses, the pass, withdrawal, quizzes, lives.
SETTINGS += [
    {
        **_s(
            "academy.price_limits",
            JSON,
            "[500, 25000]",
            "Prix minimum et maximum d'une formation vendue à l'unité (FCFA).",
            "Lowest and highest price of a course sold once (FCFA).",
        ),
        "country": "BJ",
    },
    {
        **_s(
            "academy.price_limits",
            JSON,
            "[200, 5000]",
            "Prix minimum et maximum d'une formation vendue à l'unité (centimes d'euro).",
            "Lowest and highest price of a course sold once (euro cents).",
        ),
        "country": "FR",
    },
    {
        **_s(
            "academy.pass_price_minor",
            INT,
            "2000",
            "Prix d'un mois de pass de l'Académie (FCFA). 0 : pas de pass dans ce pays.",
            "Price of a month of the Academy pass (FCFA). 0: no pass in this country.",
        ),
        "country": "BJ",
    },
    {
        **_s(
            "academy.pass_price_minor",
            INT,
            "500",
            "Prix d'un mois de pass de l'Académie (centimes d'euro). 0 : pas de pass dans ce pays.",
            "Price of a month of the Academy pass (euro cents). 0: no pass in this country.",
        ),
        "country": "FR",
    },
    {
        **_s(
            "academy.house_email",
            STR,
            "academy.bj@solangeglow.com",
            "Compte de la plateforme qui vend ses formations et le pass au Bénin.",
            "Platform account that sells its courses and the pass in Benin.",
        ),
        "country": "BJ",
    },
    {
        **_s(
            "academy.house_email",
            STR,
            "academy.fr@solangeglow.com",
            "Compte de la plateforme qui vend ses formations et le pass en France.",
            "Platform account that sells its courses and the pass in France.",
        ),
        "country": "FR",
    },
    _s(
        "academy.refund_days",
        INT,
        "14",
        "Jours pendant lesquels une élève peut se faire rembourser tant qu'elle n'a ouvert aucune leçon.",
        "Days during which a student can get her money back while she has opened no lesson.",
    ),
    _s(
        "academy.quiz_pass_percent",
        INT,
        "70",
        "Pourcentage de bonnes réponses pour réussir le quiz d'un module.",
        "Share of right answers needed to pass the quiz of a module.",
    ),
    _s(
        "academy.watched_percent",
        INT,
        "90",
        "Part d'une leçon à regarder pour qu'elle compte comme vue (%).",
        "Share of a lesson to watch for it to count as watched (%).",
    ),
    _s(
        "academy.lesson_min_seconds",
        INT,
        "180",
        "Durée minimum d'une vidéo de leçon (secondes).",
        "Shortest video of a lesson (seconds).",
    ),
    _s(
        "academy.lesson_max_seconds",
        INT,
        "600",
        "Durée maximum d'une vidéo de leçon (secondes).",
        "Longest video of a lesson (seconds).",
    ),
    _s(
        "academy.lesson_max_bytes",
        INT,
        str(500 * 1024 * 1024),
        "Taille maximum d'une vidéo de leçon envoyée (octets).",
        "Biggest video of a lesson that can be sent (bytes).",
    ),
    _s(
        "academy.resource_max_bytes",
        INT,
        str(20 * 1024 * 1024),
        "Taille maximum d'un PDF joint à une leçon (octets).",
        "Biggest PDF given with a lesson (bytes).",
    ),
    _s(
        "academy.video_url_ttl_seconds",
        INT,
        "3600",
        "Durée de validité du lien d'une vidéo de leçon (secondes).",
        "How long the link of a lesson video works (seconds).",
    ),
    _s(
        "academy.pass_notice_days",
        INT,
        "3",
        "Jours avant la fin du mois où l'élève reçoit le paiement du mois suivant du pass.",
        "Days before the end of the month when the student gets the payment of next month.",
    ),
    _s(
        "academy.live_room_open_minutes",
        INT,
        "10",
        "Minutes avant le début où la salle d'un live s'ouvre.",
        "Minutes before the start when the room of a live opens.",
    ),
    _s(
        "academy.live_reminder_hours",
        INT,
        "24",
        "Heures avant un live pour le premier rappel.",
        "Hours before a live for the first reminder.",
    ),
    _s(
        "academy.live_reminder_minutes",
        INT,
        "15",
        "Minutes avant un live pour le dernier rappel.",
        "Minutes before a live for the last reminder.",
    ),
    _s(
        "throttle.academy",
        STR,
        "240/minute",
        "Limite des actions de l'Académie par adresse IP (la lecture enregistre la position souvent).",
        "Academy actions limit per IP address (the player saves the position often).",
    ),
    # --- Calls and lives (ADR-013) ---
    _s(
        "rtc.token_ttl_seconds",
        INT,
        "600",
        "Durée de validité d'un jeton pour entrer dans un appel ou un live (secondes).",
        "How long a token to enter a call or a live stays valid (seconds).",
    ),
    _s(
        "calls.max_minutes",
        INT,
        "60",
        "Durée maximale d'un appel (minutes) ; l'appel est coupé ensuite.",
        "Longest call (minutes); the call is cut afterwards.",
    ),
    _s(
        "calls.ring_seconds",
        INT,
        "45",
        "Durée de la sonnerie avant « Appel manqué » (secondes).",
        "How long a call rings before « Missed call » (seconds).",
    ),
    _s(
        "calls.max_participants",
        INT,
        "3",
        "Nombre de personnes au plus dans l'appel d'une salle de litige.",
        "Most people in the call of a dispute room.",
    ),
    _s(
        "live.max_minutes",
        INT,
        "120",
        "Durée maximale d'un live (minutes) ; il est coupé ensuite.",
        "Longest live (minutes); it is cut afterwards.",
    ),
    _s(
        "live.max_viewers",
        INT,
        "300",
        "Nombre de spectatrices au plus dans un live.",
        "Most viewers in a live.",
    ),
    _s(
        "live.free_per_month",
        INT,
        "2",
        "Lives gratuits par mois et par pro (formation et vente ensemble) ; Glow Pro Premium "
        "en donne plus (limite « lives_per_month » de l'offre).",
        "Free lives a month for each pro (training and sales together); Glow Pro Premium "
        "gives more (limit « lives_per_month » of the plan).",
    ),
    _s(
        "live.start_early_minutes",
        INT,
        "15",
        "Minutes avant l'heure prévue où la pro peut passer en direct.",
        "Minutes before the planned time when the pro can go on air.",
    ),
    _s(
        "live.replay_max_seconds",
        INT,
        "7800",
        "Durée maximale d'un replay enregistré (secondes).",
        "Longest recorded replay (seconds).",
    ),
    _s(
        "academy.live_replay_days",
        INT,
        "30",
        "Jours pendant lesquels le replay d'un live de formation reste visible pour les inscrites.",
        "Days during which the replay of a training live stays visible to registered students.",
    ),
    _s(
        "shop.live_replay_days",
        INT,
        "7",
        "Jours pendant lesquels le replay d'une vente en live reste visible (et ses produits).",
        "Days during which the replay of a sales live stays visible (and its products).",
    ),
    _s(
        "throttle.live",
        STR,
        "240/minute",
        "Limite des lectures d'un live par adresse IP (l'écran se recharge souvent).",
        "Live reads limit per IP address (the screen reloads often).",
    ),
    _s(
        "throttle.live_write",
        STR,
        "20/minute",
        "Limite des questions et mains levées par adresse IP.",
        "Questions and raised hands limit per IP address.",
    ),
    _s(
        "throttle.calls",
        STR,
        "60/minute",
        "Limite des actions d'appel par adresse IP.",
        "Call actions limit per IP address.",
    ),
    # Diaspora gifts (module 9, ADR-014).
    _s(
        "gifts.eur_xof_rate",
        STR,
        "655.957",
        "Taux fixe de l'euro en FCFA pour les cadeaux (prix en euros, valeur en FCFA).",
        "Fixed rate of the euro in FCFA for gifts (price in euros, value in FCFA).",
    ),
    _s(
        "gifts.validity_days",
        INT,
        "365",
        "Durée de validité d'un cadeau, en jours.",
        "How long a gift can be used, in days.",
    ),
    _s(
        "gifts.cancel_days",
        INT,
        "14",
        "Jours pendant lesquels la personne qui offre peut annuler (cadeau non utilisé).",
        "Days during which the giver can cancel (unused gift), refunded in euros.",
    ),
    _s(
        "gifts.card_limits_eur",
        JSON,
        "[1000, 50000]",
        "Montant d'une carte cadeau Glow : minimum et maximum en centimes d'euro.",
        "Amount of a Glow gift card: minimum and maximum in euro cents.",
    ),
    _s(
        "gifts.message_max_seconds",
        INT,
        "60",
        "Durée maximale du message vocal ou vidéo joint à un cadeau (secondes).",
        "Longest voice or video message attached to a gift (seconds).",
    ),
    _s(
        "gifts.max_schedule_days",
        INT,
        "365",
        "Envoi programmé : jusqu'à combien de jours à l'avance.",
        "Scheduled sending: how many days ahead at most.",
    ),
    _s(
        "gifts.remind_after_days",
        INT,
        "30",
        "Rappel à la bénéficiaire si le cadeau n'est pas utilisé après ce nombre de jours.",
        "Reminder to the person when the gift is still unused after these days.",
    ),
    _s(
        "gifts.recipient_countries",
        JSON,
        '["BJ"]',
        "Pays où l'on reçoit et utilise les cadeaux (en FCFA).",
        "Countries where gifts are received and used (in FCFA).",
    ),
    _s(
        "gifts.house_email",
        STR,
        "cadeaux@solangeglow.com",
        "Compte de la plateforme qui vend les cadeaux (paiements en euros).",
        "Platform account selling the gifts (payments in euros).",
    ),
    _s(
        "throttle.gifts",
        STR,
        "60/minute",
        "Limite des actions sur les cadeaux par adresse IP.",
        "Gift actions limit per IP address.",
    ),
    _s(
        "throttle.gift_code",
        STR,
        "20/hour",
        "Limite des essais de code de carte cadeau Glow par adresse IP.",
        "Glow gift card code attempts limit per IP address.",
    ),
    # Games (module 10, ADR-015): points per action, caps, levels, wheel, quiz, challenges.
    _s(
        "glow.points",
        JSON,
        '{"checkin": 5, "streak": 50, "post": 10, "review": 20, "booking": 30, '
        '"purchase": 30, "referral": 200, "referred": 100, "quiz": 10, "poll": 5, '
        '"poll_vote": 2, "challenge_entry": 15, "challenge_vote": 2, "challenge_win": 300, '
        '"routine": 3}',
        "Barème des Glow Points : points gagnés pour chaque action.",
        "Glow Points scale: points earned for each action.",
    ),
    _s(
        "glow.daily_caps",
        JSON,
        '{"post": 3, "review": 5, "booking": 3, "purchase": 5, "poll": 2, "poll_vote": 20, '
        '"challenge_vote": 10, "routine": 2}',
        "Anti-abus : nombre maximum de fois par jour où une action rapporte des points.",
        "Anti-abuse: how many times a day an action gives points at most.",
    ),
    _s(
        "glow.daily_max_points",
        INT,
        "400",
        "Anti-abus : points gagnés au plus par jour (hors bonus de la liste suivante).",
        "Anti-abuse: most points earned a day (bonuses of the next list excepted).",
    ),
    _s(
        "glow.uncapped_actions",
        JSON,
        '["streak", "referral", "referred", "challenge_win", "wheel"]',
        "Bonus hors plafond du jour et sans multiplicateur de niveau.",
        "Bonuses outside the daily ceiling, without the level multiplier.",
    ),
    _s(
        "glow.streak_bonus_every",
        INT,
        "7",
        "Série de connexion : bonus tous les N jours d'affilée.",
        "Visit streak: bonus every N days in a row.",
    ),
    _s(
        "glow.level_thresholds",
        JSON,
        '{"star": 1000, "icon": 5000}',
        "Niveaux des clientes : points gagnés depuis le début pour être Star, Icône.",
        "Client levels: points earned since the start to be Star, Icon.",
    ),
    _s(
        "glow.level_multipliers",
        JSON,
        '{"glow": 1, "star": 1.1, "icon": 1.25}',
        "Avantage des niveaux : multiplicateur des points gagnés.",
        "Level advantage: multiplier of the points earned.",
    ),
    _s(
        "glow.purchase_purposes",
        JSON,
        '["order", "selection", "training", "package", "gift_card", "gift"]',
        "Achats qui rapportent des points (une fois l'argent versé).",
        "Purchases that give points (once the money is released).",
    ),
    _s(
        "glow.referral_window_days",
        INT,
        "7",
        "Parrainage : jours après l'inscription pour lier un compte à sa marraine.",
        "Referrals: days after sign-up to link an account to its godmother.",
    ),
    _s(
        "glow.referral_monthly_max",
        INT,
        "10",
        "Parrainage : filleules récompensées au plus par mois et par marraine.",
        "Referrals: goddaughters rewarded at most per month per godmother.",
    ),
    _s(
        "glow.voucher_min_to_pay",
        INT,
        "1000",
        "Bon Glow : reste à payer minimum d'une commande Sélection France (FCFA).",
        "Glow voucher: least amount left to pay on a France Selection order (FCFA).",
    ),
    _s(
        "glow.history_size",
        INT,
        "100",
        "Lignes affichées dans l'historique des points.",
        "Lines shown in the points history.",
    ),
    _s(
        "games.quiz_questions",
        INT,
        "3",
        "Quiz du jour : nombre de questions.",
        "Quiz of the day: number of questions.",
    ),
    _s(
        "games.quiz_days_ahead",
        INT,
        "7",
        "Quiz : brouillons préparés pour les N prochains jours.",
        "Quiz: drafts prepared for the next N days.",
    ),
    _s(
        "games.quiz_audio_max_seconds",
        INT,
        "60",
        "Quiz : durée maximale de l'audio d'une question (secondes).",
        "Quiz: longest audio of a question (seconds).",
    ),
    _s(
        "games.poll_durations_hours",
        JSON,
        "[1, 6, 24, 72]",
        "« Aide-moi à choisir » : durées de vote proposées (heures).",
        "« Help me choose »: vote durations offered (hours).",
    ),
    _s(
        "games.poll_max_open",
        INT,
        "3",
        "« Aide-moi à choisir » : questions ouvertes en même temps par personne.",
        "« Help me choose »: open questions at the same time per person.",
    ),
    _s(
        "games.challenge_votes_per_person",
        INT,
        "3",
        "Défi photo : votes par personne et par défi.",
        "Photo challenge: votes per person and per challenge.",
    ),
    _s(
        "games.challenge_weeks_ahead",
        INT,
        "4",
        "Défi photo : brouillons préparés pour les N prochaines semaines.",
        "Photo challenge: drafts prepared for the next N weeks.",
    ),
    _s(
        "games.winner_featured_days",
        INT,
        "7",
        "Défi photo : jours où la gagnante est mise en avant sur l'accueil.",
        "Photo challenge: days the winner is shown on the home page.",
    ),
    _s(
        "games.pro_levels",
        JSON,
        '{"confirmed": {"done": 10, "reviews": 5, "average": 4.0, "verified": false}, '
        '"top": {"done": 50, "reviews": 20, "average": 4.6, "verified": true}}',
        "Niveaux des pros : prestations ou commandes faites, avis, note moyenne, vérifiée.",
        "Pro levels: appointments or orders done, reviews, average rating, verified.",
    ),
    _s(
        "games.ranking_min_reviews",
        INT,
        "3",
        "Classements : avis vérifiés du mois nécessaires pour y figurer.",
        "Rankings: verified reviews of the month needed to appear.",
    ),
    _s(
        "games.ranking_prior",
        INT,
        "5",
        "Classements : poids de la moyenne générale (évite qu'un seul 5 étoiles gagne).",
        "Rankings: weight of the overall average (one 5-star review never wins).",
    ),
    _s(
        "games.ranking_size",
        INT,
        "10",
        "Classements : nombre de pros par ville et par métier.",
        "Rankings: number of pros per city and trade.",
    ),
    _s(
        "games.routine_max_steps",
        INT,
        "8",
        "Ma routine : étapes au plus le matin, et le soir.",
        "My routine: most steps in the morning, and in the evening.",
    ),
    _s(
        "games.routine_window_minutes",
        INT,
        "120",
        "Ma routine : rappel envoyé dans ce délai après l'heure choisie (minutes).",
        "My routine: reminder sent within this time after the chosen hour (minutes).",
    ),
    _s(
        "games.calendar_days",
        INT,
        "365",
        "Calendrier des fêtes : jours affichés à l'avance.",
        "Calendar of celebrations: days shown ahead.",
    ),
    _s(
        "throttle.games",
        STR,
        "120/minute",
        "Limite des actions des jeux par adresse IP.",
        "Games actions limit per IP address.",
    ),
]

# Monthly price of Premium (created with the countries; edited in the admin afterwards).
PLAN_PRICES = [("premium", "BJ", "XOF", 9_900), ("premium", "FR", "EUR", 2_900)]


class Command(BaseCommand):
    help = "Create countries (BJ, FR), currencies (XOF, EUR) and the platform settings."

    @transaction.atomic
    def handle(self, *args, **options):
        created = {"currencies": 0, "countries": 0, "settings": 0}

        currencies = {}
        for data in CURRENCIES:
            data = dict(data)
            code = data.pop("code")
            data["name"] = data["name_fr"]
            currencies[code], was_created = Currency.objects.get_or_create(code=code, defaults=data)
            created["currencies"] += was_created

        countries = {}
        for data in COUNTRIES:
            data = dict(data)
            code = data.pop("code")
            data["default_currency"] = currencies[data.pop("currency")]
            data["name"] = data["name_fr"]
            countries[code], was_created = Country.objects.get_or_create(code=code, defaults=data)
            created["countries"] += was_created

        for data in SETTINGS:
            data = dict(data)
            key = data.pop("key")
            country_code = data.pop("country")
            country = countries[country_code] if country_code else None
            data["description"] = data["description_fr"]
            _, was_created = PlatformSetting.objects.get_or_create(
                key=key, country=country, defaults=data
            )
            created["settings"] += was_created

        from apps.glowpro.models import Plan, PlanPrice

        for key, code, currency, amount in PLAN_PRICES:
            plan = Plan.objects.filter(key=key).first()
            if plan is not None and code in countries:
                PlanPrice.objects.get_or_create(
                    plan=plan,
                    country=countries[code],
                    defaults={"currency": currency, "amount_minor": amount},
                )

        self.stdout.write(
            self.style.SUCCESS(
                "seed_core: {currencies} currencies, {countries} countries, "
                "{settings} settings created.".format(**created)
            )
        )
