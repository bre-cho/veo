# Voice Acting Prompt Reference

Documents the TTS/performance directives emitted by `voice_acting_engine.py`.

## Directive decision tree

```
tension_score ≥ 85
  → tone: "low, controlled, suspenseful"
  → speed: slow
  → pause: long
  → stress_words: extracted from text

purpose in (reveal, cliffhanger, twist)
  → tone: "quiet, tense, cinematic"
  → speed: medium-slow
  → pause: medium
  → stress_words: extracted from text

purpose == hook
  → tone: "low, deliberate, captivating"
  → speed: slow
  → pause: long
  → stress_words: extracted from text

default
  → tone: "documentary, calm"
  → speed: normal
  → pause: normal
  → stress_words: []
```

## Stress word vocabulary

Words that receive TTS emphasis markers when found in segment text:

> never · too late · secret · wrong · disappeared · truth · betrayal ·
> danger · lie · lost · dead · over · already · last

## Design rule

Voice acting directives are always derived from drama state + segment purpose.
The engine never assigns directives randomly.  Every TTS parameter has a
documented reason (see decision tree above).
