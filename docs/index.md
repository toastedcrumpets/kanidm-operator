# Kanidm Operator

The Kanidm Operator deploys and manages [Kanidm](https://kanidm.com/) identity servers on Kubernetes. It turns users, groups, OAuth2 clients, and server configuration into declarative custom resources.

## Why use it?

Kanidm itself needs persistent storage for passwords and account state, but **configuration can live in Git**. This operator lets you:

- Deploy a Kanidm server with TLS, ingress, backups, and storage
- Declare users and groups as Kubernetes resources
- Provision OAuth2 clients and store client secrets in Kubernetes `Secret` objects

## Requirements

- Kubernetes cluster with a working kubeconfig
- [cert-manager](https://cert-manager.io/) for Kanidm TLS certificates
- An ingress controller terminating HTTPS (the operator configures Kanidm via the CLI over HTTPS)

## Quick links

- [Getting started](getting-started.md) — install CRDs, deploy the operator, create your first instance
- [Kanidm CRD](crds/kanidm.md) — server deployment options
- [Developing](developing.md) — run the operator locally and execute tests
- [Upgrading to Kanidm 1.10](upgrading/kanidm-1.10.md) — migration notes from older Kanidm versions

## Supported Kanidm version

The operator currently targets **Kanidm 1.10.3**. Set `spec.version` on the `Kanidm` custom resource to pin the server image tag.
