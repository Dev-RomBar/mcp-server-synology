# Security policy

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository (Security tab, "Report a
vulnerability"). Please don't open a public issue.

## Scope

This fork's read-only changes (the `Fork:` changes listed in the README): the tool allowlist,
the API method allowlist, the removed `base_url`, and the Cloudflare Access JWT check over
HTTP. A vulnerability in code this fork doesn't change belongs upstream: report it to
[atom2ueki/mcp-server-synology](https://github.com/atom2ueki/mcp-server-synology).

## Security model

The server can never change a NAS. DSM has no read-only administrator role, so the account
it uses is usually an administrator: this fork is what keeps it read-only.

- Only the health and storage tools in `src/readonly.py` (`READ_ONLY_TOOLS`) are listed. A
  tool added upstream stays hidden until it is listed there.
- The API client only sends the DSM `(api, method)` pairs in `READ_ONLY_API_METHODS`;
  anything else is refused before any HTTP request. `tests/test_fork_readonly.py` checks
  every listed tool stays inside that list.
- Tools only reach the NAS units configured on the server (no `base_url`), so the stored
  credentials can't be sent elsewhere.
- Over HTTP, every request but `/healthz` needs a valid Cloudflare Access JWT, and the server
  refuses to start without its settings unless `ALLOW_WITHOUT_ACCESS_JWT=true`.

A change that weakens any of these is a vulnerability.

## Supported versions

Only `main`.
