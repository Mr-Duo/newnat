#!/usr/bin/env bash
set -euo pipefail

# Install uv if it is not already available
if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Make uv available in the current shell
    export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
fi

# Verify uv installation
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv installation failed or uv is not in PATH." >&2
    exit 1
fi

echo "Using uv: $(uv --version)"

# Install the project and its dependencies
uv pip install --system -e .

echo "Project installation completed successfully."