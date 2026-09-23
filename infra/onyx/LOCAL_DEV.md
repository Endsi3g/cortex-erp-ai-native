# Onyx + Ollama local development

The machine currently has the official Onyx repository at `C:\Users\Kael2\Cortex\onyx` and its separate Lite deployment at `C:\Users\Kael2\Cortex\onyx-local`. The deployment is self-hosted; its database and volumes are not part of the Cortex repository.

## Verified on this machine

- Official Onyx Windows installer ran with Lite mode; Onyx services return HTTP 200 at `http://localhost:3000`.
- `qwen3:8b` is installed, answers a real Ollama generation request, and reports completion, tools, and thinking support. Its Q4_K_M weights are 5.2 GB with a 40K advertised context.
- The Onyx API container can read Ollama's `/api/tags` through `host.docker.internal:11434`.
- The Cortex Frappe container reaches the Onyx nginx service at `http://nginx` over the private `cortex_ai_private` network. The host UI is bound to loopback at `http://localhost:3000`.
- Docker Desktop reports about 15.6 GiB available to containers. Onyx Lite is the chosen local deployment; it omits vector search/indexing and connectors.
- Onyx local administrator sign-in has been verified (`cortex-admin@example.com`); its password is stored only in the Windows DPAPI-protected file `%LOCALAPPDATA%\Cortex\onyx-admin-password.dpapi`. The secret is machine-specific and must never be copied into this repository.
- The Onyx API key is configured only in the Frappe site's server-side configuration. Cortex uses `onyx_base_url=http://nginx`, `onyx_model_name=qwen3:8b`, and `cortex_chat_provider=onyx`; do not print or commit the key.
- Onyx authentication (`/api/me`), the Ollama model endpoint, and the container network path have been checked independently. A full browser-to-Cortex-to-Onyx chat and tool-execution flow still needs end-to-end validation before it is described as production-ready.

## Keep the local UI private and share a backend-only Docker network

The upstream Compose file publishes ports on every host interface by default. This local setup replaces those ports with loopback-only publishing, then connects the Cortex API and MCP service to Onyx through an external bridge network.

In PowerShell:

```powershell
docker network create cortex_ai_private
Copy-Item C:\Users\Kael2\Cortex\cortex-erp-ai-native\infra\onyx\docker-compose.override.yml C:\Users\Kael2\Cortex\onyx-local\deployment\docker-compose.override.yml
Set-Location C:\Users\Kael2\Cortex\onyx-local\deployment
docker compose -f docker-compose.yml -f docker-compose.onyx-lite.yml -f docker-compose.override.yml up -d
Set-Location C:\Users\Kael2\Cortex\cortex-erp-ai-native
docker compose -f infra/docker/docker-compose.dev.yml -f infra/docker/docker-compose.ai.yml up -d bench mcp
```

The Compose service name `nginx` becomes the private Onyx API address seen by Cortex (`http://nginx`). The Onyx web interface remains `http://localhost:3000` on this host. Ollama stays on the Windows host and Onyx reaches it at `http://host.docker.internal:11434`.

## Initial setup for a new Onyx deployment

1. Open `http://localhost:3000/auth/signup` and create the local administrator account. The first registered Onyx account is the administrator.
2. In the user profile → **Settings → API Keys**, create a dedicated key for Cortex chat, choose the minimum available permissions, and copy the value once. Never commit it or put it in a `VITE_*` variable.
3. In **Admin Panel → Configuration → Language Models**, add an Ollama provider. Use the server URL `http://host.docker.internal:11434`, fetch the model list, enable `qwen3:8b`, and make it available to the Cortex user/group. Start with a 16K context limit; increase to 32K only after checking memory use with the full Docker stack running.
4. Store the key in the target Frappe site's server-only config. The local site is `cortex.local`, and the private-network URL is `http://nginx` from `cortex_bench_dev`. Enter the key at the prompt so it does not end up in shell history:

   ```powershell
   $onyxKey = Read-Host "Onyx API key"
   docker exec cortex_bench_dev bench --site cortex.local set-config onyx_base_url http://nginx
   docker exec cortex_bench_dev bench --site cortex.local set-config onyx_api_key $onyxKey
   Remove-Variable onyxKey
   docker exec cortex_bench_dev bench --site cortex.local set-config onyx_model_name qwen3:8b
   docker exec cortex_bench_dev bench --site cortex.local set-config cortex_chat_provider onyx
   ```

5. Restart/reload the Frappe application and send a message from AI Workspace. The Cortex gateway stores the Onyx session ID on the Frappe chat session; Onyx tool IDs are sent only when explicitly mapped by Cortex server configuration. Unmapped tools remain disabled.

Do not invent numeric Onyx persona/action IDs. The chat gateway defaults to Onyx's default persona (`0`) with an empty action list. Add server-side `onyx_persona_ids` and `onyx_tool_id_map` only after matching the IDs in the deployed Onyx admin UI to Cortex's `ToolPolicyResolver` allowlist. This makes initial local chat work while keeping unverified tool execution closed.

## Service checks and lifecycle

```powershell
docker compose -f C:\Users\Kael2\Cortex\onyx-local\deployment\docker-compose.yml -f C:\Users\Kael2\Cortex\onyx-local\deployment\docker-compose.onyx-lite.yml -f C:\Users\Kael2\Cortex\onyx-local\deployment\docker-compose.override.yml ps
docker exec onyx-api_server-1 python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags', timeout=5).status)"
docker exec cortex_bench_dev python -c "import urllib.request; print(urllib.request.urlopen('http://nginx', timeout=5).status)"
```

Stop Onyx while preserving its local database and chats:

```powershell
Set-Location C:\Users\Kael2\Cortex\onyx-local\deployment
docker compose -f docker-compose.yml -f docker-compose.onyx-lite.yml -f docker-compose.override.yml stop
```

The Onyx Lite deployment supports chat, tools, uploads, Projects, and agent knowledge; connectors and corpus search/indexing are intentionally unavailable in Lite. Use the full self-hosted deployment if those capabilities become a requirement and allocate the additional Docker resources first.
