# Test Suite Documentation

This directory contains comprehensive tests for all phases of the Imagineer project.

## Test Structure

```
tests/
├── backend/
│   ├── conftest.py              # Base pytest configuration
│   ├── conftest_phases.py       # Additional fixtures for phase tests
│   ├── test_phase1_security.py  # Phase 1: Security & Logging tests
│   ├── test_phase2_albums.py    # Phase 2: Album System & Image Management tests
│   ├── test_phase3_labeling.py  # Phase 3: AI Labeling System tests
│   ├── test_integration.py      # Integration tests across all phases
│   ├── test_api.py              # Original API tests
│   └── test_utils.py            # Original utility tests
├── frontend/                    # Frontend tests (if any)
├── run_phase_tests.py          # Test runner script
└── README.md                   # This file
```

## Test Coverage

### Phase 1: Security & Logging
- **Authentication System**
  - User loading/saving
  - Password hashing and verification
  - Secret key generation
  - Admin role checking

- **Logging Configuration**
  - Development vs production logging
  - Structured logging setup
  - Log level configuration

- **CORS Configuration**
  - Development localhost origins
  - Production origin restrictions
  - Header validation

- **Security Headers**
  - Debug mode configuration
  - Secret key requirements
  - Admin endpoint protection

### Phase 2: Album System & Image Management
- **Album API Endpoints**
  - CRUD operations (Create, Read, Update, Delete)
  - Public vs admin access
  - Pagination support
  - Error handling

- **Image Management**
  - Image upload with validation
  - Image deletion with cleanup
  - Thumbnail generation
  - File type validation

- **Album-Image Associations**
  - Adding images to albums
  - Removing images from albums
  - Bidirectional relationships
  - Data consistency

- **NSFW Filtering**
  - NSFW flag management
  - Public filtering
  - Admin controls

### Phase 3: AI Labeling System
- **Image Encoding**
  - Base64 encoding for Claude API
  - Image resizing (max 1568px)
  - Format conversion (RGBA to RGB)
  - Error handling

- **Claude API Integration**
  - Single image labeling
  - Batch image labeling
  - Prompt type selection
  - Error handling and fallbacks

- **NSFW Classification**
  - SAFE, SUGGESTIVE, ADULT, EXPLICIT ratings
  - Database flag updates
  - Classification accuracy

- **Label Storage**
  - Caption labels
  - Tag labels
  - Source model tracking
  - Database relationships

### Integration Tests
- **Complete Workflows**
  - Image upload → Album creation → Labeling
  - Batch processing workflows
  - Error recovery

- **Data Consistency**
  - Relationship integrity
  - Transaction rollbacks
  - Data validation

- **Performance**
  - Large dataset handling
  - Pagination efficiency
  - Memory usage

## Running Tests

### Run All Tests
```bash
# From project root
python tests/run_phase_tests.py

# Or using pytest directly
pytest tests/backend/ -v --cov=server
```

### Run Specific Phase
```bash
# Phase 1: Security & Logging
python tests/run_phase_tests.py 1

# Phase 2: Album System
python tests/run_phase_tests.py 2

# Phase 3: AI Labeling
python tests/run_phase_tests.py 3

# Integration tests
python tests/run_phase_tests.py integration
```

### Run Individual Test Files
```bash
# Security tests
pytest tests/backend/test_phase1_security.py -v

# Album tests
pytest tests/backend/test_phase2_albums.py -v

# Labeling tests
pytest tests/backend/test_phase3_labeling.py -v

# Integration tests
pytest tests/backend/test_integration.py -v
```

## Test Configuration

### Environment Variables
Tests automatically set these environment variables:
- `FLASK_ENV=testing`
- `FLASK_SECRET_KEY=test_secret_key_for_testing_only`

### Database
Tests use an in-memory SQLite database that is automatically cleaned between tests.

### Mocking
Tests extensively use mocking for:
- External API calls (Claude)
- File system operations
- Authentication
- PIL image operations

## Test Fixtures

### Database Fixtures
- `clean_database`: Cleans database before each test
- `sample_album`: Creates a test album
- `sample_image`: Creates a test image
- `sample_album_with_images`: Creates album with multiple images

### Mock Fixtures
- `mock_claude_response`: Mock Claude API success response
- `mock_claude_error`: Mock Claude API error response
- `mock_admin_auth`: Mock admin authentication
- `mock_public_auth`: Mock public user (no auth)
- `mock_file_operations`: Mock file system operations
- `mock_pil_operations`: Mock PIL image operations

### Data Fixtures
- `temp_image_file`: Creates temporary image file
- `sample_image_data`: Creates image data for upload testing
- `admin_headers`: Admin authentication headers

## Coverage Reports

Tests generate coverage reports in multiple formats:
- Terminal output with missing lines
- HTML report in `htmlcov/` directory

## Test Categories

### Unit Tests
- Individual function testing
- Mock-based testing
- Isolated component testing

### Integration Tests
- End-to-end workflows
- Database integration
- API endpoint testing

### Error Handling Tests
- Invalid input handling
- Network error simulation
- Database error recovery

### Performance Tests
- Large dataset handling
- Memory usage validation
- Response time testing

## Continuous Integration

Tests are designed to run in CI environments:
- No external dependencies
- Deterministic results
- Fast execution
- Comprehensive coverage

## Adding New Tests

When adding new features, follow these patterns:

1. **Create test file**: `test_phaseX_feature.py`
2. **Add fixtures**: Use existing fixtures or create new ones
3. **Mock external dependencies**: Always mock external APIs/files
4. **Test error cases**: Include both success and failure scenarios
5. **Update documentation**: Add new tests to this README

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure project root is in Python path
2. **Database Errors**: Check that database is properly initialized
3. **Mock Failures**: Verify mock setup matches actual code
4. **File Path Issues**: Use absolute paths in tests

### Debug Mode
Run tests with debug output:
```bash
pytest tests/backend/ -v -s --tb=long
```

### Test Discovery
Check which tests are found:
```bash
pytest --collect-only tests/backend/
```