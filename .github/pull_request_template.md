## Change summary

Explain the problem, the chosen change, and any behavior intentionally left out of scope.

## Affected areas

- [ ] Terraform or AWS resource configuration
- [ ] Event ingestion or producer behavior
- [ ] Worker or consumer behavior
- [ ] Event schema, retry, or idempotency contract
- [ ] Tests and local fixtures
- [ ] Workflow or release automation
- [ ] Documentation or operating procedure

## Verification

List the commands or workflow runs used to verify this change.

- [ ] Unit tests (`make test-unit`)
- [ ] LocalStack integration tests (`make test-integration`)
- [ ] Lint and static checks (`make lint`)
- [ ] Terraform formatting and validation, when applicable

## Risk and operations

- [ ] No credentials, state files, or generated secrets are committed
- [ ] Duplicate delivery and partial failure behavior were considered
- [ ] Rollback and data compatibility were considered
- [ ] Documentation and runbooks were updated when contracts or recovery steps changed
