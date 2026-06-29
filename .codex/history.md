# Historial de consultes

## 2026-06-29

- Consulta: crear un repo dins `github/personal` per desenvolupar una app Python que detecti duplicats de fotos i videos a llibreries de Fotos de macOS.
- Implementat:
  - `scripts/explore_libraries.py`: inventari segur de llibreries `.photoslibrary`.
  - `scripts/find_exact_duplicates.py`: deteccio de duplicats exactes per SHA-256 i generacio de proposta revisable.
  - Proves basiques amb `unittest`.
- Decisio de seguretat: no es modifica `Photos.sqlite`, no esborra fitxers i no mou res dins del paquet `.photoslibrary`.

