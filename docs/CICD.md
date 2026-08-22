# CI/CD and Deployment Operations

This repository treats workflow output as release evidence. Missing telemetry, skipped mandatory jobs, failed package imports, security findings, and SLA regressions fail closed.

## Pipeline contracts

| Stage | Evidence produced | Blocking behavior |
| --- | --- | --- |
| Python matrix | JUnit result, 85% coverage threshold, coverage XML | Required |
| Static analysis | Ruff, Mypy, blocking Bandit report | Required |
| Supply chain | CodeQL, dependency review, pip-audit, OpenSSF Scorecard | Required |
| Package | Linux/Python 3.11 Lambda ZIP, import smoke test, SHA-256 | Required |
| Infrastructure | Local and AWS Terraform format/validation | Required |
| Integration | Terraform-applied LocalStack and asynchronous E2E tests | Required |
| Release | Conventional version, release assets, SBOM and signed attestations | Main only, after all gates |
| Deployment | Saved plan, GitHub deployment record, API smoke response | Protected environment |
| Performance | Raw telemetry, baseline comparison, incident and Pages history | Scheduled/manual gate |

All external actions are pinned to immutable full commit SHAs. Dependabot proposes grouped updates for Actions, Python, Terraform, and Docker Compose.

## One-time AWS bootstrap

The bootstrap is intentionally separate because it creates the trust and state used by subsequent Terraform runs. Run it once with an administrator identity:

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

The trust policy only accepts tokens issued for this repository's `dev` or `production` GitHub environments. Record the two Terraform outputs.

## GitHub configuration

Create `dev` and `production` environments. Add these environment variables to both:

| Variable | Value |
| --- | --- |
| `AWS_ROLE_ARN` | `aws_role_arn` bootstrap output |
| `TF_STATE_BUCKET` | `terraform_state_bucket` bootstrap output |
| `AWS_REGION` | Deployment region, normally `us-east-1` |

For `production`, enable required reviewers, prevent self-review, and restrict deployments to `main` or release tags. Enable GitHub Pages with **GitHub Actions** as its source.

In **Settings > Code security**, enable Dependency Graph. The PR dependency and license gate requires it. Until it is enabled, the workflow emits an explicit warning and continues to enforce the blocking `pip-audit` lockfile scan instead of failing for unavailable repository metadata.

Configure a `main` ruleset with:

- pull requests and conversation resolution required;
- code-owner review for `.github/` and `infra/`;
- `Required Quality Gate` as a required status check;
- merge queue enabled—the pipeline supports the `merge_group` event;
- force pushes and branch deletion blocked;
- signed commits and linear history if they match the repository contribution model.

In Actions settings, keep the default `GITHUB_TOKEN` read-only and require actions to be pinned to full SHAs.

## Release policy

Only conventional commits create releases:

- `fix:`, `perf:`, and `refactor:` create a patch release;
- `feat:` creates a minor release;
- `!` or `BREAKING CHANGE:` creates a major release;
- documentation and maintenance-only commits produce no release.

The release contains `lambda-package.zip` and `sbom.cdx.json`. Verify provenance locally with:

```bash
gh attestation verify lambda-package.zip \
  --repo AAAmer91/event-mesh-cloud-platform
```

## Promotion and rollback

After a releasable main build, the tested artifact is deployed to `dev`. Production waits at its protected environment approval. Both use the same GitHub Release tag and ZIP digest.

The deployment applies a saved Terraform plan, sends a valid order to the deployed API, and expects HTTP 201. A failed smoke test downloads the prior GitHub Release asset and reapplies Terraform before failing the deployment visibly.

For a manual promotion or rollback, run **Reusable AWS Deployment** and choose the environment plus any existing release tag. GitHub records the operation against the selected environment.

## Performance operations

The scheduled workflow restores the latest successful `performance-history` artifact, compares throughput and p99 latency with the previous baseline, and enforces absolute availability/resilience SLAs. It then:

1. uploads 90-day raw evidence;
2. publishes the trend dashboard through GitHub Pages;
3. opens or updates a labeled regression issue on failure;
4. comments on and closes the incident after recovery.

No result file means `NO DATA` and a failed gate—it can never render as a successful empty run.
