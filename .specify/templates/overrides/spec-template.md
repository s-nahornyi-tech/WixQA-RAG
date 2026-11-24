# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Accepted independently

  The study has no end users or customers and operates no service (constitution, "Scope and
  Non-Goals"). The actor of a story is whoever runs the feature: the owner, an agent, or a
  reader of the repository.
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.

  Constitution, Principle X: before the baseline run exists, state no numeric quality target.
  Once it exists, state every such target relative to the baseline's numbers and cite the runs
  under "Evidence". State no criterion about end users, customers or a running service: the
  study has none (constitution, "Scope and Non-Goals").
-->

### Measurable Outcomes

- **SC-001**: [Measurable outcome, e.g., "The audit reports zero mismatches between the index and the corpus"]
- **SC-002**: [Measurable outcome, e.g., "Recomputing a run's summary from its recorded files gives the same numbers"]
- **SC-003**: [Once the baseline run exists, a target relative to it, e.g., "The share of questions with every gold article found is not lower than in the baseline run"]

## Acceptance Checks *(mandatory)*

<!--
  ACTION REQUIRED: List the checks a machine runs to decide whether this feature is accepted
  (PROJECT.md, "Process", addition 3). Replace the example lines.

  - One check is one command, typed at the repository root, and the result a reader can
    observe: the exit code and the output or the file that shows it.
  - Write at least one check for every user story. "covers" names the user stories,
    requirements and success criteria that the check verifies.
  - Every check MUST fail before the implementation exists. State the result precisely enough
    that a missing implementation cannot produce it.
  - The command is part of this spec: the plan and the implementation make exactly this
    command work. Do not assume tooling that the constitution still lists as open under "Stack".
  - This is the only section that names commands and files. The spec quality checklist's items
    about implementation details apply to every other section, not to this one.
-->

Each check is one command and the result a reader can observe. Every check fails before the feature is implemented and passes once it is implemented. The testing agent turns each check into an automated acceptance test before any implementation is written (constitution, "Development Workflow"). This section alone names commands; the sections above stay technology-agnostic.

- **AC-001** (covers [US1, FR-001]): `[command typed at the repository root]` → [exit code, and the output or file that shows the result]
- **AC-002** (covers [US2, SC-001]): `[command]` → [observable result]

## Evidence *(mandatory)*

<!--
  ACTION REQUIRED: Cite the runs behind this spec (PROJECT.md, "Process", addition 7;
  constitution, Principle X). Replace the example rows.

  - List every decision this spec makes about the pipeline (a model, a retrieval method, a
    reranker, chunking, a prompt, a parameter value) and every numeric quality target it
    states. For each, name the run in `evals/runs/` that justifies it and, where it rests on
    a comparison, the run it was compared with.
  - A configuration chosen as a starting point, such as the baseline's, is recorded as chosen,
    not as found: write "chosen as a starting point, no run".
  - If this spec decides nothing about the pipeline and states no numeric quality target,
    replace the table with one sentence that says so.
  - The run recorded while this feature is implemented is named in the pull request (`Run:`
    and `Compared-With:`), not here.
-->

| Decision or numeric target in this spec | Justified by run | Compared with run |
|---|---|---|
| [e.g., FR-003: hybrid retrieval is adopted] | `[run-id]` | `[run-id]` |
| [e.g., SC-003: a target relative to the baseline] | `[run-id of the baseline]` | none |
| [e.g., FR-004: a value chosen as a starting point] | chosen as a starting point, no run | none |

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Users have stable internet connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing authentication system will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile API"]
