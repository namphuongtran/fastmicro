---
description: 'Guidelines for effectively using Serena MCP tools for code exploration, symbol management, and memory tracking in this repository'
applyTo: '**/*.py'
---

# Serena Tools Usage Guidelines

Instructions for effectively using Serena's semantic coding tools to explore, understand, and modify Python code in this repository.

## Overview

Serena provides intelligent, token-efficient code exploration through symbolic tools. Instead of reading entire files, use Serena's tools to navigate code semantically.

## Core Principles

### 1. Symbolic Navigation Over Full File Reads

```markdown
# WRONG: Reading entire files
read_file("module.py", 1, 1000)

# CORRECT: Use symbolic tools
1. get_symbols_overview(file) → Get all symbols in file
2. find_symbol(name_path, include_body=False) → Get symbol metadata
3. find_symbol(name_path, include_body=True) → Read specific symbol body
```

### 2. Progressive Information Gathering

1. **Start broad**: `get_symbols_overview` for file structure
2. **Narrow down**: `find_symbol` with `depth=1` for class members
3. **Deep dive**: `find_symbol` with `include_body=True` for implementation
4. **Find usages**: `find_referencing_symbols` for impact analysis

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
