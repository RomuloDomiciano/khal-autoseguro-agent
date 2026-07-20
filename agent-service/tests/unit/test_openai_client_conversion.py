"""Tests the OpenAI DTO conversion helpers directly, with no network call —
these are pure functions on OpenAIChatClient and are the part of the
integration most likely to silently drift from the SDK's shape."""
from types import SimpleNamespace

from app.integrations.llm.base import LLMMessage, LLMToolCall, ToolSpec
from app.integrations.llm.openai_client import OpenAIChatClient


def test_to_openai_message_includes_tool_calls_as_json_arguments():
    message = LLMMessage(
        role="assistant",
        content=None,
        tool_calls=[LLMToolCall(id="call_1", name="get_quote", arguments={"idade": 35})],
    )
    payload = OpenAIChatClient._to_openai_message(message)
    assert payload["role"] == "assistant"
    assert payload["tool_calls"][0]["function"]["name"] == "get_quote"
    assert payload["tool_calls"][0]["function"]["arguments"] == '{"idade": 35}'


def test_to_openai_message_includes_tool_call_id_for_tool_role():
    message = LLMMessage(role="tool", content="{}", tool_call_id="call_1", name="get_quote")
    payload = OpenAIChatClient._to_openai_message(message)
    assert payload["tool_call_id"] == "call_1"
    assert payload["name"] == "get_quote"


def test_to_openai_tool_shape():
    tool = ToolSpec(name="get_quote", description="Requests a quote", parameters={"type": "object", "properties": {}})
    payload = OpenAIChatClient._to_openai_tool(tool)
    assert payload == {
        "type": "function",
        "function": {
            "name": "get_quote",
            "description": "Requests a quote",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def test_from_openai_message_parses_tool_call_arguments():
    fake_function = SimpleNamespace(name="get_quote", arguments='{"idade": 35, "veiculo_ano": 2018}')
    fake_tool_call = SimpleNamespace(id="call_1", function=fake_function)
    fake_message = SimpleNamespace(content=None, tool_calls=[fake_tool_call])

    result = OpenAIChatClient._from_openai_message(fake_message)

    assert result.role == "assistant"
    assert result.tool_calls[0].name == "get_quote"
    assert result.tool_calls[0].arguments == {"idade": 35, "veiculo_ano": 2018}


def test_from_openai_message_handles_plain_text_with_no_tool_calls():
    fake_message = SimpleNamespace(content="Oi! Como posso ajudar?", tool_calls=None)
    result = OpenAIChatClient._from_openai_message(fake_message)
    assert result.content == "Oi! Como posso ajudar?"
    assert result.tool_calls is None
