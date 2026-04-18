# Contributing to UniSat

Thank you for your interest in contributing to UniSat! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/unisat.git`
3. Create a feature branch: `git checkout -b feat/your-feature`
4. Install dependencies: `./scripts/setup.sh`

## Development Setup

### Python (Flight Software, Ground Station, Simulation)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
pip install -r flight-software/requirements.txt
pip install -r ground-station/requirements.txt
pip install -r simulation/requirements.txt
pip install pytest pytest-cov ruff mypy
```

### Firmware (C)

```bash
sudo apt-get install gcc-arm-none-eabi cmake
cd firmware && mkdir build && cd build
cmake .. && make
```

## Code Style

### Python
- Follow PEP 8
- Type hints on all functions
- Google-style docstrings
- Max 200 lines per file
- Use `ruff` for linting: `ruff check .`
- Use `mypy` for type checking: `mypy flight-software/`

### C
- MISRA-like coding style
- Doxygen comments on all functions
- Descriptive variable names: `battery_voltage_mv`, not `bv`
- Max 200 lines per file

## Commit Messages

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `refactor`, `style`, `docs`, `test`, `chore`, `ci`

Examples:
- `feat(adcs): Add nadir pointing algorithm`
- `fix(eps): Correct battery SOC calculation`
- `docs: Update power budget table`
- `test(flight): Add orbit predictor unit tests`

## Pull Request Process

1. Ensure all tests pass: `pytest --cov`
2. Run linting: `ruff check . && mypy flight-software/`
3. Update documentation if needed
4. Write a clear PR description with:
   - What changed and why
   - How to test the changes
   - Any breaking changes

## Adding a New Payload

See `payloads/README.md` for the payload plugin interface. Each payload module should:

1. Inherit from `PayloadInterface`
2. Implement all required methods
3. Include a `config.json` with default parameters
4. Include unit tests

## Reporting Issues

- Use GitHub Issues
- Include: steps to reproduce, expected behavior, actual behavior
- Tag with appropriate labels: `bug`, `enhancement`, `documentation`

## License

By contributing, you agree that your contributions will be
licensed under the **Apache License, Version 2.0** — see the
[LICENSE](LICENSE) and [NOTICE](NOTICE) files in the repository
root for the full terms.

Under Apache-2.0 §5 (*Submission of Contributions*), any patch
you submit is automatically offered under Apache-2.0 terms
unless you explicitly state otherwise in the PR description.
Per §3 (*Grant of Patent License*), every contribution carries
an implicit patent-license grant from the contributor to
every user of the project.

> **License history:** the project was originally published
> under MIT (2026-02-15 — 2026-04-18). It migrated to Apache-2.0
> on 2026-04-18. Copies obtained during the MIT window stay
> MIT-licensed for their recipients — that's a fundamental
> property of open-source licences and cannot be retroactively
> changed.
