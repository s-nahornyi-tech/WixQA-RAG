# Specification Quality Checklist: Evaluation harness

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-26
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validated on 2026-11-26. First iteration: every item passed except "No [NEEDS CLARIFICATION] markers remain"; two markers stood in FR-003 and FR-008. Second iteration, after the owner's answers of 2026-11-26: all items passed.
- Validated again on 2026-11-27, after the owner replaced the composition of the golden set: a golden set of 100 + 100 questions drawn with a seed, a held-out set of the other 100 + 100, and a synthetic held-out set of 300. All items pass. The answers of both days are recorded in the spec under "Clarifications".
- Changed for the decision of 2026-11-27: User Story 1, FR-001 and FR-003 to FR-008, the new FR-032 to FR-036, SC-001, SC-002, SC-006 and the new SC-008, the example data, AC-001 to AC-011 and the new AC-033 to AC-046, the edge cases, "Evidence" and "Assumptions". No earlier number was reused for another meaning.
- The rule "a held-out set is never used to choose a setting" is only partly checkable by a program. The spec states the checkable part as requirements (FR-033 to FR-036) and names the rest, which only discipline keeps, under "What a program cannot check"; that paragraph is on purpose not a numbered requirement, because it cannot be tested.
- The spec states no statistical threshold for the difference between two runs; it says that 200 working questions make a small difference harder to tell from chance.
- The constitution has no place for held-out sets. The spec applies its rules to the question set of a run and says so under "Assumptions"; the amendment is the owner's to approve.
- The spec is a draft until the owner approves it; the plan does not start before that.
- "Acceptance Checks" names commands, files and exit codes by design (PROJECT.md, "Process", addition 3). The items about implementation details were applied to every other section. FR-022 names SHA-256 because the constitution defines the answer hash that way.
- "User value and business needs" was read as the needs of the operator and of a reader who repeats the study: the study has no customers and operates no service (constitution, "Scope and Non-Goals").
- Every user story, functional requirement and success criterion is covered by at least one acceptance check: 4 user stories, 36 functional requirements, 8 success criteria, 46 acceptance checks.
- The numbers of the example runs in "Acceptance Checks" were recomputed from the example's tables and agree with the lines the checks expect. They are illustrations with a known answer, not results: no run exists.
- The spec states no numeric quality target (constitution, Principle X).
- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`
