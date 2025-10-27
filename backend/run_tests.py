#!/usr/bin/env python
"""
Test Runner for DTaaS
Comprehensive test execution with reporting
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print results"""
    print(f"\n{'='*60}")
    print(f" {description}")
    print('='*60)
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=False)
        print(f"✓ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} - FAILED")
        return False


def run_all_tests():
    """Run all tests with coverage"""
    print("\n" + "="*60)
    print(" RUNNING FULL TEST SUITE")
    print("="*60)
    
    success = run_command(
        "pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing --cov-report=xml",
        "All Tests with Coverage"
    )
    
    if success:
        print("\n" + "="*60)
        print(" TEST SUMMARY")
        print("="*60)
        print("✓ All tests passed!")
        print("\nCoverage report generated:")
        print("  - HTML: htmlcov/index.html")
        print("  - XML: coverage.xml")
        print("\nOpen coverage report:")
        print("  python -m webbrowser htmlcov/index.html")
    
    return success


def run_unit_tests():
    """Run only unit tests"""
    return run_command(
        "pytest tests/ -v -m unit",
        "Unit Tests"
    )


def run_integration_tests():
    """Run only integration tests"""
    return run_command(
        "pytest tests/ -v -m integration",
        "Integration Tests"
    )


def run_specific_test(test_file):
    """Run a specific test file"""
    return run_command(
        f"pytest {test_file} -v",
        f"Test File: {test_file}"
    )


def run_with_parallel():
    """Run tests in parallel"""
    return run_command(
        "pytest tests/ -v -n auto",
        "Parallel Test Execution"
    )


def run_code_quality_checks():
    """Run code quality checks"""
    print("\n" + "="*60)
    print(" CODE QUALITY CHECKS")
    print("="*60)
    
    checks = [
        ("black --check backend/", "Black (Code Formatting)"),
        ("isort --check-only backend/", "isort (Import Sorting)"),
        ("flake8 backend/", "Flake8 (Linting)"),
        ("mypy backend/ --ignore-missing-imports", "MyPy (Type Checking)"),
        ("bandit -r backend/ -ll", "Bandit (Security Check)")
    ]
    
    results = []
    for cmd, desc in checks:
        results.append(run_command(cmd, desc))
    
    return all(results)


def main():
    parser = argparse.ArgumentParser(
        description="DTaaS Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Run unit tests only
  python run_tests.py --integration      # Run integration tests
  python run_tests.py --parallel         # Run tests in parallel
  python run_tests.py --quality          # Run code quality checks
  python run_tests.py --file tests/test_models.py  # Run specific file
        """
    )
    
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--quality', action='store_true', help='Run code quality checks')
    parser.add_argument('--file', type=str, help='Run specific test file')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    
    args = parser.parse_args()
    
    # Change to backend directory
    backend_path = Path(__file__).parent
    import os
    os.chdir(backend_path)
    
    success = True
    
    if args.unit:
        success = run_unit_tests()
    elif args.integration:
        success = run_integration_tests()
    elif args.parallel:
        success = run_with_parallel()
    elif args.quality:
        success = run_code_quality_checks()
    elif args.file:
        success = run_specific_test(args.file)
    else:
        # Run all tests by default
        success = run_all_tests()
        
        if args.quality:
            quality_success = run_code_quality_checks()
            success = success and quality_success
    
    if success:
        print("\n" + "="*60)
        print(" ✓ ALL CHECKS PASSED!")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print(" ✗ SOME CHECKS FAILED")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()

