# Narration Prompt Reference

Documents the intent → narration line mappings used by `narration_engine.py`.

## Intent classes

| Intent      | Hidden intent triggers         | Sample line                                              |
|-------------|-------------------------------|----------------------------------------------------------|
| dominate    | control                       | "He wasn't asking a question. He was setting the rules." |
| destabilize | fear, guilt                   | "And that's when everything started to feel… wrong."     |
| mislead     | lie, manipulation             | "Every word was carefully chosen. Not one of them was true." |
| hint        | default / unknown             | "Something didn't add up."                               |

## Design rule

Every narration line is derived from a `SubtextItem.hidden_intent` value.
The engine does not hallucinate intent — it classifies what the Drama Engine
already computed and maps it to a performance-ready sentence.
