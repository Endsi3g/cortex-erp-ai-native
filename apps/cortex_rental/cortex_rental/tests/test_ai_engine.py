"""Phase A: Anthropic streaming parser, the tool loop, proposals and tool gating."""

import json

import pytest

from cortex_rental.services.ai import engine
from cortex_rental.services.ai.anthropic_provider import AnthropicError, AnthropicProvider, ModelTurn
from cortex_rental.services.ai.tools import TOOLS, Tool, ToolContext, tools_for


def sse(*events):
    return [f"data: {json.dumps(e)}\n".encode() for e in events]


# ---- provider -----------------------------------------------------------------------


def test_stream_turn_assembles_text_and_tool_use_and_streams_deltas():
    seen = {}

    def transport(body, headers):
        seen["body"], seen["headers"] = body, headers
        return sse(
            {"type": "message_start", "message": {"usage": {"input_tokens": 42}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Je vérifie "}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "la dispo."}},
            {"type": "content_block_stop", "index": 0},
            {
                "type": "content_block_start",
                "index": 1,
                "content_block": {"type": "tool_use", "id": "tu_1", "name": "search_equipment"},
            },
            {
                "type": "content_block_delta",
                "index": 1,
                "delta": {"type": "input_json_delta", "partial_json": '{"query": "Alex'},
            },
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": 'a"}'}},
            {"type": "content_block_stop", "index": 1},
            {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 17}},
        )

    chunks = []
    turn = AnthropicProvider("sk-test", "claude-sonnet-5", transport).stream_turn(
        "sys", [{"role": "user", "content": "x"}], [{"name": "t"}], chunks.append
    )
    assert chunks == ["Je vérifie ", "la dispo."]
    assert turn.text == "Je vérifie la dispo."
    assert turn.tool_uses == [
        {"type": "tool_use", "id": "tu_1", "name": "search_equipment", "input": {"query": "Alexa"}}
    ]
    assert (turn.stop_reason, turn.input_tokens, turn.output_tokens) == ("tool_use", 42, 17)
    assert seen["body"]["stream"] is True and seen["body"]["model"] == "claude-sonnet-5"
    assert seen["headers"]["x-api-key"] == "sk-test" and seen["headers"]["anthropic-version"] == "2023-06-01"


def test_stream_turn_raises_on_error_event_and_requires_a_key():
    provider = AnthropicProvider("k", transport=lambda b, h: sse({"type": "error", "error": {"message": "overloaded"}}))
    with pytest.raises(AnthropicError, match="overloaded"):
        provider.stream_turn("s", [], [])
    with pytest.raises(AnthropicError):
        AnthropicProvider("")


# ---- engine loop ----------------------------------------------------------------------


class ScriptedProvider:
    """Returns pre-baked turns; records what the engine sent."""

    def __init__(self, *turns):
        self.turns = list(turns)
        self.calls = []

    def stream_turn(self, system, messages, tools, on_text=None):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": [t["name"] for t in tools]})
        turn = self.turns.pop(0)
        if on_text and turn.text:
            on_text(turn.text)
        return turn


def tool_turn(*uses, text=""):
    content = ([{"type": "text", "text": text}] if text else []) + [
        {"type": "tool_use", "id": f"tu_{i}", "name": name, "input": args} for i, (name, args) in enumerate(uses)
    ]
    return ModelTurn(content=content, stop_reason="tool_use")


def final(text):
    return ModelTurn(content=[{"type": "text", "text": text}], stop_reason="end_turn")


def run(provider, roles=None, monkeypatch=None):
    events, proposals, calls = [], [], []

    def record_proposal(tool, args, preview):
        proposals.append((tool.name, args))
        return f"ACT-{len(proposals)}"

    result = engine.run_turn(
        provider,
        "sys",
        [],
        "Bonjour",
        ToolContext(user="u@x.test", company="Demo", roles=set(roles or ["Rental Operator"])),
        lambda kind, payload: events.append((kind, payload)),
        record_proposal,
        lambda name, status, ms, err: calls.append((name, status)),
        clock=lambda: 0.0,
    )
    return result, events, proposals, calls


def test_read_tool_runs_and_its_result_goes_back_to_the_model(monkeypatch):
    fake = Tool(
        "search_equipment",
        "d",
        {"type": "object", "properties": {}, "required": ["query"]},
        "read",
        lambda args, ctx: {"data": [{"item_code": "ALEXA", "q": args["query"]}], "view": {"type": "table"}},
    )
    monkeypatch.setitem(TOOLS, "search_equipment", fake)
    provider = ScriptedProvider(
        tool_turn(("search_equipment", {"query": "alexa"}), text="Je cherche."), final("Trouvé : ALEXA.")
    )
    result, events, proposals, calls = run(provider)

    assert [b["type"] for b in result.blocks] == ["assistant_text", "widget", "assistant_text"]
    assert result.blocks[1]["data"] == [{"item_code": "ALEXA", "q": "alexa"}]
    tool_result = provider.calls[1]["messages"][-1]["content"][0]
    assert (
        tool_result["tool_use_id"] == "tu_0" and tool_result["is_error"] is False and "ALEXA" in tool_result["content"]
    )
    assert calls == [("search_equipment", "Success")]
    assert ("text", {"delta": "Je cherche."}) in events and proposals == []


def test_write_tool_is_only_proposed_never_executed(monkeypatch):
    executed = []
    monkeypatch.setitem(
        TOOLS,
        "cancel_rental",
        Tool(
            "cancel_rental",
            "d",
            {"type": "object", "properties": {}, "required": ["rental", "reason"]},
            "write",
            handler=lambda a, c: executed.append(a),
            describe=lambda a: {"title": "Annuler", "impact": [], "effect": "x"},
        ),
    )
    provider = ScriptedProvider(
        tool_turn(("cancel_rental", {"rental": "TRX-1", "reason": "client"})), final("Je propose l’annulation.")
    )
    result, events, proposals, _ = run(provider)

    assert executed == []
    assert proposals == [("cancel_rental", {"rental": "TRX-1", "reason": "client"})]
    proposal = next(b for b in result.blocks if b["type"] == "action_proposal")
    assert proposal["action_id"] == "ACT-1" and proposal["status"] == "proposed"
    assert "ne dis pas qu’elle est faite" in provider.calls[1]["messages"][-1]["content"][0]["content"]


def test_errors_unknown_tools_and_missing_arguments_are_reported_to_the_model(monkeypatch):
    def boom(args, ctx):
        raise PermissionError("Votre rôle ne permet pas de consulter les finances.")

    monkeypatch.setitem(
        TOOLS, "list_invoices", Tool("list_invoices", "d", {"type": "object", "properties": {}}, "read", boom)
    )
    provider = ScriptedProvider(
        tool_turn(("list_invoices", {}), ("delete_everything", {}), ("get_rental", {})),
        final("Je n’ai pas accès."),
    )
    result, _events, _p, calls = run(provider, roles=["System Manager"])
    results = provider.calls[1]["messages"][-1]["content"]
    assert all(r["is_error"] for r in results)
    assert (
        "rôle" in results[0]["content"]
        and "indisponible" in results[1]["content"]
        and "rental" in results[2]["content"]
    )
    assert calls == [("list_invoices", "Error"), ("delete_everything", "Error"), ("get_rental", "Error")]
    assert sum(1 for b in result.blocks if b["type"] == "tool_progress") == 3


def test_finance_tools_are_not_offered_to_counter_staff():
    names = {t.name for t in tools_for({"Cortex Counter Staff"})}
    assert "profit_and_loss" not in names and "record_advance_payment" not in names
    assert "check_availability" in names and "create_quote" in names
    assert "profit_and_loss" in {t.name for t in tools_for({"Cortex Finance Manager"})}


def test_loop_stops_after_max_rounds(monkeypatch):
    monkeypatch.setitem(
        TOOLS,
        "open_page",
        Tool(
            "open_page",
            "d",
            {"type": "object", "properties": {}},
            "ui",
            lambda a, c: {"data": {}, "view": {"route": "/x", "label": "X"}},
        ),
    )
    provider = ScriptedProvider(*[tool_turn(("open_page", {})) for _ in range(engine.MAX_ROUNDS)])
    result, *_ = run(provider)
    assert result.blocks[-1]["type"] == "error"
    assert sum(1 for b in result.blocks if b["type"] == "page_link") == engine.MAX_ROUNDS


def test_history_alternates_roles_and_drops_a_dangling_user_turn():
    rows = [
        {"sender_type": "Agent", "text": "orphan"},
        {"sender_type": "Human", "text": "Bonjour"},
        {"sender_type": "Agent", "text": "Salut"},
        {"sender_type": "Human", "text": "Et la dispo ?"},
    ]
    assert engine.history_messages(rows) == [
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": "Salut"},
    ]


def test_system_prompt_states_the_honesty_and_confirmation_rules():
    prompt = engine.system_prompt("Demo", "Alex", ["Rental Operator"], "transaction", "TRX-1", "fr-CA")
    assert "Demo" in prompt and "TRX-1" in prompt and "français" in prompt
    assert "N’invente jamais" in prompt and "confirme" in prompt
    assert "anglais" in engine.system_prompt("Demo", "Alex", [], "dashboard", None, "en-CA")


# ---- site glue (schema-strict fake frappe) ---------------------------------------------

from cortex_rental.tests.fake_frappe import fake_frappe, load  # noqa: E402


def test_call_endpoint_passes_declared_args_and_form_dict_then_restores_it():
    with fake_frappe() as fake:
        tools = load("cortex_rental.services.ai.tools")
        fake.local.form_dict = fake._dict(original=1)
        seen = {}

        def endpoint(customer: str):
            seen["arg"], seen["form"] = customer, dict(fake.local.form_dict)
            return {"data": {"ok": True}}

        assert tools.call_endpoint(endpoint, customer="C1", extra="x", empty=None) == {"ok": True}
        assert seen == {"arg": "C1", "form": {"customer": "C1", "extra": "x"}}
        assert fake.local.form_dict == {"original": 1}


def test_ai_settings_default_to_anthropic_and_read_the_key_from_site_config():
    with fake_frappe() as fake:
        config = load("cortex_rental.services.ai.config")
        assert config.ai_settings("Demo") == {"provider": "anthropic", "model": "claude-sonnet-5", "available": False}
        fake.conf["anthropic_api_key"] = "sk"
        fake.tables["Cortex Company Settings"] = [
            {"name": "Demo", "company": "Demo", "ai_provider": "Anthropic", "ai_model": "claude-opus-5-5"}
        ]
        assert config.ai_settings("Demo") == {"provider": "anthropic", "model": "claude-opus-5-5", "available": True}
        fake.tables["Cortex Company Settings"][0]["ai_provider"] = "Onyx"
        assert config.ai_settings("Demo")["provider"] == "onyx"
