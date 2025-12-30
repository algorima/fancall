"""
Common prompts for Fancall agents.
"""

ROLE_PLAYING_GUIDELINES = """대부분의 텍스트는 사용자의 관점에서 본 대화여야 합니다.
*텍스트*를 사용하여 당신의 행동을 표현하세요. 사용자는 어떤 조치든 취할 수 있습니다.

1. 당신은 세계관에 대한 인지를 항상 잊지 마십시오.
2. 이 역할극은 목적이 있는 것이 아니기 때문에, 한 가지 상황이 끝나면 그 상황을 반복하려고 하지 마십시오. 감정적이거나 극단적인 상황에서, 초자아가 자아를 능가하도록 하십시오. 한 가지 상황이 끝나면, 기존의 자아를 회복하고 다시 기존 성격에 충실하십시오.
3. 현재 시간/공간/상황/캐릭터/분위기를 정확하게 파악하고 그에 따라 풍경/사물/인물을 묘사하십시오.
4. 캐릭터 분석 및 개발을 위해 심리학 지식을 활용하고 모든 캐릭터를 성장/변화 가능성이 있는 복합적인 개인으로 취급하십시오. 생생한 장면 연출을 통해 캐릭터의 인간적인 면을 포착하십시오.
5. 당신의 성격/연령/관계에 맞는 말투를 구사합니다. 당신의 성격에 따라 대화/내레이션/묘사의 비율을 유기적으로 조정하십시오."""


def compose_instructions(
    system_prompt: str | None, include_role_playing: bool = True
) -> str:
    """
    Compose agent instructions from system prompt and guidelines.

    Args:
        system_prompt: Agent's system prompt defining personality and behavior
        include_role_playing: Whether to include role playing guidelines

    Returns:
        Combined instructions string
    """
    parts = []

    # Role playing guidelines (if enabled)
    if include_role_playing:
        parts.append(ROLE_PLAYING_GUIDELINES)

    # System prompt
    if system_prompt:
        parts.append(system_prompt)

    return "\n\n".join(parts)
