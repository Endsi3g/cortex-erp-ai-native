# Design system complet — Accounting / Profit and Loss Statement

## 1. Direction artistique

**Produit :** dashboard SaaS de comptabilité et reporting financier.

**Style :** interface enterprise moderne, sobre, dense mais respirante, inspirée des dashboards financiers premium.

**Principes :**
- Hiérarchie visuelle immédiate.
- Données financières lisibles au premier regard.
- Contraste élevé entre contenu, contrôles et états.
- Rayons doux, surfaces gris très clair et accents colorés limités.
- Navigation latérale persistante.
- Design responsive sans perdre la densité de la vue desktop.

## 2. Tokens de couleur

### Couleurs principales

```css
:root {
  --color-brand-500: #1683dc;
  --color-brand-600: #0d72c7;
  --color-brand-700: #095da8;
  --color-brand-50: #eef7ff;

  --color-income: #e785b2;
  --color-expense: #3d8dcc;
  --color-profit: #52b57c;

  --color-text-950: #202124;
  --color-text-800: #34363a;
  --color-text-600: #6f7378;
  --color-text-500: #8b8f94;
  --color-text-400: #aeb2b6;

  --color-border: #e5e7e9;
  --color-border-strong: #d7dadd;
  --color-surface: #ffffff;
  --color-surface-subtle: #f7f8f9;
  --color-surface-muted: #f1f2f3;
  --color-canvas: #ffffff;

  --color-success-50: #edf9f2;
  --color-success-600: #25965a;
  --color-warning-50: #fff8e8;
  --color-warning-600: #b97900;
  --color-danger-50: #fff0f0;
  --color-danger-600: #c53a3a;
}
```

### Règles

- Le bleu est réservé à l’action, aux contrôles actifs et à la série Expense.
- Le rose représente Income.
- Le vert représente Net Profit/Loss et les résultats positifs.
- Le noir/gris foncé sert aux chiffres et intitulés importants.
- Ne jamais utiliser une couleur saturée comme fond principal de l’application.

## 3. Typographie

Police recommandée : **Inter**. Fallback : `ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.

```css
:root {
  --font-family-sans: Inter, ui-sans-serif, system-ui, sans-serif;
  --font-size-xs: 11px;
  --font-size-sm: 13px;
  --font-size-md: 14px;
  --font-size-lg: 16px;
  --font-size-xl: 20px;
  --font-size-2xl: 24px;
  --font-size-display: 28px;

  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  --line-height-tight: 1.2;
  --line-height-normal: 1.45;
  --line-height-relaxed: 1.6;
}
```

### Usage

| Élément | Taille | Poids | Couleur |
|---|---:|---:|---|
| Titre de page | 22–24 px | 700 | `--color-text-950` |
| Chiffre KPI | 26–28 px | 500 | `--color-text-950` |
| Chiffre KPI positif | 26–28 px | 600 | `--color-profit` |
| Label KPI | 14 px | 400 | `--color-text-600` |
| Nom de compte | 14 px | 500 | `--color-text-800` |
| En-tête tableau | 13 px | 500 | `--color-text-600` |
| Navigation | 14 px | 500 | `--color-text-600` |
| Helper / métadonnée | 12 px | 400 | `--color-text-500` |

## 4. Échelle d’espacement

Utiliser une base de 4 px :

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
```

### Spacing layout

- Barre supérieure : 16 px horizontal, 12 px vertical.
- Contenu principal : 24 px horizontal.
- Gouttière entre filtres : 16 px.
- Gouttière entre KPI : 24 px.
- Padding d’une carte : 24 px.
- Hauteur de ligne tableau : 36–40 px.
- Zone graphique : 32 px autour du tracé.

## 5. Rayons, bordures et ombres

```css
:root {
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-pill: 999px;

  --shadow-none: none;
  --shadow-subtle: 0 1px 2px rgba(20, 27, 35, .04);
  --shadow-card: 0 2px 8px rgba(20, 27, 35, .05);
  --shadow-popover: 0 8px 24px rgba(20, 27, 35, .12);
}
```

- Les champs ont un rayon de 8 px.
- Les cartes ont un rayon de 10–12 px.
- Les boutons d’icône ont un rayon de 8 px.
- La bordure standard est `1px solid var(--color-border)`.
- Éviter les ombres fortes : la séparation repose principalement sur les bordures et les fonds.

## 6. Structure de l’application

```text
AppShell
├── Sidebar 64 px
│   ├── Logo
│   ├── PrimaryNavigation
│   └── UtilityNavigation
├── Topbar 60 px
│   ├── SearchCommand
│   ├── Notifications
│   ├── HelpMenu
│   └── UserMenu
└── MainContent
    ├── PageHeader
    ├── ReportToolbar
    ├── KPIOverview
    ├── FinancialChart
    └── FinancialTable
```

### Dimensions desktop

- Largeur idéale : 1440–1600 px.
- Sidebar : 64 px.
- Topbar : 60 px.
- Padding du contenu : 24 px.
- Largeur maximale utile : aucune limite stricte, mais conserver une lecture centrée.

## 7. Sidebar

### Apparence

- Fond : `#ffffff`.
- Bordure droite : `#e5e7e9`.
- Largeur : 64 px.
- Logo bleu dans un carré de 28–30 px, rayon 6 px.
- Icônes monochromes gris moyen.
- Item actif : fond `--color-brand-50`, icône `--color-brand-500`.

### Navigation

Chaque item est un carré de 40 px centré :

```tsx
<SidebarItem
  icon={Icon}
  label="Accounting"
  active={section === "accounting"}
/>
```

États :
- Default : icône `#6f7378`.
- Hover : fond `#f4f6f8`.
- Active : fond `#eef7ff`, icône bleue.
- Focus : anneau `0 0 0 3px rgba(22,131,220,.18)`.

## 8. Topbar

- Hauteur : 60 px.
- Bordure basse : `--color-border`.
- Nom du module à gauche : 15–16 px, poids 500.
- Recherche large : 320–360 px, fond `#f6f7f8`, sans bordure visible au repos.
- Placeholder : gris moyen.
- Raccourci clavier affiché à droite dans une petite capsule.
- Notifications : bouton icône 36 px.
- Profil : avatar 28 px avec nom ou menu compact.

## 9. En-tête de page

```text
Accounting
Profit and Loss Statement
```

- Nom de section : 14 px, poids 500, gris foncé.
- Titre : 22–24 px, poids 700.
- Actions alignées à droite : bouton select `Financial Statements`, bouton `Actions`, bouton refresh, bouton more.
- Sur écran étroit, les actions passent sous le titre.

## 10. Contrôles de rapport

### Select / combobox

Dimensions : hauteur 36 px, rayon 8 px, padding horizontal 12 px.

```css
.report-control {
  height: 36px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: #f3f4f5;
  color: #34363a;
  padding: 0 12px;
}
.report-control:hover {
  background: #eceeef;
}
.report-control:focus-visible {
  outline: none;
  border-color: #1683dc;
  box-shadow: 0 0 0 3px rgba(22, 131, 220, .15);
}
```

### Grille de filtres

Desktop : 6 colonnes flexibles.

```text
Ligne 1 : Company | Finance Book | Fiscal Year | From Date | To Date | Periodicity
Ligne 2 : Currency | Cost Center | Branch | Project | Report View | Accumulated Values
```

Les champs non disponibles doivent rester visuellement désactivés sans paraître cassés : texte `#aeb2b6`, fond `#f1f2f3`.

### Checkbox

- Taille : 16 px.
- Coché : fond bleu foncé, coche blanche.
- Label : 14 px.
- Espacement label : 8 px.
- Alignement vertical strict avec les champs.

## 11. KPI overview

Présenter trois indicateurs sur une carte pleine largeur :

```text
Total Income              −              Total Expense              =              Net Profit
$ 10,00,000.00                         $ 6,20,000.00                         $ 3,80,000.00
```

### Règles

- Carte blanche, rayon 12 px.
- Séparateurs verticaux discrets ou opérateurs centrés dans des capsules.
- Labels centrés.
- Montants centrés et alignés sur une même ligne de base.
- Net Profit utilise la couleur verte.
- Afficher la devise selon la locale de l’espace de travail.
- Formatage recommandé : `Intl.NumberFormat` plutôt qu’un format manuel.

```ts
const currency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
});
```

## 12. Graphique financier

### Séries

- Income : rose `#e785b2`.
- Expense : bleu `#3d8dcc`.
- Net Profit/Loss : vert `#52b57c`.

### Style

- Graphique en lignes cumulatives.
- Épaisseur : 2 px.
- Points masqués au repos, visibles au hover.
- Grille horizontale très légère : `#f0f1f2`.
- Grille verticale presque invisible.
- Axe Y : 0, 250 K, 500 K, 750 K, 1 M.
- Axe X : périodes courtes, par exemple `Apr 24–Jun 24`.
- Tooltip blanc avec bordure et ombre légère.
- Légende en bas à gauche, indicateur carré de 12 px.

### Accessibilité du graphique

Ne jamais dépendre uniquement de la couleur : afficher le nom de la série dans le tooltip et fournir un tableau de données accessible ou un résumé textuel.

## 13. Tableau financier

### En-tête

- Fond : `#f7f8f9`.
- Hauteur : 44 px.
- Première colonne : largeur 320–360 px.
- Colonnes de périodes : largeur 160–180 px.
- Texte gris foncé, poids 500.

### Lignes

- Bordure basse très légère.
- Indentation progressive de 24 px par niveau.
- Ligne parent : poids 600.
- Ligne enfant : poids 400–500.
- Montants alignés à droite.
- Zéros : `0.00` avec couleur gris moyen.
- Valeurs négatives : rouge modéré ou parenthèses selon les préférences comptables.
- Hover : fond `#fafbfc`.

### Arbre de comptes

```tsx
<AccountRow
  depth={1}
  expandable
  expanded
  name="Income"
  values={[0, 0, 1000000, 1000000]}
/>
```

Le bouton d’expansion est une zone cliquable de 28 px, avec chevron animé à 90°.

## 14. Composants réutilisables

```text
Button
IconButton
Select
Combobox
DateRangePicker
Checkbox
Badge
Tooltip
DropdownMenu
CommandMenu
PageHeader
ReportToolbar
KpiCard
KpiSummary
ChartCard
Legend
FinancialTable
AccountRow
EmptyState
Skeleton
Toast
Modal
```

### Boutons

```css
.button-primary {
  height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  background: #1683dc;
  color: white;
  font-size: 14px;
  font-weight: 600;
}
.button-secondary {
  height: 36px;
  padding: 0 14px;
  border: 1px solid #dfe2e5;
  border-radius: 8px;
  background: white;
  color: #34363a;
}
.icon-button {
  width: 36px;
  height: 36px;
  display: inline-grid;
  place-items: center;
  border-radius: 8px;
  color: #6f7378;
}
```

## 15. États fonctionnels

### Loading

- Utiliser des skeletons gris pâle.
- Conserver la structure finale pour éviter les sauts de layout.
- Le graphique affiche une zone placeholder de 280 px minimum.

### Empty state

Message : `No financial data available for the selected period.`
Action secondaire : `Adjust filters`.

### Error

Afficher une alerte compacte en haut du contenu :

`Unable to load the report. Try again.`

Bouton : `Retry`.

### Success

Après export ou actualisation : toast vert discret, position haut droite.

## 16. Responsive design

### 1280 px et plus

- Sidebar complète.
- Deux lignes de contrôles.
- KPI sur trois colonnes.
- Tableau avec scroll horizontal si nécessaire.

### 768–1279 px

- Sidebar réduite aux icônes.
- Contrôles en grille de 3 colonnes.
- KPI toujours sur trois colonnes, chiffres réduits à 22 px.
- Actions secondaires dans un menu.

### Moins de 768 px

- Sidebar transformée en navigation drawer.
- Topbar avec menu, titre court et avatar.
- Contrôles en une colonne.
- KPI empilés verticalement.
- Graphique scrollable horizontalement ou simplifié.
- Tableau conservé dans un conteneur avec scroll horizontal.

## 17. Accessibilité

- Contraste minimum WCAG AA pour le texte normal.
- Tous les boutons d’icônes ont un `aria-label`.
- Focus clavier visible sur chaque contrôle.
- `th` et `scope="col"` pour les colonnes du tableau.
- `aria-expanded` sur les lignes expansibles.
- Ne pas utiliser le rose, bleu ou vert comme unique signal d’information.
- Respecter `prefers-reduced-motion` pour les transitions.

## 18. Motion

```css
--duration-fast: 120ms;
--duration-normal: 180ms;
--ease-standard: cubic-bezier(.2, .8, .2, 1);
```

- Hover : 120 ms.
- Ouverture de menu : 180 ms.
- Chevron : rotation 180 ms.
- Pas d’animation permanente dans le dashboard.

## 19. Architecture React recommandée

```text
app/
├── accounting/
│   ├── page.tsx
│   ├── loading.tsx
│   └── components/
│       ├── accounting-shell.tsx
│       ├── report-header.tsx
│       ├── report-filters.tsx
│       ├── report-kpis.tsx
│       ├── profit-loss-chart.tsx
│       ├── financial-table.tsx
│       └── account-row.tsx
components/
├── ui/
├── layout/
└── data-display/
lib/
├── formatters.ts
├── report-calculations.ts
└── accessibility.ts
```

## 20. Modèle de données

```ts
type ReportPeriod = {
  label: string;
  income: number;
  expense: number;
  profitLoss: number;
};

type AccountRow = {
  id: string;
  name: string;
  depth: number;
  type: "group" | "account";
  expandable?: boolean;
  children?: AccountRow[];
  values: Record<string, number>;
};

type ProfitLossReport = {
  company: string;
  financeBook: string;
  fiscalYear: string;
  periods: ReportPeriod[];
  accounts: AccountRow[];
  totalIncome: number;
  totalExpense: number;
  netProfit: number;
};
```

## 21. Données de référence visibles dans l’image

```ts
const sampleReport = {
  totalIncome: 1_000_000,
  totalExpense: 620_000,
  netProfit: 380_000,
  periods: [
    { label: "Apr 24–Jun 24", income: 0, expense: 0, profitLoss: 0 },
    { label: "Jul 24–Sep 24", income: 0, expense: 0, profitLoss: 0 },
    { label: "Oct 24–Dec 24", income: 1_000_000, expense: 620_000, profitLoss: 380_000 },
    { label: "Jan 25–Mar 25", income: 1_000_000, expense: 620_000, profitLoss: 380_000 },
  ],
};
```

## 22. Checklist de reproduction

- [x] Desk Page standard `/app/cortex-accounting-pnl` avec intégration Vue 3.
- [x] Titre `Profit and Loss Statement` avec sélecteur d'états financiers (P&L / BS / CF).
- [x] Menu Actions & Export (Export CSV direct, Impression / PDF `@media print`, lien Grand Livre).
- [x] Toolbar avec filtres complets, autocomplétion `<datalist>` et champs non supportés désactivés.
- [x] Checkbox `Include Default FB Entries` et `Accumulated Values`.
- [x] Carte KPI avec Total Income − Total Expense = Net Profit et formatage de devise standardisé (`formatCurrency`).
- [x] Graphique financier SVG responsive multi-séries (Income rose, Expense bleu, Net Profit vert) avec infobulle au survol.
- [x] Légende et tableau d'accessibilité sous le graphique.
- [x] Tableau hiérarchique avec comptes expansibles/repliables et drill-down vers le Grand Livre (`General Ledger`).
- [x] Formatage monétaire cohérent et alignement numérique strict (`tabular-nums`).
- [x] États interactifs : hover, focus, loading skeleton, empty state explicite et error banner avec réessai.
- [x] Responsive mobile avec empilement vertical et scroll horizontal fluide du tableau.
- [x] Respect du contraste, navigation clavier et `@media (prefers-reduced-motion: reduce)`.
- [x] Scoping multi-tenant strict et journal d'audit append-only (`cortex.accounting.profit_and_loss_viewed`).

## 23. Critère de qualité visuelle

L’interface doit donner l’impression d’un outil professionnel, calme et fiable. Le contenu financier est prioritaire : les chiffres doivent dominer visuellement, les contrôles doivent être immédiatement compréhensibles et les éléments décoratifs doivent rester presque invisibles.

