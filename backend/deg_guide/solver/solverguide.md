# How the Degree Audit Solver Works (Conceptual Overview)

This project uses a **constraint-based solver** (ILP-style, via OR-Tools CP-SAT) to evaluate degree progress.  
At a high level, the solver answers one question:

> “Given the courses a student has taken, how can those courses be assigned to degree requirements in the best possible way?”

“Best” means **maximizing requirement completion** while obeying all academic rules.

---

## Core idea

Instead of hard-coding logic like:
- “If CS210 and CS211 are taken, then the core is done”

We model the problem as:
- **courses**
- **requirements**
- **rules about how courses may satisfy requirements**

Then we let a solver find the optimal assignment.

This is important because:
- many requirements overlap
- courses can often satisfy *multiple possible* requirements
- naive “checklists” fail when choices exist

---

## What the solver reasons about

### 1. Courses
Each course is treated as an object with fixed facts:
- course ID (e.g. `CS210`)
- subject, number, credits
- global tags (used only for university-wide categories)

The solver does *not* decide whether a course exists — only how it is used.

---

### 2. Programs (degree type, major, minor)
Each selected program contributes **requirements** to the model:
- Bachelor of Science rules
- Major rules
- Minor rules (optional)

All selected programs are combined into **one unified constraint system**.

---

### 3. Requirements
A requirement represents a graduation rule, such as:
- “Take all of these courses”
- “Choose 1 of these options”
- “Earn at least 12 credits from this group”

Each requirement defines:
- *what courses are allowed to count*
- *how much is needed*

---

## The key solver decision

The solver creates Boolean decisions of the form:

> “Does course **C** count toward requirement **R**?”

This is the fundamental variable:
- `1` = the course is used for that requirement
- `0` = it is not

The solver’s job is to decide **where each course should count**, if anywhere.

---

## Preventing double counting

By default, a course is only allowed to count **once** across all requirements.

Conceptually:
- A course cannot satisfy two different requirements at the same time
- This prevents accidental over-crediting

This rule can later be relaxed or customized, but the default keeps logic safe.

---

## How different requirement types are modeled

### “All of” requirements
Example:
> “You must take CS210, CS211, and CS212”

- Each listed course must be assigned to that requirement
- If a course is missing, the solver records that as missing work

---

### “Choose k of” requirements
Example:
> “Choose 1 of these theory courses”

- Any eligible course may satisfy the requirement
- If fewer than `k` courses are used, the solver tracks how many are missing

---

### “Credits at least” requirements
Example:
> “Earn at least 12 credits of Math or CIS”

- Credits from eligible courses are summed
- If the total is short, the solver records how many credits are missing

---

## Slack: how the solver measures what’s missing

Instead of just saying “pass / fail”, each requirement has an associated **slack value**:

- Slack = 0 → requirement fully satisfied
- Slack > 0 → requirement partially or not satisfied

Slack represents:
- missing courses
- or missing credits

This lets the solver:
- measure partial progress
- explain *how far along* a student is
- optimize intelligently

---

## Solver objective: maximize completion

The solver is asked to:

> **Minimize total slack across all requirements**

This means it tries to:
- assign courses where they help the most
- choose the best possible use of courses when multiple options exist
- produce the most complete degree audit possible

If a student could use a course in multiple ways, the solver picks the one that reduces unmet requirements the most.

---

## Why this approach is powerful

This model naturally supports:
- overlapping requirements
- “choose one of many” rules
- credit minimums
- combining degree type + major + minor
- future expansion to course recommendations

Importantly:
- **logic lives in data**, not code
- adding a new major does not require rewriting the solver
- the solver always finds the best valid assignment automatically

---

## What the solver does *not* do (by design)

The solver does **not**:
- check prerequisites
- handle term scheduling
- enforce time conflicts

Those are handled *before* or *after* the solver.

The solver’s sole responsibility is:
> **Given a set of completed courses, determine degree progress optimally and correctly.**

---

## Mental model summary

Think of the solver as:
- a smart allocator
- assigning completed courses to requirement “buckets”
- under strict academic rules
- while minimizing what’s left to do

This is why a constraint solver is used instead of simple conditionals.

---

## One-sentence summary

> The solver treats degree progress as an optimization problem, assigning taken courses to requirements in the most effective way while obeying academic rules and measuring exactly what remains to graduate.
