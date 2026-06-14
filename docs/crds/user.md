# User custom resource

Creates or updates a person account in Kanidm.

```yaml
apiVersion: kanidm.github.io/v1alpha1
kind: User
metadata:
  name: marcus
  namespace: kanidm
spec:
  name: marcus
  displayName: Marcus
  kanidmName: kanidm-instance
  emails:
    - marcus@example.com
```

## Fields

| Field | Description |
|-------|-------------|
| `kanidmName` | Name of the target `Kanidm` CR |
| `name` | Kanidm account name (immutable after creation) |
| `displayName` | Human-readable name shown in Kanidm |
| `emails` | Email addresses attached to the account |

The operator authenticates to Kanidm as `idm_admin` using credentials from the Kanidm namespace.

## Example

See [`manifests/example/users.yaml`](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/users.yaml).
