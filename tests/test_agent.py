from google.adk.models.lite_llm import LiteLlm

from doc_qa.agent import resolve_model


def test_bare_gemini_name_passes_through_as_string():
    assert resolve_model("gemini-2.5-flash") == "gemini-2.5-flash"


def test_provider_prefixed_name_is_wrapped():
    model = resolve_model("openai/gpt-5.6-terra")
    assert isinstance(model, LiteLlm)
    assert model.model == "openai/gpt-5.6-terra"
