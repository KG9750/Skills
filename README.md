# Skills

Personal Codex skills repository.

## Layout

Each skill lives in its own directory under `skills/`:

```text
skills/
  student-exam-paper-generator/
    SKILL.md
    agents/
      openai.yaml
```

Keep future skills in the same `skills/<skill-name>/` structure so they remain independent and easy to install or update.

## Included Skills

- `claude-code-review`: Calls local Claude Code from Codex as an independent read-only reviewer for code, plan, diff, branch, or repository reviews.
- `certo`: Adversarial reviewer for writing, product/prototype, architecture, and code work; finds high-risk problems, gives options, recommendations, and strict scores.
- `novel-to-webcomic`: Adapts prose into comic scripts, visual bibles, finished comic assets, React/Vite webcomic readers, and source-safe retro urban action manga workflows.
- `student-exam-paper-generator`: Generates printable PDF exam papers and answer sheets for students.
- `xhs-post-packager`: Creates Xiaohongshu image-post packages with cover art, Kami-style cards, humanized captions, 10+ search tags, and GitHub high-star project cover metadata.
