# Privacy Policy (Draft v1)

> **DRAFT — REQUIRES LEGAL REVIEW BEFORE ANY EXTERNAL USE.**
>
> This is a working draft written to translate the data-handling commitments in `idea.md` §10 into plain-English language a user can read. It is **not** the policy that ships. Counsel must review and rewrite as needed before this is published, linked from the App Store, or used in any external context. Specific items flagged inline with `LEGAL-REVIEW`, `CLINICAL-REVIEW`, or `PRODUCT-DECISION` are open questions for the appropriate reviewer.

**Effective date:** *to be set on publication.*

---

## What this document is

This is the privacy policy for **egosyntonic**, a reflective journaling app. It explains what information we collect when you use the app, why we collect it, who we share it with (and don't), how long we keep it, and what you can do with it.

We've written this in plain English. If anything here is unclear, contact us at the address at the bottom of this page.

A short summary of what matters most:

- Everything you write in the app is stored in your account so the app can remember it across time. Remembering across time is the core feature.
- We do not sell your data. We do not share your data with advertisers, analytics services, or any third party other than the Google Cloud services that run the app itself.
- Everything is encrypted, both when it's moving between your phone and our servers and when it's stored.
- You can export everything you've shared. You can delete individual entries, individual logged behaviors, or your entire account.
- This app is for adults (18+). It is not designed for children.
- This app is **not therapy**, not a crisis service, and not medical care. If you are in crisis, please reach 988 (call or text) or text HOME to 741741 to reach the Crisis Text Line.

---

## What information we collect

We collect three kinds of information.

### 1. Information you give us directly

- **Your account.** When you sign in with Apple, we receive an email address (or Apple's private relay email) and a unique user identifier. We use this to recognize you across sessions.
- **Your intake responses.** When you first sign up, we ask a series of questions about how you've been doing. Your answers are stored in your account.
- **Your journal entries and chat messages.** Everything you write in the app is stored.
- **Things you log.** If you choose to log meals, behaviors, or how you're feeling at a given moment, those entries are stored.
- **Your settings and preferences.** Including how often you want the app to surface observations, what kinds of content you want to engage with, and anything else you tell the app you prefer.

### 2. Information the app derives from what you give us

The app reads what you've written and produces structured notes about it — for example, "this entry mentions feeling overwhelmed at work" or "this entry references a behavior the user has logged before." These structured notes are stored alongside your entries so the app can find patterns over time.

The app also keeps an evolving picture of what you've talked about and what seems important to you. This picture updates after every conversation. You can view what the app currently understands about you in the "What I've learned about you" view in the app, and you can correct anything that's not right.

### 3. Information about how you use the app

- **Operational logs.** When the app works, we record what happened (how long the response took, whether anything failed, how much each step cost) so we can keep it running well. These logs don't include the content of your messages.
- **Crash reports.** If the app crashes, we receive a report that helps us fix the bug. We use Google's Firebase Crashlytics for this. Crash reports are scrubbed to remove any content from your messages.
- **Feedback.** If you mark a message as helpful or not helpful, or if you correct something the app told you, we record that so we can improve.

> PRODUCT-DECISION: Whether Firebase Crashlytics is enabled in v1. If it is not, remove the relevant lines.

---

## How we use this information

We use what you share with us to do exactly one thing: run the app for you. Specifically:

- To **recognize you across sessions** so what you've shared is there when you come back.
- To **produce responses to your messages** that are informed by what you've shared before.
- To **surface patterns** in your own words back to you, when the app's reasoning layer notices something that might be useful.
- To **keep the app running well**: monitor latency, debug crashes, prevent abuse, manage cost.
- To **honor your safety**: detect signals that you may be in crisis and respond with crisis resources and a recommendation to reach professional support.

We do not use your data:

- To **train any AI model.** Your messages and journal entries are not used to train Google's models, our own models, or anyone else's. (Google's terms for the services we use prohibit your inputs from being used to improve their models when we send them through the appropriate API channels.) > LEGAL-REVIEW: confirm exact language matches Google's current Gemini API and Vertex AI terms.
- To **advertise to you** or to anyone else. The app does not contain advertising.
- To **profile you** for commercial purposes outside the app itself.
- To **share with any third party** other than the Google Cloud services that run the app.

---

## Who we share information with

We use Google Cloud to run the app. The services we use are:

- **Firebase Authentication** — for sign-in.
- **Cloud Firestore** — to store your account, your entries, the structured notes the app derives, and the app's evolving picture of what you've shared.
- **Vertex AI Vector Search** — to find relevant past entries when you write something new.
- **Gemini API** — Google's large language model, used to read your messages and produce responses.
- **Cloud Run** — to run the backend that orchestrates the app.
- **Cloud Tasks, Cloud Logging, Cloud Trace, Secret Manager, Artifact Registry** — supporting services for reliability, monitoring, secret storage, and deployment.

All of these are Google Cloud services running within a single Google Cloud project that we control. Google processes your data only as needed to run these services for us, under Google's data-processing terms. > LEGAL-REVIEW: confirm scope and references to Google's data-processing addendum.

**We do not share your data with anyone else.** No advertisers. No analytics companies (we don't use any). No data brokers. No other apps. No clinical institutions or insurance companies. No researchers outside our team — research on user data, if it ever happens, requires separately-recorded informed consent and is not how this app operates today.

If we are ever legally required to disclose data (subpoena, court order), we will push back where appropriate and notify you where we are legally permitted to. > LEGAL-REVIEW: confirm the right language for disclosure obligations under applicable law.

---

## How long we keep your information

- **Your account and your entries** are kept as long as your account exists.
- **The app's derived notes** about your entries are kept as long as the entries they're derived from exist.
- **Operational logs** are kept for up to 90 days, then automatically deleted. > PRODUCT-DECISION: confirm retention window once observability is wired.
- **Crash reports** are kept for up to 90 days. > PRODUCT-DECISION: confirm Crashlytics retention window.
- **Backups** are kept for up to 30 days after a deletion to allow recovery from accidental destructive changes.

When you delete your account, we delete your data within **30 days**. Backups expire on the same window. After that, your data is gone from our systems.

---

## How we protect your information

- **In transit:** every connection between the app and our servers uses TLS encryption.
- **At rest:** all data stored in Google Cloud services is encrypted at rest by default.
- **Access controls:** only the systems that need your data have access to it, scoped through identity and access management policies. Human access by our team is limited to debugging and reviewing specific situations (see "Human review" below), is logged, and is governed by access controls.
- **Audit logs:** reads and writes to the central document representing your state are logged to a separate audit trail.

No security is absolute. If we ever experience a breach affecting your data, we will notify you and applicable regulators as the law requires. > LEGAL-REVIEW: confirm specific breach-notification language for applicable jurisdictions.

---

## Human review

A small number of conversations are reviewed by our team to help us improve the app and ensure it's behaving safely:

- **Safety-flagged conversations.** When the app's safety layer flags a conversation (for example, because it detected crisis language), members of our team and our clinical advisor may review what happened to make sure the app responded appropriately.
- **Conversations where you marked an insight as wrong.** When you correct something the app told you, we review what happened to understand why the app got it wrong and to improve.
- **A small random sample of other conversations.** During closed beta, a small random sample of conversations is reviewed by our team to check for problems the app didn't flag.

Reviews are limited to what's needed to understand the situation. Reviewer access is logged. We do not use review for any purpose other than improving the app and ensuring safe behavior.

> LEGAL-REVIEW: confirm this disclosure is sufficiently specific, and that it's properly framed for the beta participation agreement separately.

---

## Your choices

### Export

You can export everything you've shared with the app — your entries, logs, intake responses, the app's derived notes, and the app's current picture of what it understands about you. The export is provided as a structured archive you can download.

### Delete

You can delete:

- **An individual entry or message.** It's removed from the app and from the systems that find related entries.
- **An individual logged behavior.** Same.
- **Your entire account.** Everything is deleted within 30 days.

Deletion is permanent. We do not maintain "ghost" records of deleted entries beyond the 30-day backup window.

### Correct

In the app's "What I've learned about you" view, you can mark anything the app has inferred as "not quite right" or "this isn't me anymore." Corrections update the app's evolving picture of you and inform future reasoning.

### Restrict

You can adjust how often the app surfaces observations to you, what you want it to track, and what kinds of content you want to engage with. These settings are honored immediately.

---

## Children

This app is for adults aged 18 and older. We do not knowingly collect information from anyone under 18. If you believe a minor has signed up, contact us and we will delete the account.

> CLINICAL-REVIEW: Confirm the 18+ age cut. The product is not designed for adolescents in v1 even though the underlying clinical literature includes adolescent populations. The minimum age may be revisited with the clinical advisor in a later version with a separately-designed intake.

---

## International users

The app is operated from the United States and data is stored on Google Cloud infrastructure located in the United States. If you are using the app from another country, you understand that your data is transferred to and processed in the United States.

> LEGAL-REVIEW: GDPR / UK GDPR considerations for any non-US users, including lawful-basis statements, data subject rights, and data transfer mechanisms. The current draft does not constitute a GDPR-compliant policy.

---

## Changes to this policy

If we change this policy, we will post the new version in the app and on our marketing site. Material changes (anything that affects what data we collect, how we use it, or who we share it with) will be communicated to you directly — for example, via an in-app notice — before they take effect.

---

## Contact

> PRODUCT-DECISION: Contact address for privacy questions. Default: a `privacy@` address on the product domain once registered.

Questions? Concerns? Want to request a copy of your data, or have an account deleted? Reach out at *to be filled in*.

---

## Crisis resources

This app is not therapy and not a crisis service. If you are in crisis or thinking about hurting yourself:

- Call or text **988** (Suicide and Crisis Lifeline, US).
- Text **HOME** to **741741** to reach the Crisis Text Line.

---

## Open items for review

- > LEGAL-REVIEW: end-to-end pass by counsel before any external use.
- > LEGAL-REVIEW: exact wording on Google's data processing terms reference.
- > LEGAL-REVIEW: jurisdiction-specific breach-notification commitments.
- > LEGAL-REVIEW: GDPR / UK GDPR / state-law (CCPA/CPRA etc.) compliance pass.
- > LEGAL-REVIEW: language and form of disclosure on human review, including its placement in the beta agreement.
- > CLINICAL-REVIEW: confirm 18+ age cut and the framing for it.
- > PRODUCT-DECISION: contact address; retention windows for operational logs and crash data; whether Crashlytics is enabled at all.
