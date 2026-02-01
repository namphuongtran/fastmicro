---
description: 'MANDATORY: Use Serena, Context7, and Sequential Thinking MCP tools for Python development. These tools provide semantic code exploration, up-to-date documentation, and structured problem-solving.'
applyTo: '**/*.py'
---

# MCP Tools Usage Guidelines - MANDATORY

## ⚠️ CRITICAL: THREE MANDATORY MCP TOOLS

### 1. SERENA - Code Exploration & Editing
**ALWAYS use Serena tools BEFORE using standard file operations for Python files.**
- Provides semantic, token-efficient code exploration
- Symbol-based navigation and editing
- Memory persistence across sessions

### 2. CONTEXT7 - Library Documentation
**ALWAYS verify library APIs with Context7 BEFORE implementation.**
- Training data may be outdated
- APIs change between library versions
- Best practices evolve

### 3. SEQUENTIAL THINKING - Complex Problem Solving
**Use for architecture decisions, multi-step implementations, and debugging.**
- Structured iterative reasoning
- Hypothesis-verification workflow
- Course correction capabilities

## Decision Tree: Which MCP Tool to Use?

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK TYPE                        │ MCP TOOL                    │
├──────────────────────────────────┼─────────────────────────────┤
│ Complex problem / Architecture   │ SEQUENTIAL THINKING         │
│ Multi-step implementation        │ sequential-thinking         │
│ Debugging complex issues         │                             │
├──────────────────────────────────┼─────────────────────────────┤
│ Using any library/framework      │ CONTEXT7                    │
│ Datetime/timezone operations     │ resolve-library-id →        │
│ Unsure about API patterns        │ get-library-docs            │
├──────────────────────────────────┼─────────────────────────────┤
│ Explore Python code structure    │ SERENA                      │
│ Find symbol usages               │ find_symbol,                │
│ Edit Python functions/classes    │ find_referencing_symbols,   │
│ Track progress across sessions   │ replace_symbol_body,        │
│                                  │ write_memory                │
└──────────────────────────────────┴─────────────────────────────┘
```

### Serena-Specific Decision Tree

```
Need to understand Python code structure?
├── YES → Use `get_symbols_overview` or `find_symbol`
│         NOT `read_file`
│
├── Need to find where a symbol is used?
│   └── Use `find_referencing_symbols`
│       NOT `grep_search`
│
├── Need to edit Python code?
│   └── Use `replace_symbol_body`, `insert_before_symbol`, `insert_after_symbol`
│       NOT `replace_string_in_file`
│
├── Need to search for patterns?
│   └── Use `search_for_pattern` with relative_path filter
│       NOT `grep_search` without filters
│
└── About to make changes?
    └── FIRST call `think_about_task_adherence`
```

## Context7 Usage Patterns

### When to Use Context7

| Scenario | Why Verify |
|----------|------------|
| Using any library/framework | APIs change between versions |
| Datetime/timezone operations | Common source of bugs |
| Database operations | ORM patterns change significantly |
| Authentication/Security | Critical to use current patterns |
| Testing frameworks | pytest, asyncio patterns change |
| Pydantic models | v1 vs v2 have breaking changes |

### Context7 Workflow

```markdown
# Step 1: Resolve the library ID
mcp_context7_resolve-library-id
  libraryName: "pydantic v2"

# Step 2: Get documentation for specific topic
mcp_context7_get-library-docs
  context7CompatibleLibraryID: "/pydantic/pydantic"
  topic: "model_config validation"
```

### Key Libraries in This Project

| Library | Context7 ID | Common Topics |
|---------|-------------|---------------|
| FastAPI | `/fastapi/fastapi` | dependencies, lifespan, middleware |
| Pydantic | `/pydantic/pydantic` | model_config, validators, Field |
| SQLAlchemy | `/sqlalchemy/sqlalchemy` | async, session, relationships |
| structlog | `/hynek/structlog` | configuration, processors |
| pytest | `/pytest-dev/pytest` | fixtures, markers, async |

## Sequential Thinking Usage Patterns

### When to Use Sequential Thinking

1. **Architecture decisions** - Designing module structures, choosing patterns
2. **Complex problem decomposition** - Breaking down large features
3. **Multi-step implementations** - Changes across multiple files
4. **Debugging complex issues** - Tracing through multiple layers
5. **Risk analysis** - Security, performance, breaking changes

### Sequential Thinking Workflow

```markdown
# Each thought builds on previous understanding
mcp_sequential-th_sequentialthinking
  thought: "Analyzing the repository pattern implementation..."
  thoughtNumber: 1
  totalThoughts: 5  # Can be adjusted dynamically
  nextThoughtNeeded: true
  isRevision: false  # Set true if revising earlier thinking
```

### Integration: Sequential Thinking + Serena + Context7

```
1. Sequential Thinking: Analyze problem, plan approach
   ↓
2. Context7: Verify library APIs and best practices
   ↓
3. Serena: Gather code context with symbolic tools
   ↓
4. Sequential Thinking: Refine plan based on findings
   ↓
5. Serena: think_about_task_adherence
   ↓
6. Serena: Make changes with editing tools
   ↓
7. Serena: think_about_whether_you_are_done
   ↓
8. Serena: Write memory to track progress
```

## Mandatory Checkpoints

### Before Starting Any Python Task

1. **Activate Serena tools** if not already active:
   - `activate_file_search_tools`
   - `activate_symbol_management_tools`
   - `activate_memory_management_tools`

2. **Read relevant memories** to understand prior context:
   - Call `list_memories` to see available context
   - Read memories related to current task

### Before Making Code Changes

1. **Call `think_about_task_adherence`** - MANDATORY
2. Gather context using symbolic tools
3. Call `think_about_collected_information` to validate understanding

### After Completing Work

1. **Call `think_about_whether_you_are_done`** - MANDATORY
2. **Write memory** if decisions or progress should be preserved

## Tool Usage Patterns

### Exploring a Module

```markdown
# Step 1: List directory contents
list_dir("/path/to/module")

# Step 2: Get symbols overview for a file
get_symbols_overview(relative_path="shared/exceptions/base.py")

# Step 3: Examine specific class
find_symbol(name_path_pattern="BaseException", include_body=False, depth=1)

# Step 4: Read specific method
find_symbol(name_path_pattern="BaseException/to_dict", include_body=True)
```

### Finding Symbol References

```markdown
# Find all usages of a function/class
find_referencing_symbols(
    name_path_pattern="CustomException",
    include_body=False  # Just locations first
)

# Then read specific references if needed
find_referencing_symbols(
    name_path_pattern="CustomException",
    include_body=True,
    relative_path="specific/file.py"  # Narrow scope
)
```

### Pattern Search for Unknown Symbols

```markdown
# When you don't know the exact symbol name
search_for_pattern(
    pattern="async def.*repository",
    relative_path="shared/dbs/",
    is_regex=True
)
```

## Memory Management

### When to Write Memories

- **Architecture decisions**: After making significant design choices
- **Progress tracking**: After completing a phase or milestone
- **Context preservation**: Important information for future sessions
- **Learnings**: Patterns discovered, gotchas, best practices

### Memory Naming Conventions

```markdown
# Good memory names
shared-library-architecture-plan.md
database-patterns-decisions.md
auth-implementation-progress.md
observability-standards.md

# Bad memory names
notes.md
temp.md
stuff.md
```

### Memory Content Structure

```markdown
# Memory: [Topic Name]

## Summary
Brief overview of what this memory contains.

## Details
- Key point 1
- Key point 2

## Decisions Made
- Decision 1: Rationale
- Decision 2: Rationale

## Progress (if tracking)
- [x] Completed item
- [ ] Pending item

## Last Updated
[Date]
```

## Editing with Serena

### Symbol-Based Editing

```markdown
# Replace entire function/method body
replace_symbol_body(
    name_path_pattern="ClassName/method_name",
    relative_path="path/to/file.py",
    new_body="def method_name(self):\n    # new implementation"
)

# Insert new code after a symbol
insert_after_symbol(
    name_path_pattern="last_function",
    relative_path="path/to/file.py",
    content="\ndef new_function():\n    pass"
)

# Insert new code before a symbol
insert_before_symbol(
    name_path_pattern="first_class",
    relative_path="path/to/file.py",
    content="# Module docstring\n\nimport os\n"
)
```

### Renaming Symbols

```markdown
# Rename across codebase
rename_symbol(
    name_path_pattern="OldClassName",
    new_name="NewClassName",
    relative_path="path/to/file.py"  # Optional: limit scope
)
```

## Thinking Tools

### think_about_collected_information

Use AFTER a sequence of search/read operations:
- Validates you have sufficient context
- Identifies gaps in understanding
- Suggests next steps

### think_about_task_adherence

Use BEFORE making changes:
- Ensures you're still on track
- Validates approach aligns with user request
- Catches scope creep

### think_about_whether_you_are_done

Use when you believe task is complete:
- Validates all requirements met
- Identifies missing pieces
- Confirms readiness for user review

## Best Practices

### DO

- Use symbolic tools for code exploration
- Write memories for important decisions
- Use `think_about_*` tools at appropriate checkpoints
- Narrow searches with `relative_path` when possible
- Use `include_body=False` first, then `True` when needed

### DON'T

- Read entire files when symbols suffice
- Make changes without understanding context
- Skip the thinking tools for complex tasks
- Forget to update memories after completing work
- Use overly broad searches without filters

## Integration with Other Tools

### Combining with Sequential Thinking

```markdown
1. Use sequential-thinking for complex analysis
2. Use Serena tools to gather code context
3. Use think_about_collected_information to validate
4. Use Serena editing tools to make changes
5. Write memory to track progress
```

### Combining with Context7

```markdown
1. Use Context7 for library documentation
2. Use Serena to find where patterns apply in codebase
3. Use Serena editing tools to implement patterns
```

## Quick Reference Card

### Tool Activation (Run First!)

| Category | Activation Command |
|----------|-------------------|
| File Search | `activate_file_search_tools` |
| Symbol Management | `activate_symbol_management_tools` |
| Code Insertion | `activate_code_insertion_tools` |
| Memory | `activate_memory_management_tools` |
| Task Adherence | `activate_task_adherence_tools` |

### Serena vs Standard Tools

| Task | ❌ Don't Use | ✅ Use Instead |
|------|-------------|----------------|
| Read Python code | `read_file` | `find_symbol(include_body=True)` |
| Find usages | `grep_search` | `find_referencing_symbols` |
| Edit function | `replace_string_in_file` | `replace_symbol_body` |
| Add new code | `create_file` / manual | `insert_after_symbol` |
| Search patterns | `grep_search` | `search_for_pattern` |

### Mandatory Workflow (All Three MCP Tools)

```
┌─────────────────────────────────────────────────┐
│ 1. ACTIVATE SERENA TOOLS (if not active)        │
│    → activate_symbol_management_tools           │
│    → activate_memory_management_tools           │
├─────────────────────────────────────────────────┤
│ 2. READ MEMORIES (understand prior context)     │
│    → list_memories → read relevant ones         │
├─────────────────────────────────────────────────┤
│ 3. COMPLEX TASK? → SEQUENTIAL THINKING          │
│    → Plan approach with structured thoughts     │
│    → Break down into steps                      │
├─────────────────────────────────────────────────┤
│ 4. USING LIBRARIES? → CONTEXT7                  │
│    → resolve-library-id                         │
│    → get-library-docs for relevant topics       │
├─────────────────────────────────────────────────┤
│ 5. EXPLORE CODE (Serena symbolic navigation)    │
│    → get_symbols_overview                       │
│    → find_symbol (include_body=False first)     │
│    → find_referencing_symbols                   │
├─────────────────────────────────────────────────┤
│ 6. VALIDATE UNDERSTANDING                       │
│    → think_about_collected_information          │
├─────────────────────────────────────────────────┤
│ 7. BEFORE CHANGES                               │
│    → think_about_task_adherence ⚠️ MANDATORY    │
├─────────────────────────────────────────────────┤
│ 8. MAKE CHANGES (Serena symbolic editing)       │
│    → replace_symbol_body                        │
│    → insert_before/after_symbol                 │
├─────────────────────────────────────────────────┤
│ 9. VERIFY COMPLETION                            │
│    → think_about_whether_you_are_done           │
├─────────────────────────────────────────────────┤
│ 10. SAVE PROGRESS                               │
│    → write_memory (if important)                │
└─────────────────────────────────────────────────┘
```

## Why These Three MCP Tools?

### Serena
1. **Token Efficiency**: Reading symbols is cheaper than reading entire files
2. **Semantic Understanding**: Tools understand code structure, not just text
3. **Safe Editing**: Symbol-based edits are more precise than string replacement
4. **Context Preservation**: Memories persist across sessions
5. **Quality Checkpoints**: Thinking tools catch errors before they happen

### Context7
1. **Up-to-Date Documentation**: Training data becomes outdated, Context7 is current
2. **Version-Specific**: Get docs for the exact library version you're using
3. **Topic-Focused**: Query specific features instead of reading entire docs
4. **Avoid Deprecated Patterns**: Libraries evolve, APIs change
5. **Best Practices**: Current community recommendations, not stale patterns

### Sequential Thinking
1. **Structured Analysis**: Break complex problems into manageable steps
2. **Hypothesis-Verification**: Test assumptions before implementing
3. **Course Correction**: Revise earlier thoughts when new info emerges
4. **Branching Exploration**: Explore multiple approaches before committing
5. **Audit Trail**: Record of reasoning for complex decisions
