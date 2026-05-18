# app

SwiftUI iOS client.

> **Deferred to Phase 2.** This directory exists as a placeholder so the monorepo layout is stable. No Swift code is written until Phase 1 (the CoT reasoning backend) meets its exit criteria.

When work begins, the structure will follow the approved plan:

```
app/
├── Project.swift        # Tuist manifest
├── Sources/
│   ├── App/             # SwiftUI entry, navigation
│   ├── DesignSystem/    # Tokens, primitives, type ramp
│   ├── Chat/            # Primary interaction surface
│   ├── Insights/        # Insight cells, transparency view
│   ├── Tracking/        # Lightweight logging
│   └── Intake/          # Onboarding flow
└── Generated/           # swift-openapi-generator output (gitignored)
```
