# Group custom resource

Creates a Kanidm group and sets its members.

```yaml
apiVersion: kanidm.github.io/v1alpha1
kind: Group
metadata:
  name: git-users
  namespace: kanidm
spec:
  kanidmName: kanidm-instance
  name: git-users
  members:
    - marcus
```

## Fields

| Field | Description |
|-------|-------------|
| `kanidmName` | Name of the target `Kanidm` CR |
| `name` | Kanidm group name |
| `members` | List of Kanidm account names to add to the group |

Updating `spec.members` triggers a reconcile that calls `kanidm group set-members`.

## Example

See [`manifests/example/groups.yaml`](https://github.com/juniorfoo/kanidm-operator/blob/master/manifests/example/groups.yaml).
