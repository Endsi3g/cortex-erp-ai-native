# Politique de sécurité — Cortex ERP

Cortex est construit sur Frappe / ERPNext v15 (application `cortex_rental`, base MariaDB). La sécurité des données transactionnelles et l'étanchéité entre sociétés sont au cœur de sa conception.

## Principes et garde-fous

1. **Isolation entre sociétés** : aucune personne ni aucun agent ne peut lire ou modifier les données d'une autre société. Chaque API vérifie la société de la personne connectée ; des tests de charge, de concurrence et d'abus le vérifient (`docs/audit/STRESS_TEST_2026-10-06.md`).
2. **Droits et supervision humaine** : les actions à impact financier (confirmation d'un contrat, paiement, versement de consignation) passent par une demande d'approbation décidée par une personne autorisée. Un agent ne peut jamais approuver ; une personne ne décide pas de sa propre demande (auto-approbation du seul approbateur désactivée par défaut, activable avec avertissement et audit).
3. **Assistant IA** : ses outils lisent et proposent sous les droits de la personne connectée ; il n'écrit, n'approuve ni ne confirme rien. Les clés des fournisseurs de modèles sont chiffrées côté serveur et n'atteignent jamais le navigateur. Le budget mensuel par société limite l'usage.
4. **Audit immuable** : les évènements d'audit et les messages de conversation ne se modifient ni ne se suppriment (retirer une conversation de son historique la masque seulement).
5. **Défense en profondeur** : validation des entrées, frein de débit par utilisateur, vérification du contenu réel des images, limites de longueur, erreurs sûres, en-têtes de sécurité, verrouillage de compte, appels sans compte limités à une liste fermée et protégés par adresse ou par signature (`apps/cortex_rental/cortex_rental/services/defense.py`).
6. **Avant la mise en production** : `bench --site <site> execute cortex_rental.ops.predeploy.run` doit réussir (mode développeur éteint, mot de passe `Administrator` changé, comptes de démonstration désactivés, correctifs appliqués). Les outils de `dev_tools/` ne sont jamais exécutés en production. Voir [`docs/ops/DEPLOIEMENT.md`](docs/ops/DEPLOIEMENT.md).

## Signaler une vulnérabilité

Si vous découvrez une faille de sécurité dans Cortex :

1. **Ne créez pas d'issue publique sur GitHub.**
2. Envoyez un rapport détaillé par courriel à **security@cortexerp.com**.
3. Incluez la description, les étapes pour reproduire la faille et l'impact potentiel (isolation entre sociétés, audit, approbations, données de clients).

Nous accusons réception sous 24 heures ouvrables et publions un correctif dans les meilleurs délais.
