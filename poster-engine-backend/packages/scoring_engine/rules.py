def score_prompt(prompt: str, variant_type: str) -> dict:
    text = prompt.lower()
    product_focus = 92 if "product must dominate" in text or "product close" in text else 75
    luxury_score = 94 if any(x in text for x in ["luxury", "gold", "premium", "dior", "ysl", "chanel"]) else 70
    trust_score = 90 if "visible skin texture" in text and "no plastic skin" in text else 68
    attention_score = 88 if variant_type in ["before_after_split", "product_closeup"] else 84
    ctr_score = 87 if "cta" in text else 78
    conversion_score = 86 if "benefit" in text or "cta" in text else 80
    final_score = (
        ctr_score * 0.25
        + attention_score * 0.20
        + luxury_score * 0.20
        + product_focus * 0.20
        + conversion_score * 0.15
    )
    status = "pass"
    if product_focus < 85:
        status = "block_product_focus"
    elif luxury_score < 80:
        status = "regenerate_luxury"
    elif trust_score < 80:
        status = "reduce_ai_look"
    return {
        "ctr_score": ctr_score,
        "attention_score": attention_score,
        "luxury_score": luxury_score,
        "trust_score": trust_score,
        "product_focus": product_focus,
        "conversion_score": conversion_score,
        "final_score": round(final_score, 2),
        "status": status,
    }
