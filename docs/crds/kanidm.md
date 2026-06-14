# Kanidm custom resource

Deploys a Kanidm server and the Kubernetes objects it needs: PVCs, TLS certificate, ingress, configmap, and admin credential secrets.

```yaml
apiVersion: kanidm.github.io/v1alpha1
kind: Kanidm
metadata:
  name: kanidm-instance
  namespace: kanidm
spec:
  version: 1.10.3
  domain: idm.example.com
  certificate:
    issuer: letsencrypt-prod
  database:
    fsType: other
    storageClass: standard
    storageSize: 1Gi
    arcSize: 2048
  backup:
    enabled: true
    schedule: "0 9 * * *"
    versions: 7
    storageClass: standard
    storageSize: 7Gi
  webPort: 8443
  ldapPort: 3890
  logLevel: info
  highAvailability:
    enabled: false
    replicas: 1
  ingress:
    enabled: true
    ingressClassName: nginx
    trustXForwardedFor: true
    annotations:
      nginx.ingress.kubernetes.io/backend-protocol: HTTPS
      cert-manager.io/cluster-issuer: letsencrypt-prod
```

## Key fields

| Field | Description |
|-------|-------------|
| `version` | Kanidm server image tag (`kanidm/server:{version}`) |
| `domain` | DNS name and Kanidm `domain` / WebAuthn origin |
| `certificate.issuer` | cert-manager `ClusterIssuer` name for the server TLS cert |
| `database.*` | PVC for the Kanidm database |
| `backup.*` | Online backup PVC and schedule |
| `ingress.*` | Ingress resource; defaults to `ingressClassName: nginx`; set `trustXForwardedFor` when behind a reverse proxy |
| `highAvailability` | Not yet implemented — keep `enabled: false` |

## Status

When provisioning completes, the operator sets:

```yaml
metadata:
  annotations:
    kanidm.github.io/processed: "true"
```

It also creates `admin-credentials` and `idm-admin-credentials` secrets in the Kanidm namespace.

## Example

See [`manifests/example/kanidm.yaml`](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/kanidm.yaml).
