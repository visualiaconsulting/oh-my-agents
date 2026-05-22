---
name: validator
description: QA specialist — validates and reviews code
mode: subagent
model: lmstudio/qwen2.5-coder-1.5b-instruct
temperature: 0.1
permission:
  edit: deny
  bash: deny
  read: allow
  task: deny
---

QA specialist — validates and reviews code. Running locally via LM Studio (Qwen2.5 Coder 1.5B, 1.5B).
