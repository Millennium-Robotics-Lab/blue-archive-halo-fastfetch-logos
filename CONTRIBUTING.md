# Contributing

Preserve the halo’s identifying geometry. Circles stay circular. Keep detached elements, notches, and overlap gaps visible. Use bold strokes where the grid allows them.

1. Add the student’s name, slug, color, and exact reference URLs to `catalog.json`.
2. Create `logos/<slug>/design.json` with `student`, `rationale`, and `rows` fields.
3. Supply exactly 34 rows of 34 characters. Use `#` for filled pixels and `.` for empty pixels.
4. Keep the outermost row and column empty on all four sides.
5. Run `uv run scripts/build_collection.py`.
6. Compare the resulting mark against the source at large and small sizes.
7. Inspect tabs, frame overlaps, ring openings, and separate side marks individually.
8. Run `uv run scripts/build_collection.py --check --fastfetch`.

The source grid is the editable design. Update it and rebuild rather than editing generated exports individually. Use the existing `design.json` files as schema examples.

Record intentional simplifications in `rationale`. Automated checks verify export consistency and text rendering; they do not establish visual fidelity.
