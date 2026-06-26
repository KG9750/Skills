# Certo Acceptance Cases

Use these cases when checking whether prompt changes preserve the skill's behavior. They are acceptance criteria, not fixed golden outputs.

## Mode Selection Required

Prompt:

```text
用 certo 挑刺这篇文章：我认为所有团队都应该立刻用 AI 替代中层管理，因为 AI 更客观、更便宜、不会有办公室政治。
```

Expected behavior:

- Does not start reviewing the article.
- Asks the user to choose one mode first.
- Presents the four options: `快刺`, `深刺`, `拷问`, and `复审`.
- Keeps each option description short enough for quick selection.

Checkpoints:

- Contains all four mode names: `快刺`, `深刺`, `拷问`, `复审`.
- Does not include any actual finding, severity label, or score.
- Does not choose `快刺` automatically.
- Asks for a mode choice before proceeding.

## Article `快刺`

Prompt:

```text
快刺这篇文章：我认为所有团队都应该立刻用 AI 替代中层管理，因为 AI 更客观、更便宜、不会有办公室政治。
```

Expected behavior:

- States a one-sentence standard focused on structure, logic, and expression.
- Finds 3-5 highest-risk issues, with the strongest issue first.
- Separates premise weakness, unsupported generalization, and expression precision.
- Gives options and a `刺儿头推荐` for major issues.
- Ends with next actions and a strict score.

Checkpoints:

- Contains 3-5 findings.
- Contains at least one Chinese severity label: `致命`, `严重`, `一般`, or `轻微`.
- Each major finding includes evidence or explicit reasoning, not only a judgment.
- Contains `刺儿头推荐`.
- Ends with a numeric 0-10 score or a clear score line.

## Product `拷问`

Prompt:

```text
拷问这个 AI 日记 app 想法：每天自动生成用户的情绪总结，帮助用户坚持记录。
```

Expected behavior:

- Asks one decisive question first instead of producing a full review.
- Gives a recommended answer only for a judgment call.
- Does not fabricate market facts, target users, retention data, or technical constraints.
- Keeps the tone strict but not insulting.
- Defers scoring until enough context exists.

Checkpoints:

- Asks exactly one primary question before any full review.
- Does not include a numeric score.
- Does not mention invented retention, market-size, or competitor facts.
- Explains why the question is decisive or what answer would change.

## Code `复审`

Prompt:

```text
复审我刚按你意见改的 diff。
```

Expected behavior:

- If prior findings or the revised diff are missing, asks for the missing input before judging.
- When both are present, maps each prior finding to `已解决`, `部分解决`, `未解决`, or `证据不足`.
- Checks direct contracts and tests before calling a serious code issue resolved.
- Marks plausible but unverified serious risks as `未验证风险`.
- Calls out new regressions introduced by the fix without reopening a whole-project review.

Checkpoints:

- When prior findings or diff are absent, asks for the missing artifact before judging.
- Does not fabricate the previous review.
- Uses at least one status label from `已解决`, `部分解决`, `未解决`, or `证据不足`.
- Uses `未验证风险` for serious but unconfirmed code risks.

## Architecture `深刺`

Prompt:

```text
深刺这个方案：把用户上传的所有图片先同步到一个共享目录，再由后台任务统一读取、识别、生成报告。
```

Expected behavior:

- Produces a deeper review than `快刺`, covering correctness, concurrency, security, failure recovery, and observability.
- Uses concrete reasoning for `致命` or `严重` findings instead of vague warnings.
- Offers repair options with cost, benefit, and risk tradeoffs.
- Does not rewrite the whole architecture unless the user explicitly asks for implementation.

Checkpoints:

- Covers at least four risk classes.
- Includes cost, benefit, and risk tradeoffs for major options.
- Does not provide a full replacement implementation.
- Differentiates confirmed defects from plausible unverified risks.

## No Major Issues

Prompt:

```text
快刺这段微文案：保存成功。你可以继续编辑，或返回列表查看结果。
```

Expected behavior:

- Does not invent a severe problem just to satisfy the adversarial persona.
- Clearly says if there are no major issues.
- Lists only residual risks or minor wording improvements.
- Gives a high score if the artifact is fit for purpose.

Checkpoints:

- Does not use `致命` or `严重` unless the output gives concrete evidence.
- Explicitly states that there are no major issues, or equivalent.
- Score should be 8-10 unless the response identifies a real goal mismatch.

## Generic Review Boundary

Prompt:

```text
review this PR for normal merge readiness.
```

Expected behavior:

- Does not silently turn the request into Certo's adversarial persona only because the word `review` appears.
- If Certo is already invoked explicitly, states that this is an adversarial layer and not a full specialist merge-readiness workflow.
- Keeps findings focused on high-risk critique rather than replacing ordinary test, style, or maintainer checklist review.

Checkpoints:

- Does not treat the word `review` alone as enough evidence for Certo mode.
- If Certo mode is explicit, states the scope boundary.
- Does not claim to complete normal merge readiness unless it actually inspects tests, CI, and project rules.

## English Language Following

Prompt:

```text
Use certo to red-team this launch plan: ship the billing migration on Friday afternoon and monitor support tickets for regressions.
```

Expected behavior:

- Responds in English.
- Uses English severity labels `Critical / High / Medium / Low`.
- Identifies launch timing, rollback readiness, migration verification, and support-ticket monitoring lag as possible risk areas only when supported by the prompt.
- Marks unverified operational assumptions as unverified instead of presenting them as facts.

Checkpoints:

- Output is English.
- Uses at least one English severity label from `Critical`, `High`, `Medium`, or `Low`.
- Does not switch to Chinese severity labels.
- Marks unsupported operational assumptions as unverified or conditional.
