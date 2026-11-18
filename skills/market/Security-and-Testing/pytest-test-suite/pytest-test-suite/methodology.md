# Testing Methodology (Mandatory)

## Test layering (test pyramid)

| Layer | Share | Rules |
|-------|-------|-------|
| Unit | ~70% | Isolated functions/classes, all external dependencies mocked; each must run in milliseconds |
| Integration | ~20% | Verify inter-module collaboration; in-memory DB or containerized dependencies allowed |
| End-to-end | ~10% | Tagged `@pytest.mark.e2e`, excluded from regular CI runs by default |

## Test case design

- Equivalence partitioning + boundary value analysis (empty, zero, max, illegal types).
- Every public function covered on at least: **happy path, boundary path, error path**.
- Prefer black-box behavior testing; test implementation details only when necessary.
- First analyze the code and produce a test plan (inventory of test targets);
  **wait for approval before writing any code**.

## Per-test rules

- Follow the AAA pattern: Arrange / Act / Assert, separated by blank lines.
- One test verifies exactly one scenario; no unrelated multiple asserts.
- Naming: `test_<behavior>__<scenario>__<expected_result>`,
  e.g. `test_calculate_nav__negative_amount__raises_valueerror`.
  Parametrized cases covering one equivalence class keep the same convention with a
  collective scenario segment; the per-case `ids` provide the concrete scenario
  (e.g. `test_calculate_nav__valid_amounts__returns_expected_nav[zero amount]`).
- Every test has a one-line docstring describing Given / When / Then.
- No `for` loops, `if` branches, or `try/except` inside test bodies —
  use `@pytest.mark.parametrize` for all variants.
- Use plain `assert` with explanatory messages; assert exceptions with
  `pytest.raises(..., match=...)`.

### Canonical test shape

```python
def test_calculate_nav__negative_amount__raises_valueerror(bond_portfolio):
    """Given a portfolio and negative amount, when calculating NAV, then raise ValueError."""
    amount = -100

    with pytest.raises(ValueError, match="amount must be non-negative"):
        calculate_nav(bond_portfolio, amount)
```

```python
@pytest.mark.parametrize(
    ("amount", "expected"),
    [(0, Decimal("0")), (1000, Decimal("10.50"))],
    ids=["zero amount", "typical amount"],
)
def test_calculate_nav__valid_amounts__returns_expected_nav(bond_portfolio, amount, expected):
    """Given a valid amount, when calculating NAV, then return the expected value."""
    result = calculate_nav(bond_portfolio, amount)

    assert result == expected, f"NAV for {amount} should be {expected}, got {result}"
```

## FIRST principles (acceptance baseline)

- **F**ast: each unit test < 100 ms.
- **I**ndependent: zero inter-test dependencies; any order, any subset passes.
- **R**epeatable: no randomness / current time / real network; fix random seeds,
  freeze time with freezegun or monkeypatch.
- **S**elf-validating: the exit code is the result; no manual output inspection.
- **T**imely: tests map 1:1 to the code under test.
