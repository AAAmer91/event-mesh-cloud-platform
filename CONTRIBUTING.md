# Contributing

Changes should preserve the event contract, at-least-once delivery assumptions, and repeatability of the Terraform environments. Keep pull requests focused and document any operational tradeoff introduced by a change.

## Development setup

Prerequisites:

- Docker with Compose v2
- Python 3.11 or later
- Terraform 1.5 or later
- GNU Make

Create a virtual environment and install the locked development dependencies:

```bash
git clone https://github.com/AAAmer91/event-mesh-cloud-platform.git
cd event-mesh-cloud-platform
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r dev-requirements.txt
```

Start LocalStack, package the handlers, and create the local infrastructure:

```bash
make up
make package
make tf-init
make tf-apply
```

## Verification

Run the checks affected by the change:

```bash
make test-unit
make test-integration
make lint
```

Infrastructure changes should also pass formatting and validation through the corresponding Make targets or CI jobs. Changes to retry behavior, event schemas, idempotency, or queue configuration should include an integration test for the relevant failure path.

## Pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/) because release calculation depends on commit type.
- Add or update tests for behavior changes when an automated check is practical.
- Update architecture or operating documentation when contracts, controls, or recovery steps change.
- Do not commit credentials, Terraform state, generated packages, or local environment files.
- Wait for the aggregate required quality gate before merge.

Security findings should follow [SECURITY.md](SECURITY.md), not a public issue or ordinary pull request.
