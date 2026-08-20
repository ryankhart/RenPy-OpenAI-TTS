# Windows GUI installer implementation plan

## T-GUI-001: Testable controller and path formatting
Traces to AC-GUI-001–005.

- Add failing tests for frozen source resolution, dry-run formatting, and controller delegation.
- Implement pure helper functions before Tk widgets.
- Add the Tkinter window using those tested helpers.

## T-GUI-002: Frozen bundle verification
Traces to AC-GUI-006–008.

- Add failing tests for runtime manifest validation and self-test reports.
- Add headless `--self-test` and `--install-test` modes.
- Add PyInstaller build script with explicit runtime data.

## T-GUI-003: Build and delivery

- Run full tests and compatibility guard.
- Build the real one-file windowed EXE.
- Execute self-test and temporary fixture install through the EXE.
- Scan package/source for secrets and inspect artifact metadata.
- Stage explicit paths, independently review the exact snapshot, commit locally, rebuild, and deliver.
