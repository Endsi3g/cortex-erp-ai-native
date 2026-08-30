# ==============================================================================
# CORTEX ERP AI-NATIVE — ROOT MAKEFILE (Frappe / ERPNext / Python FastMCP)
# ==============================================================================

COMPOSE_DEV = docker compose -f infra/docker/docker-compose.dev.yml

.PHONY: help up down restart ps logs shell-bench shell-mcp test lint check-all env format

help: ## Afficher l'aide des commandes disponibles
	@echo "Cortex ERP AI-Native — Commandes du Monorepo :"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

env: ## Créer le fichier .env depuis .env.example si inexistant
	@if [ ! -f .env ]; then cp .env.example .env && echo "Fichier .env créé."; else echo "Le fichier .env existe déjà."; fi

up: env ## Démarrer l'ensemble de la pile Docker locale (MariaDB, Redis, MinIO, Frappe, FastMCP)
	$(COMPOSE_DEV) up -d

down: ## Arrêter et supprimer les conteneurs Docker locaux
	$(COMPOSE_DEV) down

restart: down up ## Redémarrer la pile Docker locale

ps: ## Lister l'état des conteneurs de la pile
	$(COMPOSE_DEV) ps

logs: ## Suivre les logs de tous les conteneurs
	$(COMPOSE_DEV) logs -f

logs-bench: ## Suivre les logs du conteneur Frappe Bench
	$(COMPOSE_DEV) logs -f bench

logs-mcp: ## Suivre les logs du conteneur FastMCP Python
	$(COMPOSE_DEV) logs -f mcp

shell-bench: ## Ouvrir un shell interactif dans le conteneur Frappe Bench
	$(COMPOSE_DEV) exec bench bash

shell-mcp: ## Ouvrir un shell interactif dans le conteneur FastMCP Python
	$(COMPOSE_DEV) exec mcp bash

test: ## Exécuter la suite de tests Python (pytest)
	pytest apps/

lint: ## Lancer le linter Python (Ruff)
	ruff check apps/
	ruff format --check apps/

format: ## Formater le code Python avec Ruff
	ruff format apps/
	ruff check --fix apps/

check-all: ## Exécuter le script de validation complète avant revue Claude
	./bin/pre-claude-check.sh
