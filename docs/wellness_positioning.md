# Wellness Positioning

*Operational translation of `idea.md` §1 (product premise) and §9 (safety) into concrete product, marketing, App Store, and copy decisions. Companion to `docs/safety_templates.md` (templates and crisis language) and the privacy and terms drafts in this directory.*

This document is the load-bearing source for any claim or framing the product makes about itself, anywhere it is rendered to a user or reviewer. If a claim surface (store listing, intake string, marketing site, support reply, press response) is not covered here, it should be added here before it ships.

---

## 1. What wellness-positioning means in practice

The product is a **reflective journaling tool with ED-informed (and broader mental-health-informed) design**. It is not a digital therapeutic, not a medical device, not a clinical service. This is a positioning decision encoded in every claim, screen, and store-listing string.

### 1.1 Three categories, and which one we are

| Category | What it is | Regulatory posture | Examples |
|---|---|---|---|
| **Wellness app** *(what we are)* | Software supporting general well-being. No diagnosis, no treatment claims, no clinical efficacy claims. | FDA enforcement discretion under the General Wellness Policy (2019); App Store consumer rules apply. | Reflective journaling apps, mood diaries, meditation apps without therapy claims. |
| **Digital therapeutic / DTx** *(what we are not)* | Software intended to prevent, manage, or treat a disease or condition. | FDA 510(k) or De Novo clearance typical (Software as a Medical Device). HIPAA-covered if integrated into care. | Prescription-only therapeutics, CBT-i apps with treatment claims. |
| **Medical device** *(what we are not)* | Hardware or software that diagnoses, monitors, or treats a condition under a clinical claim. | FDA-cleared/approved. | Continuous glucose monitors, FDA-cleared ECG apps. |

The line that keeps us in the first row is **claim restraint**. We can describe what the app *does* (notice patterns in journal entries, surface the user's own past words, offer reflective prompts). We cannot describe what the app *treats*, *improves*, *reduces*, or *prevents* in clinical terms.

### 1.2 The single sentence that governs every claim

The product is a **reflective journaling app that uses longitudinal memory of what users have said to surface their own patterns back to them.** It is designed with awareness of eating-disorder and broader mental-health-adjacent content. It does not diagnose, does not treat, and is not a substitute for professional care.

Every other claim is a paraphrase of, or constrained by, that sentence.

### 1.3 What this rules out structurally

- No "evidence-based treatment" framing. We are not delivering a treatment.
- No outcome promises ("reduces ED symptoms," "improves mood," "decreases relapse").
- No diagnosis or screening claims ("find out if you have an eating disorder," "are you depressed?").
- No comparative claims against therapy, other apps, or clinical care.
- No claims that the app is "for eating disorders" — the design is ED-informed; the audience is broader than diagnosed users.
- No claims of clinical validation, FDA clearance, HIPAA compliance, or affiliation with any clinical institution unless and until those are formally true.

---

## 2. App Store category decision framework

> CLINICAL-REVIEW: Final pick for the App Store primary category is deferred to the clinical advisor. The clinical advisor's call on category determines what App Review will scrutinize most heavily and how aggressively we tune claim language. The framework below is the input to that decision, not the decision itself.

The two viable primary categories are **Health & Fitness** and **Lifestyle**. A third option, **Medical**, is excluded — that category is reviewed against medical-device and diagnostic-tool standards and is incompatible with the wellness positioning.

### 2.1 Health & Fitness

**Pros**
- Higher organic discoverability for users searching ED, mental-health, or journaling terms.
- Aligns with how users will mentally classify the app.
- Matches the actual content of the app (mental health is a Health & Fitness sub-domain).

**Cons**
- Apple's App Review applies stricter scrutiny to health claims in this category. Any phrase resembling diagnosis, treatment, or symptom-reduction is more likely to be rejected.
- Health & Fitness apps are more likely to be flagged for App Tracking Transparency, health data handling, and HealthKit conformance even when we do not integrate HealthKit.
- More likely to be compared by reviewers to medical-device standards in edge cases.

### 2.2 Lifestyle

**Pros**
- Lower App Review scrutiny on health claims.
- Better fit for the "thoughtful journal, not health tracker" aesthetic in `idea.md` §8.2.
- Reduces risk that a future eval write-up or marketing post is read as a clinical claim.

**Cons**
- Lower organic discoverability for the users most likely to benefit.
- Users searching for mental-health journaling tools may not encounter the app.
- Mismatch with how the product actually functions.

### 2.3 Recommended posture pending clinical-advisor decision

Default-lean toward **Lifestyle** for v1. The wellness positioning is the load-bearing constraint, and Lifestyle is the category whose review standards align with that constraint. Discoverability cost is real but recoverable through subtitle, keywords, and outside-the-store acquisition.

A reconsideration trigger: if growth depends materially on Health & Fitness category search, revisit with the clinical advisor and tighten claim language across all surfaces before the category change.

> CLINICAL-REVIEW: Confirm category choice. Confirm whether to declare any HealthKit-adjacent data type (we do not use HealthKit in v1; declaration is the question).

---

## 3. Claims surface

The "claims surface" is every place the product makes a statement about itself: store listing, in-app onboarding, marketing site, support replies, press responses, social media. Every surface inherits the constraints in §1.2.

### 3.1 What we say

**Permitted framings**
- "A reflective journaling app with longitudinal memory."
- "Notices patterns in what you've written and surfaces them back to you."
- "Designed for people who want to think more carefully about what they're going through."
- "Built with awareness of eating-disorder and broader mental-health content."
- "Helps you see your own words across time."
- "A calm space for journaling, with thoughtful prompts."
- "Private by design. Your journal stays yours."
- "Not therapy. Not a crisis service. A tool for reflection."

**Permitted descriptors for what the app does**
- "Surfaces patterns" / "notices themes" / "reflects your own words back to you."
- "Asks thoughtful questions" / "offers reflective prompts."
- "Remembers what you've told it" / "draws on what you've shared before."
- "Designed with ED-informed and mental-health-informed care."

### 3.2 What we never say

**Diagnostic claims** — never
- "Find out if you have [condition]."
- "Screens for [condition]."
- "Detects [condition]."
- "Identifies [diagnosis]."
- "Diagnoses [anything]."

**Treatment / efficacy claims** — never
- "Treats [condition]."
- "Reduces symptoms."
- "Improves [clinical outcome]."
- "Clinically proven."
- "Evidence-based treatment."
- "Therapy in your pocket."
- "Cures," "heals," "fixes," "manages your disorder."

**Comparative-outcome claims** — never
- "Better than therapy."
- "As effective as a therapist."
- "Replaces / substitutes for clinical care."
- "Faster recovery."
- "Reduces relapse."

**Medical-device adjacency** — never
- "FDA-cleared," "FDA-approved," "medically validated."
- "HIPAA-compliant" (until and unless that is formally established and a BAA path is live).
- "Prescription required."

**Other framings to avoid**
- Anything implying the app is "for eating disorders" as a category (the design is informed; the audience is broader).
- "Recovery app" — implies clinical recovery model.
- "Healing journey" — implies clinical outcome.
- "AI therapist" / "AI counselor" / "AI coach" — implies clinical role.
- Symptom-tracking language ("track your symptoms"). We track behaviors the user chooses to log, not symptoms.
- Numerical efficacy claims of any kind ("80% of users feel better," etc.).
- Any phrase that could be read as a promise.

### 3.3 Per-surface application

**App Store listing**
- Subtitle: short, descriptive, no claims. Example draft: "Reflective journaling with longitudinal memory." > PRODUCT-DECISION: Final subtitle wording.
- Promotional text: describes what the app does (notices patterns, reflects your words back). No outcomes.
- Description: opens with the wellness sentence in §1.2. Includes the limitations sentence ("not therapy, not a crisis service") in the first screen of the description.
- Keywords: include "journal," "reflection," "writing," "mindfulness." Exclude "anorexia," "eating disorder," "depression," "anxiety," and any DSM-coded term. ED-informed design is in the description, not the keywords.
- Screenshots: show chat, insights, and intake screens with neutral fixture text. Never show a screenshot that could be read as a clinical exchange.

**In-app onboarding strings**
- Welcome screen: brief, calm. The wellness sentence and the limitations sentence both appear before any data collection.
- Intake framing: "A few questions to help us understand where you're starting from" (per `idea.md` §6.1). Never "an assessment," "a screening," "a test."
- The intake instruments (EDE-QS, PANAS, SDT items) are not surfaced to the user as named instruments or as scores in v1 (per `idea.md` §6.1).

**Marketing site**
- Above the fold: the wellness sentence verbatim.
- A "what this is and is not" section appears in the top third of the page, not buried in a footer.
- Crisis resources (988 and Crisis Text Line) appear in the footer of every marketing page.
- No testimonial that contains a clinical outcome claim, even attributed to a user. (User testimonials are restricted to descriptive experience: "the app noticed something I hadn't," not "the app reduced my [symptom]".)

**Support copy**
- Default opening for any ambiguous mental-health support inquiry: "We're not therapy and we're not a crisis service. If you're in crisis, please reach 988 or text HOME to 741741."
- Never: "I'm sorry to hear that, let me help you with that symptom" — we don't diagnose or treat in support either.
- Refunds, account issues, and feature questions follow standard support patterns.

---

## 4. Disclaimers — exact text drafts

These are the strings the product renders in specific moments. They are drafts; the clinical advisor and legal reviewer sign off before launch.

### 4.1 App launch screen (first cold-start of the app)

> egosyntonic is a reflective journaling app. It is not therapy, not a crisis service, and not a substitute for professional care.
>
> If you're in crisis, call or text 988 in the US, or text HOME to 741741 to reach the Crisis Text Line.

This screen is dismissed by tapping continue. The launch-screen disclaimer is shown on first cold-start and re-shown after a major version update.

### 4.2 Intake gate (before the first intake question)

> Before we start, a few things to know.
>
> This app is for reflection, not treatment. It is not therapy, and it is not designed to handle a crisis.
>
> Some of the questions next ask about how you've been eating, feeling, and coping. You can skip any question. You can stop at any time. What you share stays private to your account.
>
> If you are in crisis, please reach 988 (call or text) or the Crisis Text Line (text HOME to 741741) before continuing.

User taps "I understand" to continue. The state document records the timestamp of this acknowledgement.

### 4.3 Persistent footer in settings

> egosyntonic is a reflective journaling tool. It is not therapy, not medical advice, and not a crisis service.
>
> In crisis? Call or text 988, or text HOME to 741741.

Always visible at the bottom of the settings tab. Tappable to a longer page that includes the full safety-resources list (kept in `docs/safety_templates.md`).

### 4.4 Crisis-flagged moments (rendered in chat when the safety pipeline fires)

> CLINICAL-REVIEW: Exact wording of the in-chat crisis template is owned by `docs/safety_templates.md` and is reviewed by the clinical advisor. The string below is a placeholder for cross-reference only and is not the canonical copy.

> I want to pause here. What you just shared sounds really hard, and I'm not the right tool for what you might need right now.
>
> If you are in immediate danger or thinking about hurting yourself, please reach out to someone who can help right now:
>
> - 988 (call or text) — Suicide and Crisis Lifeline.
> - Crisis Text Line — text HOME to 741741.
>
> If you have a therapist, treatment team, or someone you trust, this is a good moment to reach out to them. I'll be here when you come back.

The crisis template is fixed copy. Generation does not paraphrase it. The critic verifies the template was used verbatim when a safety flag fired (per `idea.md` §3.4, §9.1).

### 4.5 Limitations re-surfacing

When the system detects sustained reliance — e.g., several consecutive sessions of high-distress content without external support mentioned — the receptivity head surfaces a gentle reminder. > CLINICAL-REVIEW: Threshold and wording for the sustained-reliance reminder. Draft:

> I notice we've been talking about some heavy things lately. I want to remind you that I'm a reflection tool, not a therapist. If you have someone you can talk to — a therapist, a doctor, a trusted person — this might be a moment to lean on them too.

---

## 5. Privacy nutrition labels

Apple's App Privacy framework (the "nutrition labels") declares every data type the app collects, how it's linked to the user, and whether it's used for tracking. The product is a heavy collector by design; the disclosure stance is **over-disclose, never under-disclose.**

The mapping below is the working declaration. Final values are confirmed against the implementation when the iOS shell lands in Phase 2.

### 5.1 Data linked to the user

| Data type | Apple category | What it is | Why we collect it | Used for tracking? |
|---|---|---|---|---|
| Email address | Contact Info | Sign in with Apple relay address. | Account identity. | No |
| User ID | Identifiers | Firebase Auth UID. | Account identity, partitions all data. | No |
| Free-form journal text | User Content (Other User Content) | Everything the user writes in chat or intake. | Core product function (reflection + memory). | No |
| Intake responses | Sensitive Info (Health & Fitness; Other Data Types) | Responses to EDE-QS, PANAS, SDT items. | Baseline state for the reasoning pipeline. | No |
| Logged behaviors | Sensitive Info; Health & Fitness | User-logged entries on eating, body-checking, exercise, etc. | Inputs to the network head. | No |
| Inferred features | Other Data Types | Pipeline outputs: affective valence, network nodes activated, etc. | Reasoning and retrieval. | No |
| Crash data | Diagnostics | If Crashlytics is enabled with scrubbing. | Stability. | No |
| Performance data | Diagnostics | Latency, error rates, pipeline-step timings. | Reliability. | No |

> PRODUCT-DECISION: Whether Firebase Crashlytics is enabled in v1, given the BAA-eligibility posture in the plan. Default: enabled with strict scrubbing.

### 5.2 Data not linked to the user

In v1 we do not collect any unlinked data. There is no third-party analytics SDK, no advertising SDK, no third-party crash reporter outside Firebase Crashlytics, and no telemetry beyond what's listed above.

### 5.3 Data used for tracking

None. The app does not engage in App Tracking Transparency-relevant tracking (no advertising network, no cross-app data sharing). The ATT prompt is therefore not shown.

### 5.4 Sensitive content disclosure

The privacy nutrition labels include a "Sensitive Info" category. We declare it because:
- Intake instruments solicit information about eating, mood, and psychological need-state.
- Free-form journal text and inferred features can include sensitive content the user has chosen to share.

We declare Health & Fitness even though we do not use HealthKit and we do not track quantitative health metrics, because the journal content frequently references eating, body, and mental state.

---

## 6. Reviewer talking points (App Review)

App Review will scrutinize this app along three axes. The points below are the prepared response for each. Keep these handy in support and in the App Review notes attached to the submission.

### 6.1 "Is this a medical app?"

Likely trigger: ED-related vocabulary in the description, mention of journaling about eating, intake questions that resemble screening.

Response:
- The app is a reflective journaling tool. It does not diagnose any condition. It does not deliver treatment. It does not make clinical claims.
- Intake questions help calibrate the journal's reflective prompts to where the user is starting from. They are framed as "a few questions" rather than as a screening or assessment.
- The app surfaces the user's own words back to them; it does not produce diagnoses, scores, severity ratings, or predictions.
- Disclaimers ("not therapy, not a crisis service, not a substitute for professional care") are surfaced at launch, at intake, and in settings.
- No FDA clearance is claimed. The app operates within the FDA's General Wellness Policy.

### 6.2 "How do you handle crisis?"

Likely trigger: the app discusses mental-health content. App Review increasingly asks every mental-health app this.

Response:
- The pipeline includes a safety layer that runs before reasoning. If the user expresses suicidal ideation, intent to self-harm, or signals of acute medical concern, the response is replaced with a fixed safety template that:
  - validates the user,
  - surfaces 988 and Crisis Text Line (text HOME to 741741),
  - states the app is not a substitute for emergency care,
  - encourages contact with a therapist, treatment team, or trusted person.
- The safety template is fixed copy. The model does not paraphrase it. A separate critic call verifies the template was used.
- The app does not describe means of self-harm or suicide under any circumstances. This is enforced as both a model instruction and a deterministic post-generation filter (per `idea.md` §9.2).
- The app does not provide numerical guidance on calories, weight, exercise duration, or fasting (per `idea.md` §9.3). This is also model-instructed and post-filter-enforced.

### 6.3 "How is sensitive user data handled?"

Likely trigger: declared "Sensitive Info" and "User Content" data types.

Response:
- Data is encrypted at rest and in transit (`idea.md` §10).
- All data lives in a single Google Cloud project. The only third-party processors are Google services (Gemini API for inference, Vertex AI for vector storage, Firestore for state, Cloud Run for compute). No analytics, no advertising, no third-party data sharing.
- Users can export all of their data at any time. Users can delete individual entries, individual logged behaviors, or their entire account; deletion removes data from retrieval indices within a defined window.
- The privacy policy explicitly states there is no third-party sale or sharing of data.
- Sign in with Apple is the supported sign-in method (App Store requirement for third-party sign-in is satisfied; for users without other accounts, Sign in with Apple is the canonical path).

### 6.4 Other likely scrutiny

- **Age requirement.** The product is for users 18 and older. Confirmed via intake age gate and reflected in the terms of service. The app is not designed for minors and has no kids-category submission.
- **Subscriptions and IAP.** > PRODUCT-DECISION: Monetization model for v1. Defaults: free during Phase 1 closed beta, with no IAP. Subscription model deferred until after closed beta.
- **Sign in with Apple.** Required if any third-party sign-in is offered; we include Sign in with Apple by default.
- **In-app purchases referencing health outcomes.** Not applicable; no IAP in v1.

---

## 7. Open items pending decision

- > CLINICAL-REVIEW: App Store primary category (Health & Fitness vs Lifestyle).
- > CLINICAL-REVIEW: Exact wording of the in-chat crisis template (owned by `docs/safety_templates.md`).
- > CLINICAL-REVIEW: Threshold and wording for the sustained-reliance reminder.
- > PRODUCT-DECISION: Final App Store subtitle and short description.
- > PRODUCT-DECISION: Whether Firebase Crashlytics is enabled in v1.
- > PRODUCT-DECISION: Monetization model and timing.
- > PRODUCT-DECISION: Marketing site copy — drafted from this document but not yet written.
