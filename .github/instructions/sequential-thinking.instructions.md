---
description: 'Guidelines for using sequential thinking MCP tool for complex problem-solving, architecture decisions, and multi-step implementations'
applyTo: '**/*'
---

# Sequential Thinking Tool Guidelines

Instructions for effectively using the sequential-thinking MCP tool to solve complex problems through structured, iterative reasoning.

## Overview

The sequential-thinking tool enables dynamic, reflective problem-solving through structured thought chains. It's ideal for complex architectural decisions, multi-step implementations, and problems requiring course correction.

## When to Use Sequential Thinking

### Ideal Use Cases

1. **Architecture Decisions**
   - Designing module structures
   - Choosing patterns (Repository, Factory, etc.)
   - Evaluating trade-offs between approaches

2. **Complex Problem Decomposition**
   - Breaking down large features into tasks
   - Identifying dependencies between components
   - Planning implementation order

3. **Multi-Step Implementations**
   - Implementing features across multiple files
   - Refactoring with many interdependencies
   - Database schema migrations

4. **Debugging Complex Issues**
   - Tracing through multiple layers
   - Analyzing race conditions
   - Understanding unexpected behavior

5. **Risk Analysis**
   - Security vulnerability assessment
   - Performance bottleneck analysis
   - Breaking change impact evaluation

### When NOT to Use

- Simple, straightforward tasks
- Single-file modifications
- Well-defined, linear operations
- Quick lookups or information retrieval

## Tool Parameters

```typescript
{
  thought: string,           // Current thinking step
  nextThoughtNeeded: boolean, // Continue thinking?
  thoughtNumber: number,     // Current position (1-based)
  totalThoughts: number,     // Estimated total (adjustable)
  isRevision?: boolean,      // Revising previous thought?
  revisesThought?: number,   // Which thought being revised
  branchFromThought?: number, // Branching point
  branchId?: string,         // Branch identifier
  needsMoreThoughts?: boolean // Need to extend?
}
```

## Thinking Patterns

### Pattern 1: Linear Analysis

```markdown
Thought 1: Define the problem clearly
Thought 2: Identify constraints and requirements
Thought 3: List possible approaches
Thought 4: Evaluate each approach (pros/cons)
Thought 5: Select best approach with justification
Thought 6: Outline implementation steps
```

### Pattern 2: Branching Exploration

```markdown
Thought 1: Identify decision point
Thought 2: Branch A - Explore option A
Thought 3: Branch A - Evaluate implications
Thought 4: Branch B - Explore option B (branchFromThought: 1)
Thought 5: Branch B - Evaluate implications
Thought 6: Compare branches, select winner
```

### Pattern 3: Iterative Refinement

```markdown
Thought 1: Initial approach
Thought 2: Identify weakness in approach
Thought 3: Revise approach (isRevision: true, revisesThought: 1)
Thought 4: Validate revised approach
Thought 5: Finalize solution
```

### Pattern 4: Hypothesis-Verification

```markdown
Thought 1: State hypothesis
Thought 2: Identify what would prove/disprove it
Thought 3: Gather evidence (reference code, docs)
Thought 4: Evaluate evidence
Thought 5: Confirm or revise hypothesis
Thought 6: State conclusion
```

## Best Practices

### Structure Your Thoughts

```markdown
# Good thought structure
"Analyzing the repository pattern implementation:
1. Current state: No abstraction over database access
2. Problem: Direct SQLAlchemy usage couples business logic to DB
3. Proposed solution: Generic repository with type hints
4. Key consideration: Must support async operations
5. Next step: Define base repository interface"

# Bad thought structure
"I think we should use the repository pattern because it's good."
```

### Adjust Total Thoughts Dynamically

```markdown
# Start with estimate
thoughtNumber: 1, totalThoughts: 5

# Realize more analysis needed
thoughtNumber: 3, totalThoughts: 8, needsMoreThoughts: true

# Problem simpler than expected
thoughtNumber: 4, totalThoughts: 4
```

### Use Revisions Appropriately

```markdown
# When to revise
- New information invalidates previous thought
- Better approach discovered
- Constraint was missed earlier

# Revision thought
{
  thought: "Revising approach: discovered async context manager pattern is better for session management than explicit begin/commit",
  isRevision: true,
  revisesThought: 2,
  thoughtNumber: 5,
  totalThoughts: 7
}
```

### Branch for Significant Alternatives

```markdown
# Branch when
- Two viable approaches exist
- Need to explore "what if" scenarios
- Comparing architectural options

# Branch thought
{
  thought: "Exploring alternative: Event sourcing instead of CRUD",
  branchFromThought: 3,
  branchId: "event-sourcing",
  thoughtNumber: 6,
  totalThoughts: 10
}
```

## Integration with Serena

### Combined Workflow

```markdown
1. Sequential Thinking: Analyze problem, plan approach
   ↓
2. Serena: Gather code context with symbolic tools
   ↓
3. Sequential Thinking: Refine plan based on actual code
   ↓
4. Serena: think_about_task_adherence
   ↓
5. Serena: Make changes with editing tools
   ↓
6. Serena: think_about_whether_you_are_done
   ↓
7. Serena: Write memory to track progress
```

### Example: Designing Exception Hierarchy

```markdown
# Thought 1
"Analyzing exception requirements for enterprise microservices:
- Need HTTP-mapped exceptions for API responses
- Need serializable exceptions for inter-service communication
- Need base exception with common attributes
- Should support exception chaining"

# Thought 2
"Researching existing patterns in codebase..."
[Use Serena: search_for_pattern("class.*Exception", is_regex=True)]

# Thought 3
"Based on codebase analysis, no existing exception hierarchy.
Comparing approaches:
A) Flat hierarchy - simple but limited
B) Deep hierarchy - flexible but complex
C) Mixin-based - composable but harder to understand"

# Thought 4
"Selecting approach B with modifications:
- Base exception with core attributes
- HTTP exceptions inherit from base
- Domain exceptions inherit from base
- Serialization as mixin for flexibility"

# Thought 5
"Implementation plan:
1. Create BaseException in shared/exceptions/base.py
2. Create HTTP exceptions in shared/exceptions/http.py
3. Create serialization mixin
4. Add tests for each exception type"
```

## Common Pitfalls

### Avoid These

1. **Too few thoughts for complex problems**
   - Don't rush to conclusion
   - Allow for exploration and revision

2. **Not using revisions when needed**
   - It's okay to change your mind
   - Earlier thoughts can be wrong

3. **Ignoring branches for alternatives**
   - Explore options before committing
   - Document why alternatives were rejected

4. **Thoughts that don't build on each other**
   - Each thought should advance understanding
   - Reference and build on previous thoughts

5. **Setting nextThoughtNeeded=false too early**
   - Only stop when truly satisfied
   - Verify solution is complete

## Quality Checklist

Before concluding sequential thinking:

- [ ] Problem is clearly defined
- [ ] All constraints identified
- [ ] Multiple approaches considered
- [ ] Trade-offs evaluated
- [ ] Implementation path clear
- [ ] Edge cases considered
- [ ] Risks identified
- [ ] Next steps actionable
