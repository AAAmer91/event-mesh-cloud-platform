variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "event-mesh"
}

variable "enable_pitr" {
  description = "Enable DynamoDB Point-in-Time Recovery"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
