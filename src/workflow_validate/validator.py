"""
YAML Workflow Validator - Python 3.10+ Optimized
Evolved to full syntax + schema validation with heuristic linting.
Handles 2000+ line GitHub Actions workflows with guarantees.
"""

import sys
import json
import os
from typing import TypedDict, Literal, Any, Dict
from pathlib import Path
from dataclasses import dataclass, field
import re
import glob

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError, MarkedYAMLError

# Type definitions
class ValidationError(TypedDict):
    line: int
    type: str
    message: str
    severity: Literal['ERROR', 'WARNING']

class ValidationWarning(TypedDict):
    line: int
    type: str
    message: str

class FileStats(TypedDict):
    total_lines: int
    empty_lines: int
    comment_lines: int
    code_lines: int

class WorkflowStructure(TypedDict):
    has_name: bool
    has_on: bool
    has_jobs: bool
    has_env: bool
    has_permissions: bool
    job_count: int
    jobs: list[str]
    triggers: list[str]

class ValidationResult(TypedDict):
    valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationWarning]
    stats: FileStats
    structure: WorkflowStructure

@dataclass
class YAMLValidator:
    """Evolved YAML validator: Parser-backed with heuristic linting."""

    tab_pattern: re.Pattern = field(default_factory=lambda: re.compile(r'\t'))

    def validate_file(self, file_path: Path) -> ValidationResult:
        file_path = Path(file_path)
        
        result: ValidationResult = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {
                'total_lines': 0,
                'empty_lines': 0,
                'comment_lines': 0,
                'code_lines': 0
            },
            'structure': {
                'has_name': False,
                'has_on': False,
                'has_jobs': False,
                'has_env': False,
                'has_permissions': False,
                'job_count': 0,
                'jobs': [],
                'triggers': []
            }
        }
        
        if not file_path.exists():
            result['valid'] = False
            result['errors'].append({
                'line': 0,
                'type': 'FileNotFound',
                'message': f'File not found: {file_path}',
                'severity': 'ERROR'
            })
            return result
        
        yaml = YAML(typ='safe')
        data: dict[str, Any] | None = None
        lines: list[str] = []
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
            data = yaml.load(content)
        except MarkedYAMLError as e:
            result['valid'] = False
            line = (e.problem_mark.line + 1) if e.problem_mark else 0
            result['errors'].append({
                'line': line,
                'type': 'YAMLSyntaxError',
                'message': f"{e.problem} {e.context or ''}".strip(),
                'severity': 'ERROR'
            })
            return result
        except Exception as e:
            result['valid'] = False
            result['errors'].append({
                'line': 0,
                'type': 'ReadError',
                'message': f'Error reading file: {e}',
                'severity': 'ERROR'
            })
            return result
        
        result['stats']['total_lines'] = len(lines)
        
        schema_errors = self._validate_schema(data)
        result['errors'].extend(schema_errors)
        if schema_errors:
            result['valid'] = False
        
        if isinstance(data, dict):
            struct = result['structure']
            struct['has_name'] = 'name' in data and isinstance(data['name'], str)
            struct['has_on'] = 'on' in data
            struct['has_jobs'] = 'jobs' in data
            struct['has_env'] = 'env' in data
            
            # FIX 1: Normalize 'jobs' - ruamel.yaml parses bare 'jobs:' as None
            jobs_data = data.get('jobs') or {}
            
            struct['has_permissions'] = (
                'permissions' in data or
                any(
                    isinstance(job, dict) and 'permissions' in job
                    for job in jobs_data.values()
                )
            )
            
            if 'jobs' in data:
                struct['jobs'] = sorted(jobs_data.keys())
                struct['job_count'] = len(jobs_data)
            
            triggers_set = set()
            if 'on' in data:
                on_value = data['on']
                if isinstance(on_value, str):
                    triggers_set.add(on_value)
                elif isinstance(on_value, list):
                    triggers_set.update(on_value)
                elif isinstance(on_value, dict):
                    triggers_set.update(on_value.keys())
            struct['triggers'] = sorted(triggers_set)
            
            for line_num, line in enumerate(lines, start=1):
                stripped = line.strip()
                
                # Count line types
                if not stripped:
                    result['stats']['empty_lines'] += 1
                    continue
                if stripped.startswith('#'):
                    result['stats']['comment_lines'] += 1
                    continue
                
                result['stats']['code_lines'] += 1
                
                # Phase 3: Heuristic linting - warnings only
                if '\t' in line:
                    result['warnings'].append({
                        'line': line_num,
                        'type': 'TabWarning',
                        'message': 'Tab character found - Consider using spaces for consistency'
                    })
                
                if (dq_count := stripped.count('"')) % 2 != 0 and not stripped.endswith('\\'):
                    result['warnings'].append({
                        'line': line_num,
                        'type': 'PossibleUnclosedString',
                        'message': f'Odd number of double quotes ({dq_count}) detected'
                    })
                
                if (sq_count := stripped.count("'")) % 2 != 0 and not stripped.endswith('\\'):
                    result['warnings'].append({
                        'line': line_num,
                        'type': 'PossibleUnclosedString',
                        'message': f'Odd number of single quotes ({sq_count}) detected'
                    })
            
            # Empty jobs section warning
            if result['structure']['has_jobs'] and result['structure']['job_count'] == 0:
                result['warnings'].append({
                    'line': 0,
                    'type': 'EmptyJobs',
                    'message': 'Jobs section exists but no jobs detected (heuristic)'
                })
            
            # Missing trigger warning
            if not result['structure']['has_on']:
                result['warnings'].append({
                    'line': 0,
                    'type': 'NoTrigger',
                    'message': 'No workflow trigger (on:) - workflow may not run automatically'
                })
        
        # FIX 3: Phase purity enforcement - valid is True ONLY if no errors exist
        # Warnings (Phase 3) NEVER affect validity
        result['valid'] = len(result['errors']) == 0
        
        return result

    def _validate_schema(self, data: Any) -> list[ValidationError]:
        errors = []
        
        if not isinstance(data, dict):
            errors.append({
                'line': 1,
                'type': 'InvalidRoot',
                'message': 'Workflow must be a mapping (dict)',
                'severity': 'ERROR'
            })
            return errors
        
        # Required: 'on' trigger
        if 'on' not in data:
            errors.append({
                'line': 0,
                'type': 'MissingOn',
                'message': 'Required "on" trigger missing',
                'severity': 'ERROR'
            })
        else:
            on_value = data['on']
            if not isinstance(on_value, (str, list, dict)):
                errors.append({
                    'line': 0,
                    'type': 'InvalidOn',
                    'message': '"on" must be string, list, or dict',
                    'severity': 'ERROR'
                })
        
        # Required: 'jobs' section
        if 'jobs' not in data:
            errors.append({
                'line': 0,
                'type': 'MissingJobs',
                'message': 'Required "jobs" section missing',
                'severity': 'ERROR'
            })
        else:
            jobs = data['jobs']
            if not isinstance(jobs, dict):
                errors.append({
                    'line': 0,
                    'type': 'InvalidJobs',
                    'message': '"jobs" must be a mapping of job IDs to jobs',
                    'severity': 'ERROR'
                })
            else:
                for job_id, job in jobs.items():
                    if not isinstance(job, dict):
                        errors.append({
                            'line': 0,
                            'type': 'InvalidJob',
                            'message': f'Job "{job_id}" must be a mapping',
                            'severity': 'ERROR'
                        })
                        continue
                    
                    # Job must have runs-on or uses
                    if 'runs-on' not in job and 'uses' not in job:
                        errors.append({
                            'line': 0,
                            'type': 'MissingRunsOn',
                            'message': f'Job "{job_id}" missing "runs-on" or "uses"',
                            'severity': 'ERROR'
                        })
                    
                    # Validate steps if present
                    if 'steps' in job:
                        steps = job['steps']
                        if not isinstance(steps, list):
                            errors.append({
                                'line': 0,
                                'type': 'InvalidSteps',
                                'message': f'Job "{job_id}" steps must be a list',
                                'severity': 'ERROR'
                            })
                        else:
                            for step_idx, step in enumerate(steps, start=1):
                                if not isinstance(step, dict) or ('run' not in step and 'uses' not in step):
                                    errors.append({
                                        'line': 0,
                                        'type': 'InvalidStep',
                                        'message': f'Invalid step #{step_idx} in job "{job_id}": needs "run" or "uses"',
                                        'severity': 'ERROR'
                                    })
                    
                    # Validate job-level permissions
                    if 'permissions' in job:
                        perm_errors = self._validate_permissions(job['permissions'], context=f'job "{job_id}"')
                        errors.extend(perm_errors)
                    
                    # Validate job-level strategy
                    if 'strategy' in job:
                        strat_errors = self._validate_strategy(job['strategy'], context=f'job "{job_id}"')
                        errors.extend(strat_errors)
        
        # Validate workflow-level permissions
        if 'permissions' in data:
            perm_errors = self._validate_permissions(data['permissions'], context='workflow')
            errors.extend(perm_errors)
        
        # Validate workflow-level env
        if 'env' in data and not isinstance(data['env'], dict):
            errors.append({
                'line': 0,
                'type': 'InvalidEnv',
                'message': '"env" must be a mapping',
                'severity': 'ERROR'
            })
        
        return errors

    def _validate_permissions(self, perms: Any, context: str) -> list[ValidationError]:
        errors = []
        VALID_SCOPES = {
            'actions', 'checks', 'contents', 'deployments', 'id-token', 'issues',
            'discussions', 'packages', 'pages', 'pull-requests', 'repository-projects',
            'security-events', 'statuses'
        }
        VALID_LEVELS = {'read', 'write', 'none'}
        
        if isinstance(perms, str):
            # Valid shorthand permissions
            if perms not in {'read-all', 'write-all'}:
                errors.append({
                    'line': 0,
                    'type': 'InvalidPermissions',
                    'message': f'Invalid permissions shorthand in {context}: must be "read-all" or "write-all"',
                    'severity': 'ERROR'
                })
        elif isinstance(perms, dict):
            seen_scopes = set()
            for scope, level in perms.items():
                # Check for duplicate scopes
                if scope in seen_scopes:
                    errors.append({
                        'line': 0,
                        'type': 'DuplicateScope',
                        'message': f'Duplicate scope "{scope}" in permissions for {context}',
                        'severity': 'ERROR'
                    })
                seen_scopes.add(scope)
                
                # Check for valid scope
                if scope not in VALID_SCOPES:
                    errors.append({
                        'line': 0,
                        'type': 'InvalidScope',
                        'message': f'Invalid scope "{scope}" in permissions for {context}',
                        'severity': 'ERROR'
                    })
                
                # Check for valid level
                if level not in VALID_LEVELS:
                    errors.append({
                        'line': 0,
                        'type': 'InvalidLevel',
                        'message': f'Invalid level "{level}" for scope "{scope}" in {context}: must be read/write/none',
                        'severity': 'ERROR'
                    })
        else:
            # FIX 2: Changed error type to match test expectation
            errors.append({
                'line': 0,
                'type': 'InvalidPermissionsType',
                'message': f'Permissions in {context} must be a mapping or "read-all"/"write-all"',
                'severity': 'ERROR'
            })
        
        return errors

    def _validate_strategy(self, strategy: Any, context: str) -> list[ValidationError]:
        errors = []
        
        if not isinstance(strategy, dict):
            errors.append({
                'line': 0,
                'type': 'InvalidStrategy',
                'message': f'Strategy in {context} must be a mapping',
                'severity': 'ERROR'
            })
            return errors
        
        # Validate fail-fast
        if 'fail-fast' in strategy and not isinstance(strategy['fail-fast'], bool):
            errors.append({
                'line': 0,
                'type': 'InvalidFailFast',
                'message': f'"fail-fast" in strategy for {context} must be a boolean',
                'severity': 'ERROR'
            })
        
        # Validate max-parallel
        if 'max-parallel' in strategy:
            max_par = strategy['max-parallel']
            if not isinstance(max_par, int) or max_par <= 0:
                errors.append({
                    'line': 0,
                    'type': 'InvalidMaxParallel',
                    'message': f'"max-parallel" in strategy for {context} must be a positive integer',
                    'severity': 'ERROR'
                })
        
        # Validate continue-on-error
        if 'continue-on-error' in strategy and not isinstance(strategy['continue-on-error'], bool):
            errors.append({
                'line': 0,
                'type': 'InvalidContinueOnError',
                'message': f'"continue-on-error" in strategy for {context} must be a boolean (expressions not supported by validator)',
                'severity': 'ERROR'
            })
        
        # Validate matrix
        if 'matrix' in strategy:
            matrix = strategy['matrix']
            if not isinstance(matrix, dict):
                errors.append({
                    'line': 0,
                    'type': 'InvalidMatrix',
                    'message': f'"matrix" in strategy for {context} must be a mapping',
                    'severity': 'ERROR'
                })
            else:
                for var_name, variants in matrix.items():
                    if var_name in {'include', 'exclude'}:
                        # include/exclude must be list of mappings
                        if not isinstance(variants, list) or not all(isinstance(item, dict) for item in variants):
                            errors.append({
                                'line': 0,
                                'type': 'InvalidMatrixSpecial',
                                'message': f'"{var_name}" in matrix for {context} must be a list of mappings',
                                'severity': 'ERROR'
                            })
                    else:
                        # Regular matrix vars must be list of scalars
                        if not isinstance(variants, list) or not all(isinstance(item, (str, int, bool)) for item in variants):
                            errors.append({
                                'line': 0,
                                'type': 'InvalidMatrixVariants',
                                'message': f'Variants for "{var_name}" in matrix for {context} must be a list of strings/ints/bools',
                                'severity': 'ERROR'
                            })
        
        return errors

    def validate_batch(self, pattern: str) -> Dict[str, ValidationResult]:
        """Batch validation for multiple files."""
        matches = glob.glob(pattern, recursive=True)
        paths: list[Path] = []
        for match in matches:
            p = Path(match)
            if p.is_dir():
                paths.extend(p.rglob("*.yml"))
                paths.extend(p.rglob("*.yaml"))
            else:
                paths.append(p)
        
        # Deduplicate and sort for determinism
        yaml_paths = sorted(set(p for p in paths if p.suffix in {'.yml', '.yaml'}))
        
        if not yaml_paths:
            # Return structured error for no files found
            return {
                'no_files': {
                    'valid': False,
                    'errors': [{
                        'line': 0,
                        'type': 'NoFilesFound',
                        'message': f'No YAML files matched pattern: {pattern}',
                        'severity': 'ERROR'
                    }],
                    'warnings': [],
                    'stats': {
                        'total_lines': 0,
                        'empty_lines': 0,
                        'comment_lines': 0,
                        'code_lines': 0
                    },
                    'structure': {
                        'has_name': False,
                        'has_on': False,
                        'has_jobs': False,
                        'has_env': False,
                        'has_permissions': False,
                        'job_count': 0,
                        'jobs': [],
                        'triggers': []
                    }
                }
            }
        
        batch_results: Dict[str, ValidationResult] = {}
        for file_path in yaml_paths:
            result = self.validate_file(file_path)
            batch_results[str(file_path)] = result
        
        return batch_results

    def print_report(self, result: ValidationResult, verbose: bool = True) -> None:
        CHECK = '✅'
        CROSS = '❌'
        WARNING = '⚠️'
        INFO = 'ℹ️'
        
        print("=" * 70)
        print("YAML WORKFLOW VALIDATION REPORT")
        print("=" * 70)
        print()
        
        # File statistics
        print(f"{INFO} FILE STATISTICS")
        stats = result['stats']
        print(f"  Total lines:     {stats['total_lines']:,}")
        print(f"  Code lines:      {stats['code_lines']:,}")
        print(f"  Empty lines:     {stats['empty_lines']:,}")
        print(f"  Comment lines:   {stats['comment_lines']:,}")
        print()
        
        # GitHub Actions structure
        print("🔧 GITHUB ACTIONS STRUCTURE")
        struct = result['structure']
        
        def status(condition: bool) -> str:
            return CHECK if condition else CROSS
        
        print(f"  {status(struct['has_name'])} Has 'name' field")
        print(f"  {status(struct['has_on'])} Has 'on' triggers")
        print(f"  {status(struct['has_jobs'])} Has 'jobs' section")
        print(f"  {status(struct['has_env'])} Has 'env' variables")
        print(f"  {status(struct['has_permissions'])} Has 'permissions'")
        
        if struct['triggers']:
            print(f"  → Triggers: {', '.join(struct['triggers'])}")
        
        if struct['jobs']:
            print(f"  → Jobs defined: {struct['job_count']}")
            if verbose:
                jobs_to_show = struct['jobs'][:8]
                print(f"     {', '.join(jobs_to_show)}")
                if struct['job_count'] > 8:
                    print(f"     ... and {struct['job_count'] - 8} more jobs")
        
        print()
        
        # Phase 1: Syntax validation
        print("🔍 PHASE 1: SYNTAX VALIDATION")
        syntax_errors = [e for e in result['errors'] if e['type'] == 'YAMLSyntaxError']
        if not syntax_errors:
            print(f"  {CHECK} YAML syntax is VALID")
        else:
            print(f"  {CROSS} Found {len(syntax_errors)} syntax error(s)")
            for i, error in enumerate(syntax_errors[:10], start=1):
                line_info = f"Line {error['line']}" if error['line'] > 0 else "General"
                print(f"    {i}. {line_info}: {error['type']}")
                print(f"       {error['message']}")
        
        print()
        
        # Phase 2: Schema validation
        print("🔍 PHASE 2: SCHEMA VALIDATION")
        schema_errors = [e for e in result['errors'] if e['type'] != 'YAMLSyntaxError']
        if not schema_errors:
            print(f"  {CHECK} Workflow schema is VALID")
        else:
            print(f"  {CROSS} Found {len(schema_errors)} schema error(s)")
            for i, error in enumerate(schema_errors[:10], start=1):
                line_info = f"Line {error['line']}" if error['line'] > 0 else "General"
                print(f"    {i}. {line_info}: {error['type']}")
                print(f"       {error['message']}")
        
        print()
        
        # Phase 3: Lint warnings
        if warnings := result['warnings']:
            print(f"{WARNING} PHASE 3: LINT WARNINGS ({len(warnings)} found):")
            for i, warning in enumerate(warnings[:10], start=1):
                line_info = f"Line {warning['line']}" if warning['line'] > 0 else "General"
                print(f"  {i}. {line_info}: {warning['message']}")
            if len(warnings) > 10:
                print(f"  ... and {len(warnings) - 10} more warnings")
        else:
            print(f"{CHECK} No lint warnings")
        
        print()
        print("=" * 70)
        
        # Final result
        if result['valid']:
            print(f"{CHECK} RESULT: WORKFLOW IS VALID AND READY TO USE")
        else:
            print(f"{CROSS} RESULT: PLEASE FIX ERRORS BEFORE USING")
        
        print("=" * 70)

    def print_json(self, result: Any, file_path: Path | None = None) -> None:
        """JSON output with sort_keys for determinism."""
        json_output = dict(result)  # Safe copy
        json_output["version"] = "1.0"  # Explicit version
        print(json.dumps(json_output, indent=2, sort_keys=True))
        
        # GitHub Actions annotations
        if os.getenv('GITHUB_ACTIONS') == 'true':
            if isinstance(result, dict) and 'files' in result:
                # Batch mode annotations
                for f_path, f_result in result['files'].items():
                    for error in f_result['errors']:
                        line = error['line'] if error['line'] > 0 else 1
                        kind = 'error' if error['severity'] == 'ERROR' else 'warning'
                        print(
                            f"::{kind} file={f_path},line={line}::{error['type']}: {error['message']}",
                            file=sys.stderr
                        )
                    for warning in f_result['warnings']:
                        line = warning['line'] if warning['line'] > 0 else 1
                        print(
                            f"::warning file={f_path},line={line}::{warning['type']}: {warning['message']}",
                            file=sys.stderr
                        )
            else:
                # Single file annotations
                for error in result['errors']:
                    line = error['line'] if error['line'] > 0 else 1
                    kind = 'error' if error['severity'] == 'ERROR' else 'warning'
                    print(
                        f"::{kind} file={file_path},line={line}::{error['type']}: {error['message']}",
                        file=sys.stderr
                    )
                for warning in result['warnings']:
                    line = warning['line'] if warning['line'] > 0 else 1
                    print(
                        f"::warning file={file_path},line={line}::{warning['type']}: {warning['message']}",
                        file=sys.stderr
                    )

def main() -> int:
    """CLI entry point."""
    # Python version check
    if sys.version_info < (3, 10):
        print("❌ This script requires Python 3.10 or higher")
        print(f"   Current version: {sys.version}")
        print("   Please upgrade Python to use this validator")
        return 1
    
    # Usage check
    if len(sys.argv) < 2:
        print("Usage: gh workflow-validate <file.yml | --batch <pattern>> [--verbose|-v] [--json|-j]")
        return 1
    
    arg1 = sys.argv[1]
    batch_mode = arg1 == '--batch'
    
    if batch_mode:
        if len(sys.argv) < 3:
            print("Batch mode requires a pattern: --batch <pattern>")
            return 1
        pattern = sys.argv[2]
        file_path = None
    else:
        pattern = arg1
        file_path = Path(pattern)
    
    # Parse flags
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    json_mode = '--json' in sys.argv or '-j' in sys.argv
    
    validator = YAMLValidator()
    
    if batch_mode:
        print(f"Batch validating: {pattern}")
        results = validator.validate_batch(pattern)
        
        if 'no_files' in results:
            overall_valid = False
            aggregated = {
                "files": {},
                "overall_valid": overall_valid,
                "error": results['no_files']['errors'][0]['message']
            }
        else:
            overall_valid = all(r['valid'] for r in results.values())
            aggregated = {"files": results, "overall_valid": overall_valid}
    else:
        print(f"Validating: {pattern}")
        results = validator.validate_file(Path(pattern))
        overall_valid = results['valid']
        aggregated = results
    
    print(f"Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("Processing...")
    print()
    
    # Output format
    if json_mode:
        validator.print_json(aggregated, file_path)
    else:
        if batch_mode:
            if 'no_files' in results:
                print("\n--- Error ---")
                print(results['no_files']['errors'][0]['message'])
            else:
                for f_path, f_result in sorted(results.items()):
                    print(f"\n--- {f_path} ---")
                    validator.print_report(f_result, verbose=verbose)
                print("\n--- Summary ---")
                print(f"Overall valid: {'✅' if overall_valid else '❌'} ({len(results)} files)")
        else:
            validator.print_report(results, verbose=verbose)
    
    # Exit code: 0 if valid, 1 otherwise
    return 0 if overall_valid else 1
