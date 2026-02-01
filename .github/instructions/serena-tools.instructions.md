---
description: 'MANDATORY: Use Serena MCP tools FIRST for all Python code exploration, symbol management, and memory tracking. These tools are more efficient than standard file operations.'
applyTo: '**/*.py'
---

# Serena Tools Usage Guidelines - MANDATORY

## ⚠️ CRITICAL INSTRUCTION

**ALWAYS use Serena tools BEFORE using standard file operations for Python files.**

Serena provides semantic, token-efficient code exploration. Using `read_file` to read entire Python files is wasteful and should be avoided.

## Decision Tree: Which Tool to Use?

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

### Mandatory Workflow

```
┌─────────────────────────────────────────────────┐
│ 1. ACTIVATE TOOLS (if not active)               │
│    → activate_symbol_management_tools           │
│    → activate_memory_management_tools           │
├─────────────────────────────────────────────────┤
│ 2. READ MEMORIES (understand context)           │
│    → list_memories → read relevant ones         │
├─────────────────────────────────────────────────┤
│ 3. EXPLORE CODE (symbolic navigation)           │
│    → get_symbols_overview                       │
│    → find_symbol (include_body=False first)     │
│    → find_referencing_symbols                   │
├─────────────────────────────────────────────────┤
│ 4. VALIDATE UNDERSTANDING                       │
│    → think_about_collected_information          │
├─────────────────────────────────────────────────┤
│ 5. BEFORE CHANGES                               │
│    → think_about_task_adherence ⚠️ MANDATORY    │
├─────────────────────────────────────────────────┤
│ 6. MAKE CHANGES (symbolic editing)              │
│    → replace_symbol_body                        │
│    → insert_before/after_symbol                 │
├─────────────────────────────────────────────────┤
│ 7. VERIFY COMPLETION                            │
│    → think_about_whether_you_are_done           │
├─────────────────────────────────────────────────┤
│ 8. SAVE PROGRESS                                │
│    → write_memory (if important)                │
└─────────────────────────────────────────────────┘
```

## Why Serena?

1. **Token Efficiency**: Reading symbols is cheaper than reading entire files
2. **Semantic Understanding**: Tools understand code structure, not just text
3. **Safe Editing**: Symbol-based edits are more precise than string replacement
4. **Context Preservation**: Memories persist across sessions
5. **Quality Checkpoints**: Thinking tools catch errors before they happen
