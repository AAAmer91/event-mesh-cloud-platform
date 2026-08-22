output "aws_role_arn" {
  description = "Set this as AWS_ROLE_ARN in the dev and production GitHub environments"
  value       = aws_iam_role.github_deployer.arn
}

output "terraform_state_bucket" {
  description = "Set this as TF_STATE_BUCKET in the dev and production GitHub environments"
  value       = aws_s3_bucket.terraform_state.id
}
