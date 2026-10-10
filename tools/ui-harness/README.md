# Banc d'essai de l'assistant (hors Desk)

**Ce que c'est :** les vrais composants Vue de `public/js/cortex_copilot/` montés dans Chromium avec un **faux `frappe`**
(`page.html`) et des blocs de réponse produits par les vrais constructeurs Python (`blocks.json`). **Ce que ce n'est pas :** le Desk de
Frappe. Ni la feuille de style du Desk, ni son mode sombre natif, ni vos données. Toute mention « vu à l'écran » qui vient d'ici doit
dire « dans le banc d'essai ».

```bash
cd tools/ui-harness && npm install          # esbuild, Vue, playwright-core (Chromium déjà installé : PLAYWRIGHT_BROWSERS_PATH)
node build.mjs                              # compile -> out/bundle.js et out/bundle.css
cp ../../apps/cortex_rental/cortex_rental/public/css/cortex-dark.css out/dark.css
node shot.mjs . ../../docs/review/captures/phase10-cartes   # captures + test des clics (approuver, ouvrir, erreur)
node dark.mjs . ../../docs/review/captures/phase10-cartes   # clair/sombre + audit de contraste (4,5:1)
```
Adapter `chromium-1194` dans `shot.mjs`/`dark.mjs` au dossier de `/opt/pw-browsers` si la version diffère.
Régénérer `blocks.json` après un changement de bloc : voir `apps/cortex_rental/cortex_rental/services/ai/actions.py::block_for` et `stats.py::card`.
`node_modules/` et `out/` ne se versionnent pas.
