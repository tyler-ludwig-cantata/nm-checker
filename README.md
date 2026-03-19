# nm-checker

A CLI tool for validating CCBHC Quality Measures CSV files for New Mexico (v1.7 data dictionary).

Checks column counts, header names, required fields, format rules (dates, NPIs, codes, etc.), and cross-file consistency.

## Installation

Requires Python 3.11+. Install with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install .
```

Or with pip in a virtual environment:

```bash
pip install .
```

## Usage

```
nm-checker [OPTIONS] PATH [PATH...]
```

`PATH` can be one or more CSV files, or a directory containing CSV files.

### Options

| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Show all issues including warnings for passing files |
| `-o`, `--output FILE` | Write issues to a CSV report file |
| `--list-specs` | List all expected file types and filename patterns |

### Examples

```bash
# Validate all CSVs in a directory
nm-checker /path/to/submission/

# Validate specific files
nm-checker encounters.csv roster.csv

# Verbose output + save CSV report
nm-checker -v -o report.csv /path/to/submission/

# Show expected filename patterns
nm-checker --list-specs
```

A timestamped text log (`validation_YYYYMMDD_HHMMSS.txt`) is always written to the current directory.

Exit code is `0` if no errors, `1` if any errors are found.

## Supported File Types

| File Type | Description | Columns |
|-----------|-------------|---------|
| `I-SERV` | Initial service / crisis tracking | 7 (A–G) |
| `ALCOHOLUSE` | Alcohol use screening | 7 (A–G) |
| `ENCOUNTERS` | CCBHC encounter records | 96 (A–CR) |
| `DEPRESSION` | Depression screening | 9 (A–I) |
| `SDOH` | Social determinants of health | 9 (A–I) |
| `ROSTER` | CCBHC program roster | 69 (A–BQ) |
| `REVOCATION` | Revocation roster | 6 (A–F) |

Files are identified by filename pattern (e.g. `ccbhc_encounters_<org>_v<n>.csv`). Run `--list-specs` to see all patterns.

## Validations

**Per-file:**
- Column count and header name matching
- Required field presence
- Format checks: dates (YYYYMMDD, YYYYMMDDHHMMSS, HHMMSS), NPI (10 digits), phone, zip, SSN, ICD-10, CPT/HCPCS codes
- Controlled vocabulary: race, ethnicity, language, sex, gender identity, line of business, etc.

**Cross-file:**
- ORG ID consistency across all submitted files
- Patient MRN presence in Roster (`Local Patient Id`)
- Encounter # presence in ENCOUNTERS file (for ALCOHOLUSE, DEPRESSION, SDOH)
- Revocation client IDs present in Roster

## Development

```bash
# Install in editable mode with uv
uv pip install -e .

# Run directly
python -m nm_checker /path/to/csvs/
```
