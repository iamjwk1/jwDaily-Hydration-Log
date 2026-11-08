# jwDaily Hydration Log - changelog

## v1.1.0 (development; not yet released)
- Choose both a liquid type and volume for each new drink. Neither persists between registrations or card sessions.
- Six liquid types: water, coffee, tea, milk, soup, other.
- Click a drink row to open a Save / Delete / Cancel dialog. The edited record replaces its old values, and deletion permanently removes it from this integration's ledger.
- Manual date DD-MM-YYYY and time HH:MM or HH:MM:SS in local 24-hour format, including backdating.
- Undo last drink deletes only the just-created record by its server-generated ID.
- New compact glass layout with open rim and dashed red target line.
- Pace feature removed from card, sensors, config UI and calculation loop.
- Excel export with seven worksheets, including per-day breakdown and new liquid types. Old entries are categorized Unknown (legacy).
- No changes to the original Personal Hydration Manager.
- No public stable v1.1.0 release until integration load, migrations and runtime history/export tests are accepted on a real HA system.

## v1.0.2
- Initial stable release with persistent drink logging and Excel export.
