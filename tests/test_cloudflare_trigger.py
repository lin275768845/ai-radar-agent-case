from pathlib import Path


def test_cloudflare_worker_files_are_versioned_without_real_tokens():
    root = Path("cloudflare/ai-radar-trigger")
    index = root / "src/index.js"
    wrangler = root / "wrangler.toml"
    readme = root / "README.md"

    assert index.exists()
    assert wrangler.exists()
    assert readme.exists()

    index_text = index.read_text(encoding="utf-8")
    wrangler_text = wrangler.read_text(encoding="utf-8")
    readme_text = readme.read_text(encoding="utf-8")

    assert "async scheduled" in index_text
    assert 'url.pathname !== "/trigger"' in index_text
    assert "Authorization" in index_text
    assert "MANUAL_TRIGGER_SECRET" in index_text
    assert "GITHUB_TOKEN" in index_text
    assert 'const DEFAULT_GITHUB_REF = "main"' in index_text
    assert "single_card_v7.1" not in index_text
    assert "bocha_enabled" in index_text
    assert 'BOCHA_ENABLED = "true"' in wrangler_text
    assert 'crons = ["0 2 * * *"]' in wrangler_text
    assert "Authorization: Bearer <MANUAL_TRIGGER_SECRET>" in readme_text

    combined = f"{index_text}\n{wrangler_text}\n{readme_text}"
    assert "GITHUB_TOKEN=" not in combined
    assert "MANUAL_TRIGGER_SECRET=" not in combined
    assert "Bearer lin275768845" not in combined


def test_cloudflare_dispatch_payload_has_explicit_provider_controls():
    root = Path("cloudflare/ai-radar-trigger")
    index_text = (root / "src/index.js").read_text(encoding="utf-8")
    readme_text = (root / "README.md").read_text(encoding="utf-8")

    assert 'dry_run: "false"' in index_text
    assert 'skip_llm: "false"' in index_text
    assert 'send_bot: "true"' in index_text
    assert 'output_mode: "feishu_docx_import"' in index_text
    assert 'tavily_enabled: "false"' in index_text
    assert "const ref = env.GITHUB_REF || DEFAULT_GITHUB_REF" in index_text

    assert "function isTrueLike(value)" in index_text
    assert '["true", "1", "yes", "on"]' in index_text
    assert 'bocha_enabled: isTrueLike(env.BOCHA_ENABLED) ? "true" : "false"' in index_text

    assert "`BOCHA_ENABLED`: set to `true`" in readme_text
    assert "workflow input `bocha_enabled=true`" in readme_text
    assert "workflow input `bocha_enabled`" in readme_text
