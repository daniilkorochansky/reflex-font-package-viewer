# MX vs ATV Reflex — FPACK Editor

The editor presents the glyphs as users see them rather than exposing FPACK's
internal raster planes.

- Rider Name uses the first raster plane.
- Bike Number uses the verified large-font render relationship:
  `clamp(plane0 + 255 - plane1)`.
- Export produces the rendered grayscale character.
- Import converts the edited character back into FPACK raster data.
- NUL records are hidden.
- The original FPACK is never overwritten.


## Bike Number PNGs

Bike Number characters are exported as RGBA PNGs. The visible grayscale
appearance is stored in RGB and the character coverage is stored in alpha.
Editing the exported PNG in a graphics editor and importing it back preserves
both parts of the character.


## v11 rendering

Rider Name characters are displayed and exported as grayscale artwork with
zero-valued background pixels transparent. Bike Number characters remain
RGBA, with plane 0 providing intensity and plane 1 providing coverage.
