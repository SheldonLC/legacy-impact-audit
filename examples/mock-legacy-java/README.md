# Mock Legacy Java Project

This tiny project is intentionally not a buildable application. It is a deterministic fixture for testing `legacy-impact-audit`.

All names are fictitious and unrelated to any real project.

## Primary Target

- Method: `recomputePlayerScore`
- Owner class: `ArcadeScoreService`
- Owner package: `com.example.sandbox.arcade`
- Definition file: `src/main/java/com/example/sandbox/arcade/ArcadeScoreService.java`

Expected behavior:

- `TournamentJob` is a real direct caller.
- `ScoreConsoleController` is a real direct caller.
- `ScoreTemplateRegistry` is a string-only false positive.
- `workflow.xml` is a config/manual-check candidate.
- `build.xml` should be excluded by the scanner.
- test files should rank lower than production callers.

## Generic Method Target

Use method `execute` with a low `--generic-limit` to verify `REFINE_REQUIRED`.
