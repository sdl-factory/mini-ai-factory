terraform {
  required_version = ">= 1.6"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.2"
    }
  }

  # Learning setup: state is stored locally. In a real factory it lives in a remote,
  # encrypted, locked and access-controlled backend, because state contains secrets.
}
