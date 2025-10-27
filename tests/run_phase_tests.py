#!/usr/bin/env python3
"""
Test runner for all phase tests
"""

import sys
import subprocess
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_tests():
    """Run all phase tests with proper configuration"""
    
    # Set test environment
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['FLASK_SECRET_KEY'] = 'test_secret_key_for_testing_only'
    
    # Test files to run
    test_files = [
        'tests/backend/test_phase1_security.py',
        'tests/backend/test_phase2_albums.py', 
        'tests/backend/test_phase3_labeling.py',
        'tests/backend/test_integration.py'
    ]
    
    # Pytest arguments
    pytest_args = [
        'python', '-m', 'pytest',
        '-v',  # Verbose output
        '--tb=short',  # Short traceback format
        '--strict-markers',  # Strict marker handling
        '--disable-warnings',  # Disable warnings for cleaner output
        '--cov=server',  # Coverage reporting
        '--cov-report=term-missing',  # Show missing lines
        '--cov-report=html:htmlcov',  # HTML coverage report
    ]
    
    # Add test files
    pytest_args.extend(test_files)
    
    print("Running Phase Tests...")
    print("=" * 50)
    
    try:
        # Run tests
        result = subprocess.run(pytest_args, cwd=project_root, check=True)
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        return True
        
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 50)
        print(f"❌ Tests failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest: pip install pytest")
        return False

def run_specific_phase(phase):
    """Run tests for a specific phase"""
    phase_tests = {
        '1': 'tests/backend/test_phase1_security.py',
        '2': 'tests/backend/test_phase2_albums.py',
        '3': 'tests/backend/test_phase3_labeling.py',
        'integration': 'tests/backend/test_integration.py'
    }
    
    if phase not in phase_tests:
        print(f"❌ Unknown phase: {phase}")
        print(f"Available phases: {', '.join(phase_tests.keys())}")
        return False
    
    test_file = phase_tests[phase]
    pytest_args = [
        'python', '-m', 'pytest',
        '-v',
        '--tb=short',
        test_file
    ]
    
    print(f"Running Phase {phase} Tests...")
    print("=" * 50)
    
    try:
        result = subprocess.run(pytest_args, cwd=project_root, check=True)
        print(f"\n✅ Phase {phase} tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Phase {phase} tests failed with exit code {e.returncode}")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        phase = sys.argv[1]
        success = run_specific_phase(phase)
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1)