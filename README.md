# Markdown Embed Code From File

A small GitHub Action that keeps fenced code blocks in Markdown synchronized with local source files.

Instead of copying configuration, scripts, YAML, or other code into documentation by hand, add an `embed-code` directive above a normal Markdown code block. The action replaces the contents of that block with the current contents of the referenced file.

The action only updates the Markdown file. Git commit and push behavior stays in your workflow, where it is explicit and easy to debug.

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

The source file remains the single source of truth.

## Usage

The embed directive must be immediately followed by a fenced Markdown code block:

````markdown
<!-- embed-code: ./path/to/source-file -->
```language
```
````

The path is resolved relative to the Markdown file containing the directive.

For example, if the Markdown file is:

```text
docs/networking/README.md
```

then:

```markdown
<!-- embed-code: ./example.yaml -->
```

references:

```text
docs/networking/example.yaml
```

You can use any Markdown fence language:

````markdown
<!-- embed-code: ./example.sh -->
```bash
```
````

````markdown
<!-- embed-code: ./example.json -->
```json
```
````

````markdown
<!-- embed-code: ./config.yaml -->
```yaml
```
````

The language identifier is preserved. Only the contents inside the fenced block are replaced.

## GitHub Action

Use the action after checking out your repository:

```yaml
- name: Checkout repository
  uses: actions/checkout@v7

- name: Synchronize embedded code
  uses: singlecheeze/markdown-embed-code@main
  with:
    markdown: Performance/IOMMU/IOMMU.md
```

The action accepts one input:

| Input | Required | Description |
| --- | --- | --- |
| `markdown` | Yes | Path to the Markdown file that contains one or more `embed-code` directives |

The action does **not** commit or push changes. This is intentional.

## Complete Workflow Example

The following workflow updates a Markdown file whenever either the Markdown file or its source file changes, then commits the generated Markdown back to the current branch.

Create:

```text
.github/workflows/embed-code.yml
```

with:

```yaml
name: Synchronize embedded code

on:
  push:
    branches:
      - "**"
    paths:
      - "Performance/IOMMU/99-enable-iommu-pass-through.yaml"
      - "Performance/IOMMU/IOMMU.md"
      - ".github/workflows/embed-code.yml"

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
        uses: singlecheeze/markdown-embed-code@main
        with:
          markdown: Performance/IOMMU/IOMMU.md

      - name: Check for generated changes
        id: changes
        shell: bash
        run: |
          if git diff --quiet -- Performance/IOMMU/IOMMU.md; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            echo "No embedded-code changes."
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"

            echo "Generated Markdown changes:"
            git diff -- Performance/IOMMU/IOMMU.md
          fi

      - name: Commit and push generated Markdown
        if: steps.changes.outputs.changed == 'true'
        shell: bash
        run: |
          git config user.name "github-actions[bot]"
          git config user.email \
            "41898282+github-actions[bot]@users.noreply.github.com"

          git add Performance/IOMMU/IOMMU.md
          git commit -m "docs: synchronize embedded code"
          git push origin "HEAD:${GITHUB_REF_NAME}"
```

### Why commit and push are outside the action

Keeping Git operations in the consuming workflow makes the behavior visible and predictable.

The action has one responsibility:

```text
source file
    |
    v
 embed.py
    |
    v
Markdown file
```

The workflow decides what to do with the result:

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

This avoids coupling Markdown generation to pull-request APIs, GitHub event payloads, repository authentication, or branch-specific push logic.

## Multiple Embedded Files

A Markdown file can contain more than one `embed-code` directive.

Example:

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

Each block is updated independently during the same action run.

## Local Testing

The action uses a dependency-free Python script, so you can test the same behavior locally:

```bash
python3 embed.py Performance/IOMMU/IOMMU.md
```

If the Markdown changes, output looks similar to:

```text
Performance/IOMMU/IOMMU.md: updated (1 embedded block(s))
```

If everything is already synchronized:

```text
Performance/IOMMU/IOMMU.md: unchanged (1 embedded block(s))
```

You can inspect the result with:

```bash
git diff -- Performance/IOMMU/IOMMU.md
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

Then the Markdown stays portable:

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

If the entire directory moves, the relative references continue to point to the files beside the Markdown document.

## Source Links

If you want readers to be able to open the original source file, use a normal relative Markdown link above the embedded block:

````markdown
[Source: `config.yaml`](./config.yaml)

<!-- embed-code: ./config.yaml -->
```yaml
```
````

Using a relative link avoids hard-coding a repository URL, branch name, or historical commit SHA.

## Error Handling

The action fails if:

- The requested Markdown file does not exist
- An `embed-code` source file does not exist
- An embed directive is not immediately followed by a fenced code block
- A fenced code block has no closing fence
- An absolute source path is used

A failed action prints the Markdown file and location associated with the invalid directive when possible.

## Branches and Pull Requests

The example workflow uses the `push` event.

For a branch in the same repository, the normal flow is:

```text
developer pushes source change
          |
          v
workflow runs on that branch
          |
          v
Markdown is synchronized
          |
          v
bot commit is pushed to that branch
          |
          v
existing pull request sees the new commit
```

This avoids detached pull-request checkout refs and makes the destination of `git push` explicit.

Repository rules, branch protection, or organization policies can still prevent GitHub Actions from pushing to a branch. Adjust the workflow to match your repository's security model.

## Requirements

The action is a composite GitHub Action and requires:

- A runner with `python3`
- `actions/checkout` before invoking the action
- `contents: write` only if the consuming workflow intends to commit and push generated changes

The embed operation itself does not require a GitHub token and does not call the GitHub API.