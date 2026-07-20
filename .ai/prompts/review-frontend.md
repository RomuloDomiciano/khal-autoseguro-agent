# Review Frontend Changes

Act as the agent defined in:

* `.ai/agents/frontend-dev.yaml`

Read:

* `.ai/project/context.md`
* the task and acceptance criteria
* the changed files or diff
* only the surrounding source files required to understand the change
* relevant tests

## Objective

Review the frontend changes for defects, regressions and meaningful engineering risks.

Prioritize correctness over stylistic preferences.

Do not rewrite or modify the implementation unless explicitly requested.

## Review priorities

Review in this order:

1. Functional correctness and acceptance criteria
2. Security and sensitive-data exposure
3. Accessibility
4. Loading, empty, success and error states
5. Architecture and maintainability
6. Test coverage
7. Performance issues supported by evidence

## Finding requirements

Every finding must include:

* severity
* affected file or behavior
* explanation of the problem
* likely impact
* concrete recommendation

Use these severities:

* `blocking`: security issue, sensitive-data exposure, broken primary flow, serious regression or unmet mandatory requirement
* `important`: meaningful reliability, accessibility, maintainability or alternate-flow problem
* `suggestion`: optional simplification or low-impact improvement

Do not:

* invent findings to make the review appear thorough
* report personal style preferences as defects
* demand architecture changes unrelated to the task
* propose new dependencies when the existing stack is sufficient
* report speculative performance problems without plausible impact
* assume tests or commands passed without evidence

## Final response

Return:

### Assessment

Choose one:

* Ready
* Ready with non-blocking suggestions
* Not ready

Include a concise explanation.

### Blocking issues

Evidence-based blocking findings, or state that none were found.

### Important issues

Evidence-based important findings, or state that none were found.

### Suggestions

Optional improvements that do not block delivery.

### Positive observations

Relevant strengths supported by the reviewed code.

### Validation gaps

Tests, commands, runtime behavior or context that could not be verified.
