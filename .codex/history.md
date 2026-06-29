# Historial de consultes

## 2026-06-29

- Consulta: crear un repo dins `github/personal` per desenvolupar una app Python que detecti duplicats de fotos i videos a llibreries de Fotos de macOS.
- Implementat:
  - `scripts/explore_libraries.py`: inventari segur de llibreries `.photoslibrary`.
  - `scripts/find_exact_duplicates.py`: deteccio de duplicats exactes per SHA-256 i generacio de proposta revisable.
  - Proves basiques amb `unittest`.
- Decisio de seguretat: no es modifica `Photos.sqlite`, no esborra fitxers i no mou res dins del paquet `.photoslibrary`.
- Actualitzacio: afegit `scripts/find_probable_duplicates.py` per detectar fotos probablement duplicades amb dHash perceptual. La deteccio es de nomes lectura, requereix Pillow i marca tots els resultats com a revisio manual obligatoria.
- Actualitzacio: afegit output de progres al script de duplicats probables, incloent recompte inicial, percentatge de complecio, `--limit` i `--progress-every`.

