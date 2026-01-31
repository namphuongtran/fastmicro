---
applyTo: '**/*'
description: 'Guidelines for using Context7 MCP to verify library documentation before implementation'
---

# Context7 Documentation Lookup Guidelines

## Overview

Context7 MCP provides **up-to-date documentation** for libraries, frameworks, and technologies. 

**CRITICAL:** AI training data becomes outdated. Libraries change, APIs evolve, best practices shift. **Always use Context7 to verify information before implementing** - don't rely on potentially stale knowledge.

## When to Use Context7

### ALWAYS Use Context7 When:

1. **Implementing any library/framework feature** - APIs change between versions
2. **Unsure if a pattern is current** - Best practices evolve
3. **Using datetime/timezone operations** - Common source of bugs
4. **Database operations** - ORM patterns change significantly
5. **Authentication/Security** - Critical to use current patterns
6. **Testing frameworks** - pytest, asyncio patterns change
7. **Checking latest trends/approaches** - Verify current best practices
8. **Any code that "feels familiar"** - Your memory might be outdated!

### Use Context7 to Verify:

| Category | Why Verify |
|----------|-----------|
| **Library APIs** | Methods get deprecated, renamed, or removed |
| **Configuration patterns** | Pydantic v1 vs v2, old vs new config styles |
| **Async patterns** | Python async ecosystem evolves rapidly |
| **Framework conventions** | FastAPI, Django, Flask patterns change |
| **Testing approaches** | pytest-asyncio modes, fixture patterns |
| **Security practices** | OWASP recommendations update |
| **Cloud/K8s patterns** | Best practices evolve quickly |
| **Type hints** | Python typing module changes frequently |

## Usage Pattern

### Step 1: Resolve Library ID
```
mcp_context7_resolve-library-id
  libraryName: "pydantic v2"
```

### Step 2: Get Documentation
```
mcp_context7_get-library-docs
  context7CompatibleLibraryID: "/pydantic/pydantic"
  topic: "model_config validation"
```

## Examples

### Example 1: Datetime Best Practices
```
# Before implementing datetime operations:
1. resolve-library-id: "python datetime timezone"
2. get-library-docs: "/python-pendulum/pendulum" topic: "utc timezone aware"

# Result: Use datetime.now(timezone.utc), not datetime.utcnow()
```

### Example 2: Pydantic V2 Config
```
# Before using Pydantic models:
1. resolve-library-id: "pydantic"
2. get-library-docs: "/pydantic/pydantic" topic: "model_config ConfigDict"

# Result: Use model_config = ConfigDict(...), not class Config
```

### Example 3: SQLAlchemy Async
```
# Before database operations:
1. resolve-library-id: "sqlalchemy async"
2. get-library-docs: "/sqlalchemy/sqlalchemy" topic: "async session"

# Result: Use async_sessionmaker, AsyncSession patterns
```

## Anti-Patterns (What NOT to Do)

❌ **Don't trust your training data** - It's likely outdated for specific libraries
❌ **Don't assume library APIs** - Always verify current patterns
❌ **Don't use "I remember" patterns** - Verify with Context7 first
❌ **Don't skip for "simple" operations** - Even datetime has pitfalls
❌ **Don't implement without checking** - 30 seconds of verification saves hours of debugging

## The Golden Rule

> **"When in doubt, Context7 it out"**
> 
> If you're about to write code based on memory of how a library works, STOP and verify with Context7 first. Your training data is frozen in time; libraries are not.

## Integration with Other Tools

### With Serena
1. Use Context7 to verify library patterns
2. Use Serena to find existing usage in codebase
3. Ensure consistency with existing patterns

### With Sequential Thinking
1. Research phase: Use Context7 to gather documentation
2. Design phase: Apply verified patterns
3. Implementation phase: Follow documented best practices

## Checklist Before Implementation

- [ ] Identified all external libraries being used
- [ ] Resolved Context7 library IDs for each
- [ ] Retrieved documentation for relevant topics
- [ ] Verified no deprecated patterns
- [ ] Checked for breaking changes (especially Pydantic v1→v2)
- [ ] Compared with existing codebase patterns via Serena

## Key Libraries in This Project

| Library | Context7 ID | Common Topics |
|---------|-------------|---------------|
| FastAPI | `/fastapi/fastapi` | dependencies, lifespan, middleware |
| Pydantic | `/pydantic/pydantic` | model_config, validators, Field |
| SQLAlchemy | `/sqlalchemy/sqlalchemy` | async, session, relationships |
| Pendulum | `/python-pendulum/pendulum` | timezone, utc, parsing |
| structlog | `/hynek/structlog` | configuration, processors |
| pytest | `/pytest-dev/pytest` | fixtures, markers, async |

## Remember

> "Measure twice, cut once" - Always verify documentation before implementing.
> The 30 seconds spent checking Context7 can save hours of debugging deprecated patterns.
