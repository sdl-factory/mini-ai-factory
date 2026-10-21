# Project onboarding as code. Every project on the factory is one module block here,
# added through a reviewed pull request: that review is the onboarding approval.

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

module "mini_factory" {
  source = "../modules/project"

  name                     = "mini-factory"
  risk_class               = "low"
  workload_service_account = "notes-api"
}

# Onboarding a second project is one more block. Try it in phase 3, then prove that
# workloads in one namespace cannot reach the other.

module "client_a" {
  source     = "../modules/project"
  name       = "client-a"
  risk_class = "high"
  quota = {
    requests_cpu    = "2"
    requests_memory = "2Gi"
    limits_memory   = "4Gi"
    pods            = "20"
  }
}
