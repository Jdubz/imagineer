# Contributing to Imagineer

Thank you for your interest in contributing to Imagineer!

## Development Setup

1. Fork the repository
2. Clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/imagineer.git
cd imagineer
```

3. Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting: `black src/ examples/`
- Use isort for import sorting: `isort src/ examples/`
- Run flake8 for linting: `flake8 src/ examples/`

## Making Changes

1. Create a new branch for your feature:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and commit them:
```bash
git add .
git commit -m "Add your descriptive commit message"
```

3. Push to your fork:
```bash
git push origin feature/your-feature-name
```

4. Open a Pull Request on GitHub

## Testing

Before submitting a PR, ensure:
- Your code follows the style guidelines
- All existing tests pass
- New features include appropriate tests
- Documentation is updated if needed

## Reporting Issues

When reporting issues, please include:
- Operating system and version
- Python version
- GPU model and driver version
- Steps to reproduce the issue
- Expected vs actual behavior
- Any error messages or logs

## Feature Requests

We welcome feature requests! Please open an issue describing:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered
- Additional context or examples

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a positive community

Thank you for contributing!
