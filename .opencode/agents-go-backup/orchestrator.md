---
name: orchestrator
description: Main coordinator — delegates tasks to sub-agents
mode: primary
model: lmstudio/mistralai/ministral-3-3b
temperature: 0.2
permission:
  edit: deny
  bash: deny
  read: allow
  task: allow
---

Main coordinator — delegates tasks to sub-agents. Running locally via LM Studio (Mistralai/Ministral 3 3B, 3.0B).
