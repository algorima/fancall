"""
A short language reminder placed at the end of the fan's latest message

The model drifts into Korean on non-Korean calls because the prompt is Korean.
A system note did not stop it; a reminder right after the fan's words did.
"""

from livekit.agents.llm import ChatContext, ChatMessage

LANGUAGE_NAMES = {
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "id": "Indonesian",
    "vi": "Vietnamese",
}


def language_tail(language: str | None) -> str:
    """Reminder text for a non-Korean call, empty for Korean or unknown."""
    if not language:
        return ""
    code = language.split("-")[0].lower()
    if code == "ko":
        return ""
    name = LANGUAGE_NAMES.get(code, code)
    return f"(Reply in {name} only. No Korean letters.)"


def with_language_tail(chat_ctx: ChatContext, tail: str) -> ChatContext:
    """Copy of the conversation with the reminder added to the last fan message.

    The stored conversation is left alone. ChatContext.copy() shares message
    objects, so the changed message is a new one.
    """
    if not tail:
        return chat_ctx
    out = chat_ctx.copy()
    for index in range(len(out.items) - 1, -1, -1):
        item = out.items[index]
        if isinstance(item, ChatMessage) and item.role == "user":
            out.items[index] = item.model_copy(
                update={"content": [*item.content, tail]}
            )
            break
    return out
