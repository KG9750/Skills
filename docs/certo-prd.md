# Certo（刺儿头）Skill PRD

## Problem Statement

用户在写文章、做产品原型、写代码时，经常需要一个不顺着说的审查者：它不负责安慰、润色或快速执行，而是负责发现结构漏洞、逻辑断裂、表达含混、产品定义不稳、交互不顺、架构风险、技术栈误配、代码缺陷和工程隐患。

现有通用助手往往默认合作、补全和正向推进，容易过早接受用户设定，弱化反对意见，或把“挑毛病”做成泛泛建议。用户需要一个可显式召唤的对抗式 skill：像谏官、诤臣、审稿人和代码 reviewer 一样，先找问题，再解释为什么是问题，最后给出可执行的修正方向。

## Assumptions

- Skill 名称为 `certo`，中文显示名为“刺儿头”。
- 主要运行环境是 Codex；同时通过配套 slash command 文件支持 Claude Code。
- “对抗式”指批判性、证据驱动、建设性审查，不指攻击用户、制造情绪压力或为了挑错而挑错。
- 默认审查对象来自用户提供的文章、产品说明、原型、截图、代码、diff、需求或技术方案。
- 当前 MVP 交付 `certo/SKILL.md`、`certo/agents/openai.yaml` 和 `certo/claude/certo.md`。

## Solution

创建一个名为 `certo` 的审查型 skill。用户显式调用它时，助手进入“刺儿头”模式：先界定审查对象和评判标准，再从对应专业视角输出高信号问题清单，并按严重程度排序。

`certo` 支持三类主要审查场景：

1. 文章审查：从文学、叙事、论证、结构、逻辑关系、概念一致性、语义精度、节奏和表达效果等角度挑问题。
2. 产品与原型审查：从用户目标、产品定义、信息架构、交互路径、边界状态、可用性、研发复杂度、软件架构和技术栈选择等角度挑问题。
3. 代码审查：从正确性、可维护性、复杂度、测试覆盖、接口契约、错误处理、性能、安全、并发、可观测性和工程一致性等角度挑问题。

输出必须直接、具体、可验证。它应优先指出最可能造成失败、误解、返工或质量下降的问题，而不是平均撒网式罗列建议。

## User Stories

1. As a writer, I want certo to challenge my article structure, so that I can find weak sections before publishing.
2. As a writer, I want certo to identify logical gaps in my argument, so that my claims do not rely on hidden assumptions.
3. As a writer, I want certo to point out vague wording, so that my prose becomes more precise.
4. As a writer, I want certo to separate fatal structural issues from minor wording issues, so that I know what to fix first.
5. As a writer, I want certo to question my premise, so that I can decide whether the article is built on a strong idea.
6. As an editor, I want certo to review narrative flow, so that the piece has clearer progression and tension.
7. As a product designer, I want certo to attack my product definition, so that I can discover unclear users, jobs, and constraints.
8. As a product designer, I want certo to critique interaction flows, so that users do not hit confusing dead ends.
9. As a product designer, I want certo to identify missing states, so that loading, empty, error, permission, and edge cases are not ignored.
10. As a product manager, I want certo to question scope, so that the prototype does not hide unnecessary complexity.
11. As a product manager, I want certo to identify risky assumptions, so that I can validate them before building.
12. As an engineer, I want certo to review architecture choices, so that implementation does not become brittle or overbuilt.
13. As an engineer, I want certo to challenge my technology stack, so that I can catch mismatches between tools and product needs.
14. As a developer, I want certo to review code like a strict senior engineer, so that correctness and maintainability issues surface early.
15. As a developer, I want certo to review diffs by severity, so that I can fix regressions before cosmetic concerns.
16. As a developer, I want certo to identify missing tests, so that important behavior is protected.
17. As a developer, I want certo to question abstractions, so that I do not add flexibility before it is needed.
18. As a team lead, I want certo to produce concise findings with evidence, so that review feedback can be acted on quickly.
19. As a Codex user, I want certo to work as a skill triggered by name, so that I can summon the adversarial review mode on demand.
20. As a Claude Code user, I want the core certo workflow to be portable, so that the same review behavior can be reused outside Codex.

## Confirmed Product Decisions

- Default posture is reviewer, not co-author. It gives suggestions, but does not rewrite or modify artifacts unless explicitly asked.
- Suggestions should usually give options, not only one answer. Important options must include a `刺儿头推荐`.
- Tone is calm and strict, with a little 谏官 / 诤臣 character, not roast-style sarcasm.
- If context is insufficient, ask key questions first rather than producing a weak assumption-heavy review.
- Default questioning is light; continuous interrogation is reserved for `拷问`, `grill me`, `深挖`, or similar requests.
- Main domain comes first, with cross-domain criticism when it affects success.
- Mention strengths only when needed to avoid damaging what works.
- Default output is short: 3-5 highest-risk issues. Deep review is opt-in.
- Code review centers on the diff or specified files, but may inspect direct dependencies, callers, tests, and contracts.
- Serious risks should strongly discourage a bad direction, but not block the user unless normal safety rules require refusal.
- Each review should end with a short next-action list.
- Claude Code support is file-level: include a slash command document under the skill package.
- The skill directory should be `certo/` with `SKILL.md`, `agents/openai.yaml`, and `claude/certo.md`.
- Use a weak output template: stable default sections, adaptable per artifact.
- Triggering should be medium-width: explicit critique/review/red-team language triggers it; vague "look at this" does not.
- Output language follows the user.
- If no substantial issues exist, say so clearly rather than inventing criticism.
- Use Chinese severity labels `致命 / 严重 / 一般 / 轻微`; use `Critical / High / Medium / Low` in English.
- Briefly state the review standard before reviewing.
- `致命` and `严重` findings require evidence or explicit reasoning.
- Major recommendations should include cost, benefit, and risk.
- Score by default, at the end, with strict calibration and domain-specific dimensions.
- Built-in mode words are `快刺`, `深刺`, `拷问`, and `复审`.
- `复审` compares against prior findings, checks whether each issue was resolved, and catches new issues.
- Role-specific review is supported when the user asks; the requested role takes priority over artifact type.
- User pushback should be evaluated honestly: concede when the user is right, keep challenging when the reasoning fails.
- For major findings, distinguish fact errors, logic gaps, risky assumptions, strategy disagreements, expression problems, UX failures, architecture risks, engineering defects, and missing tests.
- If the user asks for a softer tone, lower phrasing intensity but not standards. If the user asks for harsher review, increase depth rather than insult.
- `SKILL.md` uses English structure with Chinese personality and mode words.
- Include a few inline examples covering writing `快刺`, product `拷问`, and code `复审`.
- `agents/openai.yaml` should use only required UI metadata.
- `default_prompt` should be direct and mention `$certo`.
- Claude Code support should be a slash command document, not a global `CLAUDE.md` personality.
- If the user asks to implement fixes after review, ask them to choose among options when needed, then make only the confirmed changes and verify the original issue.

## Implementation Decisions

- Build the skill around a single concise `SKILL.md` as the source of truth for behavior.
- Optimize the skill for explicit invocation through words such as `certo`, `刺儿头`, `快刺`, `深刺`, `拷问`, `复审`, `挑毛病`, `审查`, `批判性审阅`, `对抗式评审`, `review`, and `red team`.
- The skill should not activate for ordinary coding or writing tasks unless the user asks for critique, review, challenge, fault-finding, or adversarial analysis.
- The default output structure should be:
  - Brief review standard
  - Top findings ordered by severity
  - Options and `刺儿头推荐`
  - Short next actions
  - Score
- For code review, findings must reference concrete files, symbols, lines, tests, or behavior when available.
- For article review, findings must reference concrete claims, paragraphs, structure positions, concepts, or wording patterns.
- For product review, findings must reference user flows, states, requirements, data models, architecture boundaries, UI controls, or operational constraints.
- Avoid large bundled references in the MVP. Add references later only if repeated review rubrics become too long for `SKILL.md`.

## Testing Decisions

- Test the skill through prompt-level behavioral examples rather than unit tests, because the first version is an instruction skill.
- Use at least one article `快刺` prompt, one product `拷问` prompt, and one code `复审` prompt as acceptance examples.
- A good test checks external behavior: whether the assistant produces specific, prioritized, evidence-backed critiques, options, recommendations, next actions, and strict scoring.
- The article test should verify that certo catches structure, logic, and expression issues separately.
- The product test should verify that certo asks key questions before reviewing when context is thin.
- The code test should verify that certo behaves like a code reviewer: findings first, concrete references when available, severity ordering, and no broad refactor suggestions unless justified.
- Test that certo does not become a generic assistant: it should critique rather than immediately implement or praise.
- Test that certo remains constructive: every major finding should include options, a recommendation, or a decision point.

## Success Criteria

- A user can invoke `certo` or “刺儿头” and reliably get adversarial review behavior.
- The skill distinguishes between article, product/prototype, and code review without requiring separate skills.
- Findings are concrete enough that the user can act on them immediately.
- The skill prioritizes serious issues over surface-level nitpicks.
- The skill gives choices, marks its recommendation, and scores at the end.
- The skill remains portable enough that its core review protocol can be reused in Claude Code.
- The skill stays small enough to load quickly and not crowd the context window.

## Out of Scope

- Automatically editing the user’s article, prototype, or code without explicit instruction.
- Building a full multi-agent review system.
- Creating separate specialist skills for writing, product, and code review.
- Integrating with issue trackers, CI systems, design tools, or IDE diagnostics.
- Maintaining a large rubric library in the MVP.
- Guaranteeing exhaustive correctness, security, legal, medical, or financial review.

## Further Notes

- The product metaphor should be “诤臣 / 谏官 / 严格审查者”，不是“喷子”。它要敢说“不对”，但必须能说明凭什么。
- The skill should be especially useful before committing code, publishing essays, or turning prototypes into implementation work.
- The first implementation should favor a compact, memorable review protocol over long theoretical rubrics.
- Potential future enhancement: add optional reference rubrics if real usage shows the inline guidance is too compressed.
