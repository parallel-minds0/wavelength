# Feature preservation

Before changing wavelength behavior, read `documentation/FEATURES.md` (the
authored source is selected by `.documentation-source`) and the relevant guide
and existing regression checks. Preserve adjacent UI, shortcuts, edit/object
mode semantics, profile units, selection, undo, serialization, visibility,
ownership, import/export and worker lifecycle behavior during architectural work.

For every feature change or fix, update its stable ledger row, limitations and
verification evidence. New behavior needs a new ID. Do not delete retired IDs:
retain the row with the reason, successor and migration instructions. Incidental
removal is not authorized by a refactor; honor explicit user scope.

Run relevant behavioral tests, then `python tools/feature_inventory.py` and
`python tools/docs.py check`. The surface guard fingerprints implementation,
settings, hooks, tests, native patches and assets; it does not prove behavior.
After reviewing the delta, record it with `--update --feature WL-... --reason
"change, preservation, verification and limits"`. Never regenerate a baseline
just to hide a regression or automatically approve removed functionality.

Keep canonical Markdown, the checkout documentation mirror and the packaged
handbook synchronized. The append-only `developer/feature-changes.md` records
accepted updates. Report source, tested, installed and runtime-verified states
separately. Do not claim that the inventory alone prevents regressions.
