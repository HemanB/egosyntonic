# Design Criteria

*A wellness-positioned reflective journaling app with longitudinal therapeutic memory, designed around the navigation of egosyntonic content. Summer 2026 build, off-the-shelf models, prompt-engineered architecture.*

---

## 1. Product Premise

The core hypothesis is that most digital mental health tools fail at egosyntonic content because they either bypass it (symptom tracking with no engagement with the user's framing) or fight it directly (generic CBT-style reframing that the user experiences as adversarial). A system with strong longitudinal semantic memory of the user's own utterances and behaviors can do something neither human therapists nor existing chatbots reliably do: surface the user's own patterns back to them at moments when those patterns are causally active, in language drawn from their own prior expressions, without imposing a clinical framing.

The product is **wellness-positioned**, not a digital therapeutic. It does not diagnose, does not claim to treat, and is marketed as a reflective tool with ED-informed design rather than as an ED app. This positioning is non-negotiable for v1 and shapes every downstream decision: App Store category, marketing language, claims surface, intake framing, and the clinical disclaimers built into the product.

The primary user-facing value proposition is **"this app notices things about me I don't notice about myself."** Every architectural decision should be evaluated against whether it advances or detracts from that experience.

## 2. Theoretical Foundations

The system is grounded in four frameworks operating at four timescales. These are not competing perspectives to be averaged; they describe different temporal resolutions of the same phenomena, and the architecture preserves their separation rather than collapsing them.

**Receptivity (seconds to minutes)** draws on the just-in-time adaptive intervention and teachable moment literatures. Interventions delivered when the user is not in a state to receive them are not just wasted — they degrade trust and habituate the user to ignoring the system. A moment is intervention-receptive when the user is both psychologically open to reflection and pragmatically able to act on it.

**Episode dynamics (hours to days)** draws on dynamical systems models of eating disorders. The user is always in some state within a feedback loop; the system's job is to recognize which loop is currently active, how stable it is, and whether the user is near a transition. Different states call for different intervention postures: interrupting an active loop, supporting a stable but vulnerable state, or consolidating a moment of insight.

**Symptom network structure (weeks to months)** draws on network theory of psychopathology. Each user has an individualized symptom network — a graph of which experiences, behaviors, and cognitions causally trigger which others. This network is learned from the user's own data over time and is the primary substrate for the "noticing patterns" capability that defines the product.

**Functional substrates (trait-level)** draws on self-determination theory. Egosyntonic behaviors persist because they serve real psychological needs as maladaptive substitutes — typically for autonomy, competence, or relatedness that is being thwarted elsewhere in the user's life. This layer updates slowly and shapes the framing of all interventions.

The transtheoretical model is explicitly **not** used as a foundational scaffold. The stages-of-change model has consistently failed to demonstrate predictive utility for eating disorder treatment, and stage-matched intervention selection has no empirical support. Motivational interviewing principles, which have independent empirical support, are used at the response-generation level but not as a structural framework for intervention selection.

## 3. Reasoning Architecture

### 3.1 High-level pipeline

Every user turn is processed through a fixed sequence of LLM calls. There is no learned orchestration; the hierarchy is hardcoded and uniform across users in v1.

The pipeline:

1. **Feature extraction** runs over the incoming user message to produce a structured record of affective valence, behaviors referenced, cognitive content, and contextual markers.
2. **Retrieval** queries the user's longitudinal memory across multiple heads, each producing a candidate set of relevant past utterances and behaviors.
3. **Reasoning** takes the current message, extracted features, retrieved memory, and the current per-user state document, and produces a structured plan with sections corresponding to each of the four theoretical heads.
4. **Generation** takes the plan and produces the user-facing response, with the plan acting as a conditioning scaffold.
5. **Critic** audits the generated response against the plan and against a set of failure modes (sycophancy, collusion with egosyntonic framing, missed safety signals, inappropriate framing). If the critic flags issues, generation is regenerated with the critic's notes in context.
6. **State update** modifies the per-user state document based on what was learned from this turn.

The pipeline is approximately three to five LLM calls per turn depending on whether the critic triggers regeneration. Latency target is under five seconds for the user-visible response; state updates can run asynchronously after the response is delivered.

### 3.2 The four reasoning heads as structured prompt output

The reasoning call uses a single LLM invocation that outputs a JSON object with four sections, one per head. Each head has its own internal schema. The reasoning prompt instructs the model to reason explicitly about each head before producing the structured output, leveraging chain-of-thought capability.

The **receptivity head** outputs a score from 0 to 1 on intervention-receptiveness and a categorical assessment of the user's current state: open to reflection, in active distress, in crisis, dissociated or disengaged, or seeking practical support. It also outputs an actionability assessment: can the user act on an intervention right now given their context? The receptivity head's primary role is to gate intervention intensity. Low receptivity does not mean the system disengages; it means the system shifts toward presence and validation rather than insight-surfacing.

The **dynamical state head** outputs an assessment of which feedback loop the user is currently in, how stable that state is, and whether there are signals of an impending transition. Loop identification draws on patterns established in the user's network over time; for new users, it falls back on common ED loop archetypes from the clinical literature. The output includes an intervention posture recommendation: interrupt, support, or consolidate.

The **network head** outputs which symptom-network edges are currently active in the user's individualized network. For users with sufficient longitudinal data, this is grounded in their own history; for new users, it operates on intake-seeded priors. It identifies the most causally upstream active node, which is the recommended intervention target. It also outputs candidate patterns worth surfacing if receptivity supports it.

The **SDT head** outputs which basic psychological needs appear to be thwarted in the user's current life context and which behaviors are serving as substitutes for which needs. This head updates slowly and rarely changes its output dramatically within a single session; its primary effect is on the framing language used in generation.

### 3.3 The orchestration sub-section of the plan

Following the four head outputs, the reasoning call produces an integrated plan with the following fields:

- Intervention intensity (none, presence, light reflection, pattern-surfacing, direct invitation)
- Content focus (which network node or pattern, if any, to address)
- Framing language (which SDT need-language to use, which prior user utterances to draw vocabulary from)
- Memory references to surface (specific past utterances or logged behaviors that the response should reference)
- Safety flags (any signals that require crisis-handling, medical-stability concerns, or supervision override)

The generation prompt receives this plan and produces the response. Generation is instructed to write in the user's own register, to reference surfaced memories naturally rather than clinically, and to avoid clinical jargon entirely.

### 3.4 The critic layer

The critic is a separate LLM call that takes the generated response and the plan and evaluates against a fixed set of failure modes:

- Did the response validate the egosyntonic framing rather than surface its function?
- Did the response use clinical or pathologizing language?
- Did the response collude with the disorder's logic (e.g., agreeing that restriction is "discipline")?
- Did the response miss a safety signal flagged in the plan?
- Did the response over-deliver insight when receptivity was low?
- Did the response reference memory in a way that could feel surveilling?

If any flag fires, the generation is regenerated with the critic's notes appended. The critic does not directly edit responses; it only triggers regeneration. After two regeneration attempts, the system falls back to a minimal validating response and logs the failure for later review.

### 3.5 Per-user state document

The state document is the spine of the system and the one schema decision that cannot be deferred. It is a structured JSON document maintained per user, updated after every turn, and read by retrieval and reasoning on every turn.

Core fields:

- **Stated chief complaint** (from intake; user-editable)
- **Current network state**: the user's individualized symptom network, represented as a node list with co-activation weights and recency-decayed edge weights
- **Need-state model**: per-domain SDT assessments (work, relationships, family, self-direction) with confidence scores
- **Receptivity history**: rolling window of receptivity assessments to detect trends
- **Active loops**: list of currently-active dynamical loops with stability estimates
- **Insight surface state**: which insights have been shown to the user, when, and with what response
- **Safety state**: any active safety flags, crisis history references, medical-stability concerns
- **User preferences**: insight intensity setting, tracking preferences, communication preferences

The state document is human-readable by design. It must be possible for a future clinician view, and for the user's own transparency surface, to render meaningful subsets of this document in plain language.

## 4. Memory and Retrieval Layer

### 4.1 Storage architecture

User utterances are stored as records in a vector database (Vertex AI Vector Search in v1) with rich metadata. Each utterance record contains:

- Raw utterance text
- Embedding (from a general-purpose semantic encoder)
- Extracted features (the output of the feature extraction prompt): affective valence, behaviors referenced, cognitive content, network nodes activated, candidate need-states implicated, contextual markers
- Conversational context (preceding turns)
- Timestamp and session metadata
- Any logged behaviors associated with the same session

Logged behaviors are stored as separate structured records linked to the utterances they co-occurred with. This linkage is what allows the system to retrieve "what was the user saying around the times they logged a restriction episode" — the kind of pattern that defines the product.

### 4.2 Feature extraction at write time

When a user submits a message, a feature extraction prompt runs over it before the message is stored. This is an additional LLM call but a cheap one (small model, structured output). The extraction prompt produces metadata that is stored alongside the embedding and is critical for the metadata-filtered retrieval that the heads rely on.

The extraction schema is fixed and includes: affective dimensions, behaviors referenced from a controlled vocabulary, cognitive distortions present, network nodes (also from a controlled vocabulary), implicated need-states, and contextual markers (time, location if available, social context if mentioned).

The controlled vocabularies for behaviors and network nodes are derived from clinical taxonomies (CBT-E, ED-specific behavioral taxonomies) and are fixed at v1. Adding to these vocabularies post-launch is a schema change.

### 4.3 Multi-head retrieval

Each reasoning head can issue its own retrieval queries. Queries are hybrid: semantic similarity over embeddings, filtered by metadata. Example query patterns:

- Receptivity head: "find prior turns where the user was in a similar affective state, weighted by recency"
- Dynamical head: "find prior instances of the currently-active loop, particularly transitions out of it"
- Network head: "find prior co-activations of the currently active nodes; find prior moments when this upstream node was active"
- SDT head: "find prior expressions of thwarting in the currently-implicated need-domain"

Retrieval results from all heads are passed to the reasoning prompt. The reasoning prompt is responsible for selecting which retrieved items, if any, should be surfaced in the response. Most retrieved items will not be surfaced; they are present to inform the reasoning.

### 4.4 Memory curation

Storing every utterance creates noise and cost over time. The system curates memory in two ways. First, low-information utterances (greetings, scheduling, very short messages) are stored but down-weighted for retrieval. Second, periodic summarization runs offline produce higher-level summaries of weekly or monthly periods, which are retrievable separately when long-range context is needed. Original utterances are retained indefinitely (subject to user deletion); summaries supplement rather than replace them.

The cost of retaining everything is real but tractable at the user-counts a summer launch will see. Cost-aware curation can be a v2 problem.

## 5. The Insight Layer

The insight layer is the user-facing surface where the system's longitudinal understanding becomes visible to the user. It is the highest-stakes surface in the product: done well, it is the screenshot that drives organic acquisition; done poorly, it makes users feel surveilled and they churn.

### 5.1 Design philosophy

Insights are **observational, not interpretive**. The system surfaces patterns in the user's own data, in language drawn from the user's own utterances, with retrievable evidence backing each insight. It does not tell the user what their patterns mean, what they suggest about their psychology, or what they should do about them. The user draws the inference.

Compare:

- *Wrong*: "You have high autonomy thwarting in your work context, which is driving compensatory eating behaviors."
- *Right*: "You've mentioned feeling like you don't have much say at work three times in the last two weeks. Twice, you mentioned eating less afterward."

Every insight surfaces with two affordances: a "tap to see what this is based on" link that exposes the specific past utterances or behaviors, and a "this isn't right" correction affordance that feeds back into the system.

### 5.2 CC anchoring and graduated insight surfacing

The initial insight surface is anchored on the user's stated chief complaint from intake. For the first weeks of use, insights focus on patterns directly relevant to what the user said they wanted to work on. This serves two purposes: it gives the user a sense that the app is responsive to their stated goals, and it bounds the surface area while the network head is still cold-starting.

As longitudinal data accumulates, the system gradually introduces insights that go beyond the stated CC, framed as questions rather than assertions. The user's stated CC and the system's evolving model are tracked separately in the state document; the gap between them is itself signal, but the system does not surface that gap directly to the user. It surfaces patterns and lets the user notice their own gap.

The data-density threshold for graduated insights is fixed in v1: insights requiring three or more co-occurrences are surfaced only after at least two weeks of use. This is conservative and prevents the system from making confident-sounding claims off thin data.

### 5.3 Insight intensity as a user-controllable setting

Some users want everything the system notices; others find that overwhelming or activating. The insight layer has a user-controllable intensity setting:

- **Quiet**: insights surface only when the user explicitly asks ("what have you been noticing?")
- **Moderate** (default): the system surfaces high-confidence insights at moments of high receptivity, no more than a few per week
- **Active**: the system surfaces moderate-confidence insights more frequently, including questions and tentative observations

Intensity is adjustable at any time. The setting is also fed back into the reasoning layer so the system understands when to volunteer observations and when to wait.

### 5.4 Insight types

The insight layer supports a fixed set of insight types in v1:

- **Pattern**: "X has happened after Y, N times in M days"
- **Echo**: "You described feeling this way before, in similar words" (with surfacing of past utterance)
- **Shift**: "You're talking about X differently than you were a month ago" (positive or neutral framing only)
- **Context**: "These feelings tend to come up around [time/place/situation]"

Additional types are deferred to v2. Each type has a strict template for how it's rendered to the user and a strict threshold for when it's eligible to surface.

### 5.5 What the system does not surface

Several categories of inferred information are maintained internally but not shown to the user:

- SDT need-state assessments in clinical language
- Symptom network node weights or edge strengths
- Inferred severity or stage
- Comparative statements ("you're doing worse than X")
- Predictions ("you might restrict tomorrow")

Predictions are particularly important to avoid. Even if accurate, surfacing them creates an adversarial dynamic and risks the user gaming inputs. Patterns are retrospective; predictions are not.

## 6. Intake and Onboarding

Intake serves three functions that pull in different directions: clinical baseline for outcomes, cold-start data for the reasoning layer, and user onboarding that doesn't lose people. Total intake time target is under seven minutes for the core flow, with optional deeper sections.

### 6.1 Structured baseline

The core intake includes validated short-form instruments:

- **EDE-QS** (12 items, eating disorder examination questionnaire short form) — clinical baseline for ED-spectrum behaviors and cognitions
- **PANAS short form** or similar brief affect measure — baseline affective state
- **Brief SDT need satisfaction items** — domain-specific need satisfaction at baseline

These instruments are not user-facing as "tests." They are framed as "a few questions to help us understand where you're starting from." Scores are stored in the state document but are not shown to the user as scores in v1. Score visibility may be added in v2 if it serves users; v1 errs toward not making the app feel like assessment.

### 6.2 Open-ended seed data

Three open-ended prompts feed the reasoning layer with cold-start data:

- "Describe a recent moment when eating felt hard, in as much detail as you want."
- "What does the difficulty around eating do for you that nothing else does? (This is a hard question — take your time.)"
- "Who in your life knows what's going on for you right now?"

These produce rich utterance records that seed retrieval from day one. They are explicitly framed as optional and skippable, but most users will engage with at least one.

### 6.3 Stated chief complaint

Following the open-ended prompts, the user is asked to state, in their own words, what they want the app to help with. This becomes the anchor for the initial insight surface. It is editable at any time from settings.

### 6.4 Safety screening

Intake includes screening for active medical instability and current suicidal ideation. If either screens positive, the app takes specific action: surfaces 988 and crisis text line, provides clear language about the app's limitations, and recommends professional support. The app does not refuse to operate, but the receptivity head's default is shifted toward higher caution, and the insight layer is set to quiet by default for that user.

This is the highest-liability moment in the product. The screening language and the response language are reviewed by clinical advisors (Zucker or another credentialed reviewer) before launch. No exceptions.

## 7. Behavior Tracking

### 7.1 Design stance

Tracking exists primarily because clinician integration eventually requires it and because tracked data improves the network head's inputs. It is **not** the core interaction model and is not pushed on users.

Tracking is **optional, flexible by default, and explicitly does not include calorie counting.** This is a stance, not an oversight. Calorie tracking is iatrogenic for the user population most likely to download the app and offers little informational value to the reasoning layer. The app does not have a calorie field anywhere, and this is a marketing point.

### 7.2 Tracking modalities

Users can log a meal or behavior through two interfaces:

- **Loose entry**: "tell me about lunch" or "log something" — accepts free-text and runs feature extraction to produce structured data on the backend
- **Structured entry**: optional form with fields for time, what was eaten (qualitative, not quantitative), hunger before/after, emotions, behaviors, context

Most users will use loose entry most of the time. The structured entry exists for users who prefer it and for moments the user wants to be deliberate.

### 7.3 Behavior categories tracked

The controlled vocabulary for behaviors includes: restriction episodes, binge episodes, purging behaviors, compulsive exercise, body checking, weight checking, food rules followed or broken, social eating moments. These map directly onto network nodes for the network head.

Each logged behavior is timestamped and linked to any concurrent utterances. This linkage is what allows the system to recognize "the user logs restriction most often after evening conversations about work."

### 7.4 Tracking and the insight layer

Tracked behaviors are direct inputs to the network head and surface in insights as factual references ("you logged restriction four times in the last two weeks; three of those followed conversations about [theme]"). Behaviors that are logged but never surfaced in insights are not "wasted"; they inform the reasoning layer's understanding of the user.

Users can view their own tracking history. This view is intentionally minimal: a chronological list, no charts, no streaks, no gamification. ED apps with streak mechanics actively harm a subset of their users, and this is a category the product refuses to enter.

## 8. The User Dashboard

The v1 dashboard surfaces consist of:

1. **Chat** — the primary interaction surface
2. **Insights** — the layer described in section 5, including a "what I've learned about you" transparency view and the pattern surface
3. **Tracking** — the lightweight logging interface and a minimal history view
4. **Settings** — including insight intensity, tracking preferences, privacy controls, account management, and access to safety resources

Surfaces explicitly deferred to v2:

- A separate journal/history view of past conversations (chat scrollback is sufficient for v1)
- A clinician portal or shareable summary
- Outcomes dashboards or progress charts
- Social or community features

### 8.1 The "what I've learned about you" view

This is the transparency surface and is part of the insights tab. It renders a plain-language version of the user's state document, including:

- Their stated chief complaint
- The themes the system has been noticing
- The contexts that seem connected to their experiences
- What insights the system has surfaced recently and the user's response to them

The view is editable. The user can mark any item as "not quite right" or "this isn't me anymore," which updates the state document. This is both a trust surface and a data-quality mechanism.

### 8.2 Visual design constraints

The aesthetic target is calm, text-forward, and non-clinical. Specifically not targeted: data-dense dashboards, progress bars, achievement systems, color-coded mood states, charts of any kind in v1. The visual language should signal "thoughtful journal" rather than "health tracker."

## 9. Safety Architecture

Safety is designed into the pipeline, not bolted on. The receptivity head, the critic, and the safety state in the user document all contribute.

### 9.1 Crisis detection and response

The reasoning layer flags any signal of active suicidal ideation, intent to self-harm, or acute medical concern (signs of refeeding, severe restriction, syncope, vomiting blood). When any of these flag, the response generation follows a fixed safety template: validate the user, surface crisis resources clearly, recommend professional support, and explicitly note that the app is not a substitute for emergency care. The critic verifies that the safety template was followed.

Crisis responses do not include attempts to "talk the user down" or apply therapeutic techniques. The app's role in crisis is to bridge to appropriate human support, not to attempt to provide that support itself.

### 9.2 Means restriction language

The system does not name, list, or describe specific methods of self-harm or suicide under any circumstances, including when a user explicitly asks. This includes well-intentioned framings like "things to remove access to."

### 9.3 Eating disorder–specific safety

The system does not provide specific numerical guidance on calories, weight targets, exercise duration, or fasting durations under any circumstances. Even framed as "what's healthy" or "for general knowledge," numerical specifics in this domain can be triggering or directly harmful and are refused. The app's stance is that quantitative targets are decisions to be made with a treatment team.

The app does not validate restriction, purging, compulsive exercise, or body-checking as appropriate behaviors, even when the user frames them positively. The critic specifically checks for collusion with egosyntonic framings of these behaviors.

### 9.4 Limitations disclosure

The app surfaces, at intake and at any moment a user appears to be relying on it as a primary support, that it is not therapy, not a crisis service, and not a substitute for professional care. The language is clear and non-defensive.

## 10. Data, Privacy, and User Control

The system stores substantial sensitive data per user. Privacy and user control are first-order design constraints.

- Data is encrypted at rest and in transit.
- Users can export their full data at any time as a structured archive.
- Users can delete their account, which deletes all stored data within a defined window.
- Users can delete individual messages or logged behaviors, which removes them from retrieval indices.
- The app does not share data with third parties. The only external services in the data path are the LLM provider (Google) and the cloud provider (Google). The privacy policy is explicit about this.
- Insights and inferences are accessible to the user through the transparency surface.

The default is conservative. If the user has not explicitly opted into something, the system does not do it.

## 11. Technical Stack and Constraints

The v1 stack:

- **Frontend**: React Native (cross-platform iOS/Android from a single codebase; Android is deferred for launch but not architecturally precluded)
- **Backend**: Firebase (Auth, Firestore for app state, Cloud Functions for orchestration)
- **LLM**: Gemini 2.5 Pro for reasoning and critic calls, Gemini Flash for feature extraction and generation
- **Vector storage**: Vertex AI Vector Search
- **Hosting**: Firebase Hosting / Google Cloud

### 11.1 Why these choices

The stack is chosen to minimize integration friction and shipping risk, not to optimize any single dimension. Firebase + Vertex AI gives a single-vendor surface with reasonable defaults. Gemini's long context window is genuinely useful for the memory architecture and reduces the need for aggressive summarization. The trade-off is Gemini's aggressive safety filters, which require careful prompt engineering around ED-related content; this is solvable but is on the v1 critical path.

### 11.2 Constraints

- **No fine-tuning.** All model behavior is achieved through prompt engineering and retrieval. This caps the ceiling of system performance at what off-the-shelf models with clever orchestration can achieve, and that ceiling is rising fast enough to be acceptable.
- **No browser storage in any rendered surface.** State is server-authoritative.
- **Latency target**: user-visible response within five seconds at p95. State updates and background curation run asynchronously.
- **Cost target**: under [TBD] per active user per month at launch scale. Reassessed quarterly.

## 12. Evaluation and Iteration

The v1 product ships with logging and instrumentation sufficient to evaluate each pipeline component independently.

### 12.1 What gets logged

- Every LLM call (input, output, latency, cost) with structured metadata identifying which pipeline step
- Every retrieval query and its results
- Every critic decision and any regenerations
- Every insight surfaced and the user's response (tap, dismiss, correct, ignore)
- Every user-rated message (thumbs up/down or similar lightweight feedback)
- Weekly one-tap user-rated progress on their stated chief complaint

### 12.2 What gets evaluated

Process metrics: pipeline latency, critic flag rate by category, regeneration rate, retrieval relevance (offline judgment on sampled queries).

User-facing metrics: engagement depth (not just retention), insight tap-through rate, insight correction rate, weekly self-reported progress on stated CC.

Outcome metrics (longer horizon): change in EDE-QS scores from intake to month 1 and month 3, user-reported helpfulness, qualitative feedback.

### 12.3 What is explicitly not optimized for in v1

- Daily active usage
- Session length
- Notification engagement
- Streaks of any kind

These metrics drive engagement design that is harmful in this user population. The product optimizes for users feeling that the app is genuinely helpful when they use it, not for maximizing how often they open it.

## 13. What is Deferred

The following are explicit v2 considerations and should not be built in v1:

- Clinician portal and shareable summaries
- Fine-tuned models of any kind
- Outcomes dashboards and progress charts for users
- Voice or audio input
- Active push notifications beyond minimal reminders
- Group features, social features, community features
- Integration with wearables or passive sensors
- Multi-language support
- Insurance integration, billing, or any payment model that implies clinical service

Several of these are interesting and probably useful. None are necessary to validate the core hypothesis.

## 14. Open Questions

These are unresolved as of this document and require decisions before launch or in early iteration:

- Exact threshold and language for the data-density gate on graduated insights
- Whether the critic should operate on a single LLM call or be split into a safety critic and a clinical critic
- Whether feature extraction should use the same model as reasoning or a separate cheaper model
- Whether the SDT head should be updated on every turn or only on a periodic schedule
- How the system handles a user who explicitly asks "what do you think is going on with me" — does it surface its model, redirect, or some middle path?
- Whether the system should ever proactively message the user (push notifications based on time of day patterns) or remain strictly responsive in v1

These are decision points that benefit from a clinical advisor's input before they're locked.

## 15. Success Criteria

The v1 launch is successful if, within three months of shipping:

1. Real users have engaged with the system enough to generate meaningful longitudinal data (a meaningful number of users with at least four weeks of use)
2. At least one user spontaneously describes the "this app noticed something I didn't" experience in unprompted feedback
3. The system's safety behavior performs correctly in all logged crisis events
4. No serious clinical incidents are tied to the system's behavior
5. The architecture has held up well enough that v2 features can be built on top of it without significant refactoring of v1 foundations

Funding, valuation, user count, and revenue are not v1 success criteria. The success criteria are oriented around demonstrating that the core hypothesis — that longitudinal therapeutic memory creates a qualitatively different product experience — is real or not. Everything downstream depends on that answer.