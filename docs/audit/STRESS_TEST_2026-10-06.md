# Stress test complet et code défensif — 2026-10-06

Environnement : site `cortex.local` (Frappe/ERPNext 15, MariaDB, Redis), 4 cœurs / 16 Go. La charge a été mesurée sur
**gunicorn à 4 processus × 2 fils** (configuration de production), jamais sur le serveur de développement. Les
limites de débit ont été relevées (×1000) pendant les essais pour ne pas fausser la mesure, puis remises à 1.

## 1. Résumé

| Essai | Résultat |
| --- | --- |
| Fuzz de **tous** les endpoints (112) avec 6 210 requêtes hostiles, 3 profils (propriétaire, lecteur, invité) | **353 erreurs serveur 5xx (23 causes) → 0** après corrections |
| Courses de concurrence (HTTP réel, 12 comptoirs) : dernière unité, retenues de devis, 8 décisions d'approbation, 6 envois à clé d'idempotence | **4/4 corrects** (1 seule réservation, 1 seule retenue active, 1 seule décision, 1 seule location) |
| Isolation entre sociétés (101 contrôles par API Cortex, API de ressources, rapports, recherche, modification) | **Aucune fuite**, contrôle positif réussi |
| Charge mixte, 40 utilisateurs simultanés sans temps de réflexion, 60 s | **65,8 req/s, 0 échec**, p50 540 ms, p95 1,23 s |
| Simulation de 91 jours (589 locations, 345 factures, 630 écritures) | **0 violation d'intégrité**, grand livre équilibré à l'écart 0,00 $ |
| Force brute sur la connexion | Verrouillage après 5 échecs, **429 + `Retry-After`** (était 500) |
| Fichiers déguisés (SVG/HTML nommé `.png`) pour le logo et la photo | Refusés (vrais octets vérifiés) |
| Sauvegarde puis restauration dans un site neuf (`infra/production/backup.sh`) | Sommes de contrôle valides, 592 locations restaurées sur 592 |
| Textes de 100 000 caractères envoyés partout | Aucune colonne > 5 000 caractères en base |

## 2. Fuzz : 23 causes d'erreur 500 trouvées et corrigées

`dev_tools/fuzz_endpoints.py` lit la liste des `@frappe.whitelist` dans le code et envoie à chacun : chaîne vide, texte de
100 000 caractères, injection SQL, XSS, traversée de chemin, octet nul, Unicode bidirectionnel, gabarits (`{{7*7}}`,
`${jndi:…}`), nombres extrêmes (`1e308`, `NaN`, `-0`, 40 chiffres), JSON cassé, objets imbriqués, opérateurs Mongo.

| Famille | Cause | Correction |
| --- | --- | --- |
| 11 listes (`history`, `list_approval_requests`, `list_customers`…) | page/limite géante ou vide → erreur SQL ou `int('')` | `to_int`/`page_args` bornés (page ≤ 100 000) |
| `update_notifications`, `update_preferences` | JSON vide ou non-objet → `JSONDecodeError`/`TypeError` | `defense.json_object` |
| `preview_pricing`, `create_quote_draft`, `get_matrix`, `get_profit_and_loss`, `submit_checkin`, `complete_checkin_api`, `register_evidence_api` | champ obligatoire absent → `ValueError`/`TypeError` en 500 | `@defense.safe_input` : toute valeur invalide = **417** clair en français |
| `create_quote_draft` | dates absentes, **fin avant début facturée 1 jour en silence**, période de 10 000 ans, lignes non valides | `compute_billable_days` refuse ces cas; `clean_lines` valide quantités, tarifs, rabais, 200 lignes max |
| `create_customer_draft` | nom absent → `AttributeError` dans ERPNext | nom obligatoire |
| `search_rental_customers` | **colonne `custom_insurance_valid_until` absente du site → erreur SQL à chaque recherche de client du compositeur de devis** | lecture conditionnelle de la colonne (vrai défaut fonctionnel) |
| `update_profile` (+ étape propriétaire de l'assistant) | deux comptes avec le même mobile → `IntegrityError` | message clair « numéro déjà utilisé »; fuseau horaire validé |

Après correction : **0 erreur 5xx sur 6 210 requêtes**, aucune requête lente (> 3 s). Les 1 261 réponses 200 du profil
propriétaire sont des entrées acceptées légitimement; les 429 sont les freins de débit en action.

## 3. Courses de concurrence (HTTP réel sur gunicorn)

| Scénario | Attendu | Observé |
| --- | --- | --- |
| 12 comptoirs réservent la seule unité d'un article | exactement 1 | 1 réservation, 11 refus 417, 0 erreur |
| 12 devis simultanés pour la même unité | 1 retenue active | 1 active, 11 « stock insuffisant » |
| 8 décisions simultanées sur une approbation | 1 décision | 1×200, 7×417, statut Approuvé, 1 événement d'audit |
| 6 envois avec la même clé d'idempotence | 1 location | 1 location |

## 4. Charge (gunicorn 4×2, 40 utilisateurs sans temps de réflexion)

| | Avant optimisation | Après |
| --- | --- | --- |
| Débit | 57,3 req/s | **65,8 req/s** |
| p50 / p95 / max | 607 / 1 427 / 4 534 ms | **540 / 1 227 / 3 485 ms** |
| Échecs | 0 | 0 |
| Liste de 20 locations (lecture seule) | 175 ms | **115 ms** (lectures mémorisées) |

Un vrai utilisateur laisse plusieurs secondes entre deux actions : 65 req/s correspondent à plusieurs centaines
d'utilisateurs réels. Lectures isolées (p50) : grille de disponibilité 21 ms, file d'approbations 19 ms, démarrage de
session 22 ms, espaces de travail 38–51 ms, rapports 53–203 ms. Point chaud restant : la liste filtrée par état (275 ms).

## 5. Intégrité (simulation de 91 jours)

589 locations, 591 devis, 250 réservations, 206 contrats approuvés, 164 sorties, 143 retours, 98 clôtures, 22 retours en
retard, 4 litiges. **Zéro** : total à 0 $, surréservation, sortie sans scan, retour supérieur à la quantité, solde ou
taxes incohérents, facture sans écriture. Grand livre : 630 écritures équilibrées, écart clients/encaisse/taxes 0,00 $.
Les « erreurs » listées par la simulation (241 réservations refusées faute de disponibilité, 33 contrats sans dépôt…)
sont les refus métier attendus.

## 6. Code défensif ajouté

- `services/defense.py` : vérification des vrais octets d'image, frein global (900 req/min par personne, 120 par IP
  invitée), limites par action sensible, 429 + `Retry-After` sur verrouillage de compte, en-têtes de sécurité.
- `@defense.safe_input` sur les 112 endpoints (valeur invalide → 417 clair); `defense.json_object`; pagination bornée.
- Limites de débit sur tous les appels publics (aucun appel invité sans limite — vérifié par test); webhook Stripe plafonné à 1 Mo.
- Contrat statique testé (`tests/test_defense.py`) : chaque endpoint déclare ses méthodes HTTP, les écritures sont en
  POST seulement, la liste des appels publics est exactement la liste autorisée, chaque appel externe a un délai d'attente,
  aucun secret en dur.
- Santé réelle (`health.health`, `health.ready`) et contrôle de mise en production (`ops/predeploy.py`).
- Politique de connexion : 5 échecs puis verrouillage de 5 minutes (patch `harden_login_policy`, ne remplace jamais un
  réglage déjà choisi).

## 7. Limites et ce qui n'a pas été testé

- Une seule machine de 4 cœurs; MariaDB et l'application sur le même hôte. Pas d'essai multi-serveurs.
- Gemini, Stripe et le courriel n'ont pas été éprouvés avec de vrais comptes (aucune clé fournie).
- Pas de test d'intrusion indépendant ni d'analyse par un outil dédié (ZAP, etc.); le fuzz est maison et ne couvre pas les
  routes natives de Frappe (désk, `frappe.client`), seulement `cortex_rental.api.v1.*` et l'isolation sur les voies natives.
- La charge n'inclut pas les écritures en masse (import de milliers de lignes) ni les fichiers lourds.
- Le serveur de sockets (présence en direct) n'a pas été éprouvé sous charge.
- Frappe répond encore en anglais au message de verrouillage pour un appel sans cookie de langue (l'interface web, elle,
  affiche le français).

## 8. Rejouer les essais

```bash
bench --site cortex.local execute cortex_rental.dev_tools.simulate_company.run --kwargs '{"days": 90, "reset": 1}'
bench --site cortex.local execute cortex_rental.dev_tools.fuzz_endpoints.prepare
bench --site cortex.local set-config cortex_rate_limit_factor 1000          # pour les essais seulement
python3 apps/cortex_rental/cortex_rental/dev_tools/fuzz_endpoints.py http://localhost:8000
python3 apps/cortex_rental/cortex_rental/dev_tools/isolation_http.py http://localhost:8000
CORTEX_BASE=http://localhost:8001 CORTEX_LOAD_USERS=40 bench --site cortex.local execute cortex_rental.dev_tools.charge_et_concurrence.run
bench --site cortex.local execute cortex_rental.dev_tools.controle_longueurs.run
bench --site cortex.local set-config cortex_rate_limit_factor 1                # remettre
```
