# Contributing to Imagineer

Thank you for your interest in contributing to Imagineer!

## Development Setup

1. **Fork the repository**

2. **Clone your fork:**
```bash
git clone https://github.com/YOUR_USERNAME/imagineer.git
cd imagineer
```

3. **Install Python dependencies:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
pip install -e ".[dev]"  # Development dependencies (black, flake8, isort, pytest)
```

4. **Install frontend dependencies:**
```bash
cd web
npm install
cd ..
```

5. **Start development servers:**
```bash
make dev  # Starts both API and frontend dev servers
```

Or individually:
```bash
make api      # API server on port 10050
make web-dev  # Frontend dev server on port 10051
```

## Code Style

### Python
- Follow PEP 8 guidelines
- Use Black for code formatting: `black src/ examples/ server/`
- Use isort for import sorting: `isort src/ examples/ server/`
- Run flake8 for linting: `flake8 src/ examples/ server/`
- Add docstrings to functions and classes
- Type hints are encouraged but not required

### JavaScript/React
- Use modern ES6+ syntax
- Follow React hooks patterns
- Use functional components (not class components)
- Keep components small and focused
- Use meaningful variable and function names
- Add comments for complex logic

### CSS
- Use existing class naming conventions
- Keep styles organized by component
- Use CSS variables for colors and common values
- Maintain responsive design principles

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
- All existing tests pass (when available)
- New features include appropriate tests
- Documentation is updated if needed
- Frontend builds without errors: `make build`
- API starts without errors: `make api`

### Manual Testing Checklist
- [ ] Web UI loads correctly
- [ ] Image generation works end-to-end
- [ ] Controls (steps, guidance, seed) function properly
- [ ] Generated images appear in gallery
- [ ] Image modal shows correct metadata
- [ ] API endpoints return expected responses
- [ ] No console errors in browser dev tools

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
