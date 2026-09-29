---
name: cortex-login
description: Build or modify the Cortex two-panel login / sign-up / forgot-password / verification pages (light + dark, responsive, accessible, French). Use when asked to create or restyle a login, an auth screen, or to apply a brand theme (for example the sage/olive token set) to the auth pages.
---

# Cortex login skill

The login is **server-rendered Frappe website pages** (Jinja + one CSS file + one JS file). The codebase has no React, no shadcn and no Tailwind on these pages, so the "two-panel auth" design (form on the left, brand panel with testimonial/statement on the right, Google/Apple-style social buttons) is **ported**, not installed. Do not add `react`, `motion`, `lucide-react` or `@paper-design/shaders-react` for it.

Everything lives in `apps/cortex_rental/cortex_rental/`.

**Two implementations, one design.** `/login` is the server-rendered Frappe page (below); `/cortex/login` and its siblings are Vue + frappe-ui screens in `public/frontend/src/features/auth` (`AuthShell.vue`, `auth.css`, `authApi.ts`, `LoginView`, `SendLinkView`, `RequestAccessView`), served by the standalone app (`npm run build:spa`). Apply every visual or copy change to both, and re-run axe on both.

## Files

| Concern | File |
| --- | --- |
| Login markup (overrides Frappe `www/login`) | `www/login.html`, `www/login.py` (delegates to `frappe.www.login.get_context`) |
| Password reset page | `www/update-password.html`, `www/update_password.py` |
| Email verification result page | `www/cortex-verify.html`, `www/cortex_verify.py` |
| Sign-up form fragment | `templates/includes/cortex_signup.html` |
| Footer "Powered by" removal | `templates/includes/footer/footer_powered.html` (empty override) |
| Emails | `templates/emails/*.html` |
| Styles (tokens + layout + adaptive rules) | `public/css/cortex-login.css` |
| Behaviour (inline errors, forgot flow, 2-step signup) | `public/js/cortex_login.js` |
| Font | `public/fonts/Inter.var.woff2` |
| Logos | `public/images/cortex-logo.svg`, `cortex-logo-reversed.svg` |

Keep every Frappe element id and class the stock login relies on (`#login_email`, `#login_password`, `.for-login`, `.for-forgot`, `.for-email-login`, `.btn-login`, `.btn-login-option`, `.social-logins`). Frappe's `login.js` binds to them.

## Design rules (validated with the product owner)

0. Composition: form width 480 px, block raised about 60 px above the geometric centre of the card, logo 12 px above the title, a 15 px lead under the title, back link `← Retour à la connexion` 20 px under the action, primary label `Se connecter`, reset/email-link action `Envoyer le lien`, social buttons `Continuer avec …` above the form, email field neutral until focused (no autofocus), brand panel with a decorative Sortie/Retour/Consignation illustration (no data).

1. **Same font pairing and framework as the app.** Inter (variable) + the Cortex tokens (`--accent #066336`, ink `#171717`, radius `.5rem`). Do not introduce another font family or a second colour system in the default theme.
2. **Light and dark.** Tokens are defined on `.cx-auth` and redefined under `@media (prefers-color-scheme: dark)`. Swap logos with `.app-logo--light` / `.app-logo--dark`. Social icons that are black (GitHub) are inverted in dark.
3. **Contrast (WCAG AA).** Use the dedicated `--muted-foreground`, `--link` and `--danger-text` tokens for text; never use the raw border or accent colour for small text. Re-run axe in both schemes after any colour change.
4. **Beat Frappe's CSS.** Scope everything under `body .cx-auth.cx-auth` and use `!important` only where Frappe's `login.bundle.css` wins on specificity.
5. **Adaptive 320 → 1920 px.** ≤640 px the card is full-bleed and the brand panel stacks below; ≤380 px choice grids become one column; short landscape screens drop vertical centering; ≥1600 px the layout is capped. Touch targets ≥44 px.
6. **UX.** One primary action per view, visible labels (not placeholders), inline errors next to the field with `role="alert"`, busy state on the button within 400 ms, progress ("Étape 1 sur 2") on the sign-up, work preserved when going back, explicit success/"check your inbox" end state, anti-enumeration wording for forgot password.
7. **Copy.** French (Québec), calm and factual. No invented testimonials, logos of customers or metrics: the brand panel carries a true statement plus three product facts.

## Applying a different brand theme (e.g. sage/olive)

The default is the Cortex identity. To apply another token set (for instance `--primary #7F956A`, `--accent #495940`, `--ring #AFBEA5`, radius `1.4rem`, Plus Jakarta Sans / Lora / IBM Plex Mono):

1. Map the incoming tokens to the variables at the top of `cortex-login.css` (`--accent`, `--accent-foreground`, `--ring`, `--border`, `--card`, `--muted`, `--radius`, …) in `:root`/`.cx-auth` and the dark block. Do not rewrite selectors.
2. Only change the font if the product owner explicitly asks for it **for the whole app**; otherwise keep Inter so auth and the app match. If changed, add the `@font-face`/Google Fonts import once and update the app's Tailwind/`cortex-erp.css` font tokens in the same change.
3. Verify contrast of the new `--accent` on white and of white on `--accent` (buttons). `#7F956A` on white is ~3.2:1 and fails AA for text; use it for fills/borders only, and a darker shade for links and small text.
4. Re-run the checks below.

## Adding a social provider

Social buttons are rendered by Frappe from **Social Login Key** records: a provider appears only when it is enabled and has a client id and secret. Add an icon rule under `.btn-login-option img` in the CSS if the provider's logo needs inversion in dark. Redirect URI: `/api/method/frappe.integrations.oauth2_logins.login_via_<provider>`. See `docs/auth/LOGIN_AND_ONBOARDING.md`.

## Verification checklist

- `PYTHONPATH=apps/cortex_rental:apps/cortex-mcp python3 -m pytest apps/cortex_rental` (static tests cover the templates, tokens and copy).
- On a bench: load `/login`, `/login#signup`, `/login#forgot`, `/cortex-verify`, `/update-password` in light and dark; run axe-core (0 serious/critical); take screenshots at 320, 375, 768, 1280, 1920 px and confirm no horizontal scroll (`document.documentElement.scrollWidth <= innerWidth`).
- Never leave test OAuth credentials enabled on a bench.
- Update `CHANGELOG.md` and `docs/auth/LOGIN_AND_ONBOARDING.md` when behaviour changes.
