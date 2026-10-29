"""The reply model: LiveKit Inference when configured, else OpenAI-compatible, with an optional fallback."""

from livekit.agents import inference
from livekit.agents.llm import LLM, FallbackAdapter
from livekit.agents.types import NOT_GIVEN
from livekit.plugins import openai

from fancall.settings import FancallModelSettings


def build_llm(model_settings: FancallModelSettings) -> LLM:
    """First model from settings, falling back to a second one when the first stalls."""
    reasoning_effort = model_settings.openai_reasoning_effort or NOT_GIVEN
    llms: list[LLM] = []
    if model_settings.llm_inference_model:
        llms.append(inference.LLM(model=model_settings.llm_inference_model))
    else:
        llms.append(
            openai.LLM(
                model=model_settings.openai_model,
                base_url=model_settings.openai_base_url or NOT_GIVEN,
                api_key=model_settings.openai_api_key or NOT_GIVEN,
                reasoning_effort=reasoning_effort,
            )
        )
    if model_settings.openai_fallback_model:
        llms.append(
            openai.LLM(
                model=model_settings.openai_fallback_model,
                reasoning_effort=reasoning_effort,
            )
        )
    # 첫 모델이 멈추면 대답이 통째로 늦어지므로 다른 모델로 넘어간다
    return (
        FallbackAdapter(llms, attempt_timeout=model_settings.openai_attempt_timeout)
        if len(llms) > 1
        else llms[0]
    )
