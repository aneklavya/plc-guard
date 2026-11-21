"""Compile Structured Text with MatIEC (iec2c), OpenPLC's ST-to-C compiler.

Used to check that dataset programs and LLM repairs are valid IEC 61131-3.
iec2c is found, in order, through:
  1. $PLCGUARD_IEC2C: a command prefix, e.g. "iec2c -I /opt/matiec/lib";
  2. `iec2c` on PATH (Linux, CI);
  3. WSL on Windows, with MatIEC built in /opt/matiec (see docs/10-stage3-repair.md);
  4. the `plcguard-matiec` Docker image (tools/matiec/Dockerfile).
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass
class CompileResult:
    ok: bool
    errors: list[str]

    def summary(self, limit: int = 5) -> str:
        return "compiles" if self.ok else "; ".join(self.errors[:limit])


class CompilerUnavailable(RuntimeError):
    pass


def _wsl_path(path: Path) -> str:
    drive, rest = path.drive.rstrip(":").lower(), path.as_posix()[2:]
    return f"/mnt/{drive}{rest}"


@lru_cache(maxsize=1)
def _backend() -> tuple[str, list[str]]:
    if os.environ.get("PLCGUARD_IEC2C"):
        return "native", shlex.split(os.environ["PLCGUARD_IEC2C"])
    if shutil.which("iec2c"):
        lib = os.environ.get("MATIEC_LIB", "/opt/matiec/lib")
        return "native", ["iec2c", "-I", lib]
    if os.name == "nt" and shutil.which("wsl"):
        probe = subprocess.run(["wsl", "-u", "root", "--", "test", "-x", "/opt/matiec/iec2c"],
                               capture_output=True, timeout=60)
        if probe.returncode == 0:
            return "wsl", ["wsl", "-u", "root", "--", "/opt/matiec/iec2c",
                           "-I", "/opt/matiec/lib"]
    if shutil.which("docker"):
        probe = subprocess.run(["docker", "image", "inspect", "plcguard-matiec"],
                               capture_output=True, timeout=60)
        if probe.returncode == 0:
            return "docker", ["docker", "run", "--rm"]
    raise CompilerUnavailable("MatIEC (iec2c) not found; see docs/10-stage3-repair.md")


def available() -> bool:
    try:
        _backend()
        return True
    except (CompilerUnavailable, OSError, subprocess.SubprocessError):
        return False


def compile_st(source: str, timeout: float = 60) -> CompileResult:
    """Compile one program. Raises CompilerUnavailable if there is no iec2c."""
    kind, cmd = _backend()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp).resolve()
        (tmp_path / "out").mkdir()
        (tmp_path / "prog.st").write_text(source, encoding="utf-8", newline="\n")
        if kind == "native":
            args = [*cmd, "-T", str(tmp_path / "out"), str(tmp_path / "prog.st")]
        elif kind == "wsl":
            base = _wsl_path(tmp_path)
            args = [*cmd, "-T", f"{base}/out", f"{base}/prog.st"]
        else:
            args = [*cmd, "-v", f"{tmp_path}:/src", "plcguard-matiec", "prog.st"]
        env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    text = proc.stdout + proc.stderr
    errors = [re.sub(r"^.*?prog\.st:", "line ", ln).strip()
              for ln in text.splitlines() if "error" in ln.lower() and "Bailing" not in ln]
    return CompileResult(proc.returncode == 0, errors if proc.returncode else [])
