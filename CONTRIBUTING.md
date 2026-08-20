# Contributing to Event-Mesh Cloud Platform

Thank you for your interest in contributing! This project follows modern platform engineering standards, test-driven development, and strict infrastructure automation.

---

## 🛠️ Development Workflow

1. **Prerequisites:**
   - Docker & Docker Compose
   - Python 3.11+
   - HashiCorp Terraform 1.5+

2. **Clone & Setup:**
   ```bash
   git clone https://github.com/AAAmer91/event-mesh-cloud-platform.git
   cd event-mesh-cloud-platform
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   pip install -r dev-requirements.txt
   ```

3. **Start LocalStack & Apply Infrastructure:**
   ```bash
   make up
   make tf-init
   make tf-apply
   ```

4. **Run Tests & Linters:**
   ```bash
   make test-unit
   make test-integration
   make lint
   ```

---

## 📜 Pull Request Guidelines

- All commits must follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`).
- All code changes must include corresponding unit and integration tests.
- PRs must pass all GitHub Actions automated workflows before merge.
