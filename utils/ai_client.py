"""
utils/ai_client.py — Groq (kênh 1) + OpenRouter (kênh 2), OpenAI-compatible API
"""
from __future__ import annotations

from dataclasses import dataclass
try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False
    OpenAI = None  # type: ignore

# Kênh 1: Groq
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"  # hoặc llama-3.3-70b-specdec nếu Groq hỗ trợ

# Kênh 2: OpenRouter
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

ai_providers: list = []
_last_provider_idx = 0
AI_AVAILABLE = False
# Model đã chọn qua /model — áp dụng mọi nhóm
_global_provider_pref: str | None = None


@dataclass
class _AIProvider:
    label: str
    client: object
    model: str


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).upper()
    markers = (
        "503", "429", "500", "502", "504",
        "UNAVAILABLE", "OVERLOADED", "RATE LIMIT",
        "QUOTA", "TIMEOUT", "HIGH DEMAND",
    )
    return any(m in msg for m in markers)


def init_ai_providers(groq_keys: list[str], openrouter_keys: list[str]) -> None:
    """Khởi tạo danh sách provider: Groq trước, OpenRouter sau."""
    global ai_providers, AI_AVAILABLE, _last_provider_idx

    ai_providers = []
    _last_provider_idx = 0

    if not OPENAI_SDK_AVAILABLE:
        print("[WARN] Chưa cài openai. Chạy: pip install openai")
        AI_AVAILABLE = False
        return

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

    AI_AVAILABLE = len(ai_providers) > 0
    if AI_AVAILABLE:
        groq_n = len(groq_keys)
        or_n = len(openrouter_keys)
        print(
            f"[OK] AI: Groq ({groq_n} key, {GROQ_MODEL}) → "
            f"OpenRouter ({or_n} key, {OPENROUTER_MODEL})"
        )


def _provider_kind(prov: _AIProvider) -> str:
    return "groq" if prov.label.startswith("Groq") else "openrouter"


def set_provider(provider: str) -> None:
    """Đặt model cho mọi nhóm."""
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
    return "Tự động (Groq → OpenRouter)"


def _ordered_providers(chat_id: int | None) -> list:
    """Sắp xếp provider: ưu tiên theo /model, còn lại làm dự phòng."""
    pref = get_effective_provider(chat_id)
    groq = [p for p in ai_providers if _provider_kind(p) == "groq"]
    orp = [p for p in ai_providers if _provider_kind(p) == "openrouter"]
    if pref == "groq":
        return groq + orp
    if pref == "openrouter":
        return orp + groq
    return groq + orp if groq or orp else list(ai_providers)


def generate_ai_chat(system_prompt: str, user_content: str, chat_id: int | None = None) -> str:
    """Gọi chat completion; lỗi thì thử provider dự phòng."""
    global _last_provider_idx

    if not ai_providers:
        raise RuntimeError("Chưa cấu hình AI (groq: / openrouter: trong secrets.txt)")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    ordered = _ordered_providers(chat_id)
    if not ordered:
        raise RuntimeError("Không có provider AI nào khả dụng")

    n = len(ordered)
    last_error = None

    for attempt in range(n):
        prov: _AIProvider = ordered[attempt]
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
            if attempt < n - 1:
                continue
            raise

    raise last_error or RuntimeError("Không gọi được AI")
