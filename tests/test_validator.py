import unittest
from pathlib import Path
import tempfile
import os
import sys
from workflow_validate.validator import YAMLValidator, main, ValidationResult

class TestYAMLValidator(unittest.TestCase):
    def setUp(self):
        self.validator = YAMLValidator()

    def create_temp_yaml(self, content: str) -> Path:
        with tempfile.NamedTemporaryFile(suffix='.yml', delete=False) as tmp:
            tmp.write(content.encode('utf-8'))
            return Path(tmp.name)

    def tearDown(self):
        # Clean up any temp files if needed
        pass

    def test_valid_workflow(self):
        content = """
name: Test Workflow
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
            self.assertTrue(result['valid'])
            self.assertEqual(len(result['errors']), 0)
            self.assertEqual(len(result['warnings']), 0)
            self.assertTrue(result['structure']['has_name'])
            self.assertTrue(result['structure']['has_on'])
            self.assertTrue(result['structure']['has_jobs'])
            self.assertEqual(result['structure']['job_count'], 1)
            self.assertEqual(result['structure']['jobs'], ['build'])
            self.assertEqual(result['structure']['triggers'], ['push'])
        finally:
            os.unlink(tmp_path)

    def test_invalid_syntax(self):
        content = """
name: Test
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
            self.assertFalse(result['valid'])
            self.assertGreater(len(result['errors']), 0)
            self.assertEqual(result['errors'][0]['type'], 'YAMLSyntaxError')
        finally:
            os.unlink(tmp_path)

    def test_missing_on(self):
        content = """
name: Test
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
            self.assertEqual(result['errors'][0]['type'], 'MissingOn')
        finally:
            os.unlink(tmp_path)

    def test_invalid_permissions(self):
        content = """
name: Test
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

    def test_lint_warnings(self):
        content = """
name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest\t# Tab here (non-indent position)
    steps:
      - run: echo "hello world"  # Even quotes
      - run: "echo 'hello' with extra ' quote"  # Odd single quotes inside valid double-quoted scalar
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            self.assertTrue(result['valid'])  # Syntax passes, warnings only
            self.assertEqual(len(result['errors']), 0)
            self.assertGreater(len(result['warnings']), 0)
            warning_types = [w['type'] for w in result['warnings']]
            self.assertIn('TabWarning', warning_types)
            self.assertIn('PossibleUnclosedString', warning_types)
        finally:
            os.unlink(tmp_path)

    def test_empty_jobs_warning(self):
        content = """
name: Test
on: push
jobs:
"""
        tmp_path = self.create_temp_yaml(content)
        try:
            result = self.validator.validate_file(tmp_path)
            self.assertTrue(result['valid'])  # Empty jobs is warning, not error
            self.assertEqual(len(result['errors']), 0)
            self.assertGreater(len(result['warnings']), 0)
            self.assertEqual(result['warnings'][0]['type'], 'EmptyJobs')
        finally:
            os.unlink(tmp_path)

    def test_batch_mode_valid(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            file1 = dir_path / 'wf1.yml'
            file2 = dir_path / 'wf2.yml'
            file1.write_text("""
name: WF1
on: push
jobs:
  job1:
    runs-on: ubuntu-latest
    steps:
      - run: echo
""")
            file2.write_text("""
name: WF2
on: pull_request
jobs:
  job2:
    runs-on: ubuntu-latest
    steps:
      - run: echo
""")
            results = self.validator.validate_batch(str(dir_path))
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r['valid'] for r in results.values()))

    def test_batch_mode_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results = self.validator.validate_batch(str(Path(tmp_dir) / '*.nonexistent'))
            self.assertIn('no_files', results)
            self.assertFalse(results['no_files']['valid'])
            self.assertEqual(results['no_files']['errors'][0]['type'], 'NoFilesFound')

    def test_main_exit_codes(self):
        # Test CLI behavior indirectly via main
        with tempfile.NamedTemporaryFile(suffix='.yml') as tmp:
            tmp.write(b"""
name: Test
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo
""")
            tmp.flush()
            sys_argv = sys.argv
            sys.argv = ['prog', tmp.name]
            try:
                exit_code = main()
                self.assertEqual(exit_code, 0)
            finally:
                sys.argv = sys_argv

        # Invalid file
        sys_argv = sys.argv
        sys.argv = ['prog', 'nonexistent.yml']
        try:
            exit_code = main()
            self.assertEqual(exit_code, 1)
        finally:
            sys.argv = sys_argv

if __name__ == '__main__':
    unittest.main()
