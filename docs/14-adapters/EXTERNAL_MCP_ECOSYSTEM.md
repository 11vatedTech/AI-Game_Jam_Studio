# External MCP Ecosystem — Integration Without Reinvention

## DCC-MCP Core

Priority integration candidate for cross-application control. Evaluate it as an independently versioned server. Its host catalog is a discovery index; experimental, discovery-only and fully actionable adapter operations must remain distinct. Record source revision, license, dependency and security posture, available tools per host, main-thread dispatch behavior, postcondition guarantees, host version matrix and local Windows smoke results.

Attach it as a separate Freebuff MCP server using its verified upstream setup instructions. Keep the studio's local MCP server separate. Do not duplicate DCC-MCP Core capability implementations until an integration gap is demonstrated.

## AI Game Dev

Treat as a product benchmark and potential specialist engine integration. Reproduce representative workflows in the same engine/version where possible. Separate local features from hosted/paid features. Record tool quality and completeness, not simply feature catalog size. Keep benchmark results versioned because the upstream product changes.

## MCP integration rules
- One MCP server owns one clear set of tools and trust boundaries.
- Namespaces must be clear and tool IDs unambiguous.
- Do not expose a dangerous tool to an agent merely because the protocol supports it.
- Capture tool schemas and revisions at install time.
- Set timeouts, cancellation and output-size limits.
- Require human approval for project mutation, arbitrary code, external network, secrets and publishing.
- After every write, query the application state and verify postconditions.
- Disable/rollback a server that fails conformance or security review without disabling unrelated capability domains.
