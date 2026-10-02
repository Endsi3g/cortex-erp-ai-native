"""Fournisseurs de modèles. Changer de modèle = changer le champ « Modèle » des réglages de l'IA ; changer de
fournisseur = ajouter une classe ici. Le reste de la passerelle ne connaît que l'interface `LLMProvider`.

Le préfixe de l'identifiant choisit le fournisseur (`gemini-…` → Google). Aucun identifiant de modèle n'est codé en dur
ailleurs que dans les réglages.
"""

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class AIConfigurationError(RuntimeError):
    """L'IA n'est pas (ou mal) configurée : clé manquante, modèle inconnu."""


class AIProviderError(RuntimeError):
    """Le fournisseur a refusé ou n'a pas répondu ; le message est sûr à afficher."""

    def __init__(self, message: str, status: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]
    id: str = ""


@dataclass
class ProviderResult:
    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = None  # message natif du fournisseur, à renvoyer tel quel au tour suivant


class LLMProvider(ABC):
    name = "abstract"

    def __init__(
        self, model: str, api_key: str, timeout: int = 60, temperature: float = 0.2, max_output_tokens: int = 1024
    ):
        self.model = model
        self.api_key = api_key
        self.timeout = max(10, min(int(timeout or 60), 180))
        self.temperature = temperature
        self.max_output_tokens = int(max_output_tokens or 1024)

    # messages natifs
    @abstractmethod
    def user_message(self, text: str) -> Any: ...

    @abstractmethod
    def assistant_message(self, result: ProviderResult) -> Any: ...

    @abstractmethod
    def tool_results_message(self, results: List[Dict[str, Any]]) -> Any: ...

    @abstractmethod
    def history_message(self, role: str, text: str) -> Any: ...

    @abstractmethod
    def generate(self, system: str, messages: List[Any], tools: List[Dict[str, Any]]) -> ProviderResult: ...


class GeminiProvider(LLMProvider):
    """Google Gemini (API « generateContent » avec appel de fonctions)."""

    name = "Google Gemini"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def user_message(self, text: str) -> Any:
        return {"role": "user", "parts": [{"text": text}]}

    def history_message(self, role: str, text: str) -> Any:
        return {"role": "user" if role == "user" else "model", "parts": [{"text": text}]}

    def assistant_message(self, result: ProviderResult) -> Any:
        # On renvoie le message tel que reçu : les modèles récents y joignent des signatures à conserver entre les tours.
        if result.raw:
            return result.raw
        parts: List[Dict[str, Any]] = []
        if result.text:
            parts.append({"text": result.text})
        for call in result.tool_calls:
            parts.append({"functionCall": {"name": call.name, "args": call.args}})
        return {"role": "model", "parts": parts}

    def tool_results_message(self, results: List[Dict[str, Any]]) -> Any:
        return {
            "role": "user",
            "parts": [{"functionResponse": {"name": r["name"], "response": {"result": r["result"]}}} for r in results],
        }

    def _declarations(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in tools]

    def request_body(self, system: str, messages: List[Any], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": messages,
            "generationConfig": {"temperature": self.temperature, "maxOutputTokens": self.max_output_tokens},
        }
        if tools:
            body["tools"] = [{"functionDeclarations": self._declarations(tools)}]
        return body

    def parse(self, payload: Dict[str, Any]) -> ProviderResult:
        candidates = payload.get("candidates") or []
        if not candidates:
            reason = (payload.get("promptFeedback") or {}).get("blockReason")
            raise AIProviderError("Le modèle n'a pas pu répondre à cette demande." + (f" ({reason})" if reason else ""))
        content = candidates[0].get("content") or {}
        text_parts, calls = [], []
        for index, part in enumerate(content.get("parts") or []):
            if part.get("text") and not part.get("thought"):
                text_parts.append(part["text"])
            call = part.get("functionCall")
            if call:
                calls.append(ToolCall(name=call.get("name", ""), args=call.get("args") or {}, id=str(index)))
        usage = payload.get("usageMetadata") or {}
        return ProviderResult(
            text="".join(text_parts).strip(),
            tool_calls=calls,
            input_tokens=int(usage.get("promptTokenCount") or 0),
            output_tokens=int(usage.get("candidatesTokenCount") or 0) + int(usage.get("thoughtsTokenCount") or 0),
            raw=content or None,
        )

    def generate(self, system: str, messages: List[Any], tools: List[Dict[str, Any]]) -> ProviderResult:
        if not self.api_key:
            raise AIConfigurationError("Aucune clé API n'est configurée pour le fournisseur d'IA.")
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"
        data = json.dumps(self.request_body(system, messages, tools), ensure_ascii=False).encode("utf-8")
        last: Optional[Exception] = None
        for attempt in range(2):
            request = urllib.request.Request(
                url,
                data=data,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return self.parse(json.loads(response.read().decode("utf-8")))
            except urllib.error.HTTPError as exc:
                last = self._http_error(exc)
                if not (isinstance(last, AIProviderError) and last.retryable) or attempt:
                    raise last from exc
                time.sleep(1.0)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last = AIProviderError(
                    "Le service d'IA n'a pas répondu à temps. Réessayez dans un instant.", retryable=True
                )
                if attempt:
                    raise last from exc
                time.sleep(1.0)
        raise last or AIProviderError("Le service d'IA est indisponible.")

    @staticmethod
    def _http_error(exc: urllib.error.HTTPError) -> Exception:
        if exc.code in (401, 403):
            return AIConfigurationError(
                "La clé API du fournisseur d'IA est refusée. Un administrateur doit la vérifier."
            )
        if exc.code == 404:
            return AIProviderError("Ce modèle d'IA n'est pas disponible chez le fournisseur.", status=404)
        if exc.code == 429:
            return AIProviderError(
                "Le service d'IA est très sollicité. Réessayez dans un instant.", status=429, retryable=True
            )
        if exc.code >= 500:
            return AIProviderError("Le service d'IA est momentanément indisponible.", status=exc.code, retryable=True)
        return AIProviderError(f"Le service d'IA a refusé la demande (erreur {exc.code}).", status=exc.code)


class ScriptedProvider(LLMProvider):
    """Fournisseur de test : rejoue des réponses prévues, sans réseau. Sert aux tests et au mode développement."""

    name = "Simulation"

    def __init__(self, script: List[ProviderResult], **kwargs):
        super().__init__(model=kwargs.pop("model", "scripted"), api_key="-", **kwargs)
        self.script = list(script)
        self.calls: List[Dict[str, Any]] = []

    def user_message(self, text):
        return {"role": "user", "text": text}

    def history_message(self, role, text):
        return {"role": role, "text": text}

    def assistant_message(self, result):
        return {"role": "assistant", "text": result.text, "calls": [(c.name, c.args) for c in result.tool_calls]}

    def tool_results_message(self, results):
        return {"role": "tool", "results": results}

    def generate(self, system, messages, tools):
        self.calls.append({"system": system, "messages": list(messages), "tools": [t["name"] for t in tools]})
        if not self.script:
            raise AIProviderError("Plus de réponse prévue.")
        return self.script.pop(0)


def provider_for(model: str, api_key: str, **options) -> LLMProvider:
    """Choisit le fournisseur d'après l'identifiant du modèle."""
    lowered = (model or "").strip().lower()
    if lowered.startswith("gemini"):
        return GeminiProvider(model.strip(), api_key, **options)
    raise AIConfigurationError(f"Modèle d'IA non pris en charge : « {model} ». Utilisez un identifiant « gemini-… ».")
