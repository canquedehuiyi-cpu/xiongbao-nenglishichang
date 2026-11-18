# pytest Engineering Standards & Deliverables

## Directory layout (generate exactly this)

```
tests/
├── conftest.py              # global fixtures (config, paths, shared mocks)
├── unit/                    # unit tests, mirroring the src/ structure
│   └── test_<module>.py
├── integration/
│   └── test_<module>_integration.py
├── e2e/
│   └── test_<feature>.py
├── fixtures/                # test data files (JSON/YAML)
└── factories.py             # test data builders
```

## Specific rules

- **Layered conftest.py**: only cross-directory shared fixtures go in the top-level
  file; local fixtures live in their own subdirectory's conftest.py.
- **Fixtures**: names express what they provide; keep scope minimal (`function` by
  default); use `yield` teardown for stateful fixtures.
- **Parametrize**: all data-driven cases use `@pytest.mark.parametrize` with readable
  ids — `ids=["empty input", ...]` for the list form, or
  `pytest.param(..., id="empty input")` per case. Each case name still follows the
  `test_<behavior>__<scenario>__<expected_result>` convention with a collective
  scenario segment (see methodology.md, Per-test rules).
- **Markers**: custom markers (`e2e` / `slow` / `live`) must be registered in the
  pytest config.
- **Mocking**: isolate all external dependencies via `monkeypatch` / `pytest-mock`;
  centralize mocks in fixtures; no hand-written patch decorators inside test bodies.
- **File header**: each test file starts with a comment block stating what it tests,
  what it does NOT test, and which fixtures it depends on.

### Test file header template

```python
"""Tests for <module_under_test>.

Tests:    <behaviors covered>
Does NOT test: <excluded concerns, e.g. DB persistence -> integration layer>
Fixtures used: <fixture_a> (global conftest), <fixture_b> (unit/conftest)
"""
```

## Configuration template

Generate a `[tool.pytest.ini_options]` section in pyproject.toml (or pytest.ini if the
project has no pyproject.toml):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config"
markers = [
    "e2e: end-to-end tests, excluded from regular CI runs",
    "slow: takes a long time to run",
    "live: requires live external services",
]
```

Layer selection is done via directory conventions:
`pytest tests/unit`, `pytest tests/integration`, `pytest tests/e2e -m e2e`,
and default runs exclude e2e via `-m "not e2e"` in addopts or CI config.

## Deliverables (in this exact order)

1. **Test plan**: a table of `test target -> test type -> case count -> key scenarios`
2. **Directory structure**: full file tree
3. **conftest.py and factories.py**, with each fixture annotated with its purpose
4. **Test code**: complete, runnable files; no ellipsis or placeholder omissions
5. **pytest configuration + run commands**, per layer (unit / integration / e2e),
   plus the coverage command:
   `pytest tests/unit tests/integration --cov=<src_pkg> --cov-branch --cov-report=term-missing`
6. **Self-check report**: tick off every acceptance item listed in SKILL.md
