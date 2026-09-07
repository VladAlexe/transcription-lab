"""Find names in strings.py and design_tokens.py that nothing anywhere refers to.

A name that appears exactly once in the whole tree is its own definition and nothing else.
Run it after any change that removes a screen or a control; dead constants are the residue
of a redesign and they are what makes a file look bigger than the thing it configures.
"""
from __future__ import annotations

import pathlib
import re

SKIP = {".venv", "build", ".flet", "__pycache__"}


def blob() -> str:
    root = pathlib.Path(__file__).resolve().parent
    return "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py")
                     if not any(x in p.parts for x in SKIP))


def dead(module, text: str) -> list[str]:
    return sorted(name for name in dir(module)
                  if name.isupper() and not name.startswith("_")
                  and len(re.findall(rf"\b{name}\b", text)) == 1)


def prune(path: str, names: list[str]) -> int:
    file = pathlib.Path(path)
    kept, dropping, removed = [], False, 0
    for line in file.read_text(encoding="utf-8").splitlines(keepends=True):
        head = re.match(r"([A-Z_]+)\s*=", line)
        if head and head.group(1) in names:
            dropping = True; removed += 1
            continue
        if dropping and line[:1] in (" ", "\t"):
            continue
        dropping = False
        kept.append(line)
    file.write_text("".join(kept), encoding="utf-8")
    return removed


if __name__ == "__main__":
    import design_tokens
    import strings
    text = blob()
    for module, path in ((strings, "strings.py"), (design_tokens, "design_tokens.py")):
        names = dead(module, text)
        print(f"{path}: {len(names)} unused -> {', '.join(names) or 'none'}")
        prune(path, names)
