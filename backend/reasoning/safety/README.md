# safety

The non-negotiable safety layer (idea.md §9).

## Components

- **`classifier.py`** — pre-pipeline scan. Catches active SI, self-harm intent, medical-acute, asking-for-methods, asking-for-numbers, and user-requested-resources. Deterministic regex in fixture mode; live mode adds a Gemini Flash classifier on top.
- **`templates.py`** — fixed safety-response templates, one per category. Drafted v0; **require clinical-advisor sign-off before any external user touches the app.** Versioned and immutable per deploy.
- **`post_filters.py`** — deterministic post-generation backstop. Scans every generated response for numerical ED content, clinical jargon, method mentions, and diagnosis language. Failures force critic regeneration.

## How it plugs into the orchestrator

```
user turn
   │
   ▼
classify_safety_signals(utterance)
   │
   ├─► fires? ──► get_template_for_classification(category)
   │                    │
   │                    ▼
   │             Use the template VERBATIM. Skip full reasoning pipeline.
   │             Critic still runs to verify template adherence.
   │
   └─► clean: continue with extraction → retrieval → reasoning → generation
                                                                      │
                                                                      ▼
                                                  check_response_safety(text)
                                                                      │
                                                            ┌─────────┴─────────┐
                                                          pass                 fail
                                                            │                   │
                                                            ▼                   ▼
                                                 ship to user        force critic flag,
                                                                      regenerate
```

## Hard requirements (idea.md §9)

- The system **never** names, lists, or describes specific methods of self-harm or suicide. Including when the user explicitly asks. Including "things to remove access to" framings.
- The system **never** gives numerical guidance on calories, weight targets, exercise duration, or fasting durations. Including framed as "what's healthy" or "for general knowledge."
- Crisis responses **never** attempt to "talk the user down" or apply therapeutic techniques. They validate, surface resources, recommend professional support, and name the app's limitation.
- The app **never** diagnoses.

## Status

v0 drafts. All template bodies are tagged `CLINICAL_REVIEW_PENDING`. Production deploy gate (TODO) blocks promotion until a `clinical_advisor_signoff.yaml` is checked in alongside each template version.
