# Zimaflow

Zimaflow turns a rough development request into a structured workflow you can
execute and review. It routes requirements, plans tasks, coordinates OpenSpec
workflows, checks implementations, preserves session continuity through
handovers, and captures reusable lessons. It supports Claude Code, Codex, and
WorkBuddy.

## Quick start

Install the CLI for the host you use before adding Zimaflow. This checkout
contains Zimaflow 1.22.3.

Claude Code:

```sh
claude plugin marketplace add zima-explorer/zima-flow
claude plugin install zimaflow@zimaflow
```

Codex:

```sh
codex plugin marketplace add zima-explorer/zima-flow
codex plugin add zimaflow@zimaflow
```

## Restricted networks

The owner/repository commands above use GitHub over HTTPS. If GitHub HTTPS
access is restricted, clone the repository over SSH and register the local
checkout from its parent directory:

```sh
git clone git@github.com:zima-explorer/zima-flow.git
claude plugin marketplace add ./zima-flow
codex plugin marketplace add ./zima-flow
```

## Verify the installation

List the installed plugin in each host:

```sh
claude plugin list
```

```sh
codex plugin list
```

For WorkBuddy, set the absolute distribution and project roots. The version
command runs from the distribution checkout. Doctor targets an initialized
Zimaflow project, which must contain at least `.zimaflow/project.yaml` and
`openspec/config.yaml`:

```sh
ZIMAFLOW_ROOT=/absolute/path/to/zima-flow
PROJECT_ROOT=/absolute/path/to/your-project

"$ZIMAFLOW_ROOT/runtime/zimaflow/bin/zimaflow" --version
"$ZIMAFLOW_ROOT/runtime/zimaflow/bin/zimaflow" doctor workbuddy \
  --project "$PROJECT_ROOT" \
  --runtime-manifest "$ZIMAFLOW_ROOT/adapters/workbuddy/runtime-manifest.yaml"
```

## WorkBuddy

WorkBuddy uses the portable runtime at `runtime/zimaflow` through the adapter
contract in `adapters/workbuddy/runtime-manifest.yaml`. The distribution provides
the runtime; doctor evaluates the initialized project selected by `--project`.
WorkBuddy does not require a marketplace entry.

## Update or remove

Update or remove the Claude Code plugin and its marketplace entry:

```sh
claude plugin update zimaflow@zimaflow
claude plugin uninstall zimaflow@zimaflow
claude plugin marketplace remove zimaflow
```

Refresh the Codex marketplace snapshot, or remove the plugin and marketplace
entry:

```sh
codex plugin marketplace upgrade zimaflow
codex plugin remove zimaflow@zimaflow
codex plugin marketplace remove zimaflow
```

## Verify the release

Verify a checkout from its repository root:

```sh
./verify-release.sh --distribution .
```

The verifier checks the version, manifest structure, artifact hashes, and any
drift in the recorded release payload.

## What is included

- Claude Code plugin: `plugins/claude`
- Codex plugin: `plugins/codex`
- WorkBuddy adapter: `adapters/workbuddy`
- Shared runtime: `runtime/zimaflow`

## Integrity and trust

`release-manifest.yaml` records the expected artifact and payload hashes. The
verifier recalculates them and reports drift when the checkout no longer matches
those recorded values.

The manifest is not signed, so this integrity check is not proof of who created
the release and does not establish cryptographic authenticity.

## License

Zimaflow is available under the MIT License. See [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES).
