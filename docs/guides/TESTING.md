# Testing Guide

This document describes the testing infrastructure and how to run tests for the Imagineer project.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Backend Testing](#backend-testing)
- [Frontend Testing](#frontend-testing)
- [Coverage Reports](#coverage-reports)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)

---

## Overview

Imagineer uses a comprehensive testing strategy covering both backend and frontend:

- **Backend**: pytest with pytest-cov for Python code
- **Frontend**: Vitest with React Testing Library for JavaScript/React code

### Test Structure

```
tests/
├── backend/
│   ├── conftest.py           # Pytest fixtures and configuration
│   ├── test_api.py           # API endpoint tests
│   └── test_utils.py         # Utility function tests
└── frontend/
    └── (tests colocated with components in web/src/)

web/src/
├── App.test.jsx              # Main app tests
├── components/
│   ├── GenerateForm.test.jsx
│   └── ImageGallery.test.jsx
└── test/
    └── setup.js              # Test setup and global config
```

---

## Quick Start

### Install Test Dependencies

**Backend:**
```bash
source venv/bin/activate
pip install -r requirements.txt  # Includes pytest, pytest-cov
```

**Frontend:**
```bash
cd web
npm install  # Includes vitest, @testing-library/react
```

### Run All Tests

```bash
make test
```

This runs both backend and frontend tests sequentially.

---

## Backend Testing

### Run Backend Tests

```bash
# All backend tests
make test-backend

# Or directly with pytest
source venv/bin/activate
pytest tests/backend/ -v
```

### Backend Test Categories

#### 1. API Endpoint Tests (`test_api.py`)

Tests all REST API endpoints:

- **Health Check** - `/api/health`
- **Configuration** - `/api/config` (GET/PUT)
- **Generation** - `/api/generate` (POST)
- **Jobs** - `/api/jobs` (GET)
- **Outputs** - `/api/outputs` (GET)

**Example:**
```python
def test_generate_valid_prompt(client, sample_job_data):
    """Test POST /api/generate with valid data succeeds"""
    response = client.post('/api/generate',
                          data=json.dumps(sample_job_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
```

#### 2. Utility Function Tests (`test_utils.py`)

Tests core utility functions:

- Device detection (`get_device`, `get_optimal_dtype`)
- Filename generation (`generate_filename`)
- Image operations (`save_image_with_metadata`, `preprocess_image`, `create_image_grid`)
- Prompt loading (`load_prompt_list`)

**Example:**
```python
def test_save_image_with_metadata(test_image, test_metadata, tmp_path):
    """Test saving image with metadata creates both files"""
    output_path = tmp_path / 'test_image.png'
    save_image_with_metadata(test_image, output_path, test_metadata)

    assert output_path.exists()
    metadata_path = output_path.with_suffix('.json')
    assert metadata_path.exists()
```

### Backend Test Fixtures

Pytest fixtures are defined in `tests/backend/conftest.py`:

- `app` - Flask test application
- `client` - Test client for making requests
- `temp_config` - Temporary configuration file
- `temp_output_dir` - Temporary output directory
- `sample_job_data` - Sample generation job data

---

## Frontend Testing

### Run Frontend Tests

```bash
# All frontend tests
make test-frontend

# Or directly with npm
cd web
npm test

# Watch mode (interactive)
cd web
npm test -- --watch

# UI mode (visual test runner)
cd web
npm run test:ui
```

### Frontend Test Categories

#### 1. Component Tests

**GenerateForm** (`GenerateForm.test.jsx`):
- Form rendering
- Input validation
- Submission handling
- Slider controls (steps, guidance scale)
- Seed input (random/fixed modes)

**ImageGallery** (`ImageGallery.test.jsx`):
- Image rendering
- Modal interactions
- Empty states
- Metadata display

**App** (`App.test.jsx`):
- Configuration loading
- Image list loading
- Generation workflow
- Error handling
- Loading states

#### 2. Integration Tests

Frontend tests use mocked axios to test API integration without actual backend calls:

```javascript
vi.mock('axios')

beforeEach(() => {
  axios.get.mockResolvedValue({ data: mockConfig })
})
```

---

## Coverage Reports

### Generate Coverage Reports

```bash
make test-coverage
```

This generates HTML coverage reports for both backend and frontend:

- **Backend**: `coverage/backend/index.html`
- **Frontend**: `web/coverage/index.html`

### View Coverage

```bash
# Backend coverage
open coverage/backend/index.html

# Frontend coverage
open web/coverage/index.html
```

### Coverage Goals

- **Target**: 80%+ code coverage
- **Critical paths**: 100% coverage for security-critical code (input validation, path traversal protection)

---

## Writing Tests

### Backend Test Template

```python
import pytest
from pathlib import Path

class TestMyFeature:
    """Tests for my feature"""

    def test_basic_functionality(self, client):
        """Test basic functionality"""
        response = client.get('/api/myendpoint')
        assert response.status_code == 200

    def test_error_handling(self, client):
        """Test error handling"""
        response = client.post('/api/myendpoint',
                              data=json.dumps({'invalid': 'data'}),
                              content_type='application/json')
        assert response.status_code == 400
```

### Frontend Test Template

```javascript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MyComponent from './MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText(/expected text/i)).toBeInTheDocument()
  })

  it('handles user interaction', async () => {
    const user = userEvent.setup()
    const mockCallback = vi.fn()

    render(<MyComponent onClick={mockCallback} />)

    await user.click(screen.getByRole('button'))
    expect(mockCallback).toHaveBeenCalled()
  })
})
```

### Best Practices

1. **Test names should be descriptive**
   - ✅ `test_generate_invalid_seed_returns_400`
   - ❌ `test_seed`

2. **One assertion per test (when possible)**
   - Makes failures easier to diagnose

3. **Use fixtures for setup**
   - Avoid repetitive setup code

4. **Mock external dependencies**
   - Database calls, API requests, file I/O

5. **Test edge cases**
   - Empty inputs, boundary values, error conditions

6. **Keep tests fast**
   - Use mocks instead of real resources
   - Avoid unnecessary sleeps/waits

---

## Security Testing

Critical security tests are included:

### Path Traversal Prevention

```python
def test_serve_path_traversal_blocked(client):
    """Test path traversal attempts are blocked"""
    test_paths = [
        '../../../etc/passwd',
        '..%2F..%2F..%2Fetc%2Fpasswd',
    ]
    for path in test_paths:
        response = client.get(f'/api/outputs/{path}')
        assert response.status_code in [403, 404]
```

### Input Validation

```python
def test_generate_invalid_seed(client):
    """Test POST /api/generate with invalid seed returns 400"""
    test_cases = [
        {'prompt': 'test', 'seed': -1},
        {'prompt': 'test', 'seed': 2147483648},
        {'prompt': 'test', 'seed': 'invalid'},
    ]
    for data in test_cases:
        response = client.post('/api/generate',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400
```

---

## CI/CD Integration

### GitHub Actions Workflow (Future)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest tests/backend/ --cov --cov-report=xml
      - uses: codecov/codecov-action@v3

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd web && npm install
      - run: cd web && npm test -- --coverage
```

---

## Troubleshooting

### Backend Tests

**Import errors:**
```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Fixture not found:**
- Check `conftest.py` is in the correct location
- Ensure fixture name matches

### Frontend Tests

**Module not found:**
```bash
cd web
npm install
```

**jsdom errors:**
- Ensure `vitest.config.js` has `environment: 'jsdom'`
- Check `web/src/test/setup.js` is configured

**Component not rendering:**
- Check mocks are properly configured
- Verify test setup file is loaded

---

## Running Tests in Development

### Watch Mode

```bash
# Backend (with pytest-watch)
pip install pytest-watch
cd tests/backend
ptw

# Frontend (built into Vitest)
cd web
npm test -- --watch
```

### Debug Mode

```bash
# Backend
pytest tests/backend/ -v --pdb  # Drop into debugger on failure

# Frontend
cd web
npm run test:ui  # Visual test runner with debugging
```

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Best Practices](https://testingjavascript.com/)

---

**Last Updated:** October 13, 2025
