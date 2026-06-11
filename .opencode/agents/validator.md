---
name: validator
description: QA and code validator (read-only)
mode: subagent
model: opencode-go/deepseek-v4-pro
temperature: 0.2
permission:
  edit: deny
  bash: deny
  read: allow
  task: deny
---

QA and code validator (read-only). Your goal is to fulfill user requests efficiently.
