# Scoring

## Heat Score

Heat prioritizes spread over raw engagement. Use a 0-100 score.

Default weights:

- Cross-platform spread: 35
- Engagement and velocity: 20
- Source prominence: 15
- Controversy strength: 15
- Novelty and recency: 10
- Evidence richness: 5

Cross-platform spread should be the highest weight because single-platform engagement is easily distorted by large accounts.

Recency is computed from item timestamps. Items outside `general.heating_days` are filtered before scoring. Items inside `general.fresh_hours` count as fresh. Unknown timestamps are retained but receive a reduced recency component.

By default, normalization requires a gossip signal before scoring. Ordinary product launches, paper releases, and neutral reposts should be filtered unless their text contains a controversy term or maps to a conflict category.

## Credibility Score

Credibility uses a separate 0-100 score.

Default weights:

- First-party source: 35
- Verifiable public evidence: 25
- Independent corroboration: 20
- Source reputation: 10
- Claim specificity: 10

Screenshots, deleted-post caches, and secondhand summaries may support an event, but they should not outrank accessible first-party sources.

Search snippets are treated cautiously. A single generic search snippet should remain a weak signal. A search-backed event may rise to `rumor` when it comes from a reputable source domain or when multiple independent domains point at the same clustered event. This does not make the event confirmed; it only means the lead is traceable enough to follow.

## Main Board vs Early Signals

Put events in Main Board when they have high credibility, first-party evidence, or multiple independent public sources. Put events in Early Signals when heat is high but evidence is thin, secondhand, anonymous, or still unfolding.

Never write an Early Signal headline as a confirmed fact.

Use neutral wording for weak signals. Do not describe a low-evidence item as "升温" unless it has already passed the gossip gate and has meaningful corroboration.

## Deduplication and Clustering

Use two layers:

1. Deduplicate exact URL, platform post id, or normalized canonical id.
2. Cluster into events using primary entity, category, date bucket, and a lightweight topic signature derived from high-signal terms/text.

If cluster confidence is low, keep candidates separate.
