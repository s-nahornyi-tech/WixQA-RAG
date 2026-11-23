---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: REQUIRED for every feature of this project (constitution, "Development Workflow"). In every user story the tests come first: the testing agent writes one acceptance test for each check in the "Acceptance Checks" of spec.md, and the tests MUST fail before any implementation task of that story starts. The coding agent MUST NOT change an acceptance test; a test that is wrong goes back to the testing agent.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Roles**: Tasks under a "Tests" heading belong to the testing agent, CI/CD tasks to the DevOps agent, and all other tasks to the coding agent. The code review agent checks the pull request's diff against spec.md and the constitution; that check is not a task in this list.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!--
  ============================================================================
  IMPORTANT: The tasks below are EXAMPLE TASKS for illustration purposes only.

  The /speckit-tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these example tasks in the generated tasks.md file.

  REQUIRED in every tasks.md of this project (these are not examples):
  - every user story phase starts with its "Tests" block: one acceptance test task for each
    check of spec.md ("Acceptance Checks") that covers the story, then the task that runs the
    tests and confirms that each fails;
  - every user story phase ends with the task that runs the same tests and confirms that each
    passes, with no acceptance test changed;
  - the final phase ends with the "Acceptance and evidence" block.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Setup database schema and migrations framework
- [ ] T005 [P] Implement authentication/authorization framework
- [ ] T006 [P] Setup API routing and middleware structure
- [ ] T007 Create base models/entities that all stories depend on
- [ ] T008 Configure error handling and logging infrastructure
- [ ] T009 Setup environment configuration management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (REQUIRED - written first by the testing agent) ⚠️

> **NOTE: Write these tests FIRST, one for each check of spec.md that covers this story. They MUST FAIL before implementation starts**

- [ ] T010 [P] [US1] Acceptance test for check AC-001 in tests/acceptance/test_[name].py
- [ ] T011 [P] [US1] Acceptance test for check AC-002 in tests/acceptance/test_[name].py
- [ ] T012 [US1] Run the tests of User Story 1 and confirm that each fails because the behaviour is missing

**Checkpoint (red)**: Every test of User Story 1 exists and fails. No implementation task of this story starts before this point

### Implementation for User Story 1

- [ ] T013 [P] [US1] Create [Entity1] model in src/models/[entity1].py
- [ ] T014 [P] [US1] Create [Entity2] model in src/models/[entity2].py
- [ ] T015 [US1] Implement [Service] in src/services/[service].py (depends on T013, T014)
- [ ] T016 [US1] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T017 [US1] Add validation and error handling
- [ ] T018 [US1] Add logging for user story 1 operations
- [ ] T019 [US1] Run the tests of User Story 1 and confirm that each passes, with no acceptance test changed

**Checkpoint (green)**: The tests of User Story 1 pass unchanged. User Story 1 is fully functional and can be accepted on its own

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (REQUIRED - written first by the testing agent) ⚠️

- [ ] T020 [P] [US2] Acceptance test for check AC-003 in tests/acceptance/test_[name].py
- [ ] T021 [US2] Run the tests of User Story 2 and confirm that each fails because the behaviour is missing

### Implementation for User Story 2

- [ ] T022 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T023 [US2] Implement [Service] in src/services/[service].py
- [ ] T024 [US2] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T025 [US2] Integrate with User Story 1 components (if needed)
- [ ] T026 [US2] Run the tests of User Story 2 and confirm that each passes, with no acceptance test changed

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (REQUIRED - written first by the testing agent) ⚠️

- [ ] T027 [P] [US3] Acceptance test for check AC-004 in tests/acceptance/test_[name].py
- [ ] T028 [US3] Run the tests of User Story 3 and confirm that each fails because the behaviour is missing

### Implementation for User Story 3

- [ ] T029 [P] [US3] Create [Entity] model in src/models/[entity].py
- [ ] T030 [US3] Implement [Service] in src/services/[service].py
- [ ] T031 [US3] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T032 [US3] Run the tests of User Story 3 and confirm that each passes, with no acceptance test changed

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional unit tests (if requested) in tests/unit/
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation

### Acceptance and evidence (REQUIRED - last)

- [ ] TXXX Run every check of the "Acceptance Checks" of spec.md exactly as written and confirm the observable result of each
- [ ] TXXX Record an evaluation run in evals/runs/ and compare it pairwise with the previous run, if one exists (only if the feature changes what the pipeline retrieves or answers)

> **NOTE: The run's identifier goes into the pull request (`Run:` and `Compared-With:`). A feature that cannot change what the pipeline retrieves or answers has no such task, and its pull request states `Run: none`**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if several agents work at once)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if several agents work at once)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different agents

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Acceptance test for check AC-001 in tests/acceptance/test_[name].py"
Task: "Acceptance test for check AC-002 in tests/acceptance/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run the tests of User Story 1; they pass unchanged
5. User Story 1 can be accepted on its own, as the first slice

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → First slice ready for acceptance (MVP!)
3. Add User Story 2 → Test independently → Next slice ready for acceptance
4. Add User Story 3 → Test independently → Next slice ready for acceptance
5. Each story adds value without breaking previous stories

### Parallel Agent Strategy

With several agents working at once:

1. Setup + Foundational are completed first
2. Once Foundational is done, the stories proceed side by side, each with its tests first:
   - User Story 1
   - User Story 2
   - User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing; the coding agent never changes an acceptance test
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
