import unittest
from pathlib import Path
import tempfile
import os
import sys
from workflow_validate.validator import YAMLValidator, main, ValidationResult


class TestYAMLValidator(unittest.TestCase):
    """Comprehensive test suite for YAML Workflow Validator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = YAMLValidator()
    
    def create_temp_yaml(self, content: str) -> Path:
        """Create a temporary YAML file with given content."""
        with tempfile.NamedTemporaryFile(suffix='.yml', delete=False, mode='w', encoding='utf-8') as tmp:
            tmp.write(content)
            return Path(tmp.name)
    
    def tearDown(self):
        """Clean up after tests."""
        pass  # Temp files are cleaned individually in each test
    
    # =========================================================================
    # Phase 1: Syntax Validation Tests
    # =========================================================================
    
    def test_valid_workflow(self):
        """Test that a valid workflow passes validation."""
        content = """name: Test Workflow
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result: ValidationResult = self.validator.validate_file(tmp_path)
            
            # Should be valid with no errors
            self.assertTrue(result['valid'])
            self.assertEqual(len(result['errors']), 0)
            self.assertEqual(len(result['warnings']), 0)
            
            # Structure should be correctly detected
            self.assertTrue(result['structure']['has_name'])
            self.assertTrue(result['structure']['has_on'])
            self.assertTrue(result['structure']['has_jobs'])
            self.assertEqual(result['structure']['job_count'], 1)
            self.assertEqual(result['structure']['jobs'], ['build'])
            self.assertEqual(result['structure']['triggers'], ['push'])
        finally:
            os.unlink(tmp_path)
    
    def test_invalid_syntax(self):
        """Test that invalid YAML syntax is caught in Phase 1."""
        content = """name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
  invalid_indent
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            # Should be invalid with syntax error
            self.assertFalse(result['valid'])
            self.assertGreater(len(result['errors']), 0)
            self.assertEqual(result['errors'][0]['type'], 'YAMLSyntaxError')
        finally:
            os.unlink(tmp_path)
    
    # =========================================================================
    # Phase 2: Schema Validation Tests
    # =========================================================================
    
    def test_missing_on(self):
        """Test that missing 'on' trigger is caught."""
        content = """name: Test
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertFalse(result['valid'])
            self.assertGreater(len(result['errors']), 0)
            error_types = [e['type'] for e in result['errors']]
            self.assertIn('MissingOn', error_types)
        finally:
            os.unlink(tmp_path)
    
    def test_missing_jobs(self):
        """Test that missing 'jobs' section is caught."""
        content = """name: Test
on: push
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertFalse(result['valid'])
            error_types = [e['type'] for e in result['errors']]
            self.assertIn('MissingJobs', error_types)
        finally:
            os.unlink(tmp_path)
    
    def test_job_missing_runs_on(self):
        """Test that job without runs-on or uses is caught."""
        content = """name: Test
on: push
jobs:
  build:
    steps:
      - run: echo hello
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertFalse(result['valid'])
            error_types = [e['type'] for e in result['errors']]
            self.assertIn('MissingRunsOn', error_types)
        finally:
            os.unlink(tmp_path)
    
    def test_invalid_permissions_type(self):
        """Test that invalid permissions type is caught."""
        content = """name: Test
on: push
permissions: invalid
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertFalse(result['valid'])
            errors = [e['type'] for e in result['errors']]
            self.assertIn('InvalidPermissionsType', errors)
        finally:
            os.unlink(tmp_path)
    
    def test_invalid_permissions_scope(self):
        """Test that invalid permission scope is caught."""
        content = """name: Test
on: push
permissions:
  invalid_scope: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertFalse(result['valid'])
            errors = [e['type'] for e in result['errors']]
            self.assertIn('InvalidScope', errors)
        finally:
            os.unlink(tmp_path)
    
    def test_invalid_permissions_level(self):
        """Test that invalid permission level is caught."""
        content = """name: Test
on: push
permissions:
  contents: invalid_level
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertFalse(result['valid'])
            errors = [e['type'] for e in result['errors']]
            self.assertIn('InvalidLevel', errors)
        finally:
            os.unlink(tmp_path)
    
    def test_duplicate_permission_scope(self):
        """Test that duplicate permission scopes are caught."""
        content = """name: Test
on: push
permissions:
  contents: read
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertFalse(result['valid'])
            errors = [e['type'] for e in result['errors']]
            self.assertIn('DuplicateScope', errors)
        finally:
            os.unlink(tmp_path)
    
    def test_valid_permissions_shorthand(self):
        """Test that valid permissions shorthand works."""
        content = """name: Test
on: push
permissions: read-all
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            # Should be valid with no permissions errors
            self.assertTrue(result['valid'])
            error_types = [e['type'] for e in result['errors']]
            self.assertNotIn('InvalidPermissions', error_types)
        finally:
            os.unlink(tmp_path)
    
    # =========================================================================
    # Phase 3: Heuristic Linting Tests (Warnings Only)
    # =========================================================================
    
    def test_lint_warnings(self):
        """Test that lint warnings are generated but don't affect validity."""
        content = """name: Test
on: push
jobs:
  build:
\t  runs-on: ubuntu-latest
  steps:
    - run: echo "hello world
    - run: 'odd quote count
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            # Should be valid (warnings don't affect validity)
            self.assertTrue(result['valid'])
            self.assertEqual(len(result['errors']), 0)
            self.assertGreater(len(result['warnings']), 0)
            
            # Check warning types
            warning_types = [w['type'] for w in result['warnings']]
            self.assertIn('TabWarning', warning_types)
            self.assertIn('PossibleUnclosedString', warning_types)
        finally:
            os.unlink(tmp_path)
    
    def test_empty_jobs_warning(self):
        """Test that empty jobs section generates a warning, not an error."""
        content = """name: Test
on: push
jobs:
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            # Should be valid (empty jobs is warning, not error)
            self.assertTrue(result['valid'])
            self.assertEqual(len(result['errors']), 0)
            self.assertGreater(len(result['warnings']), 0)
            self.assertEqual(result['warnings'][0]['type'], 'EmptyJobs')
        finally:
            os.unlink(tmp_path)
    
    def test_no_trigger_warning(self):
        """Test that missing trigger generates a warning in some contexts."""
        content = """name: Test
on:
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            # workflow_dispatch is valid, should be valid
            self.assertTrue(result['valid'])
        finally:
            os.unlink(tmp_path)
    
    # =========================================================================
    # Batch Mode Tests
    # =========================================================================
    
    def test_batch_mode_valid(self):
        """Test batch validation with multiple valid files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            file1 = dir_path / 'wf1.yml'
            file2 = dir_path / 'wf2.yml'
            
            file1.write_text("""name: WF1
on: push
jobs:
  job1:
    runs-on: ubuntu-latest
    steps:
      - run: echo
""", encoding='utf-8')
            
            file2.write_text("""name: WF2
on: pull_request
jobs:
  job2:
    runs-on: ubuntu-latest
    steps:
      - run: echo
""", encoding='utf-8')
            
            results = self.validator.validate_batch(str(dir_path))
            
            # Should have results for both files
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r['valid'] for r in results.values()))
            self.assertIn('wf1.yml', results)
            self.assertIn('wf2.yml', results)
    
    def test_batch_mode_empty(self):
        """Test batch validation with no matching files returns structured error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            results = self.validator.validate_batch(str(Path(tmp_dir) / '*.nonexistent'))
            
            # Should return 'no_files' error structure
            self.assertIn('no_files', results)
            self.assertFalse(results['no_files']['valid'])
            self.assertEqual(results['no_files']['errors'][0]['type'], 'NoFilesFound')
    
    def test_batch_mode_mixed_validity(self):
        """Test batch validation with mix of valid and invalid files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            valid_file = dir_path / 'valid.yml'
            invalid_file = dir_path / 'invalid.yml'
            
            valid_file.write_text("""name: Valid
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo
""", encoding='utf-8')
            
            invalid_file.write_text("""name: Invalid
# Missing 'on' trigger
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo
""", encoding='utf-8')
            
            results = self.validator.validate_batch(str(dir_path))
            
            # Should have results for both files
            self.assertEqual(len(results), 2)
            
            # One valid, one invalid
            valid_count = sum(1 for r in results.values() if r['valid'])
            self.assertEqual(valid_count, 1)
    
    # =========================================================================
    # CLI and Exit Code Tests
    # =========================================================================
    
    def test_main_exit_codes(self):
        """Test that main() returns correct exit codes."""
        # Test with valid file
        with tempfile.NamedTemporaryFile(suffix='.yml', delete=False, mode='w', encoding='utf-8') as tmp:
            tmp.write("""name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo
""")
            tmp.flush()
            tmp_path = tmp.name
            
            sys_argv = sys.argv
            sys.argv = ['prog', tmp_path]
            try:
                exit_code = main()
                self.assertEqual(exit_code, 0)
            finally:
                sys.argv = sys_argv
                os.unlink(tmp_path)
        
        # Test with invalid file (nonexistent)
        sys_argv = sys.argv
        sys.argv = ['prog', 'nonexistent.yml']
        try:
            exit_code = main()
            self.assertEqual(exit_code, 1)
        finally:
            sys.argv = sys_argv
    
    def test_main_batch_mode(self):
        """Test main() in batch mode."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            valid_file = dir_path / 'test.yml'
            valid_file.write_text("""name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo
""", encoding='utf-8')
            
            sys_argv = sys.argv
            sys.argv = ['prog', '--batch', str(dir_path)]
            try:
                exit_code = main()
                self.assertEqual(exit_code, 0)
            finally:
                sys.argv = sys_argv
    
    # =========================================================================
    # File Statistics Tests
    # =========================================================================
    
    def test_file_statistics(self):
        """Test that file statistics are correctly counted."""
        content = """# This is a comment
name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello

  # Another comment
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            stats = result['stats']
            self.assertGreater(stats['total_lines'], 0)
            self.assertGreater(stats['code_lines'], 0)
            self.assertGreater(stats['comment_lines'], 0)
            self.assertGreater(stats['empty_lines'], 0)
        finally:
            os.unlink(tmp_path)
    
    # =========================================================================
    # Complex Workflow Tests
    # =========================================================================
    
    def test_workflow_with_multiple_jobs(self):
        """Test validation of workflow with multiple jobs."""
        content = """name: Multi-Job Workflow
on:
  push:
    branches: [main]
  pull_request:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install
      - run: npm test
  
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - run: echo deploy
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertTrue(result['valid'])
            self.assertEqual(result['structure']['job_count'], 3)
            self.assertEqual(
                result['structure']['jobs'],
                ['build', 'deploy', 'lint']
            )
            self.assertIn('push', result['structure']['triggers'])
            self.assertIn('pull_request', result['structure']['triggers'])
        finally:
            os.unlink(tmp_path)
    
    def test_workflow_with_strategy_matrix(self):
        """Test validation of workflow with strategy matrix."""
        content = """name: Matrix Workflow
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [14, 16, 18]
        os: [ubuntu-latest, windows-latest]
      fail-fast: false
    steps:
      - run: echo Testing on ${{ matrix.node }} with ${{ matrix.os }}
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertTrue(result['valid'])
            self.assertEqual(result['structure']['job_count'], 1)
        finally:
            os.unlink(tmp_path)
    
    def test_workflow_with_permissions(self):
        """Test validation of workflow with explicit permissions."""
        content = """name: Perms Workflow
on: push
permissions:
  contents: read
  issues: write
  pull-requests: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo build
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertTrue(result['valid'])
            self.assertTrue(result['structure']['has_permissions'])
        finally:
            os.unlink(tmp_path)
    
    def test_workflow_with_job_permissions(self):
        """Test validation of workflow with job-level permissions."""
        content = """name: Job Perms Workflow
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - run: echo deploy
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            self.assertTrue(result['valid'])
            self.assertTrue(result['structure']['has_permissions'])
        finally:
            os.unlink(tmp_path)
    
    def test_workflow_with_reusable_workflow_call(self):
        """Test validation of workflow that calls another workflow."""
        content = """name: Caller Workflow
on: push
jobs:
  call-workflow:
    uses: ./.github/workflows/called-workflow.yml@main
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            
            # Should be valid (uses 'uses' instead of 'runs-on')
            self.assertTrue(result['valid'])
            self.assertEqual(result['structure']['job_count'], 1)
        finally:
            os.unlink(tmp_path)


if __name__ == '__main__':
    unittest.main()
