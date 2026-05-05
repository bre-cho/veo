# 06 — Scoring System

Current file:

```txt
packages/scoring_engine/rules.py
```

## Scores

- CTR score
- Attention score
- Luxury score
- Trust score
- Product focus
- Conversion score
- Final score

## Formula

```python
final_score = (
    ctr_score * 0.25 +
    attention_score * 0.20 +
    luxury_score * 0.20 +
    product_focus * 0.20 +
    conversion_score * 0.15
)
```

## Hard Rules

```txt
product_focus < 85 → BLOCK
luxury_score < 80 → REGENERATE
trust_score < 80 → reduce AI look
text_dominance > 30% → FAIL
cta_visibility < 70 → OPTIMIZE
```

## Next Patch

Replace heuristic scoring with computer vision checks:

- OCR text-area ratio.
- Object detection for product size.
- Face/skin realism classifier.
- Brand color consistency.
