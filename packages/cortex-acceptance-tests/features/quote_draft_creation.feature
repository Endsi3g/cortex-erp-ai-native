# language: fr
Fonctionnalité: Création de brouillon de soumission par un agent IA sans blocage d'inventaire
  En tant qu'agent Onyx Copilote
  Je veux créer une soumission (quote) à partir d'une demande client
  Afin de préparer le travail de l'opérateur sans impacter les stocks réels

  Scénario: Création réussie d'un devis indicatif
    Étant donné un client actif "Studio Nova" avec UUID "c3a6f140-5e82-4933-bc4e-d05ec2c6c0a1"
    Et que l'article "RED V-Raptor 8K" SKU "CAM-RED-001" est disponible du "2026-09-10" au "2026-09-15"
    Quand l'agent Onyx appelle l'outil "create_quote_draft" avec:
      | sku         | quantite | remise |
      | CAM-RED-001 | 1        | 0      |
    Alors la réponse indique un statut "draft_created"
    Et une transaction en statut "quote" est enregistrée dans PostgreSQL
    Et aucun verrou de calendrier n'est posé sur l'inventaire
    Et un événement est consigné dans "audit_events" avec l'acteur "agent_onyx"
