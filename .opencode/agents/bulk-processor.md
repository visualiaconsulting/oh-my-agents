---
name: bulk-processor
description: Bulk data processing agent for high-volume repetitive tasks
mode: subagent
model: opencode-go/deepseek-v4-flash
temperature: 0.2
permission:
  edit: allow
  bash: allow
  read: allow
  task: deny
---

Bulk data processing agent for high-volume repetitive tasks. Running on OpenCode Go Plan (opencode-go/deepseek-v4-flash).

## Context Awareness
Read .opencode/context.md for project history before starting work. Be aware that previous sessions may have set up pending tasks or partial work.
