# Template and Script Contract

## Template Variables

- `{{PROJECT_NAME}}`: basename of the resolved project root.
- `{{PROJECT_ROOT}}`: resolved absolute project root path.

Render templates with Python string replacement. Do not use `sed` for path-bearing values.

## Managed Marker

Generated scripts managed by this skill must include:

```text
initiate_new_project managed
```

Only scripts with this marker may be run automatically on later invocations.

Generated `docs/generated/project-directory.md` files managed by this skill must include:

```text
initiate_new_project managed: project-directory
```

Only directory index files with this marker may be overwritten by the managed update script. If an existing index file lacks the marker, preserve it and report manual action.

## Reports

Initialization output must always use these section labels:

- `Created:`
- `Skipped existing:`
- `Generated:`
- `Manual action required:`

Validation output must use:

- `OK`
- `Missing:`
- `Invalid:`
- `Not executable:`
- `Runtime error:`
