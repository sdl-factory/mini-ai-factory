variable "name" {
  description = "Project name. Becomes the namespace name, so it must be a valid DNS label."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$", var.name))
    error_message = "name must be a lowercase DNS label (letters, digits, hyphens)."
  }
}

variable "risk_class" {
  description = "Project risk class from intake: drives how strict gates and isolation are."
  type        = string
  default     = "low"

  validation {
    condition     = contains(["low", "medium", "high"], var.risk_class)
    error_message = "risk_class must be low, medium or high."
  }
}

variable "quota" {
  description = "Hard resource limits for the whole namespace, so one project cannot starve others."
  type = object({
    requests_cpu    = string
    requests_memory = string
    limits_memory   = string
    pods            = string
  })
  default = {
    requests_cpu    = "1"
    requests_memory = "1Gi"
    limits_memory   = "2Gi"
    pods            = "10"
  }
}

variable "workload_service_account" {
  description = "Name of the identity the project's workloads run as."
  type        = string
  default     = "app"
}

variable "developer_group" {
  description = "SSO group that gets edit rights in this namespace only. Empty disables the binding."
  type        = string
  default     = ""
}
