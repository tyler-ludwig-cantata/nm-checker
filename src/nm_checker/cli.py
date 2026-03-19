"""CLI entry point for the CCBHC CSV validator."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import typer
from rich.console import Console

from nm_checker.specs import detect_file_type, ALL_SPECS
from nm_checker.validator import validate_file, FileResult
from nm_checker.cross_file import run_cross_file_checks
from nm_checker.reporter import (
    print_file_result, print_cross_file_result, print_summary, write_report_csv,
    save_text_log, console,
)

app = typer.Typer(
    name="nm-checker",
    help="CCBHC Quality Measures CSV validator for New Mexico (v1.7 data dictionary)",
    add_completion=False,
)


def _find_csv_files(paths: List[Path]) -> List[Path]:
    files = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.glob("*.csv")))
        elif p.is_file() and p.suffix.lower() == ".csv":
            files.append(p)
    return files


@app.command()
def main(
    paths: List[Path] = typer.Argument(
        ...,
        help="CSV file(s) or directory containing CSV files to validate",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Show all issues including warnings for passing files",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Write issues to a CSV report file",
    ),
    list_specs: bool = typer.Option(
        False, "--list-specs",
        help="List all expected file types and their filename patterns",
    ),
) -> None:
    if list_specs:
        console.print("\n[bold]Expected file types and filename patterns:[/bold]\n")
        for spec in ALL_SPECS:
            console.print(f"  [cyan]{spec.file_type}[/cyan]: {spec.description}")
            console.print(f"    Pattern: [dim]{spec.filename_pattern}[/dim]")
            console.print(f"    Columns: {len(spec.columns)}\n")
        return

    csv_files = _find_csv_files(paths)
    if not csv_files:
        console.print("[red]No CSV files found in the specified path(s).[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]CCBHC QM CSV Validator[/bold] — {len(csv_files)} file(s) found\n")

    # --- Per-file validation ---
    file_results: Dict[str, FileResult] = {}

    for csv_path in csv_files:
        spec = detect_file_type(csv_path.name)
        if spec is None:
            result = FileResult(
                path=str(csv_path),
                file_type=None,
                detected=False,
            )
            result.issues = []
            from nm_checker.validator import Issue
            result.issues.append(Issue(
                file=csv_path.name, row=None, col=None, col_name=None,
                message=f"Filename does not match any known CCBHC file naming pattern. "
                        f"Run with --list-specs to see expected patterns.",
                severity="WARNING",
            ))
            file_results[csv_path.name] = result
        else:
            result = validate_file(csv_path, spec)
            # Use file_type as key; if duplicate, append filename
            key = spec.file_type if spec.file_type not in file_results else csv_path.name
            file_results[key] = result

        print_file_result(result, verbose=verbose)

    # --- Cross-file validation ---
    console.print()
    console.print("[bold]Cross-file checks:[/bold]")
    cross_result = run_cross_file_checks(
        {k: v for k, v in file_results.items() if v.file_type is not None}
    )
    print_cross_file_result(cross_result, verbose=verbose)

    # --- Summary ---
    print_summary(file_results, cross_result)

    # --- Optional CSV output ---
    if output:
        write_report_csv(file_results, cross_result, output)

    # --- Always write txt log ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path.cwd() / f"validation_{timestamp}.txt"
    save_text_log(log_path)

    # Exit with error code if any errors found
    total_errors = (
        sum(r.error_count for r in file_results.values()) + cross_result.error_count
    )
    if total_errors > 0:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
