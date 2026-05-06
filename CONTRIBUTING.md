# Contributing to VidChain

Thanks for your interest in contributing. This document covers the process for bug reports, feature requests, and pull requests.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Contribution Workflow](#contribution-workflow)
- [Code Guidelines](#code-guidelines)
- [Adding a Sensor Node](#adding-a-sensor-node)
- [Tests](#tests)
- [Commit Messages](#commit-messages)
- [Reporting Issues](#reporting-issues)

---

## Getting Started

Before contributing, please:

1. Check [open issues](https://github.com/rahulsiiitm/videochain-python/issues) to avoid duplicate work.
2. For significant changes, open an issue first to discuss the approach.
3. Fork the repository and work on a feature branch — never commit directly to `main`.

---

## Development Setup

```bash
git clone https://github.com/<your-fork>/videochain-python
cd videochain-python

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Pull required model weights
ollama pull moondream
ollama pull llama3
```

---

## Project Structure

```
videochain-python/
├── vidchain/
│   ├── __init__.py          # Public API surface (VidChain class)
│   ├── engine/              # IRIS core — routing, fusion, summarization
│   ├── nodes/               # Sensor node implementations
│   │   ├── base.py          # BaseNode abstract class
│   │   ├── keyframe.py      # AdaptiveKeyframeNode
│   │   ├── llava.py         # LlavaNode
│   │   ├── yolo.py          # YoloNode
│   │   ├── whisper.py       # WhisperNode
│   │   ├── ocr.py           # OcrNode
│   │   ├── tracker.py       # TrackerNode
│   │   ├── emotion.py       # EmotionNode
│   │   └── action.py        # ActionNode
│   ├── pipeline/            # VideoChain pipeline orchestration
│   ├── memory/              # ChromaDB + GraphRAG persistence layer
│   ├── api/                 # FastAPI routes
│   └── cli/                 # CLI entry points
├── tests/
├── assets/
└── pyproject.toml
```

---

## Contribution Workflow

```
fork → branch → change → test → pull request
```

1. **Fork** the repo and create a branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** following the code guidelines below.

3. **Run tests** and ensure nothing is broken.

4. **Push** and open a pull request against `main`.

5. A maintainer will review within a few days. Be prepared to address feedback.

---

## Code Guidelines

- Python 3.11+. Type hints on all public functions and class methods.
- Follow existing file and class naming conventions.
- No new external dependencies without prior discussion in an issue.
- Keep node classes single-responsibility — one modality per node.
- Document public methods with docstrings (NumPy style preferred).
- Do not commit model weights, large binaries, or personal test videos.

---

## Adding a Sensor Node

All sensor nodes inherit from `BaseNode`. To add a new one:

**1. Create your node class**

```python
# vidchain/nodes/mynode.py
from vidchain.nodes.base import BaseNode, FrameContext

class MyNode(BaseNode):
    """One-line description of what this node detects or extracts."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # initialize your model/resources here

    def process(self, ctx: FrameContext) -> FrameContext:
        """
        Process a single frame context.

        Parameters
        ----------
        ctx : FrameContext
            Contains the current frame, timestamp, and accumulated metadata.

        Returns
        -------
        FrameContext
            Updated context with this node's output merged in.
        """
        # your logic here
        ctx.metadata["my_node"] = { ... }
        return ctx
```

**2. Export it**

Add to `vidchain/nodes/__init__.py`:

```python
from vidchain.nodes.mynode import MyNode
```

**3. Write a test**

Add `tests/test_mynode.py` with at least one unit test using a synthetic frame.

**4. Document it**

Add a row to the **Available Nodes** table in `README.md`.

---

## Tests

```bash
# Run all tests
pytest tests/

# Run a specific file
pytest tests/test_mynode.py -v

# With coverage
pytest --cov=vidchain tests/
```

Tests should be fast and not require a live Ollama instance. Mock model calls where necessary.

---

## Commit Messages

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>: <short description>

[optional body]
```

| Type | When to use |
| :--- | :--- |
| `feat` | New feature or node |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change with no behavior change |
| `test` | Adding or updating tests |
| `chore` | Build, deps, config |

Examples:
```
feat: add DepthNode for monocular depth estimation
fix: resolve concurrency lock deadlock on rapid ingest
docs: add MyNode to README sensor table
```

---

## Reporting Issues

When filing a bug, include:

- VidChain version (`pip show vidchain`)
- Python and CUDA version
- Ollama version and models pulled
- Minimal reproduction steps
- Full traceback if applicable

Feature requests are welcome — describe the use case, not just the implementation.

---

**Author:** Rahul Sharma — IIIT Manipur  
**License:** MIT
