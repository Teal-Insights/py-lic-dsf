# Remodeled Input 4 / Input 5 bindings

Prototype of the reshape-to-keys pass: instrument, holder, and vintage
dimensions move from `series_context` / series id into `key:` via
`value_map` (and `row_label` for issuance year).

Original extraction-pipeline shards under `bindings/*.yaml` are not in git
(they are local copies). These files are generated from them.

| Sheet | Original series | Remodeled | Headline |
|---|---:|---:|---|
| Input 4 | 211 | **26** | grace / interest / maturity / disbursements keyed by `INSTRUMENT` |
| Input 5 | 1125 | **116** | vintage cube **871 → 3** (`stock` / `principal` / `interest`) keyed by `INSTRUMENT`, `HOLDER`, `ISSUANCE_YEAR`, `TIME_PERIOD` |

See `input4-audit.md` and `input5-audit.md` for cell coverage (no original cell dropped; bounding boxes add blanks, especially Input 5 vintage triangles).

Regenerate:

```bash
python bindings/remodeled/remodel_input4.py
python bindings/remodeled/_remodel_input5.py
```
