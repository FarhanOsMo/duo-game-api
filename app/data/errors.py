"""Error type shared by the loader, the validator and scripts/validate_data.py."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DataIssue:
    file: str
    entry_id: str
    message: str

    def __str__(self) -> str:
        return f"data/{self.file} [{self.entry_id}]: {self.message}"


class DataValidationError(Exception):
    """Raised at startup when data/ is unusable. Lists every issue found, not just the first,
    so one CI run tells a designer everything to fix in their export."""

    def __init__(self, issues: list[DataIssue]) -> None:
        self.issues = issues
        lines = "\n".join(f"  - {issue}" for issue in issues)
        super().__init__(f"{len(issues)} data validation issue(s):\n{lines}")
