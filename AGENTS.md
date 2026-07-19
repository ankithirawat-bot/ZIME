# ZIME Development Guide

## Project Overview

ZIME is an evidence-driven investment research and decision platform for the Indian stock market. The goal is to build an AI Portfolio Manager that automatically discovers high-quality investment opportunities across multiple time horizons.

## Roles

### Product Owner (Human)

- Defines vision, priorities, and requirements
- Approves architecture decisions and sprint plans
- Reviews and accepts completed work
- Sets priorities for next milestones
- Has final say on all product decisions

### Lead Architect (ChatGPT)

- Designs architecture and technical specifications
- Plans sprints and breaks work into capabilities
- Reviews code for architectural consistency
- Documents decisions and maintains ARCHITECTURE.md
- Does NOT write production code
- Does NOT commit changes

### Engineering Agent (Opencode)

- Implements code per approved specifications
- Writes tests and runs verification
- Follows coding standards and architecture patterns
- Updates documentation when implementation changes architecture
- Does NOT commit changes unless explicitly instructed
- Does NOT modify unrelated files

## Architecture Principles

1. **Layered design**: core -> factors -> engines -> services -> API
2. **Factor framework**: All quantitative logic inherits from BaseFactor
3. **Immutable results**: FactorResult is a frozen dataclass
4. **No exceptions from factors**: Invalid data returns value=None, signal=NEUTRAL
5. **Registry pattern**: Factors self-register at import time
6. **Minimal dependencies**: Each module imports only what it needs

## Coding Standards

- Python 3.12+
- Type hints on all public methods
- Docstrings on all public classes and methods
- Line length: 100 characters (Ruff formatter)
- Double quotes for strings
- 4-space indentation
- No comments unless explicitly requested

## Workflow

- Capability-based development (one capability at a time)
- Verify before marking complete
- Never auto-commit changes
- Keep changes minimal and focused

## Task Size Rules

| Size | Scope | Example |
|------|-------|---------|
| Small | 1 file | New factor implementation |
| Medium | 2-5 files | New engine + supporting changes |
| Large | 5+ files | Architecture change, new subsystem |

## Verification Checklist

Before completing any task:

1. All imports resolve (no circular imports)
2. Tests pass
3. Ruff lint clean
4. No unrelated files modified
5. Documentation updated if architecture changed

# Project Storage Policy

## Primary Development Drive

The ZIME project is hosted on **D:**.

### Rules

- Keep all source code inside the project directory on D:.
- Keep all generated reports inside the project directory.
- Keep all logs inside the project directory.
- Keep all datasets inside the project directory.
- Keep all exported files inside the project directory.
- Keep all project-owned configuration files inside the project directory.

Do **NOT** intentionally create project files under:

- C:\Users\
- C:\Temp\
- C:\Projects\
- %LOCALAPPDATA%
- %APPDATA%

### Exceptions

The following are acceptable because they are operating system or tool managed:

- Python cache (`__pycache__`)
- pip cache
- pytest cache
- virtual environment metadata
- Windows temporary files
- Git internal files
- Visual Studio Code cache

If a tool needs a temporary working directory, prefer using a location inside the project on D: whenever practical.