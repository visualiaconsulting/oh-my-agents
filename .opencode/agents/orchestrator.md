---
name: orchestrator
description: Main coordinator that delegates tasks to specialized agents
mode: primary
model: opencode-go/deepseek-v4-pro
temperature: 0.2
permission:
  edit: deny
  bash: deny
  read: allow
  task: allow
---

Main coordinator that delegates tasks to specialized agents. Running on OpenCode Go Plan (opencode-go/deepseek-v4-pro).
