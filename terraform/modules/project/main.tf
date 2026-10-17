# A project's isolated home in the cluster: the "secure project isolation" part of onboarding.
# Each resource is one isolation layer; none of them is enough on its own.

locals {
  labels = {
    "app.kubernetes.io/managed-by" = "terraform"
    "factory/project"              = var.name
    "factory/risk-class"           = var.risk_class
  }
}

# 1. Namespace with Pod Security Admission set to "restricted": no root, no privilege
#    escalation, no host access. Non-compliant pods are rejected by the API server.
resource "kubernetes_namespace_v1" "this" {
  metadata {
    name = var.name
    labels = merge(local.labels, {
      "pod-security.kubernetes.io/enforce" = "restricted"
      "pod-security.kubernetes.io/audit"   = "restricted"
      "pod-security.kubernetes.io/warn"    = "restricted"
    })
  }
}

# 2. Quota: a ceiling for the whole project (noisy-neighbour protection).
resource "kubernetes_resource_quota_v1" "this" {
  metadata {
    name      = "project-quota"
    namespace = var.name
    labels    = local.labels
  }

  spec {
    hard = {
      "requests.cpu"    = var.quota.requests_cpu
      "requests.memory" = var.quota.requests_memory
      "limits.memory"   = var.quota.limits_memory
      "pods"            = var.quota.pods
    }
  }

  depends_on = [kubernetes_namespace_v1.this]
}

# 3. Defaults for containers that do not declare resources. Note: memory limits but no
#    default CPU limit, on purpose (CPU limits cause throttling
#    even when the node has idle CPU).
resource "kubernetes_limit_range_v1" "this" {
  metadata {
    name      = "container-defaults"
    namespace = var.name
    labels    = local.labels
  }

  spec {
    limit {
      type            = "Container"
      default         = { memory = "256Mi" }
      default_request = { cpu = "50m", memory = "64Mi" }
      max             = { memory = "1Gi" }
    }
  }

  depends_on = [kubernetes_namespace_v1.this]
}

# 4. Network: deny everything by default, then allow only what is needed.
resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny-all"
    namespace = var.name
    labels    = local.labels
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }

  depends_on = [kubernetes_namespace_v1.this]
}

resource "kubernetes_network_policy_v1" "allow_dns" {
  metadata {
    name      = "allow-dns-egress"
    namespace = var.name
    labels    = local.labels
  }

  spec {
    pod_selector {}
    policy_types = ["Egress"]

    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "k8s-app" = "kube-dns" }
        }
      }

      ports {
        port     = "53"
        protocol = "UDP"
      }

      ports {
        port     = "53"
        protocol = "TCP"
      }
    }
  }

  depends_on = [kubernetes_namespace_v1.this]
}

# Pods inside the project may talk to each other; nothing outside the project may reach in.
resource "kubernetes_network_policy_v1" "allow_same_namespace" {
  metadata {
    name      = "allow-same-namespace"
    namespace = var.name
    labels    = local.labels
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]

    ingress {
      from {
        pod_selector {}
      }
    }

    egress {
      to {
        pod_selector {}
      }
    }
  }

  depends_on = [kubernetes_namespace_v1.this]
}

# 5. Workload identity: a dedicated service account, with no API token mounted by default.
resource "kubernetes_service_account_v1" "workload" {
  metadata {
    name      = var.workload_service_account
    namespace = var.name
    labels    = local.labels
  }

  automount_service_account_token = false

  depends_on = [kubernetes_namespace_v1.this]
}

# 6. Access: the project's developers (an SSO group) can edit this namespace and nothing else.
resource "kubernetes_role_binding_v1" "developers" {
  count = var.developer_group == "" ? 0 : 1

  metadata {
    name      = "developers-edit"
    namespace = var.name
    labels    = local.labels
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = "edit"
  }

  subject {
    kind      = "Group"
    name      = var.developer_group
    api_group = "rbac.authorization.k8s.io"
  }

  depends_on = [kubernetes_namespace_v1.this]
}
