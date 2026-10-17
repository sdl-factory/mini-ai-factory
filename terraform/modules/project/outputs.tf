output "namespace" {
  description = "The project's namespace."
  value       = var.name
}

output "service_account" {
  description = "The identity the project's workloads run as."
  value       = var.workload_service_account
}
