import subprocess
import sys
import tomllib
from pathlib import Path

from ai_radar_agent import __version__


def test_pyproject_version_matches_package_version():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["version"] == __version__ == "0.2.0"


def test_module_version_flag_outputs_current_version():
    result = subprocess.run(
        [sys.executable, "-m", "ai_radar_agent", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "ai-radar-agent 0.2.0"
