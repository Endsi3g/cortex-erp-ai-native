# Cortex — guide d'usage du logo

Direction retenue : **Return ring** (concept B). Sources et exports : ce dossier. Concepts comparés : `../logo-concepts/`.

## 1. Le logo
- **Idée** : un anneau ouvert, le matériel qui sort et revient, avec l'unité dans l'ouverture. Le point est l'unique accent : l'élément en mouvement, la décision humaine. Un C d'une seule forme, sans étincelle ni halo.
- **Versions** : horizontale (principale) · empilée · symbole seul · wordmark seul.
- **Fichiers maîtres** (`*.svg`) : `cortex-horizontal`, `cortex-stacked`, `cortex-symbol`, `cortex-wordmark`. Versions sur fond sombre : `*-reversed`. Coupe petite taille : `cortex-symbol-small` (et `-reversed`).
- **Variantes** : `variants/` (noir, blanc, vert `#047857`, carré) · icônes web et PWA : `web/`.

## 2. Zone de protection
Laisser autour du logo une marge d'au moins **1 × l'épaisseur de l'anneau** (≈ 23 % du diamètre de l'anneau) sur chaque côté. La marge suit la taille du logo ; jamais de distance fixe.

## 3. Tailles minimales
| Version | Écran | Impression |
|---|---|---|
| Horizontale | 96 px de large | à définir avec l'imprimeur |
| Empilée | 64 px de large | à définir avec l'imprimeur |
| Symbole | 16 px (utiliser `cortex-symbol-small` sous 32 px) | à définir avec l'imprimeur |

## 4. Couleur
Les couleurs viennent des tokens de `public/css/cortex-tokens.css`. Aucune valeur CMYK ni Pantone n'a été définie : à faire valider par un imprimeur avant toute impression.

| Rôle | HEX | Token |
|---|---|---|
| Encre (anneau, wordmark) | `#09090B` | `--cortex-text` |
| Accent (point) | `#047857` | `--cortex-primary-600` |
| Fond sombre (icône d'app) | `#022C22` | `--cortex-primary-900` |
| Accent sur fond sombre | `#34D399` | `--cortex-emerald-400` |

Contrastes calculés (WCAG) : vert sur blanc 5,48:1 · encre sur blanc 19,9:1 · blanc sur fond sombre 15,2:1 · menthe sur fond sombre 7,9:1. Le vert et l'encre côte à côte ne font que 3,6:1 : le point se distingue par sa **forme**, jamais par la couleur seule.

**Associations approuvées** : couleur sur blanc · version inversée sur `#022C22` · noir sur blanc · blanc sur photo calme ou fond uni.

## 5. Typographie
- Wordmark : **Inter SemiBold**, converti en tracés (aucun texte vivant), espacement −1,2 %. Licence : SIL Open Font License 1.1, qui autorise l'usage dans un logo.
- Interface : Inter (token `--font-sans`).
- Le crénage automatique de la police n'a pas été appliqué ; les paires ont été vérifiées à l'œil.

## 6. À éviter
Ne pas étirer ni déformer · ne pas recolorer hors palette · ne pas faire pivoter · pas d'ombre, contour, dégradé ni halo · ne pas déplacer le point · ne pas redessiner le wordmark en tapant le nom · pas de fond chargé sans conteneur · pas de violet ni d'étincelles.

## 7. Dans le produit
- Desk ERPNext : `hooks.py → app_logo_url` pointe vers `public/images/cortex-logo.svg` (coupe petite taille, couleur).
- Interface Cortex : composant `CortexLogo.vue` (symbole + « Cortex » en Inter SemiBold).
- Favicon de la SPA : `frontend/public/favicon.svg`.

## 8. Limites connues
- Aucune recherche de marque ni d'antériorité n'a été faite : à confirmer par un professionnel avant tout dépôt.
- Aucun format PDF/AI/EPS : SVG et PNG seulement.
- La planche `presentation.html` nomme le concept « A » : c'est une étiquette du gabarit.
