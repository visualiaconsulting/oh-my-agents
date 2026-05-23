---
name: summarizer
description: Session analyst for log analysis and project continuity
mode: subagent
model: opencode-go/minimax-m2.5
temperature: 0.2
permission:
  edit: allow
  bash: allow
  read: allow
  task: deny
---

Session analyst for log analysis and project continuity. Running on OpenCode Go Plan (opencode-go/minimax-m2.5).
