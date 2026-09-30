"""Reject binaries, credentials and personal paths in the tracked release tree."""

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {'.py', '.md', '.json', '.txt', '.cmd', '.yml', '.yaml'}
SPECIAL = {'.gitignore', '.gitattributes'}
SKIP = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache'}


def main():
    try:
        result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True)
        names = result.stdout.decode('utf8').strip('\0').split('\0') if result.stdout else []
    except (OSError, subprocess.CalledProcessError):
        names = []
    if not names:
        names = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and not set(p.relative_to(ROOT).parts) & SKIP]
    problems = []
    for name in names:
        path = ROOT / name
        if path.is_symlink() or path.suffix.lower() not in ALLOWED and path.name not in SPECIAL:
            problems.append(f'Yayımlanmaması gereken dosya türü: {name}')
            continue
        if path.stat().st_size > 512 * 1024:
            problems.append(f'Beklenmeyen büyük dosya: {name}')
            continue
        try:
            text = path.read_text(encoding='utf8')
        except (UnicodeError, OSError):
            problems.append(f'Metin olmayan dosya: {name}')
            continue
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
            problems.append(f'Özel anahtar: {name}')
        if re.search(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})', text):
            problems.append(f'Erişim belirteci: {name}')
        if re.search(r'(?i)[A-Z]:[/\\]Users[/\\][^\s/\\]+', text):
            problems.append(f'Kişisel bilgisayar yolu: {name}')
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        return 1
    print(f'{len(names)} dosya kontrol edildi: oyun paketi, font ikilisi, anahtar veya kişisel yol bulunmadı.')
    print('Bu dar kapsamlı kontrol, paylaşım izni veya eksiksiz gizli bilgi taraması değildir.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
