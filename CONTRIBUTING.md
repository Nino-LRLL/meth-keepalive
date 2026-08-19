# Contributing to Meth

Thanks for taking the time to contribute! Meth is a small, focused tool —
we want to keep it that way.

## Ground rules

- **Small and focused.** A feature must serve the core mission: *keep
  Windows awake while your work is running*. If a feature adds complexity
  without immediate value, it gets postponed.
- **Reliability first.** Never sacrifice reliability for a new feature. If a
  change risks leaving Windows in a bad state, it does not get merged.
- **No hacks.** No fake input, no undocumented APIs, no permanent Windows
  modifications.
- **Testable layers.** UI is separated from Core and Windows. New code must
  follow the same separation and come with tests (the Windows API is mocked
  in tests).

## Getting started

1. Fork the repository and clone it.
2. Set up the environment:

   ```bat
   pip install -r requirements.txt
   ```

3. Run the tests:

   ```bat
   python -m unittest discover -s tests -v
   ```

4. Create a branch: `git checkout -b feature/your-feature`.

## Development

- Code style: PEP 8, type hints where useful, docstrings in English.
- Comments and user-facing strings can be English or French (both are
  welcome).
- Run `python -m unittest discover -s tests -v` before opening a PR — all
  tests must pass.

## Testing on real hardware

Some behaviors can only be verified on real Windows hardware (lid events,
power state). If you add lid/power code, please note in the PR what you
tested and on what hardware. The test suite mocks the Windows API, so real
verification is valuable.

## Pull requests

- Keep PRs small and focused on one change.
- Update the CHANGELOG if the change is user-visible.
- Update the relevant README (English or French) if behavior or usage
  changes.
- Reference the issue your PR fixes, if any.

## Code of conduct

By participating you agree to our [Code of Conduct](CODE_OF_CONDUCT.md).
