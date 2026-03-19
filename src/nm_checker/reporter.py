"""Rich-formatted validation report output."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text
from rich.panel import Panel

from nm_checker.validator import FileResult, Issue
from nm_checker.cross_file import CrossFileResult

console = Console(record=True)


def save_text_log(output_path: Path) -> None:
    """Write the full console output to a plain-text file."""
    text = console.export_text()
    output_path.write_text(text, encoding="utf-8")
    console.print(f"[dim]Log written to: {output_path}[/dim]")


def _severity_color(severity: str) -> str:
    return "red" if severity == "ERROR" else "yellow"


def print_file_result(result: FileResult, verbose: bool = False) -> None:
    status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
    ftype = result.file_type or "UNKNOWN"
    console.print(
        f"  {status} [{ftype}] {Path(result.path).name} "
        f"— {result.row_count} rows, "
        f"[red]{result.error_count} error(s)[/red], "
        f"[yellow]{result.warning_count} warning(s)[/yellow]"
    )
    if not result.detected:
        console.print("    [yellow]File type could not be determined from filename[/yellow]")

    if (result.issues and not result.passed) or verbose:
        for issue in result.issues[:50]:  # cap output
            color = _severity_color(issue.severity)
            loc = f"row {issue.row}" if issue.row else "file"
            col = f" {issue.col}" if issue.col else ""
            console.print(
                f"    [{color}]{issue.severity}[/{color}] "
                f"[dim]{loc}{col}:[/dim] {issue.message}"
            )
        if len(result.issues) > 50:
            console.print(f"    [dim]... and {len(result.issues) - 50} more issues[/dim]")


def print_cross_file_result(result: CrossFileResult, verbose: bool = False) -> None:
    if not result.issues:
        console.print("  [green]PASS[/green] [CROSS-FILE] No cross-file issues found")
        return

    status = "[red]FAIL[/red]" if result.error_count > 0 else "[yellow]WARN[/yellow]"
    console.print(
        f"  {status} [CROSS-FILE] "
        f"[red]{result.error_count} error(s)[/red], "
        f"[yellow]{result.warning_count} warning(s)[/yellow]"
    )
    if not result.error_count == 0 or verbose:
        for issue in result.issues[:50]:
            color = _severity_color(issue.severity)
            loc = f"row {issue.row}" if issue.row else "file"
            file_ref = f"[{issue.file}]" if issue.file != "CROSS-FILE" else ""
            console.print(
                f"    [{color}]{issue.severity}[/{color}] "
                f"[dim]{file_ref} {loc}:[/dim] {issue.message}"
            )
        if len(result.issues) > 50:
            console.print(f"    [dim]... and {len(result.issues) - 50} more issues[/dim]")


def print_summary(
    file_results: Dict[str, FileResult],
    cross_result: CrossFileResult,
) -> None:
    total_files = len(file_results)
    passed = sum(1 for r in file_results.values() if r.passed)
    total_errors = sum(r.error_count for r in file_results.values()) + cross_result.error_count
    total_warnings = sum(r.warning_count for r in file_results.values()) + cross_result.warning_count

    console.print()
    if total_errors == 0:
        console.print(Panel(
            f"[green bold]ALL CHECKS PASSED[/green bold]\n"
            f"{passed}/{total_files} files passed · "
            f"{total_warnings} warning(s)",
            title="Summary", border_style="green",
        ))
    else:
        console.print(Panel(
            f"[red bold]VALIDATION FAILED[/red bold]\n"
            f"{passed}/{total_files} files passed · "
            f"[red]{total_errors} error(s)[/red] · "
            f"[yellow]{total_warnings} warning(s)[/yellow]",
            title="Summary", border_style="red",
        ))


def write_report_csv(
    file_results: Dict[str, FileResult],
    cross_result: CrossFileResult,
    output_path: Path,
) -> None:
    """Write all issues to a CSV file for spreadsheet review."""
    import csv
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Severity", "File", "File Type", "Row", "Column", "Column Name", "Message"])
        for ftype, result in file_results.items():
            for issue in result.issues:
                writer.writerow([
                    issue.severity,
                    Path(result.path).name,
                    result.file_type or "UNKNOWN",
                    issue.row or "",
                    issue.col or "",
                    issue.col_name or "",
                    issue.message,
                ])
        for issue in cross_result.issues:
            writer.writerow([
                issue.severity,
                issue.file,
                "CROSS-FILE",
                issue.row or "",
                issue.col or "",
                issue.col_name or "",
                issue.message,
            ])
    console.print(f"\n[dim]Report written to: {output_path}[/dim]")
