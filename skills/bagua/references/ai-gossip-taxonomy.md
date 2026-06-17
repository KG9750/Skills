# AI Gossip Taxonomy

## Categories

- `founder-drama`: founder, CEO, investor, or public figure conflict.
- `product-fail`: launch failure, outage, hallucination incident, pricing backlash, policy reversal.
- `benchmark-dispute`: benchmark gaming, eval dispute, misleading charts, replication fight.
- `legal-dispute`: lawsuit, regulatory complaint, trade-secret claim, or legal accusation involving an AI company, product, or public figure.
- `funding-rumor`: financing, acquisition, valuation, investor conflict, runway rumor.
- `open-source-conflict`: license fight, maintainer dispute, fork drama, contributor accusation.
- `paper-attribution`: credit dispute, authorship fight, dataset or citation controversy.
- `employee-leak`: public employee claim, resignation thread, culture dispute.
- `safety-ethics`: safety policy, model misuse, alignment dispute, whistleblower claim.
- `platform-policy`: API access, moderation, model marketplace, account suspension.
- `community-backlash`: broad community criticism without one clear dispute owner.

## Built-In Entity Seeds

Keep entities maintainable and non-exhaustive. Users should extend long-term tracking through local config.

Companies and labs:
OpenAI, Anthropic, xAI, Google DeepMind, Meta AI, Mistral, Perplexity, Hugging Face, Cursor, Cognition, Scale AI, Character.AI, Midjourney, Runway, ElevenLabs, Stability AI.

Products and projects:
ChatGPT, Claude, Grok, Gemini, Llama, Mistral, Le Chat, Perplexity, Cursor, Devin, Sora, Whisper, Stable Diffusion, ComfyUI, vLLM, LangChain, LlamaIndex.

Public-figure search should be configured separately from company and product search. Use public names for discovery, but apply stricter wording and credibility labels in reports.

## Controversy Signals

English:
drama, beef, dispute, accused, accusation, fired, resigned, lawsuit, fraud, fake benchmark, benchmark gaming, misleading, plagiarism, copied, leaked, meltdown, apology, deleted, retracted, called out, exposed, scam.

Chinese keywords may be useful for report phrasing, but v1 does not collect Chinese social platforms directly.
