"""
utils/ai_client.py — Groq (kênh 1) + OpenRouter (kênh 2) + Gemini (kênh 3)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False
    OpenAI = None  # type: ignore

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False
    genai = None  # type: ignore
    genai_types = None  # type: ignore

# Kênh 1: Groq
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Kênh 2: OpenRouter
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

# Kênh 3: Gemini
GEMINI_MODEL = "gemini-2.0-flash"

ai_providers: list = []
gemini_keys: list[str] = []
gemini_key_index = 0
_gemini_lock = asyncio.Lock()
_last_provider_idx = 0
AI_AVAILABLE = False
_global_provider_pref: str | None = None


@dataclass
class _AIProvider:
    label: str
    client: object
    model: str


class GeminiProvider:
    """Provider Gemini — key xoay vòng round-robin, độc lập fallback Groq/OpenRouter."""

    def __init__(self, keys: list[str]) -> None:
        self.keys = list(keys)

    @property
    def available(self) -> bool:
        return bool(self.keys) and GEMINI_SDK_AVAILABLE


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).upper()
    markers = (
        "503", "429", "500", "502", "504",
        "UNAVAILABLE", "OVERLOADED", "RATE LIMIT",
        "QUOTA", "TIMEOUT", "HIGH DEMAND",
    )
    return any(m in msg for m in markers)


def init_ai_providers(
    groq_keys: list[str],
    openrouter_keys: list[str],
    gemini_keys_list: list[str] | None = None,
) -> None:
    """Khởi tạo provider: Groq, OpenRouter, Gemini keys."""
    global ai_providers, gemini_keys, gemini_key_index, AI_AVAILABLE, _last_provider_idx

    ai_providers = []
    gemini_keys = list(gemini_keys_list or [])
    gemini_key_index = 0
    _last_provider_idx = 0

    if not OPENAI_SDK_AVAILABLE and not gemini_keys:
        print("[WARN] Chưa cài openai. Chạy: pip install openai")
        AI_AVAILABLE = False
        return

    if OPENAI_SDK_AVAILABLE:
        for i, key in enumerate(groq_keys, 1):
            ai_providers.append(
                _AIProvider(
                    label=f"Groq#{i}",
                    client=OpenAI(api_key=key, base_url=GROQ_BASE_URL),
                    model=GROQ_MODEL,
                )
            )

        for i, key in enumerate(openrouter_keys, 1):
            ai_providers.append(
                _AIProvider(
                    label=f"OpenRouter#{i}",
                    client=OpenAI(
                        api_key=key,
                        base_url=OPENROUTER_BASE_URL,
                        default_headers={
                            "HTTP-Referer": "https://github.com/telegram-bot",
                            "X-Title": "Thu Ky Bot",
                        },
                    ),
                    model=OPENROUTER_MODEL,
                )
            )

    if gemini_keys and not GEMINI_SDK_AVAILABLE:
        print("[WARN] Có gemini: trong secrets nhưng chưa cài google-genai")

    AI_AVAILABLE = len(ai_providers) > 0 or bool(gemini_keys)
    if AI_AVAILABLE:
        groq_n = len(groq_keys)
        or_n = len(openrouter_keys)
        gem_n = len(gemini_keys)
        print(
            f"[OK] AI: Groq ({groq_n} key) → OpenRouter ({or_n} key) → "
            f"Gemini ({gem_n} key, {GEMINI_MODEL})"
        )


def _provider_kind(prov: _AIProvider) -> str:
    return "groq" if prov.label.startswith("Groq") else "openrouter"


def set_provider(provider: str) -> None:
    global _global_provider_pref
    if provider not in ("groq", "openrouter"):
        raise ValueError("provider phải là groq hoặc openrouter")
    _global_provider_pref = provider


def get_provider() -> str | None:
    return _global_provider_pref


def get_effective_provider(chat_id: int | None = None) -> str | None:
    return _global_provider_pref


def get_provider_label(provider: str | None) -> str:
    if provider == "groq":
        return f"Groq ({GROQ_MODEL})"
    if provider == "openrouter":
        return f"OpenRouter ({OPENROUTER_MODEL})"
    return "Tự động (Groq → OpenRouter → Gemini)"


def _ordered_providers(chat_id: int | None) -> list:
    pref = get_effective_provider(chat_id)
    groq = [p for p in ai_providers if _provider_kind(p) == "groq"]
    orp = [p for p in ai_providers if _provider_kind(p) == "openrouter"]
    if pref == "groq":
        return groq + orp
    if pref == "openrouter":
        return orp + groq
    return groq + orp if groq or orp else list(ai_providers)


def _messages_to_gemini(messages: list[dict]) -> tuple[str | None, list]:
    """Tách system_instruction và contents cho Gemini API."""
    system_parts: list[str] = []
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append(
            genai_types.Content(
                role=gemini_role,
                parts=[genai_types.Part(text=content)],
            )
        )
    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return system_instruction, contents


def _call_gemini_sync(api_key: str, messages: list[dict]) -> str:
    client = genai.Client(api_key=api_key)
    system_instruction, contents = _messages_to_gemini(messages)
    if not contents:
        raise RuntimeError("Không có tin nhắn để gửi Gemini")

    config_kwargs: dict = {"temperature": 0.7}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=genai_types.GenerateContentConfig(**config_kwargs),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini trả về rỗng")
    return text


async def get_gemini_response(messages: list[dict]) -> str:
    """Gọi gemini-2.0-flash với key xoay vòng round-robin."""
    global gemini_key_index

    if not gemini_keys:
        raise RuntimeError("Chưa cấu hình Gemini (gemini: trong secrets.txt)")
    if not GEMINI_SDK_AVAILABLE:
        raise RuntimeError("Chưa cài google-genai. Chạy: pip install google-genai")

    async with _gemini_lock:
        key = gemini_keys[gemini_key_index % len(gemini_keys)]
        gemini_key_index = (gemini_key_index + 1) % len(gemini_keys)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_gemini_sync, key, messages)


async def generate_ai_chat(messages: list[dict], chat_id: int | None = None) -> str:
    """Gọi chat: Groq → OpenRouter → Gemini (Gemini xoay key riêng)."""
    global _last_provider_idx

    if not messages:
        raise RuntimeError("Danh sách messages rỗng")

    if not AI_AVAILABLE:
        raise RuntimeError("Chưa cấu hình AI (groq:/openrouter:/gemini: trong secrets.txt)")

    ordered = _ordered_providers(chat_id)
    last_error: Exception | None = None

    for prov in ordered:
        try:
            response = prov.client.chat.completions.create(
                model=prov.model,
                messages=messages,
                temperature=0.7,
            )
            text = (response.choices[0].message.content or "").strip()
            if not text:
                raise RuntimeError("Model trả về rỗng")
            if prov in ai_providers:
                _last_provider_idx = ai_providers.index(prov)
            return text
        except Exception as e:
            last_error = e
            print(f"[WARN] {prov.label} lỗi: {e}")

    if gemini_keys:
        try:
            return await get_gemini_response(messages)
        except Exception as e:
            last_error = e
            print(f"[WARN] Gemini lỗi: {e}")

    raise last_error or RuntimeError("Không gọi được AI")
