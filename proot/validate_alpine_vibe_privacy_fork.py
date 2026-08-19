from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("/home/ubuntu/goar-xyz/proot/alpine-vibe-mistral")
PACKAGE = ROOT / "vibe"

errors: list[str] = []
for source in sorted(PACKAGE.rglob("*.py")):
    try:
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
    except SyntaxError as exc:
        errors.append(f"syntax: {source.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")

pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
for dependency in ("sentry-sdk", "sounddevice", "opentelemetry-"):
    if dependency in pyproject:
        errors.append(f"dependency remains: {dependency}")

for forbidden_dir in (
    PACKAGE / "cli" / "audio_player",
    PACKAGE / "cli" / "audio_recorder",
    PACKAGE / "cli" / "transcribe",
):
    if forbidden_dir.exists():
        errors.append(f"removed audio directory remains: {forbidden_dir.relative_to(ROOT)}")

update_files = [
    item.relative_to(PACKAGE / "cli" / "update_notifier").as_posix()
    for item in (PACKAGE / "cli" / "update_notifier").rglob("*")
    if item.is_file()
]
if update_files != ["__init__.py"]:
    errors.append(f"unexpected update-notifier files: {update_files}")

for source in sorted(PACKAGE.rglob("*.py")):
    text = source.read_text(encoding="utf-8")
    for match in re.finditer(
        r"^\s*(?:from|import)\s+(?:sentry_sdk|sounddevice|opentelemetry)(?:[.\s]|$)",
        text,
        re.MULTILINE,
    ):
        errors.append(
            f"forbidden dependency import: {source.relative_to(ROOT)}:{text[:match.start()].count(chr(10)) + 1}"
        )

if errors:
    raise SystemExit("\n".join(errors))

print(f"privacy-fork static validation passed: {len(list(PACKAGE.rglob('*.py')))} Python files")
