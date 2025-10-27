# GitHub Actions Workflows

This directory contains comprehensive GitHub Actions workflows for the Imagineer project.

## Workflows Overview

### 🧪 Core Testing Workflows

#### `ci.yml` - Continuous Integration
- **Purpose**: Main CI workflow that runs on every PR and push
- **Triggers**: Push to main/develop, PRs, manual dispatch
- **Jobs**:
  - Backend Tests (Python linting, formatting, unit tests)
  - Frontend Tests (Node.js linting, unit tests, build)
  - Integration Tests (End-to-end API and frontend testing)
  - Security Tests (Bandit, Safety, npm audit)
  - Build Tests (Versioning system, build verification)
  - Test Summary (Comprehensive results overview)

#### `test.yml` - Comprehensive Tests
- **Purpose**: Detailed testing workflow with coverage reporting
- **Triggers**: Push to main/develop, PRs, manual dispatch
- **Features**:
  - Backend tests with coverage
  - Frontend tests with coverage
  - Integration tests
  - Security scanning
  - Build verification
  - Codecov integration

#### `test-frontend.yml` - Frontend-Specific Tests
- **Purpose**: Focused frontend testing with Node.js version matrix
- **Triggers**: Changes to web/ directory, PRs, manual dispatch
- **Features**:
  - Tests on Node.js 18, 20, 21
  - ESLint checking
  - Unit tests with coverage
  - Build verification

#### `test-python-matrix.yml` - Python Version Matrix
- **Purpose**: Test backend compatibility across Python versions
- **Triggers**: Changes to backend code, PRs, manual dispatch
- **Features**:
  - Tests on Python 3.8, 3.9, 3.10, 3.11, 3.12
  - Full linting and formatting checks
  - Unit tests with coverage

### 🔍 Specialized Workflows

#### `e2e-tests.yml` - End-to-End Tests
- **Purpose**: Comprehensive end-to-end testing
- **Triggers**: PRs, manual dispatch
- **Features**:
  - Backend API endpoint testing
  - Frontend build verification
  - Versioning system testing
  - Deployment script testing

#### `performance-tests.yml` - Performance Testing
- **Purpose**: Performance and load testing
- **Triggers**: PRs, manual dispatch
- **Features**:
  - API response time testing
  - Frontend build performance
  - Memory usage analysis
  - Build output size analysis

#### `security-scan.yml` - Security Scanning
- **Purpose**: Comprehensive security vulnerability scanning
- **Triggers**: PRs, weekly schedule, manual dispatch
- **Features**:
  - Python security (Bandit, Safety, pip-audit)
  - Node.js security (npm audit)
  - Dependency vulnerability scanning
  - Security report generation

#### `code-quality.yml` - Code Quality & Coverage
- **Purpose**: Advanced code quality analysis
- **Triggers**: PRs, manual dispatch
- **Features**:
  - Python code quality (Black, isort, Flake8, MyPy)
  - Node.js code quality (ESLint, TypeScript)
  - Comprehensive coverage reporting
  - Codecov integration

### 🔄 Maintenance Workflows

#### `dependency-updates.yml` - Dependency Updates
- **Purpose**: Automated dependency update checking
- **Triggers**: Weekly schedule, manual dispatch
- **Features**:
  - Python dependency updates
  - Node.js dependency updates
  - Security vulnerability scanning
  - Update report generation

### 🚀 Deployment Workflows

#### `deploy-frontend.yml` - Frontend Deployment
- **Purpose**: Deploy frontend to production
- **Triggers**: Push to main, manual dispatch
- **Features**:
  - Frontend build and testing
  - SSH deployment to server
  - Atomic deployment with rollback
  - Deployment verification

#### `terraform.yml` - Infrastructure Management
- **Purpose**: Manage infrastructure with Terraform
- **Triggers**: Push to main, manual dispatch
- **Features**:
  - Terraform format checking
  - Terraform validation
  - Infrastructure planning
  - Cloudflare resource management

### 📊 Legacy Workflows

#### `test-backend.yml` - Backend Tests (Legacy)
- **Purpose**: Legacy backend testing workflow
- **Status**: Deprecated in favor of `ci.yml`
- **Triggers**: Changes to backend code

## Workflow Features

### 🎯 Smart Triggering
- **Path-based triggers**: Workflows only run when relevant files change
- **Conditional execution**: Jobs run based on file changes and event types
- **Manual dispatch**: All workflows can be triggered manually

### 📊 Comprehensive Reporting
- **GitHub Step Summaries**: Detailed results in PR comments
- **Codecov Integration**: Coverage reporting for both frontend and backend
- **Artifact Uploads**: Security reports and test results
- **Status Checks**: Required status checks for PR merging

### 🔒 Security & Quality
- **Security Scanning**: Automated vulnerability detection
- **Code Quality**: Linting, formatting, and type checking
- **Dependency Management**: Automated update checking with Dependabot
- **Performance Testing**: Load and performance analysis

### 🚀 Deployment & Infrastructure
- **Atomic Deployments**: Safe deployment with rollback capability
- **Infrastructure as Code**: Terraform-based infrastructure management
- **Version Management**: Automated versioning and cache busting

## Configuration

### Environment Variables
- `NODE_VERSION`: Node.js version (default: 20)
- `PYTHON_VERSION`: Python version (default: 3.12)

### Required Secrets
- `SSH_PRIVATE_KEY`: SSH key for deployment
- `SSH_HOST`: Deployment server hostname
- `SSH_USER`: Deployment server username
- `CLOUDFLARE_API_TOKEN`: Cloudflare API token
- `CLOUDFLARE_DOMAIN`: Cloudflare domain
- `CLOUDFLARE_TUNNEL_ID`: Cloudflare tunnel ID

### Dependabot Configuration
- Automated dependency updates for Python, Node.js, and GitHub Actions
- Weekly update schedule
- Smart ignore rules for major version updates
- Automatic PR creation with proper labels

## Usage

### Running Tests Locally
```bash
# Backend tests
pytest tests/backend/ -v --cov=server --cov=src

# Frontend tests
cd web && npm test

# Integration tests
./scripts/deploy/check-deployment.sh
```

### Manual Workflow Triggers
1. Go to Actions tab in GitHub
2. Select the desired workflow
3. Click "Run workflow"
4. Choose branch and options
5. Click "Run workflow"

### Viewing Results
- **PR Comments**: Test results appear in PR comments
- **Actions Tab**: Detailed logs and artifacts
- **Codecov**: Coverage reports and trends
- **Artifacts**: Download security reports and test results

## Best Practices

1. **Always run tests locally** before pushing
2. **Review security reports** regularly
3. **Update dependencies** when security vulnerabilities are found
4. **Monitor performance** trends over time
5. **Keep workflows up to date** with latest actions

## Troubleshooting

### Common Issues
- **Flaky tests**: Check for race conditions or timing issues
- **Build failures**: Verify all dependencies are properly installed
- **Security warnings**: Review and address vulnerability reports
- **Performance regressions**: Compare with previous runs

### Getting Help
- Check workflow logs in the Actions tab
- Review PR comments for test summaries
- Download artifacts for detailed analysis
- Check the project's main README for setup instructions