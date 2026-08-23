# CI/CD and Deployment Operations

The workflows implement a build-once promotion model for the proof of concept. Pull requests verify application and infrastructure changes; main-branch releases package an immutable Lambda artifact; protected environments control AWS deployment. This document covers the GitHub and AWS configuration that cannot be expressed entirely in workflow files.

## Pipeline stages

| Stage | Output | When it blocks |
| --- | --- | --- |
| Python matrix | JUnit results, coverage XML, and an 85% coverage check | Pull request and main verification |
| Static analysis | Ruff, Mypy, and Bandit results | Pull request and main verification |
| Supply chain | CodeQL, dependency review, pip-audit, and OpenSSF Scorecard results | According to event and repository capability |
| Package | Linux/Python 3.11 Lambda ZIP, import smoke test, and SHA-256 digest | Before release or deployment |
| Infrastructure | Terraform format and configuration validation | Pull request and main verification |
| Integration | Terraform-applied LocalStack and asynchronous flow tests | Pull request and main verification |
| Release | Conventional version, release assets, SBOM, and provenance | Releasable main-branch changes |
| Deployment | Saved plan, GitHub deployment record, and API smoke response | Selected protected environment |
| Performance | Raw result, baseline comparison, issue state, and Pages history | Scheduled or manual run |

External actions are pinned to full commit SHAs. Dependabot proposes grouped updates for Actions, Python, Terraform, and Docker Compose; pinned references still require periodic review and updating.

Some jobs are intentionally conditional. For example, OpenSSF Scorecard runs on its supported main-branch, scheduled, or manual contexts rather than every pull-request event. A skipped conditional job is different from a failed required gate, so branch protection should require the aggregate `Required Quality Gate` defined by the primary workflow.

## One-time AWS bootstrap

The bootstrap creates the OIDC trust relationship and remote Terraform state used by later deployments. Run it once with an authorized administrator identity:

```bash
terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap apply \
  -var="state_bucket_name=YOUR-GLOBALLY-UNIQUE-STATE-BUCKET"
```

If the AWS account already has GitHub's OIDC provider, import it before applying:

```bash
terraform -chdir=infra/terraform/bootstrap import \
  aws_iam_openid_connect_provider.github \
  arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com
```

The trust policy limits tokens to this repository's `dev` and `production` GitHub environments. Review the generated IAM plan against the target account's policies and retain the role ARN and state-bucket outputs.

## GitHub configuration

Create `dev` and `production` environments. Add these environment variables to both:

| Variable | Value |
| --- | --- |
| `AWS_ROLE_ARN` | `aws_role_arn` bootstrap output |
| `TF_STATE_BUCKET` | `terraform_state_bucket` bootstrap output |
| `AWS_REGION` | Target deployment region, such as `us-east-1` |

For `production`, enable required reviewers, prevent self-review, and restrict deployments to `main` or approved release tags. Enable GitHub Pages with **GitHub Actions** as its source if the performance history site is required.

In **Settings > Code security**, enable Dependency Graph. The pull-request dependency and license check uses that repository metadata. The lockfile `pip-audit` scan remains the package vulnerability gate when dependency-review metadata is unavailable.

Configure a `main` ruleset with:

- pull requests and conversation resolution required;
- code-owner review for `.github/` and `infra/`;
- `Required Quality Gate` as a required status check;
- merge queue enabled if the repository uses it;
- force pushes and branch deletion blocked;
- signed commits and linear history if required by the team contribution model.

Keep the default `GITHUB_TOKEN` read-only in Actions settings. Individual jobs request only the additional permissions they need.

## Release policy

The release workflow interprets conventional commits as follows:

- `fix:`, `perf:`, and `refactor:` increment the patch version;
- `feat:` increments the minor version;
- `!` or `BREAKING CHANGE:` increments the major version;
- documentation and maintenance-only commits do not create a release.

The release contains `lambda-package.zip` and `sbom.cdx.json`. Verify GitHub provenance after downloading an artifact:

```bash
gh attestation verify lambda-package.zip \
  --repo AAAmer91/event-mesh-cloud-platform
```

An attestation links an artifact to its workflow identity and source context. It does not establish that the source code is free of defects.

## Promotion and rollback

After a releasable main build, the tested ZIP is deployed to `dev`. Production waits for its protected-environment approval. Both environments use the same GitHub Release asset and verify its digest before deployment.

The deployment applies a saved Terraform plan, sends a valid order to the API, and expects HTTP 201. If the smoke test fails, the workflow attempts to obtain the previous GitHub Release asset and reapply the earlier version before reporting failure. Operators must still confirm service recovery and investigate state or schema changes that an artifact rollback cannot reverse.

For a manual promotion or rollback, run **Reusable AWS Deployment** and select an environment plus an existing release tag. GitHub records the job against that environment.

## Performance history

The scheduled workflow restores the latest successful `performance-history` artifact, compares throughput and p99 latency with the previous baseline, and evaluates the configured availability and resilience thresholds. It then uploads the current result, renders the Pages history, and opens, updates, or closes a labeled regression issue based on the outcome.

A missing or invalid result is treated as `NO DATA` and fails the gate. The benchmark is useful for detecting regressions in the controlled LocalStack runner environment; it is not an AWS capacity or production load test.

## Operational boundaries

Repository automation does not configure organization-wide runner policy, AWS account vending, centralized log retention, cost controls, production alert routing, or Terraform state recovery. Those controls remain responsibilities of the platform and operations teams adopting this pattern.
