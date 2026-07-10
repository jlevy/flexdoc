# Supply-Chain Security

This repo applies a lightweight supply-chain hardening policy.
**Read this before adding or upgrading any dependency.** It exists because the
open-source registries (PyPI included) are under steady attack: malicious package
versions get published, try to exfiltrate credentials or install persistence, and are
usually yanked within minutes to days.
Waiting out that window neutralizes most of the risk at the cost of slightly staler
dependencies.

This is the project-local flag file.
The full cross-ecosystem policy lives in the
[supply-chain-hardening guidebook](https://github.com/jlevy/supply-chain-hardening).
FlexDoc and Chopdiff share this policy; coordinate cutoff changes so their common
dependencies resolve to the same vetted versions when they are developed together.

## The Rules Here

1. **14-day cool-off.** Never resolve to a package version less than 14 days old.
   In this uv project the cutoff is enforced by `exclude-newer` in `pyproject.toml`, so
   `uv lock`, `uv sync`, and `uv run` all honor it: dev and CI install the same vetted
   versions and nothing silently pulls a just-published release.
2. **Commit the lockfile; install frozen.** `uv.lock` is committed.
   CI installs with `uv sync --locked`, which fails if the lock and `pyproject.toml`
   have drifted. Never re-resolve without reviewing the lockfile diff like a code diff.
3. **Prefer wheels; review build code.** Building an sdist runs arbitrary code.
   Prefer prebuilt wheels (`uv` does by default) and treat any source build as code to
   review.
4. **Audit after changes.** Run `pip-audit` (CI runs it on every push) and address
   findings before merging.
5. **Don’t upgrade for its own sake.** The safest upgrade is the one you skip: each bump
   is fresh attack surface.
   Bump for a concrete reason: a needed feature, a fix, or a CVE.

## How the Cool-Off Is Configured

`pyproject.toml` carries the cutoff as a full RFC 3339 timestamp (uv rejects a bare date
in this field):

```toml
[tool.uv]
exclude-newer = "2026-06-26T00:00:00Z"
```

uv records this cutoff inside `uv.lock`. If the cutoff in config and lock disagree (for
example, if you set `UV_EXCLUDE_NEWER` to a different value), uv treats the lock as
stale and silently re-resolves **without** the cool-off, so keep the cutoff in
`pyproject.toml` rather than passing it only on the command line.

## Upgrading Dependencies

Bumping the cutoff date is the upgrade action.
Set it to 14 days ago and re-lock:

```shell
# Move the cool-off window forward, then re-resolve within it.
NEW_CUTOFF="$(date -u -d '14 days ago' +%Y-%m-%dT00:00:00Z)"   # GNU date (Linux)
# macOS: NEW_CUTOFF="$(date -u -v-14d +%Y-%m-%dT00:00:00Z)"
sed -i "s|^exclude-newer = .*|exclude-newer = \"$NEW_CUTOFF\"|" pyproject.toml

EMPTY_UV_CONFIG="$(mktemp -d)"
trap 'rm -rf "$EMPTY_UV_CONFIG"' EXIT
XDG_CONFIG_HOME="$EMPTY_UV_CONFIG" make upgrade
XDG_CONFIG_HOME="$EMPTY_UV_CONFIG" make lint test
```

Review the `uv.lock` diff before committing: confirm the version jumps are expected and
that no unexpected new dependency appeared.
uv merges user-level configuration into project resolution, including per-package
cutoffs. The temporary empty configuration directory prevents a developer’s unrelated
exceptions from entering the committed lockfile; verify the lockfile’s `[options]`
section contains only project-approved settings.

A per-package exception’s version does not move when only the global cutoff changes: uv
keeps the already-locked version if it still satisfies the constraints.
To pull a fixed version into the lock the first time (or after widening an exception),
force just that package with `uv lock --upgrade-package <name>`.

## Exception Process

When a version inside the 14-day window is genuinely needed, take the exception
**explicitly and on the record**. Pin it with a per-package override and document the
reason. Agents never self-approve an exception: a human signs off.

uv supports per-package cutoffs:

```toml
[tool.uv.exclude-newer-package]
some-package = "2026-05-24T00:00:00Z"
```

When the over-age package no longer needs the exception (its normal-cutoff version has
caught up), remove the override and re-lock.

### Active Exceptions

There are no active per-package cool-off exceptions.

### Audit-Gate Ignores

Distinct from the cool-off overrides above: `pip-audit --ignore-vuln <ID>` suppresses a
specific advisory at the audit gate (`.github/workflows/ci.yml`). Use it only for a
finding in a **tool dependency that flexdoc does not ship** and that has no fix
available within the cool-off window.
It does not change dependency resolution or the cool-off.

There are no active audit-gate ignores.
The 2026-06-26 cutoff resolves `pip` 26.1.2 and `msgpack` 1.2.1, and the unignored audit
passes.

## Untrusted Repositories

Treat any freshly cloned third-party repo as untrusted.
Don’t run `install` / `build` / `test` / `run` against it on a machine with credentials
until you’ve reviewed it: `build` backends, import-time code, and test files all execute
code. Prefer a container or sandbox.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
