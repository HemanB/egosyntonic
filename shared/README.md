# shared

Contract surface between backend and (eventually) the iOS app. Schema changes here require both downstream consumers to be updated in the same PR — CI enforces.

## Layout

```
shared/
├── schemas/         # JSON Schema for state document, plan, extraction, insight
└── vocabularies/    # Controlled vocab: behaviors, network nodes, need-domains
```

The controlled vocabularies in `vocabularies/` are derived from clinical taxonomies (CBT-E, ED-specific behavioral lists, SDT need domains) per `docs/idea.md` §4.2. Adding entries post-launch is a schema change.

v1 vocabularies start ED-specific; future condition packs will extend the same schema.
