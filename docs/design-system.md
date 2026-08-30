# Cortex Operations System — design system

Foundation layer only in this pass: tokens, theme, utilities, branding,
and nine reusable Vue components. No new operational pages — see
`HANDOFF.md` for what's next (Composer, Check-in, Approvals, chat).

## Principes

- **Personnalité** : moderne, précis, calme, professionnel, technique.
- **Inspiration** : Linear (densité), Notion (clarté), Apple (finition).
- **Priorité** : vitesse au comptoir et fiabilité avant esthétique
  décorative — pas de gradients, pas de dashboard de cartes vides.
- **Densité** : mode confortable (défaut) et mode compact, via la classe
  `cx-density-compact` sur `.cortex-app` (voir `cortex-utilities.css`).
- **Couleur** : jamais l'unique signal — toujours icône + texte + couleur
  (+ tooltip si l'état n'est pas évident). Voir `CortexStatusBadge`.

## Packaging — pourquoi pas de projet `frontend/` npm/Vite/TypeScript

Une version antérieure de ce spec demandait un projet
`apps/cortex_rental/frontend/` séparé avec des tokens en `.ts`. Décision
prise avec l'utilisateur : **CSS + Vue natif dans `public/`**, pas de
second pipeline de build.

Pourquoi : l'écran Disponibilité (déjà livré) utilise le pattern natif
documenté par Frappe ("Vue in a Desk Page" — `frappe.require()` d'un
`.bundle.js` compilé par `bench build`, zéro étape de build
supplémentaire). Ajouter un projet npm/Vite séparé maintenant, sans
bench accessible dans cet environnement pour vérifier qu'il compile
réellement, aurait répété le risque déjà évité pour Disponibilité — et
créé deux systèmes de build parallèles à maintenir en synchro. Revoir
cette décision une fois un vrai bench confirmé (voir `HANDOFF.md` §3).

Conséquence concrète :
- tokens = CSS custom properties (`cortex-tokens.css`), pas `tokens.ts`;
- composants = fichiers `.vue` simples sous `public/js/cortex_shared/`,
  important les uns les autres via imports relatifs — pas de types
  TypeScript, pas de `component-contracts.md` généré, écrit à la main
  (voir `docs/design-system-component-contracts.md`);
- pas de Tailwind (nécessite PostCSS) — un petit jeu d'utilitaires CSS
  écrits à la main dans `cortex-utilities.css`, seulement ce dont les
  composants Cortex ont réellement besoin.

## Palette

Toutes les valeurs vivent dans
`apps/cortex_rental/cortex_rental/public/css/cortex-tokens.css` — ce
document ne les recopie pas pour éviter la dérive ; se référer au
fichier pour les valeurs exactes. Structure :

- **Neutres** : fond, surfaces, bordures, texte (4 niveaux d'emphase).
- **Marque Cortex** : indigo, échelle 50–900.
- **Couleurs sémantiques** : success/warning/danger/info/violet,
  échelle 50/500/600/700.
- **Tokens d'état métier** : voir section suivante.

## États — wired vs. reserved

Le spec propose 16 tokens d'état (`quote`, `draft`, `reservation`,
`contract`, `checked_out`, `partial_return`, `returned`,
`invoice_prepared`, `invoiced`, `closed`, `cancelled`, `disputed`,
`conflict`, `quarantine`, `repair`, `missing`). Tous sont définis dans
`cortex-tokens.css` — mais seuls certains correspondent à une vraie
valeur de DocType aujourd'hui :

| Token | Wired ? | Source réelle |
|---|---|---|
| `quote`, `reservation`, `contract`, `checked_out`, `returned`, `closed`, `cancelled`, `disputed` | ✓ | `Cortex Rental Transaction.rental_state` |
| `quarantine`, `repair`, `missing` | ✓ | `Serial No.cortex_status` (custom field) |
| `conflict` | ✓ | signal UI (`get_matrix`'s `has_conflict`), pas une valeur de champ |
| `draft`, `partial_return`, `invoice_prepared`, `invoiced` | ✗ réservé | aucun DocType n'émet cette valeur aujourd'hui |

**Règle** : ne construis pas un écran qui affiche un badge `reserved`
comme si l'état existait réellement — c'est exactement le problème de
"liens morts" qui a motivé cette passe de travail (voir
`CHANGELOG.md`, cinquième vague). `CortexStatusBadge` rend quand même
ces clés (le contrat du composant ne casse pas quand l'état devient
réel plus tard), mais les pages elles-mêmes ne doivent pas prétendre
qu'elles sont atteignables.

Mapping exact `rental_state`/`cortex_status` → clé de token :
`public/js/cortex_shared/stateMeta.js` (`RENTAL_STATE_KEY`,
`SERIAL_STATUS_KEY`) — source unique, pas dupliquée par écran.

## Contraste WCAG 2.2 AA — vérifié, pas suppose

`bin/check-contrast.py` parse les tokens réellement livrés et calcule
les ratios de contraste (formule WCAG relative luminance) pour chaque
paire texte/fond et bordure/page. Aucun framework de test JS n'existe
dans ce dépôt (pas de `package.json`/vitest nulle part) — c'est le
substitut réel et vérifiable à l'exigence du spec ("vérification que
les couleurs texte importantes respectent contraste AA").

**Premier run** : les valeurs de bordure du spec original (tons pastel
~50-niveau) échouaient toutes le seuil 3:1 contre une page blanche —
les fonds de badge eux-mêmes ne font qu'environ 1.1:1 de contraste
contre blanc, donc la bordure est ce qui doit réellement porter la
limite du composant, pas juste un accent décoratif. Corrigé en
remplaçant chaque bordure par la teinte 500/600 de sa famille de
couleur (même intention visuelle, contraste réel). Voir l'historique
git de `cortex-tokens.css` et `CHANGELOG.md` pour le detail exact.

Lancer : `python3 bin/check-contrast.py` — sort en code 1 avec le détail
si une paire échoue.

## Typographie

Échelle définie en classes utilitaires dans `cortex-theme.css`
(`.cx-title-page`, `.cx-title-section`, `.cx-title-card`,
`.cx-text-body`, `.cx-text-table`, `.cx-text-label`, `.cx-text-meta`,
`.cx-text-kpi`, `.cx-text-mono`). Police : pile système (voir note
"Inter" ci-dessous).

Règles :
- Jamais de texte gris clair (`--cortex-text-disabled`) pour une
  information critique — utiliser `.cx-text-critical`.
- Rien sous 12px pour du contenu opérationnel.
- Identifiants transaction/serial : `.cx-text-mono` (police mono).

### Note "Inter"

Le spec liste `"Inter"` en premier dans la pile de police, mais aucun
fichier webfont n'est livré dans cette passe : l'auto-héberger sans
bench pour vérifier le rendu, ou dépendre d'un CDN externe pour un
outil interne, étaient tous les deux pires que l'option honnête —
les polices système de repli (San Francisco sur Mac, Segoe UI sur
Windows) rendent déjà proche de l'esthétique Inter. À revoir une fois
un vrai bench disponible.

## Espacement, rayons, élévation

Valeurs dans `cortex-tokens.css` (`--space-*`, `--radius-*`,
`--shadow-*`) — identiques au spec. Règles d'usage : cartes 8px,
modales/panneaux 12px, badges pill (999px), tables très peu d'ombre.

## Responsive

Breakpoints du spec (desktop large ≥1440px, desktop 1024–1439px,
tablette 768–1023px, mobile <768px) documentés mais **pas encore
implémentés en CSS** dans cette passe — aucune page n'a encore de
layout à adapter (Disponibilité est desktop-first aujourd'hui). À
appliquer avec le premier écran qui a réellement besoin de tablette
(Check-in, per le PRD).

## Accessibilité

- Focus visible : `.cortex-app :focus-visible` → anneau indigo 2px,
  offset 2px (`cortex-theme.css`) — WCAG 2.2 AA "focus visible".
- Couleur jamais seule : voir `CortexStatusBadge`/`CortexRiskBadge`
  (icône + texte + couleur systématiquement).
- `prefers-reduced-motion: reduce` respecté globalement sous
  `.cortex-app`.
- Boutons icon-only : chaque composant qui en a doit porter
  `aria-label` — appliqué composant par composant, voir
  `docs/design-system-component-contracts.md`.

## Mode sombre

**Pas implémenté dans cette passe** (décision confirmée avec
l'utilisateur) — seul le mode clair est défini et documenté ci-dessus.
`cortex-theme.css` scope tout sous `.cortex-app` justement pour qu'un
futur bloc `:root[data-theme="dark"]` puisse être ajouté sans toucher
au clair existant ni au Desk Frappe natif. Ne pas ajouter de valeurs
sombres non testées visuellement (aucun bench pour les voir rendues) —
le spec met lui-même en garde contre un "faux dark mode".

## Conventions d'intégration

Toute page/composant Cortex doit :
1. Wrapper sa racine dans une classe `.cortex-app` (resets, focus ring
   et `prefers-reduced-motion` n'appliquent qu'à l'intérieur — ce dépôt
   ne doit jamais modifier le style du Desk Frappe hors de ses propres
   pages).
2. Consommer les tokens via `var(--cortex-*)`/`var(--state-*)`, jamais
   de couleur hex en dur dans un composant (exception : `stateMeta.js`
   n'a pas de couleurs, seulement des clés vers les tokens).
3. Importer les composants partagés depuis `public/js/cortex_shared/`
   plutôt que de dupliquer un badge/skeleton/empty-state ad-hoc.

## Branding Frappe

`hooks.py` : `app_logo_url`, `app_icon`, `app_color` (clés hooks.py
réelles, vérifiées contre `docs.frappe.io/framework/user/en/python-api/hooks`
avant utilisation). Logo : `public/images/cortex-logo.svg`, un
monogramme indigo placeholder — un vrai logo est une décision de marque
pour plus tard, pas inventée ici. Aucune modification du core Frappe :
tout passe par les hooks documentés de cette app.

## Composants livrés dans cette passe

Voir `docs/design-system-component-contracts.md` pour le contrat
détaillé de chacun (props, événements, accessibilité) :
`CortexStatusBadge`, `CortexRiskBadge`, `CortexReadinessIndicator`,
`CortexEmptyState`, `CortexPageHeader`, `CortexEvidenceLink`
(placeholder), `CortexAuditTimeline` (placeholder),
`CortexLoadingState`, `CortexErrorState`.

Composants spécifiques à un écran (`CortexAvailabilityCell`,
`CortexSerialAssignment`, `CortexApprovalCard`, etc.) **pas construits
ici** — ce sont des composants de page, pas de fondation ; ils
arriveront avec l'écran qui les utilise réellement.
