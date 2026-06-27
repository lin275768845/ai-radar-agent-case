# GitHub Sync Boundary

## GitHub-tracked

- Source code under `ai_radar_agent/`
- Tests under `tests/`
- Workflow files under `.github/`
- Configuration examples such as `.env.example`
- Documentation, README, prompts, Docker files, and project metadata

## Local-only

- Real `.env` files and any `.env.*` except `.env.example`
- Secrets, credentials, tokens, private keys, and certificates
- Local run outputs under `outputs/`
- Local virtual environments and caches such as `.venv/`, `.pytest_cache/`, `__pycache__/`, and `*.egg-info/`
- Local databases, private data, and logs

## Private storage

Use `$AI_RADAR_LOCAL_PRIVATE_DIR/` for private local files that should not live in GitHub.
