from packages.scoring_engine.rules import score_prompt


def test_scoring_engine_returns_full_contract():
    prompt = """
    Luxury campaign with product must dominate and CTA benefit.
    Realistic model with visible skin texture and no plastic skin.
    """
    result = score_prompt(prompt, "product_closeup")

    for key in [
        "ctr_score",
        "attention_score",
        "luxury_score",
        "trust_score",
        "product_focus",
        "conversion_score",
        "final_score",
        "status",
    ]:
        assert key in result

    assert 0 <= result["final_score"] <= 100
    assert result["status"] in {"pass", "block_product_focus", "regenerate_luxury", "reduce_ai_look"}
