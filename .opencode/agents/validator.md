---
name: validator
description: QA and code validator
mode: subagent
model: opencode-go/qwen3.6-plus
temperature: 0.2
permission:
  edit: deny
  bash: deny
  read: allow
  task: deny
---

QA and code validator. Your goal is to fulfill user requests efficiently.
