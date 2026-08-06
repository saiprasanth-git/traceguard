# CI integration

The gate is a single command that exits non-zero on findings, so it drops into
any CI system.

```bash
traceguard check --root .
```

| Exit code | Meaning |
| --- | --- |
| `0` | Clean at the configured threshold |
| `1` | Findings - fail the job |
| `2` | Usage error |

## GitHub Actions

The workflow shipped in this repository (`.github/workflows/ci.yml`) is the
reference. The traceability portion reduces to:

```yaml
  traceability:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install traceguard

      - name: Requirements traceability gate
        run: traceguard check --root .

      - name: Generate evidence
        if: always()
        run: traceguard report --format html -o build/traceability.html

      - name: Publish the matrix to the run summary
        if: always()
        run: traceguard report --format markdown >> "$GITHUB_STEP_SUMMARY"

      - name: Retain evidence against this commit
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: traceability-evidence
          path: build/traceability.html
```

`if: always()` matters: you want the report **especially** when the gate failed,
because that is the report that shows the reviewer exactly which links are
missing. Writing the Markdown matrix into `$GITHUB_STEP_SUMMARY` puts the
findings on the run page, so a reviewer never has to download an artefact to see
what broke.

## GitLab CI

```yaml
traceability:
  image: python:3.12-slim
  script:
    - pip install traceguard
    - traceguard check --root .
    - traceguard report --format html -o build/traceability.html
  artifacts:
    when: always
    paths:
      - build/traceability.html
    expire_in: 1 year
```

## Jenkins (declarative)

```groovy
stage('Traceability') {
  steps {
    sh 'pip install traceguard'
    sh 'traceguard check --root .'
    sh 'traceguard report --format html -o build/traceability.html'
  }
  post {
    always {
      archiveArtifacts artifacts: 'build/traceability.*', fingerprint: true
    }
  }
}
```

## pre-commit

Catching a gap before it reaches CI is cheaper. Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: traceguard
        name: requirements traceability
        entry: traceguard check --root .
        language: system
        pass_filenames: false
        files: '^(requirements/|src/|include/|tests/)'
```

`pass_filenames: false` is required: the graph is only valid when evaluated over
the whole project, not over the staged subset.

## Makefile target

For projects that already drive verification from `make`, mirror the example:

```make
.PHONY: trace report
trace:
	traceguard check --root .

report:
	traceguard report --root . --format markdown -o build/traceability.md
	traceguard report --root . --format html     -o build/traceability.html
	traceguard report --root . --format json     -o build/traceability.json
```

## Consuming the JSON output

The JSON report is stable under the `traceguard/v1` schema, so dashboards can
consume it directly:

```bash
traceguard report --format json \
  | python -c 'import json,sys; d=json.load(sys.stdin); print(d["metrics"]["verification_coverage_pct"])'
```

Top-level keys:

| Key | Contents |
| --- | --- |
| `schema` | `"traceguard/v1"` |
| `metrics` | Requirement counts, implementation and verification coverage percentages, error and warning counts |
| `requirements` | One object per requirement: id, title, level, dal, derived, rationale, parents, children, source, code refs, tests |
| `findings` | One object per finding: rule, severity, message, requirement, source |

Every path is relative to the project root, so the report is reproducible across
build agents and safe to archive as certification evidence.

## Progressive adoption on an existing codebase

Turning the gate on hard against a mature repository produces hundreds of
findings and gets it switched off again. Instead:

1. Start with `--fail-on never` and publish the report. Nothing blocks; the team
   sees the real coverage number.
2. Annotate the safety-critical subsystems first. Narrow the `code` and `tests`
   globs in `traceguard.toml` to just those directories.
3. Switch that scope to `fail_on = "error"` once it is clean. The gate now
   protects what you have fixed.
4. Widen the globs one subsystem at a time, repeating steps 2 and 3.
5. Move to `fail_on = "warning"` for DAL A/B scopes once the error rules hold
   steady.

Each step is a small, reviewable pull request, and the coverage percentage in the
report gives the programme a number to track.
