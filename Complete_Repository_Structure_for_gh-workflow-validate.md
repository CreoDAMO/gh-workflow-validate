# Complete Repository Structure for gh-workflow-validate

## Directory Tree

```
gh-workflow-validate/
├── .github/
│   └── workflows/
│       └── validate.yml
├── src/
│   └── workflow_validate/
│       ├── __init__.py
│       └── validator.py
├── tests/
│   └── test_validator.py
├── examples/
│   ├── valid-workflow.yml
│   └── invalid-workflow.yml
├── gh-workflow-validate
├── setup.py
├── MANIFEST.in
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
└── workflow-validator-output.schema.json
```

---

## File Contents

### `.github/workflows/validate.yml`

```yaml
name: Validate Workflows
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
      
      - name: Run tests
        run: python -m unittest tests/test_validator.py -v
      
      - name: Validate workflows (self-validation)
        run: python gh-workflow-validate --batch ".github/workflows/*.yml" --json
```

---

### `src/workflow_validate/__init__.py`

```python
"""gh-workflow-validate - GitHub Actions workflow validator."""

__version__ = "1.0.0"
__author__ = "CreoDAMO"
__license__ = "MIT"

from .validator import YAMLValidator, main

__all__ = ["YAMLValidator", "main", "__version__"]
```

---

### `gh-workflow-validate`

```python
#!/usr/bin/env python3
"""CLI entry point for gh-workflow-validate."""

from workflow_validate.validator import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

**Note:** Make this file executable:
```bash
chmod +x gh-workflow-validate
```

---

### `setup.py`

```python
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme = Path(__file__).parent / "README.md"
long_description = readme.read_text(encoding="utf-8") if readme.exists() else ""

# Read version from package
about = {}
version_file = Path(__file__).parent / "src" / "workflow_validate" / "__init__.py"
with open(version_file) as f:
    exec(f.read(), about)

setup(
    name="gh-workflow-validate",
    version=about["__version__"],
    description="Parser-backed, schema-validated GitHub Actions workflow validator with batch mode and CI annotations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="CreoDAMO",
    author_email="creodamo@example.com",
    url="https://github.com/CreoDAMO/gh-workflow-validate",
    project_urls={
        "Bug Reports": "https://github.com/CreoDAMO/gh-workflow-validate/issues",
        "Source": "https://github.com/CreoDAMO/gh-workflow-validate",
        "Documentation": "https://github.com/CreoDAMO/gh-workflow-validate#readme",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    scripts=["gh-workflow-validate"],
    install_requires=[
        "ruamel.yaml>=0.17.0",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="github-actions workflow validation yaml ci-cd linter",
    zip_safe=False,
)
```

---

### `MANIFEST.in`

```
include README.md
include LICENSE
include CHANGELOG.md
include workflow-validator-output.schema.json
recursive-include tests *.py
recursive-include examples *.yml
```

---

### `LICENSE`

```
MIT License

Copyright (c) 2024 CreoDAMO

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

### `CHANGELOG.md`

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-17

### Added
- Initial stable release
- Parser-backed YAML syntax validation (Phase 1)
- Structural schema validation for GitHub Actions (Phase 2)
  - Required sections: `on`, `jobs`
  - Job structure validation
  - Step structure validation
  - Permissions scope and level validation
  - Strategy matrix validation
- Heuristic linting with non-blocking warnings (Phase 3)
  - Tab character detection
  - Unclosed string detection
  - Empty jobs detection
  - Missing trigger warnings
- Batch mode for repository-wide validation
  - Glob pattern support
  - Directory expansion
  - Structured error handling for no matches
- Versioned JSON output (v1.0)
  - Single-file output format
  - Batch aggregation format
  - Formal JSON Schema (Draft 2020-12)
- GitHub Actions CI integration
  - Native annotations to stderr
  - Proper exit codes (0/1)
  - `GITHUB_ACTIONS` environment detection
- Comprehensive unit tests
  - Syntax validation tests
  - Schema validation tests
  - Batch mode tests
  - CLI integration tests
- Complete documentation
  - README with examples
  - JSON Schema documentation
  - Usage guides
  - FAQ section

### Design Principles
- Epistemic honesty: proves only what can be proven
- Bounded correctness: clear guarantees and non-goals
- Deterministic outputs: same input → same output
- CI-safe: proper exit codes and annotations

### Non-Goals (Deliberate Exclusions)
- No expression evaluation (`${{ }}`)
- No runtime simulation
- No auto-fixing
- No cross-file inference
- No parallel batch processing (sequential for determinism)

[1.0.0]: https://github.com/CreoDAMO/gh-workflow-validate/releases/tag/v1.0.0
```

---

### `.gitignore`

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Testing
.tox/
.coverage
.coverage.*
.cache
.pytest_cache/
htmlcov/
*.cover
.hypothesis/

# Distribution
dist/
build/
*.egg-info/

# Temporary files
*.log
*.tmp
.temp/
```

---

### `examples/valid-workflow.yml`

```yaml
name: Example Valid Workflow
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  pull-requests: write

env:
  NODE_VERSION: '18'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build
        run: npm run build

  test:
    runs-on: ubuntu-latest
    needs: build
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        node: [16, 18, 20]
    steps:
      - uses: actions/checkout@v4
      
      - name: Run tests
        run: npm test
```

---

### `examples/invalid-workflow.yml`

```yaml
name: Example Invalid Workflow

# Missing required 'on' trigger

jobs:
  build:
    # Missing required 'runs-on'
    steps:
      # Missing 'run' or 'uses'
      - name: Invalid step

  test:
    runs-on: ubuntu-latest
    permissions:
      invalid-scope: read  # Invalid permission scope
    strategy:
      matrix: "not-a-dict"  # Should be a mapping
    steps:
      - run: echo "test"
```

---

## Setup Instructions

### Initial Repository Setup

```bash
# 1. Create repository on GitHub
# Go to https://github.com/CreoDAMO and create 'gh-workflow-validate'

# 2. Clone and set up locally
git clone https://github.com/CreoDAMO/gh-workflow-validate.git
cd gh-workflow-validate

# 3. Create all directories
mkdir -p .github/workflows src/workflow_validate tests examples

# 4. Copy all file contents from above into their respective locations

# 5. Make CLI executable
chmod +x gh-workflow-validate

# 6. Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 7. Install in development mode
pip install -e .

# 8. Run tests
python -m unittest tests/test_validator.py -v

# 9. Test CLI
./gh-workflow-validate examples/valid-workflow.yml
./gh-workflow-validate --batch examples/ --json

# 10. Commit and push
git add .
git commit -m "Initial release v1.0.0"
git push origin main

# 11. Create release tag
git tag v1.0.0
git push origin v1.0.0
```

### Publishing to PyPI

```bash
# 1. Install build tools
pip install build twine

# 2. Build distribution
python -m build

# 3. Check distribution
twine check dist/*

# 4. Upload to TestPyPI (optional, for testing)
twine upload --repository testpypi dist/*

# 5. Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ gh-workflow-validate

# 6. Upload to PyPI
twine upload dist/*
```

### GitHub CLI Extension Setup

```bash
# 1. Ensure executable is in repo root
ls -l gh-workflow-validate

# 2. Create GitHub release
gh release create v1.0.0 \
  --title "v1.0.0 - Initial Stable Release" \
  --notes "See CHANGELOG.md for details"

# 3. Users can now install with:
gh extension install CreoDAMO/gh-workflow-validate
```

---

## Verification Checklist

After setting up the repository, verify:

- [ ] All files created in correct locations
- [ ] `gh-workflow-validate` is executable
- [ ] Virtual environment activated
- [ ] Package installs: `pip install -e .`
- [ ] Tests pass: `python -m unittest tests/test_validator.py -v`
- [ ] CLI works: `./gh-workflow-validate examples/valid-workflow.yml`
- [ ] Batch mode works: `./gh-workflow-validate --batch examples/`
- [ ] JSON output valid: `./gh-workflow-validate examples/valid-workflow.yml --json | jq`
- [ ] Invalid workflow detected: `./gh-workflow-validate examples/invalid-workflow.yml`
- [ ] Self-validation passes: `./gh-workflow-validate --batch .github/workflows/`
- [ ] Git repository initialized
- [ ] All files committed
- [ ] Tag created: `git tag v1.0.0`
- [ ] Pushed to GitHub
- [ ] GitHub Actions workflow runs successfully
- [ ] PyPI package built: `python -m build`
- [ ] PyPI package uploaded (when ready)

---

## Quick Start After Setup

```bash
# Install from repository
pip install git+https://github.com/CreoDAMO/gh-workflow-validate.git

# Or install as GitHub CLI extension
gh extension install CreoDAMO/gh-workflow-validate

# Use it
gh workflow-validate .github/workflows/ci.yml
gh workflow-validate --batch ".github/workflows/" --json
```

---

## Maintenance Notes

### Version Bumping

1. Update version in `src/workflow_validate/__init__.py`
2. Update `CHANGELOG.md` with changes
3. Commit: `git commit -am "Bump version to x.y.z"`
4. Tag: `git tag vx.y.z`
5. Push: `git push && git push --tags`
6. Build and upload to PyPI

### Adding Tests

1. Add test to `tests/test_validator.py`
2. Run: `python -m unittest tests/test_validator.py -v`
3. Ensure all tests pass before committing

### Updating Schema

1. Modify `workflow-validator-output.schema.json`
2. Update version field if breaking change
3. Document in `CHANGELOG.md`
4. Update README if needed

---

**Repository is now complete and ready for v1.0.0 release! 🚀**
