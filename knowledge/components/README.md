# Component knowledge

Records here capture **design knowledge about parts used in reference
designs**: why a part was used, the parameters that matter for that use (with
the datasheet or reference location they came from), application conditions,
design considerations and only those alternatives that a cited source names.
They are not a parametric catalogue and do not duplicate the AIPE Transistor
Database.

## Integration with existing AIPE databases

Each record has:

```json
"external_refs": {"aipe_component_db": null, "aipe_transistor_db": null}
```

Set these to the corresponding database keys when the databases are connected.
An integration adapter should:

1. look up `part_number` and `orderable_variants` in the AIPE database;
2. fill `external_refs` with the matching key (never overwrite a non-null key
   without review);
3. keep parametric data in the database and design knowledge here; the
   retrieval API returns both ids so an agent can join them.

Power semiconductors from the references (C3M0075120K, C3M0030090K, the
Wolfspeed modules cited in PRD-09301) intentionally have no records here; they
belong to the Transistor Database.

## Datasheet status

`datasheet.url_status` is `verified-pdf` only when the URL was downloaded and
the content was a PDF (`datasheet.acquisition` holds date, size and SHA-256).
`unverified` means a manufacturer URL is recorded but could not be confirmed;
`not-located` means no official URL was found and parameters come from the
reference documents only.
