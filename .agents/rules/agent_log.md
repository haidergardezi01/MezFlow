---
trigger: always_on
description: Rule to ensure all agent activities, decisions, and progress are documented in Docs/AGENT_LOG.md
---

# Agent Activity Logging Rule

## Guidelines for MezFlow Project:
1. **Maintain Persistent History**:
   - Every major user request, design decision, architectural choice (ADR), file creation/modification, and git operation must be recorded in [`Docs/AGENT_LOG.md`](../../Docs/AGENT_LOG.md).
2. **Log Structure**:
   - **Session & Date**: Group entries chronologically.
   - **User Prompt**: Brief summary of what the user asked.
   - **Actions & Deliverables**: Clear bulleted list of tools used, files created/edited, and tests or commands run.
   - **Git Operations**: Note commits (hashes and messages) and pushes.
   - **State & Next Steps**: Keep the "Current Repository State Summary" and "Next Steps Queue" updated.
3. **Integrity**: Never delete past entries in `Docs/AGENT_LOG.md`; always append new entries.
