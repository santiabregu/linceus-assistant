"""Audit which top-level symbols are unused outside their own file."""
import re
import subprocess
import sys
from pathlib import Path


def audit(target_path: str):
    target = Path(target_path)
    src = target.read_text(encoding='utf-8')
    lines = src.splitlines()

    top_level = re.findall(r'^(?:def|class)\s+(\w+)', src, re.MULTILINE)
    print(f"{target}: {len(top_level)} símbolos a nivel módulo")
    print()

    target_str = str(target).replace('\\', '/')

    for n in top_level:
        if n.startswith('__'):
            continue
        pat = re.compile(rf'\b{n}\b')
        own_count = sum(1 for ln in lines if pat.search(ln))

        cmd = ['grep', '-rln', '--include=*.py', rf'\b{n}\b',
               'actions/', 'admin/', 'knowledge_base/', 'rag/', 'tests/', 'data/']
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        other = [
            l for l in r.stdout.splitlines()
            if l.replace('\\', '/') != target_str
        ]

        cmd2 = ['grep', '-rln', rf'\b{n}\b', 'domain.yml']
        r2 = subprocess.run(cmd2, capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
        yml = r2.stdout.splitlines() if r2.returncode == 0 else []

        if own_count == 1 and not other and not yml:
            mark = "*** CANDIDATO BORRAR ***"
        elif not other and not yml:
            mark = f"interno ({own_count - 1} usos)"
        else:
            mark = f"externo ({len(other) + len(yml)} archivos)"

        print(f"  {n:45s} {mark}")


if __name__ == '__main__':
    audit(sys.argv[1])
