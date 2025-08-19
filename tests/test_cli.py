"""Tests for CLI functionality"""

import pytest
from click.testing import CliRunner
from scripts.cli import cli


class TestCLI:
    """Test CLI commands"""
    
    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help command"""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Browser Recording System' in result.output
    
    def test_record_help(self):
        """Test record command help"""
        result = self.runner.invoke(cli, ['record', '--help'])
        assert result.exit_code == 0
        assert '--project' in result.output
        assert '--user' in result.output
    
    def test_record_missing_project(self):
        """Test record command without project"""
        result = self.runner.invoke(cli, ['record'])
        assert result.exit_code != 0
        assert 'required' in result.output.lower()
    
    def test_menu_command(self):
        """Test menu command exists"""
        result = self.runner.invoke(cli, ['menu', '--help'])
        assert result.exit_code == 0
    
    def test_test_command(self):
        """Test test command exists"""
        result = self.runner.invoke(cli, ['test', '--help'])
        assert result.exit_code == 0