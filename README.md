# Markdown Embed Code From File

A lightweight GitHub Action that recursively keeps fenced code blocks in Markdown synchronized with local source files.

Add an `embed-code` directive above a normal Markdown code block. The action walks the checked-out repository, finds Markdown files containing embed directives, and replaces each managed code block with the current contents of the referenced source file.

The source file remains the single source of truth.

## Features

- Recursively scans the repository for `.md` and `.markdown` files.
- Processes every valid `<!-- embed-code: ... -->` directive it finds.
- Resolves source paths relative to the Markdown file containing the directive.
- Preserves the Markdown code-fence language.
- Ignores example directives shown inside fenced code blocks.
- Validates all embeds before writing changes.
- Prevents source paths from escaping the repository.
- Uses only the Python standard library.
- Requires no Docker image or third-party Python packages.
- Leaves Git commit and push behavior to the consuming workflow.
- Exposes outputs that indicate whether files changed and how many embeds were processed.

## Example

Given this repository layout:

```text
Performance/
└── IOMMU/
    ├── IOMMU.md
    └── 99-enable-iommu-pass-through.yaml
```

Add this to `Performance/IOMMU/IOMMU.md`:

````markdown
[Source: `99-enable-iommu-pass-through.yaml`](./99-enable-iommu-pass-through.yaml)

<!-- embed-code: ./99-enable-iommu-pass-through.yaml -->
```yaml
```
````

When the action runs, the code block is synchronized with the source file:

````markdown
[Source: `99-enable-iommu-pass-through.yaml`](./99-enable-iommu-pass-through.yaml)

<!-- embed-code: ./99-enable-iommu-pass-through.yaml -->
```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: master
  name: 99-enable-iommu-pass-through
spec:
  kernelArguments:
    - "iommu=pt"
```
````

## Embed Syntax

The directive must be immediately followed by a fenced Markdown code block:

````markdown
<!-- embed-code: ./path/to/source-file -->
```language
```
````

The source path is relative to the Markdown file containing the directive.

For example:

```text
docs/
└── networking/
    ├── README.md
    └── example.yaml
```

Inside `docs/networking/README.md`:

````markdown
<!-- embed-code: ./example.yaml -->
```yaml
```
````

The action reads `docs/networking/example.yaml`.

You can use any normal Markdown fence language, for example:

````markdown
<!-- embed-code: ./example.sh -->
```bash
```

<!-- embed-code: ./example.json -->
```json
```

<!-- embed-code: ./config.yaml -->
```yaml
```
````

Only the content inside each managed code block is replaced. The directive, opening fence, language identifier, closing fence, and surrounding Markdown remain intact.

## Repository-Wide Scanning

The action does not require a path to a specific Markdown file.

A single invocation scans the entire checked-out repository:

```yaml
- name: Synchronize embedded code
  id: embed
  uses: singlecheeze/markdown-embed-code@main
```

The action recursively examines `.md` and `.markdown` files under `$GITHUB_WORKSPACE`.

For example:

```text
.
├── README.md
├── docs/
│   ├── README.md
│   └── networking/
│       └── NETWORKING.md
├── Performance/
│   ├── IOMMU/
│   │   └── IOMMU.md
│   └── Storage/
│       └── README.md
└── examples/
    └── example.markdown
```

All of those Markdown files are eligible for processing during the same run. Files without an `embed-code` directive are left unchanged. The `.git` directory is skipped.

## GitHub Action Usage

Use the action after checking out the repository:

```yaml
- name: Checkout repository
  uses: actions/checkout@v7

- name: Synchronize embedded code
  id: embed
  uses: singlecheeze/markdown-embed-code@main
```

There are no required inputs.

The action updates files in the checked-out workspace but does **not** commit or push them.

## Outputs

The action exposes the following outputs:

| Output | Description |
| --- | --- |
| `changed` | `true` if one or more Markdown files were changed |
| `scanned_files` | Number of Markdown files scanned |
| `files_with_embeds` | Number of Markdown files containing valid embed directives |
| `files_changed` | Number of Markdown files that were modified |
| `embedded_blocks` | Total number of embedded code blocks processed |

Example:

```yaml
- name: Synchronize embedded code
  id: embed
  uses: singlecheeze/markdown-embed-code@main

- name: Show summary
  run: |
    echo "Changed: ${{ steps.embed.outputs.changed }}"
    echo "Markdown files scanned: ${{ steps.embed.outputs.scanned_files }}"
    echo "Files with embeds: ${{ steps.embed.outputs.files_with_embeds }}"
    echo "Files changed: ${{ steps.embed.outputs.files_changed }}"
    echo "Embedded blocks: ${{ steps.embed.outputs.embedded_blocks }}"
```

## Complete Workflow Example

Create `.github/workflows/embed-code.yml`:

```yaml
name: Synchronize embedded code

on:
  push:
    branches:
      - "**"

  workflow_dispatch:

permissions:
  contents: write

jobs:
  embed-code:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout current branch
        uses: actions/checkout@v7

      - name: Synchronize embedded code
        id: embed
        uses: singlecheeze/markdown-embed-code@main

      - name: Show generated changes
        if: steps.embed.outputs.changed == 'true'
        shell: bash
        run: |
          echo "Markdown files changed: ${{ steps.embed.outputs.files_changed }}"
          echo "Embedded blocks processed: ${{ steps.embed.outputs.embedded_blocks }}"
          git status --short
          git diff

      - name: Commit and push generated Markdown
        if: steps.embed.outputs.changed == 'true'
        shell: bash
        run: |
          git config user.name "github-actions[bot]"
          git config user.email \
            "41898282+github-actions[bot]@users.noreply.github.com"

          git add -A
          git commit -m "docs: synchronize embedded code"
          git push origin "HEAD:${GITHUB_REF_NAME}"
```

### Why the workflow runs on every push

Because an embedded source can be any local file type, maintaining a `paths:` filter for every possible source would make the workflow fragile. Running the scanner on each push keeps the workflow generic. Markdown files without embed directives are only scanned and are not modified.

## Why Commit and Push Are Outside the Action

The action has one responsibility:

```text
source files
     |
     v
  embed.py
     |
     v
Markdown files
```

The consuming workflow decides what happens next:

```text
Markdown changed?
       |
     +---+
     |   |
    no  yes
     |   |
   exit  commit
          |
          v
        push
```

Keeping Git operations outside the action makes authentication, branch behavior, commit messages, and repository policy explicit in the consuming workflow.

## Multiple Embedded Files

A single Markdown document can contain multiple embedded files:

````markdown
## MachineConfig

<!-- embed-code: ./machineconfig.yaml -->
```yaml
```

## Validation Script

<!-- embed-code: ./validate.sh -->
```bash
```

## Example Output

<!-- embed-code: ./example.json -->
```json
```
````

The action can also process embeds spread across many Markdown files throughout the repository in the same run.

## Source Links

If you want readers to open the original source file, use a normal relative Markdown link above the embedded block:

````markdown
[Source: `config.yaml`](./config.yaml)

<!-- embed-code: ./config.yaml -->
```yaml
```
````

Relative links avoid hard-coding repository names, branch names, GitHub URLs, or historical commit SHAs.

## Directives Inside Documentation Examples

The scanner understands fenced Markdown blocks.

An `embed-code` directive shown inside a fenced example is treated as documentation rather than as a real embed request. This means a README can safely demonstrate the action syntax without the scanner trying to process those examples.

## Repository Boundary Protection

Embed paths must remain inside the checked-out repository.

Valid:

```markdown
<!-- embed-code: ./config.yaml -->
```

Also valid when the resolved file remains inside the repository:

```markdown
<!-- embed-code: ../shared/example.yaml -->
```

Invalid:

```markdown
<!-- embed-code: ../../../../etc/passwd -->
```

Absolute paths are also rejected.

## Validation and Atomic Updates

The action validates all discovered embed directives before writing any files.

If one directive is invalid, the action fails and does not partially update other Markdown files.

Validation failures include:

- a referenced source file does not exist;
- a directive is not immediately followed by a fenced code block;
- a code block has no closing fence;
- an absolute source path is used; or
- a source path resolves outside the repository.

## Local Testing

The action uses a dependency-free Python script.

Run it locally with a target repository path:

```bash
python3 embed.py /path/to/repository
```

To test against the current directory:

```bash
python3 embed.py .
```

A run that changes files produces output similar to:

```text
updated: Performance/IOMMU/IOMMU.md (1 embedded block(s))
updated: Storage/NVMe/README.md (3 embedded block(s))

Markdown embed summary
  Markdown files scanned: 47
  Files with embeds:      8
  Embedded blocks:        19
  Files changed:          2
```

If everything is already synchronized:

```text
Markdown embed summary
  Markdown files scanned: 47
  Files with embeds:      8
  Embedded blocks:        19
  Files changed:          0
```

Inspect generated changes with:

```bash
git status --short
git diff
```

## Recommended Repository Pattern

Keep source files and the documentation that references them close together when practical:

```text
docs/
└── example/
    ├── README.md
    ├── config.yaml
    ├── install.sh
    └── example.json
```

Then your documentation remains portable:

````markdown
<!-- embed-code: ./config.yaml -->
```yaml
```

<!-- embed-code: ./install.sh -->
```bash
```

<!-- embed-code: ./example.json -->
```json
```
````

If the entire directory moves, the relative source references continue to work.

## Branches and Pull Requests

The recommended workflow uses the `push` event.

For a branch in the same repository:

```text
developer pushes source change
          |
          v
workflow runs on that branch
          |
          v
repository-wide embed scan
          |
          v
Markdown synchronized
          |
          v
bot commit pushed to branch
          |
          v
existing pull request sees new commit
```

This avoids detached pull-request checkout refs and makes the push destination explicit.

Repository rules, protected branches, organization policies, or workflow permissions can still prevent GitHub Actions from pushing. Adjust the workflow to match your repository's security model.

## Migration From the Original Action

Earlier versions required a specific Markdown file and encoded the source path into the code-fence language:

````markdown
```yaml:Performance/IOMMU/99-enable-iommu-pass-through.yaml
```
````

The current version separates the source path from the Markdown language:

````markdown
<!-- embed-code: ./99-enable-iommu-pass-through.yaml -->
```yaml
```
````

Earlier workflows also invoked the action like this:

```yaml
- uses: singlecheeze/markdown-embed-code@main
  with:
    markdown: Performance/IOMMU/IOMMU.md
    token: ${{ secrets.GITHUB_TOKEN }}
    message: Synchronizing Readme
    silent: false
```

The current action needs only:

```yaml
- name: Synchronize embedded code
  id: embed
  uses: singlecheeze/markdown-embed-code@main
```

Git commit and push behavior now belongs in the workflow rather than inside the action.

## Simplified Architecture

The current implementation intentionally removes the dependencies and infrastructure required by the original version.

It does not require:

- Docker;
- PyGithub;
- Pydantic;
- Marko;
- cryptography;
- PyNaCl;
- cffi;
- GitHub API authentication;
- pull-request event parsing; or
- built-in Git commit/push logic.

The action is a composite action that executes:

```bash
python3 "$GITHUB_ACTION_PATH/embed.py" "$GITHUB_WORKSPACE"
```

The embed operation itself does not require a GitHub token.

## Version Pinning

Examples in this README use:

```yaml
uses: singlecheeze/markdown-embed-code@main
```

while developing the action.

For long-term use, create a release tag and pin consuming repositories to that version:

```yaml
uses: singlecheeze/markdown-embed-code@v2
```

This prevents later changes to `main` from unexpectedly changing existing workflows.

## Requirements

The action requires:

- a GitHub Actions runner with `python3`; and
- `actions/checkout` before invoking the action.

If the workflow will commit generated files, it also needs:

```yaml
permissions:
  contents: write
```

The embed operation itself requires no GitHub token and makes no GitHub API calls.

## Action Repository Layout

The simplified action can be kept very small:

```text
markdown-embed-code/
├── action.yaml
├── embed.py
├── README.md
└── LICENSE
```

No runtime dependency files or Docker image are required.

## License

See [LICENSE](./LICENSE).
