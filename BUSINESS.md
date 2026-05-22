# SimAB — Monetization Strategy

> Open core + hosted SaaS + GCP Marketplace. The clean answer is "yes to all of it," but the choices need to be made in the right order.

---

## The short version

| Question | Answer |
|---|---|
| Must the hackathon submission be open source? | **Yes — hard requirement.** Must have a detectable license in the repo. |
| Can open-source projects be sold on GCP Marketplace? | **Yes.** Postgres, MongoDB, Redis, n8n, PostHog all do this. |
| What's the right license? | **MIT for the hackathon**, consider switching to **AGPL or FSL** after launch if hosting takes off. |
| What's the business model? | **Open core + hosted SaaS** — free to self-host forever, paid for someone to operate it for you. |
| Revenue paths? | Three: direct subscriptions (Stripe), GCP Marketplace (billed by Google), enterprise contracts. |

---

## Why open source isn't in conflict with monetization

This trips up a lot of first-time builders. Open source means *you can't stop others from running the code*. It doesn't mean you can't sell anything related to the code. The most successful AI / dev-tool companies of the last decade all built businesses around open-source cores:

| Company | OSS license | What they sell |
|---|---|---|
| MongoDB | SSPL (was AGPL) | MongoDB Atlas — managed hosting |
| PostHog | MIT | PostHog Cloud — managed, team features |
| Supabase | Apache 2.0 | Supabase Cloud — managed Postgres + tooling |
| n8n | Sustainable Use License | n8n Cloud — managed workflow hosting |
| Plausible | AGPL | Plausible.io — managed analytics |
| Cal.com | AGPL | Cal.com Cloud — managed scheduling |
| Sentry | FSL | Sentry SaaS — managed error tracking |

**The pattern:** the code is free. The convenience of not running it is what you pay for. SimAB fits this pattern exactly — most users won't want to run a SQLite + Gemini key + dashboard themselves.

---

## License choice

Three reasonable choices for SimAB, each with a different defensive posture:

### MIT (recommended for the hackathon)
- **Pros:** Maximally permissive, accepted everywhere, simplest. Required for some downstream use cases (companies that ban AGPL).
- **Cons:** A competitor can fork SimAB, host it under a different name, and you have no recourse. AWS did this to MongoDB and ElasticSearch.
- **When to choose:** Hackathon submission, early validation phase, no immediate competitive threat.

### AGPL v3
- **Pros:** "Copyleft" — if anyone hosts a modified version, they must release their changes back. This protects against managed-hosting competitors.
- **Cons:** Many enterprises (especially the ones with budget) ban AGPL. Limits adoption.
- **When to choose:** Once you have a hosted offering with paying customers and want to prevent AWS/GCP from cloning it.

### Functional Source License (FSL)
- **Pros:** Sentry's invention. Restrictive for 2 years (no competing hosted offering allowed), then automatically becomes Apache 2.0 / MIT. Best of both worlds.
- **Cons:** Newer, less widely understood, technically not OSI-approved "open source" — some hackathon judges may interpret rules strictly.
- **When to choose:** When the project is mature enough that someone might want to clone the hosted version. Probably year 2 for SimAB.

**My recommendation:** Ship MIT for the hackathon. The "open source" requirement in the rules language calls for a detectable, recognized license — MIT is the safest. Plan to revisit in 6 months if a hosted SaaS gets traction.

---

## The business model: three tiers + enterprise

### Tier 0: Self-hosted (free, forever)

```
Audience:   Developers, hobbyists, scrappy startups
Price:      $0
What:       Full source, self-hosted, bring-your-own Gemini key
Costs you:  Nothing — they cover their own LLM costs
Revenue:    Brand awareness, contributor pipeline, top-of-funnel
```

This is what gets shipped to the hackathon and posted on GitHub. It's the entirety of the open-source repo. Everything else is built on top.

### Tier 1: Hosted Free ($0/month)

```
Audience:   Solo PMs, designers trying it out, blog readers
Price:      $0
What:       Hosted at app.simab.io with a generous free tier
Limits:     5 runs/month, 1 user, 30-day run history
Costs you:  ~$0.40/user/month in Gemini API costs (paid tier)
Revenue:    None directly — this is the funnel for paid tiers
```

The hosted free tier is what makes SimAB accessible to PMs who can't self-host. The economics work: at $0.08 per pretest on the paid Gemini tier, 5 runs costs you $0.40 in COGS. Slack a few of these users into the Growth tier and you make it back.

### Tier 2: Hosted Growth ($29/month)

```
Audience:   Solo founders, individual marketers, freelancers
Price:      $29/month
What:       Personal hosted workspace
Limits:     100 runs/month, 1 user, unlimited history
Includes:   Persona library, GA4 connector, MCP server access,
            markdown export, Slack notifications
Costs you:  ~$8/user/month in Gemini costs
Margin:     ~70% gross
```

The pricing sweet spot for solo users who care enough to pay but won't justify a team plan. The MCP server + GA4 connector are the value props that justify the upgrade from free.

### Tier 3: Hosted Team ($99/month)

```
Audience:   Marketing teams (2–10 people), early-stage product teams
Price:      $99/month flat — not per-seat
What:       Shared team workspace
Limits:     500 runs/month, up to 10 users, shared persona library
Includes:   Everything in Growth + team persona library,
            Slack integration, Linear webhook, weekly scheduled audits
Costs you:  ~$40/team/month in Gemini costs
Margin:     ~60% gross
```

Flat team pricing (not per-seat) is the right call for a tool that gets used a few times a week. Per-seat pricing would discourage adding designers and PMs who only check in occasionally — defeating the whole multi-persona positioning.

### Tier 4: Enterprise (custom, via GCP Marketplace)

```
Audience:   Companies with procurement, compliance, SSO needs
Price:      Starts at $1,500/month, custom from there
What:       Enterprise hosted or private deployment
Includes:   SSO/SAML, audit logs, SOC2 deployment, SLA,
            unlimited runs, custom MCP integrations, dedicated support,
            data residency options (US/EU)
Distribution: Google Cloud Marketplace listing — billed via GCP
```

This is where GCP Marketplace shines. Enterprise customers already have a GCP billing relationship and procurement processes. Listing on the marketplace means they can buy SimAB through their existing vendor — no new contracts, no payment integration, no procurement cycle. Google takes ~20% but unlocks pre-qualified buyers.

---

## Unit economics

Numbers I can actually defend:

**Cost per pretest (paid Gemini tier, post-free-quota):**

| Agent call | Tokens | Cost |
|---|---|---|
| BriefNormalizer (Flash, vision) | ~3,000 | $0.0009 |
| ScenarioBuilder (Flash) | ~4,000 | $0.0012 |
| SimAgent × 20 (Flash-Lite, vision) | 20 × 1,200 = 24,000 | $0.024 |
| BiasAuditor (Flash) | ~5,000 | $0.0015 |
| Synthesizer (Pro) | ~8,000 | $0.052 |
| **Total per pretest** | ~44,000 | **~$0.08** |

Hosting overhead: Cloud Run free tier covers ~2M requests/month. Past that, ~$0.0001 per request. At 1,000 paying users × 100 runs/month = 100K requests = well within free tier.

**Margins at scale:**
- Growth tier ($29): user does 50 runs avg → $4 COGS → 86% gross margin
- Team tier ($99): team does 200 runs avg → $16 COGS → 84% gross margin
- Enterprise ($1,500): unlimited runs but maybe 1,000/month → $80 COGS → 95% gross margin

These are *good* margins. The product works as a business.

**Break-even math:**
- Need ~$10K/month MRR to cover one founder's time + infra
- 350 Growth users *or* 100 Team accounts *or* 7 Enterprise contracts
- Year 1 realistic target: 30 paying customers split across tiers ≈ $3-5K MRR

---

## Publishing on GCP Marketplace — the actual steps

Open source doesn't matter to the marketplace. What matters is that you have a deployable, billable service. Here's what's required:

### Prerequisites (do these in any order)
1. **Become a Google Cloud Partner** — apply via partneradvantage.goog. Takes ~2 weeks for review. Free.
2. **Create a public producer project** in GCP that hosts the agent's container image and Agent Card.
3. **Have a working hosted version** — Cloud Run deployment of SimAB with a stable URL.

### Marketplace listing requirements
4. **Agent Card** at `/.well-known/agent-card.json` — already in the scaffold. ✓
5. **A2A endpoints** — `POST /a2a/v1/tasks` and `GET /a2a/v1/tasks/{id}`. Already in the scaffold. ✓
6. **Pricing model** — choose one:
   - **Subscription** (flat monthly, like Team tier)
   - **Usage-based** (per pretest run)
   - **Outcome-based** (per "successful" outcome — risky for early product)
7. **Terms of Service** — publish a basic ToS document.
8. **Privacy policy** — publish a data-handling policy.
9. **Support SLA** — define response times for paying customers.

### Billing integration (the technical bit)
10. **Subscribe to Pub/Sub topic** that delivers entitlement events from Cloud Commerce API.
11. **Implement entitlement handler** — when a customer purchases your agent, you receive an event; your code auto-provisions their workspace.
12. **Implement metering API calls** if usage-based — report consumption back to Google.

The scaffold has the Agent Card and A2A endpoints. The Pub/Sub + entitlement handler is roughly 200 lines of additional code — a few days of work post-competition.

### Pricing the marketplace listing
- Google takes 3% of revenue (this was higher before; check current rate)
- *Plus* whatever your hosting costs are
- Recommendation: price marketplace listings 30-50% higher than direct, to account for Google's cut and the "easier procurement" premium that enterprise customers will pay

So if direct Team tier is $99/month, marketplace Team tier could be $149/month.

---

## What stays open vs what's proprietary

This is the most important strategic decision. The rule: **open source everything that's commodity, keep proprietary everything that compounds.**

### Open source (in the repo, MIT-licensed)
- The five agents (BriefNormalizer, ScenarioBuilder, SimAgent, BiasAuditor, Synthesizer)
- The stigmergy pattern + SQLite shared state
- The MCP server
- The Next.js dashboard
- The GA4 connector
- Markdown export, share pages, Slack integration
- The A2A endpoints + Agent Card
- The Pydantic schemas

**Why open these:** Anyone can rebuild them in a weekend if they're good enough. The moat isn't the code.

### Closed / hosted-only (not in the public repo)
- **Multi-tenant workspace layer** — auth, billing, team management
- **Persona library "intelligence"** — the proprietary scoring of which personas surface real issues vs noise (compounds with run history)
- **Cross-tenant insights** — *opt-in* benchmarks like "your conversion friction is 30% higher than typical SaaS pricing pages" (only useful if you have many tenants' data)
- **Enterprise compliance modules** — SSO, audit logs, SOC2 attestations
- **Premium personas** — vetted persona libraries for specific industries (healthcare, fintech, e-commerce)
- **Marketplace billing integration** — the Pub/Sub handler etc.

**The compounding moat:** the more runs the hosted SaaS sees, the smarter the persona scoring gets. A self-hosted instance never benefits from this. That's an ethical, durable competitive advantage — the hosted version is genuinely better, not artificially so.

---

## Hackathon-specific business framing

For the Devpost submission, lean into the open-source angle. Judges (especially the Arize partner judges) like to see real, deployable systems. Your pitch can include:

> "SimAB is MIT-licensed and free to self-host forever. The hosted offering at simab.io exists for teams who don't want to run their own infrastructure, with enterprise tiers available through the Google Cloud Marketplace via the A2A endpoints shown in this repo."

This signals: *I built a real product with a real business model, I'm thinking past the hackathon, and I'm not just chasing the $5K prize.* That's compelling to judges deciding between submissions of similar technical quality.

---

## Timeline

```
Month 0 (now)        : Build scaffold, submit to hackathon
Month 0.5            : Hackathon result (target: top-3 in Arize track = $2-5K)
Month 1-2            : Open source repo gets community traction
                       Set up app.simab.io with free + Growth tiers (Stripe)
Month 3-4            : First 20 paying customers ($500-1,000 MRR)
                       Apply to Google Cloud Partner program
Month 5-6            : Submit to GCP Marketplace
                       Add Team tier
Month 7-9            : First enterprise pipeline via marketplace
                       Consider switching to AGPL/FSL if needed
Month 10-12          : Target $5-10K MRR
Year 2               : $50K+ MRR target, decision point on raising vs bootstrapping
```

Realistic, not optimistic. The hackathon is the entry point, not the business plan.

---

## TL;DR

1. **Open source the entire scaffold under MIT** for the hackathon. It's required and it's the right move.
2. **Operate a hosted version at app.simab.io** with three tiers ($0, $29, $99). The hosted version handles ops, billing, team features.
3. **List on Google Cloud Marketplace** for enterprise distribution once the hosted version has traction. The Agent Card and A2A endpoints are already in the scaffold.
4. **Keep multi-tenancy, billing, and cross-tenant intelligence proprietary.** Everything that requires the hosted version to run is fair to keep closed.
5. **Switch from MIT to AGPL or FSL only if competitive cloning becomes a real threat** — typically year 2.

This is a real business model that fits the hackathon constraints, fits the product, and has been validated by every major open-source dev-tool company of the last decade.
