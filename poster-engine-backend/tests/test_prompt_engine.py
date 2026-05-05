from packages.prompt_engine.beauty import VARIANT_TYPES, generate_variant_prompts


def test_generate_variant_prompts_returns_all_variants():
    prompts = generate_variant_prompts(
        project={"product_name": "Luxury Red Lipstick", "offer": "Inbox chọn màu theo cá tính"},
        brand={"brand_voice": "luxury, premium, trustworthy"},
    )
    assert len(prompts) == len(VARIANT_TYPES)
    assert [item["variant_type"] for item in prompts] == VARIANT_TYPES
    assert all(isinstance(item["prompt"], str) and item["prompt"].strip() for item in prompts)
