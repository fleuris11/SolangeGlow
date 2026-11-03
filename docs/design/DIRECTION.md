# Direction artistique « Glow éditorial »

Maquettes : [Figma, Solange Glow — Glow v2](https://www.figma.com/design/IYJeVoJF24xJ0F1HCixBSb).
Captures : `docs/design/direction/`. Crédits des photos : `docs/design/PHOTOS.md`.

## L'idée

> Sur Solange Glow, **le pétale du logo devient la fenêtre** par laquelle on découvre de vraies
> peaux, et **le nom « Solange »** devient l'architecture de la page.

Test du concurrent : mets Planity ou Fenty dans cette phrase, elle ne marche plus. Le pétale n'est
qu'à nous.

**Le geste vivant de la page d'accueil** : on touche un métier (Tresses, Maquillage, Coiffure…), la
photo du pétale change et le bouton devient « Trouver ma pro de tresses ». Ça marche au pouce, et
sans JavaScript le choix reste un lien.

**Le moment que personne d'autre n'a** : le code de réception en six très grands chiffres or sur
fond de nuit. C'est la promesse du produit (l'argent bloqué) rendue visible.

## Deux variantes

### A. « Couverture » : plus magazine (ma recommandation)
La première image est une couverture : nom géant, photo en pétale, peu de mots. Le reste de la page
alterne les sections jour et nuit, les photos à tailles inégales et les aplats (hibiscus, poudre).

- Pour : frappe tout de suite, très reconnaissable, fier, proche de « magazine beauté qu'on peut toucher ».
- Contre : demande de très bonnes photos, et l'action arrive une demi-seconde après l'émotion.

### B. « Story » : plus sociale
La première image est une story plein écran d'une vraie pro, avec son prix et un bouton de réservation.
On glisse vers le haut pour passer à la pro suivante.

- Pour : très vivant, on comprend sans lire, et ça montre de vraies pros.
- Contre : ressemble à TikTok et Instagram, donc moins de personnalité ; lourd en 3G (vidéo dès l'arrivée) ;
  sans pros réelles au lancement, l'écran serait vide ou mensonger.

### Ce que je recommande
**La variante A pour l'accueil public, et le meilleur de B dans l'application connectée** : stories en plein
écran et fil en grandes photos. La marque impressionne à la première visite, et l'usage quotidien reste
familier.

## Comment la direction s'applique

| Sujet | Décision |
| --- | --- |
| Photo | Une image dominante par écran. Pétale pour les pros, 4:5 pour les publications, plein cadre pour les en-têtes |
| Jour et nuit | Nuit pour les moments forts : ouverture, vitrine, lives, code, réussite. Jour pour l'usage courant |
| Couleur | Hibiscus sur l'action seulement. Or pour le code et les récompenses. Aplats hibiscus et poudre en section entière |
| Lumière | Une seule : la lueur chaude tirée de la photo, sur les fonds de nuit |
| Type | Fraunces très grand, Atkinson pour tout le reste. Le zéro barré d'Atkinson est gardé : il se lit mieux |
| Application connectée | Plus calme que la vitrine : mêmes couleurs et photos, moins d'effets. L'agenda et les tableaux de bord restent des outils |

## Moments signature

| Moment | Déclencheur | Durée | Courbe | Animations réduites |
| --- | --- | --- | --- | --- |
| Ouverture de l'accueil : masque pétale, puis titre ligne par ligne | Arrivée, une fois | 600 ms puis 280 ms | `cubic-bezier(0.23, 1, 0.32, 1)` | Tout visible, fondu 120 ms |
| Carte qui devient page | Appui sur une pro ou une publication | 320 ms | `cubic-bezier(0.77, 0, 0.175, 1)` | Changement direct |
| Halo Glow | Pro avec story ou créneau libre | 600 ms, une fois | `cubic-bezier(0.23, 1, 0.32, 1)` | Anneau fixe |
| Éclosion | Paiement, réservation, code validé, cadeau reçu | 600 ms, avec vibration | `cubic-bezier(0.23, 1, 0.32, 1)` | Coche en fondu |
| Défilement éditorial (accueil public) | Défilement : jour vers nuit, léger parallaxe | Lié au défilement | `linear` | Sections fixes |

## Micro-interactions

| Geste | Effet | Durée |
| --- | --- | --- |
| Appui sur un bouton | Enfoncement à 0,97 | 160 ms |
| J'aime | Petit pétale qui s'envole, compteur qui roule | 450 ms et 180 ms |
| Stories, galerie photos | Glisser au doigt, avec élan | Suit le doigt |
| Tirer pour rafraîchir | Le pétale s'ouvre avec le geste | Suit le doigt |
| Chargement | Squelettes qui ont la forme du contenu | Instantané |
| Toast | Glisse du bas, sort plus vite qu'il n'entre | 220 ms et 160 ms |

Jamais d'animation sur une action clavier ni sur un geste répété toute la journée (agenda, envoi de messages).
Seulement `transform`, `opacity` et `clip-path`, et 2 animations au plus dans le champ de vision.

## Pourquoi ça ne ressemble ni à un template ni à une marque

- **Pas de template** : ni héros centré, ni rangée de cartes à icônes, ni dégradé décoratif.
- **Glossier et Topicals** posent aussi un nom géant. Chez eux, le nom se pose sur le visage ou le produit ;
  chez nous, c'est la photo qui s'ouvre à travers le pétale, et la couleur vient du logo.
- **Pattern** alterne des aplats vifs et des portraits : on en garde le principe (aplat franc, vraie peau),
  pas la composition.

## Arbitrages entre les outils

La priorité est celle que tu as fixée : `solange-design`, puis `emil-design-eng`, puis `ui-ux-pro-max` et taste.

| Conseil écarté | Source | Raison |
| --- | --- | --- |
| Rose et lavande, Playfair et Inter | `ui-ux-pro-max` | Notre identité est fixée, et ce résultat est générique |
| « Éviter le mode sombre » | `ui-ux-pro-max` | La nuit fait partie de la direction |
| Aucune lueur, aucun dégradé | `design-taste-frontend` | `solange-design` autorise le halo et la lueur, rien d'autre |
| Photos carrées, pas de rayon | `design-taste-frontend` | Le pétale et les rayons hiérarchisés sont notre signature |
| Photo qui recouvre un titre | Composition « photos sur le titre » | Illisible : les photos passent à côté du titre, jamais dessus |

## Performance : le point dur

Le budget (ADR-004) est de 230 Ko, et la page de réservation est déjà à 229,5 Ko.

- **Pages applicatives** : ouverture, éclosion, halo et pression en CSS seul. `motion` chargé à la demande,
  uniquement sur les écrans qui ont des gestes (stories, galerie, feuille glissable).
- **Pages marketing** : GSAP chargé après le premier affichage, avec un budget séparé contrôlé en CI (ADR-020).
- **Première image** : la photo du pétale s'affiche sans attendre le JavaScript. Aucune vidéo en première image.
- **Risque** : viser 90 sur Lighthouse en 3G avec de grandes photos reste difficile. On part de 70 à 83. Je
  donnerai les vrais chiffres, écran par écran.

## Les photos

- **Personnes** : [Nappy](https://nappy.co/license), usage commercial autorisé, crédit facultatif (je crédite quand
  même). C'est la source principale.
- **Gestes africains** (nattes, tresseuses, mariée) : Wikimedia Commons. La plupart sont en CC BY-SA : crédit
  obligatoire et même licence pour une image retouchée. Je les réserve aux données de démonstration.
- **Produits** : StockSnap (CC0).
- Pexels a refusé les robots et aucune clé Unsplash n'est fournie : ces sources n'ont pas été utilisées.

**Limite à connaître** : ces licences couvrent la photo, pas forcément le droit à l'image des personnes. Pour
une publicité ou l'accueil en production, le mieux reste une vraie séance photo à Cotonou avec des modèles
qui signent une autorisation. C'est aussi ce qui donnera le plus d'authenticité.

## Ce que Figma n'a pas permis

L'offre gratuite limite une collection de variables à un seul mode : la nuit a donc ses propres variables
(`color/nuit/*`). Dans le code, chaque couleur aura bien ses deux valeurs. La carte d'Explorer est un dessin
de maquette : le vrai écran garde MapLibre.
