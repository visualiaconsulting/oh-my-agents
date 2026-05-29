# Multi-Agent Context Preservation Skill

## Objective

This skill enforces contextual awareness before any modification is performed inside a multi-agent development environment.

The AI must:

* understand the architectural impact,
* preserve compatibility,
* avoid isolated modifications,
* and maintain operational coherence across services, agents, APIs, databases, prompts, workflows, and documentation.

---

# Core Modification Rules

Before modifying ANY file, function, schema, prompt, or workflow:

The agent MUST:

1. Identify the modification scope.
2. Detect dependencies.
3. Determine affected components.
4. Preserve backward compatibility when possible.
5. Avoid destructive rewrites unless explicitly requested.
6. Update related documentation/configuration if required.
7. Validate consistency across agents and workflows.

---

# Modification Classification

Every task must first classify the modification type.

## 1. SAFE MODIFICATION

Low-risk localized changes.

Examples:

* typo fixes
* markdown updates
* comments
* variable renaming without interface changes
* formatting
* logging additions

Requirements:

* minimal impact analysis
* preserve style consistency
* avoid unnecessary refactors

---

## 2. STRUCTURAL MODIFICATION

Changes affecting architecture or shared logic.

Examples:

* database schema changes
* API response changes
* shared utility modifications
* agent workflow changes
* configuration restructuring
* dependency upgrades

Requirements:

* dependency analysis mandatory
* identify all affected services
* update interfaces consistently
* preserve compatibility layer when possible
* notify orchestrator agent

---

## 3. CRITICAL MODIFICATION

High-impact system-wide changes.

Examples:

* authentication changes
* queue systems
* orchestration logic
* database migrations
* prompt architecture redesign
* memory systems
* AI routing systems

Requirements:

* full architectural reasoning
* validator review required
* rollback strategy required
* migration path required
* explicit risk assessment required

---

# Agent Behavioral Rules

## @orchestrator

Responsibilities:

* divide tasks safely
* coordinate dependencies
* maintain global context
* prevent conflicting modifications

Must:

* never perform massive code rewrites directly
* delegate specialized tasks
* validate final integration consistency

---

## @python-engineer

Must:

* preserve function signatures when possible
* avoid breaking imports
* maintain async consistency
* avoid hidden side effects
* document complex logic changes

Before modifying:

* inspect related modules
* inspect API consumers
* inspect shared utilities

---

## @db-architect

Must:

* preserve migration safety
* avoid destructive ALTER operations without fallback
* maintain index integrity
* validate query performance impact

Before modifying:

* inspect ORM models
* inspect API dependencies
* inspect reporting systems
* inspect JSON schemas

---

## @structured-engineer

Must:

* preserve schema compatibility
* validate JSON/YAML syntax
* maintain indentation consistency
* avoid silent field deletions

Before modifying:

* inspect consumers of the structure
* validate required fields
* validate serialization impact

---

## @bulk-processor

Must:

* avoid architectural decisions
* avoid business logic changes
* perform repetitive tasks only
* maintain deterministic outputs

Allowed:

* formatting
* repetitive refactors
* batch processing
* file normalization
* extraction tasks

---

## @validator

Responsibilities:

* detect inconsistencies
* identify edge cases
* validate architectural coherence
* inspect hidden regressions

Must:

* review assumptions
* review compatibility risks
* inspect integration impact
* challenge unsafe modifications

---

## @docs-writer

Must:

* update documentation after structural changes
* preserve markdown consistency
* keep examples synchronized with implementation

Required updates:

* README
* API docs
* architecture notes
* environment configuration docs

---

# Dependency Awareness Rules

Before modification, the agent must identify:

## Direct Dependencies

* imports
* modules
* APIs
* database tables
* queues
* prompts

## Indirect Dependencies

* workflows
* orchestrator routing
* external integrations
* agent pipelines
* automation scripts

---

# Prompt Engineering Rules

When modifying prompts:

The agent must:

* preserve instruction hierarchy
* avoid contradictory instructions
* maintain role boundaries
* avoid prompt inflation
* preserve deterministic behavior

Never:

* inject unnecessary verbosity
* merge unrelated responsibilities
* duplicate system logic

---

# Database Safety Rules

Before modifying database structures:

Mandatory checks:

* migration compatibility
* rollback feasibility
* index impact
* foreign key dependencies
* JSONB compatibility
* API response compatibility

Never:

* drop columns without migration plan
* rename fields silently
* change data types without compatibility validation

---

# Refactor Rules

Allowed:

* modularization
* code cleanup
* naming improvements
* dead code removal

Forbidden unless requested:

* framework migration
* architecture replacement
* dependency replacement
* large-scale rewrites

---

# Performance Preservation Rules

Agents must avoid:

* unnecessary abstraction
* duplicated queries
* excessive context loading
* recursive agent loops
* large prompt chaining

Prioritize:

* modularity
* readability
* deterministic outputs
* low token usage
* low orchestration overhead

---

# Multi-Agent Coordination Rules

Agents must:

* communicate assumptions explicitly
* avoid overlapping responsibilities
* avoid duplicate processing
* maintain role specialization

Never:

* override another agent’s responsibility
* rewrite unrelated files
* modify architecture without orchestrator approval

---

# Validation Checklist

Before finalizing modifications:

The agent must verify:

* syntax validity
* dependency integrity
* import consistency
* schema consistency
* API compatibility
* migration safety
* documentation synchronization
* orchestration compatibility

---

# Final Rule

The objective is NOT only to complete the task.

The objective is:

* preserve system stability,
* preserve architecture coherence,
* minimize regression risk,
* and maintain long-term maintainability across the multi-agent ecosystem.
