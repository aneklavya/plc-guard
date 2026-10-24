"""Fail if an API key could end up in git. Runs in CI and locally."""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),        # Google API key
    re.compile(r"\bAQ\.[0-9A-Za-z_-]{20,}"),      # Google auth key
    re.compile(r"sk-or-v1-[0-9a-f]{20,}"),        # OpenRouter
    re.compile(r"nvapi-[0-9A-Za-z_-]{20,}"),      # NVIDIA build.nvidia.com
    re.compile(r"sk-[A-Za-z0-9_-]{32,}"),         # OpenAI-style
]


def _committable_files() -> list[Path]:
    """Tracked files plus untracked ones that .gitignore would not stop."""
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [ROOT / f for f in out.splitlines() if (ROOT / f).is_file()]


def test_no_api_keys_in_committable_files():
    leaks = []
    for path in _committable_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pat in KEY_PATTERNS:
            if pat.search(text):
                leaks.append(f"{path.relative_to(ROOT)} matches {pat.pattern}")
    assert not leaks, "possible API key in a file git would commit:\n" + "\n".join(leaks)


def test_env_example_has_no_values():
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            assert line.rstrip().endswith("="), f".env.example must stay empty: {line[:20]}"


def test_dotenv_is_gitignored():
    res = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT)
    assert res.returncode == 0, ".env must be listed in .gitignore"
