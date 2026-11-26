import asyncio

import httpx
import pytest

from app.generation import GenerationError, OllamaGenerator


def test_ollama_answer_sends_untrusted_context_to_local_chat_api() -> None:
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = __import__("json").loads(request.content)
        return httpx.Response(
            200,
            json={"message": {"content": "The note says networks connect devices."}},
        )

    generator = OllamaGenerator(transport=httpx.MockTransport(handler))
    answer = asyncio.run(
        generator.answer(
            "What do networks do?",
            [{"filename": "notes.txt", "chunk_index": 0, "text": "Networks connect devices."}],
        )
    )

    assert answer == "The note says networks connect devices."
    assert captured["url"].endswith("/api/chat")
    assert captured["payload"]["stream"] is False
    assert "untrusted data" in captured["payload"]["messages"][0]["content"]
    assert "notes.txt (chunk 0)" in captured["payload"]["messages"][1]["content"]


def test_ollama_rejects_invalid_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    generator = OllamaGenerator(transport=httpx.MockTransport(handler))
    with pytest.raises(GenerationError):
        asyncio.run(
            generator.answer(
                "What is this?",
                [{"filename": "notes.txt", "chunk_index": 0, "text": "A note."}],
            )
        )


def test_ollama_does_not_call_model_without_sources() -> None:
    generator = OllamaGenerator()
    answer = asyncio.run(generator.answer("What is in my files?", []))
    assert "couldn't find relevant information" in answer
