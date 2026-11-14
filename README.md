# newnat

**newnat** is a Python command-line tool that extracts functions from source files, applies code transformations to them, and saves the results. It parses code with [tree-sitter](https://tree-sitter.github.io/tree-sitter/) and rewrites the syntax tree instead of raw text, so the output stays syntactically valid and keeps the same behavior as the original.

**Supported languages:** Python, JavaScript, Go

## Features

- **Syntax-aware**: transformations target real language constructs through tree-sitter, not regex matches.
- **Functionality-preserving**: each transform is meant to change the form of the code, not what it does.
- **Multiple transforms**: apply one or several, either independently or chained.
- **Config-driven**: describe many runs in one YAML file, with shared defaults and per-run overrides.
- **Simple setup**: one install script, managed with [uv](https://docs.astral.sh/uv/).

## Available transforms

| Name | Description |
| ---- | ----------- |
| `block_swap` | Swaps code blocks (default transform) |
| `insert_dead_code` | Inserts dead code that never affects behavior |
| `var_renaming` | Renames variables |
| `operand_swap` | Swaps operands of operations |

## Installation

From the repository root, run:

```bash
bash install.sh
```

The script will:

1. Check whether `uv` is installed, and install it if it is missing.
2. Install `newnat` in **editable mode**, so source changes take effect without reinstalling.

Verify the install:

```bash
newnat --version
```

> If `newnat` is not found, restart your shell or make sure the directory where `uv` places its binaries is on your `PATH`.

## Usage

```bash
newnat [file] [options]
newnat -c run.yaml
```

### Quick start

Transform a single file with the default transform (`block_swap`):

```bash
newnat samples/manifest.go
```

Apply several transforms, chained one after another:

```bash
newnat samples/aggregate.js -t block_swap insert_dead_code --continuous
```

Run everything described in a config file:

```bash
newnat -c run.yaml
```

### Command-line options

| Option | Description |
| ------ | ----------- |
| `file` | Source file to parse. Optional if set in `--config`. |
| `-c`, `--config run.yaml` | YAML config file. Explicit CLI flags override its values. |
| `-t`, `--transform NAME [NAME ...]` | One or more transforms. May be repeated. Default: `block_swap`. |
| `--continuous` | Chain transforms: the output of the first is the input of the second, and so on. Without it, each transform runs separately on the original code. |
| `--diff` | Also write a unified diff between the output of each step and the original file. |
| `--include-anonymous` | Include anonymous functions and callbacks. |
| `--result-dir DIR` | Root folder for outputs. |
| `-j`, `--job-name NAME` | Job name for the output of jobs. Default: a timestamp (`YYYY-MM-DD__hh-mm-ss`). |
| `-v`, `--version` | Show the version and exit. |

### Separated vs. chained jobs

Each job reports its type when it runs:

- **separated**: every transform is applied independently to the original functions.
- **chained** (`--continuous`): transforms are applied in order, so `t2` receives the output of `t1`.

### Diff output

With `--diff`, newnat also writes a unified diff comparing the output of each step against the **original** file. In a chained job, the diff for step 2 therefore shows the combined changes of steps 1 and 2 relative to the original, not just step 2's own changes.

Example (`insert_dead_code` on a Go file):

```diff
--- a/manifest.go
+++ b/manifest.go
@@ -152,6 +152,10 @@
 				c.desc.Digest = headerDigest
 			}
 		}
+		for _i_8 := 0; _i_8 < 0; _i_8++ {
+			return fromOrig(c, mc.orig)
+		}
+		
 		c.setRateLimit(mc.header)
 	}
 	if mc.orig != nil {
```

The inserted loop never executes (`_i_8 < 0` is false from the start), so behavior is unchanged.

## Configuration (`run.yaml`)

Top-level keys act as defaults for every run. Each entry under `runs` can override them.

```yaml
# Top-level keys act as defaults for every run
# current transforms: block_swap, insert_dead_code, var_renaming, operand_swap, for_while_swap
transform: [block_swap, insert_dead_code]
continuous: true
diff: true

runs:
  - file: samples/manifest.go
  - file: [samples/_readers.py, samples/aggregate.js]   # a list of files is fine too
    transform: insert_dead_code
    continuous: false
```

In this example:

- The first run applies `block_swap` then `insert_dead_code` to `samples/manifest.go`, chained, using the top-level defaults.
- The second run applies only `insert_dead_code` to both `samples/_readers.py` and `samples/aggregate.js`, with `continuous` turned off.

Config keys mirror the CLI options: `file`, `transform`, `continuous`, `diff`, `include_anonymous`, `result_dir`, `job_name`.

> Precedence: CLI flags override the config file, and per-run values override the top-level defaults.

## Examples

The [`example/`](example/) folder contains a ready-to-run setup:

```
example/
├── run.yaml   # sample configuration
└── run.sh     # sample launcher
```

`run.sh`:

```bash
#!/bin/bash

newnat -c run.yaml
```

Run it:

```bash
cd example
bash run.sh
```

## How it works

1. **Parse**: the source file is parsed by tree-sitter into a syntax tree.
2. **Extract**: functions are located in the tree (anonymous ones too, with `--include-anonymous`).
3. **Transform**: the selected transforms rewrite the matching nodes, separately or chained.
4. **Save**: results are written under the result directory, grouped by job name.

## Development

`newnat` is installed in editable mode by `install.sh`, so you can edit the code and re-run immediately.

```bash
uv sync
uv run newnat -c example/run.yaml
```

