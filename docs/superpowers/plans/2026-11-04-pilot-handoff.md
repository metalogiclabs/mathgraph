# Pilot handoff refinement implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** concise, consistent, usable pilot handoff.
**Architecture:** existing static Worker page, unchanged native controller and scoped authority; update owned PR metadata and one stale status.
**Tech Stack:** JavaScript ES modules, existing GitHub/Cloudflare deployment and browser qualification.
**Spec:** docs/superpowers/specs/2026-11-04-pilot-handoff-design.md

## Global Constraints
- Preserve exact opaque approved JPEG, commands, finite evidence, invitation authority and no upstream writes.
- Keep private collaboration details out of public source and PRs.
- Preserve historical evidence; supersede stale status rather than delete.

## Review Focus
- Existing clipboard/form interactions and six-case disclosure remain functional on mobile and desktop.
- Report example links resolve consistently to42,43 and the positive recheck.
- License/security/data prose describes actual mechanisms without unsupported guarantees.
- First-use instructions distinguish example comments from inbox URL commands.
- Current deployment bindings and credentials remain inherited without expansion.

### Task1: refine static page and owned overviews
- [ ] Replace page body with complementary positioning, short flow, consistent links and command table; fold support details.
- [ ] Run existing page/contract tests; update browser navigation to open the relevant collapsed form details.
- [ ] Commit/publish candidate, qualify browser interactions, review rendered page, deploy exact qualified bundle with existing bindings.
- [ ] Update42/35/40 overviews and stale queued inbox status; re-read changes.
- [ ] Record qualification/deployment and final scope in canonical checkpoint.
