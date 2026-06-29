# Scripts utilitzats en aquesta sessio

No s'ha utilitzat cap script auxiliar fora dels fitxers del repo.

Comandes manuals rellevants:

- `pwd`
- `rg --files -g 'AGENTS.md' -g '.codex/**'`
- `ls`
- `ls github`
- `find . -maxdepth 3 -type d -name personal`
- `git status --short`
- `mkdir -p .codex github/personal/mac-photos-duplicate-finder`
- `python3 -m unittest discover -s tests`
- `python3 -m py_compile ...`
- `chmod +x scripts/explore_libraries.py scripts/find_exact_duplicates.py`
- `find . -type d -name __pycache__ -prune -exec rm -rf {} +`
- `git init`
- `python3 -m unittest discover -s tests`
- `python3 -m py_compile ...`
- `python3 scripts/find_probable_duplicates.py --help`
- `python3 scripts/find_probable_duplicates.py --library /private/tmp/codex-empty.photoslibrary --output-dir /private/tmp/codex-probable-report --progress-every 1`
