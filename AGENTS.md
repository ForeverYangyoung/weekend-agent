<!-- BEGIN SUPER DEV CURSOR -->
---
description: "Super Dev pipeline governance - research-first commercial-grade delivery. Activates when user says /super-dev or super-dev:"
alwaysApply: true
---

# Super Dev Pipeline Rules
- When the user triggers `/super-dev ...`, enter Super Dev pipeline mode immediately.
- Start with research and write output/*-research.md as a real file in the repository.
- Always read and maintain output/*-prd.md, output/*-architecture.md, and output/*-uiux.md as source-of-truth project files.
- **Before research/docs:** read `.super-dev/WORKFLOW.md` — canonical PRD/architecture live in `01-题目工程拆解.md` and `02.架构和agent.md`; do not fork duplicate requirements.
- Summarize the three core documents to the user and wait for user confirmation before creating Spec/tasks or writing code.
- Create Spec/tasks only after confirmation.
- Execute frontend-first delivery before backend/database tasks, then run quality gate before release.
- **Backend:** `backend/` is the implemented LangGraph + FastAPI stack; extend it, do not replace with scaffold patterns.
- Before any UI implementation, first lock the icon library, typography, design token system, component ecosystem, and page skeleton from output/*-uiux.md.
- Do not use emoji as functional icons or placeholders.
- For non-conversational AI products, avoid Claude / ChatGPT-style sidebar chat shells unless the UI plan explicitly justifies them.
- Keep using the component ecosystem and design token direction defined in output/*-uiux.md rather than switching ad hoc.
- If `.super-dev/SESSION_BRIEF.md` exists, read it before responding and keep the current Super Dev gate active across follow-up edits.

## Coding Constraints (active during ALL coding phases)
- Before writing ANY code, run `cat package.json` to check framework versions. If unsure, read official docs first.
- Icons MUST come from Lucide/Heroicons/Tabler. No emoji as icons. No purple/pink gradient themes.
- Frontend fetch URLs must exactly match backend route definitions (see `backend/server.py`).
- Before writing each file: correct imports, no emoji, colors from tokens only.
- After completing a feature, run build + lint. Fix errors before moving on.

## Super Dev System Flow Contract
- SUPER_DEV_FLOW_CONTRACT_V1
- PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery
- DOC_CONFIRM_GATE: required
- PREVIEW_CONFIRM_GATE: required
- HOST_PARITY: required
<!-- END SUPER DEV CURSOR -->
