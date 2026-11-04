# Permissions and Human Approval

## Permission model

Capabilities declare required scopes. Permissions should be granted per project, application, path, operation class, and duration where possible.

Example scopes:

- `project.read`, `project.write`, `project.delete`
- `app.inspect`, `app.modify`, `app.execute_script`, `app.install_plugin`
- `process.launch`, `process.terminate`
- `network.read`, `network.write`, `network.publish`
- `secrets.read` (exceptional, narrowly scoped)
- `artifact.export`, `release.publish`

## Approval-required actions

- Deleting or overwriting approved sources/assets.
- Installing executable plugins, custom nodes, packages, drivers or applications.
- Running arbitrary scripts/commands outside a reviewed sandbox.
- Accessing or transmitting secrets or private project content.
- Opening remote network endpoints, uploading assets, publishing builds, or posting publicly.
- Starting paid subscriptions, purchases, paid API calls or cloud workloads.
- Irreversible operations or broad batch edits to existing projects.

## Approval record

Record requested action, exact target/scope, reason, expected side effects, risks, alternatives, requester, approver, time, expiry, and resulting evidence. Approval does not make an unsafe action acceptable; technical controls remain required.

## Reversible-first principle

Prefer duplicate project/worktree, staged copy, transaction/undo group, backup, dry run and diff review before mutation. Destructive action must be narrowly targeted and recoverable where possible.
