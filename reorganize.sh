#!/bin/bash
# Reorganize Imagineer project structure
# Run with: bash reorganize.sh

set -e

echo "================================================"
echo "IMAGINEER PROJECT REORGANIZATION"
echo "================================================"
echo ""
echo "This will:"
echo "  1. Create new directory structure"
echo "  2. Move documentation files to docs/"
echo "  3. Move scripts to scripts/"
echo "  4. Setup web/ frontend directory"
echo "  5. Clean up old files"
echo "  6. Update .gitignore"
echo "  7. Update Flask server paths"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."
echo ""

cd "$(dirname "$0")"

# Step 1: Create directory structure
echo "[1/7] Creating directory structure..."
mkdir -p docs
mkdir -p scripts/setup
mkdir -p tests
mkdir -p web/src/{components,api,styles}
echo "  ✓ Directories created"

# Step 2: Move documentation files
echo ""
echo "[2/7] Moving documentation files..."
mv SETUP.md docs/ 2>/dev/null || echo "  - SETUP.md already moved or missing"
mv SERVER_README.md docs/API.md 2>/dev/null || echo "  - SERVER_README.md already moved or missing"
mv SETUP_INSTRUCTIONS.md docs/DEPLOYMENT.md 2>/dev/null || echo "  - SETUP_INSTRUCTIONS.md already moved or missing"
mv CONTRIBUTING.md docs/ 2>/dev/null || echo "  - CONTRIBUTING.md already moved or missing"
echo "  ✓ Documentation moved to docs/"

# Step 3: Move scripts
echo ""
echo "[3/7] Moving scripts..."
mv start_server.sh scripts/ 2>/dev/null || echo "  - start_server.sh already moved or missing"
mv setup_drives.sh scripts/setup/ 2>/dev/null || echo "  - setup_drives.sh already moved or missing"
mv setup_samba.sh scripts/setup/ 2>/dev/null || echo "  - setup_samba.sh already moved or missing"
mv update_config_for_speedy.sh scripts/setup/configure_speedy.sh 2>/dev/null || echo "  - update_config_for_speedy.sh already moved or missing"
echo "  ✓ Scripts moved to scripts/"

# Step 4: Setup web directory
echo ""
echo "[4/7] Setting up web frontend directory..."

# Create placeholder files
cat > web/package.json << 'EOF'
{
  "name": "imagineer-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build --outDir ../public",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "axios": "^1.7.9"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.11"
  }
}
EOF

cat > web/vite.config.js << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../public',
    emptyOutDir: true
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
EOF

cat > web/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Imagineer - AI Image Generation</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
EOF

cat > web/src/main.jsx << 'EOF'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
EOF

cat > web/src/App.jsx << 'EOF'
import React from 'react'
import './styles/App.css'

function App() {
  return (
    <div className="App">
      <h1>Imagineer</h1>
      <p>AI Image Generation Toolkit</p>
      <p>Frontend is ready for development!</p>
      <p>Run: <code>cd web && npm install && npm run dev</code></p>
    </div>
  )
}

export default App
EOF

cat > web/src/styles/index.css << 'EOF'
:root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #333;
}

#root {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
}
EOF

cat > web/src/styles/App.css << 'EOF'
.App {
  text-align: center;
  color: white;
}

h1 {
  font-size: 3.2em;
  line-height: 1.1;
  margin-bottom: 1rem;
}

code {
  background: rgba(255, 255, 255, 0.1);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-family: monospace;
}
EOF

cat > web/README.md << 'EOF'
# Imagineer Web Frontend

React + Vite frontend for Imagineer.

## Development

```bash
# Install dependencies
npm install

# Start dev server (with API proxy)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Structure

```
web/
├── src/
│   ├── App.jsx              # Main app component
│   ├── main.jsx             # Entry point
│   ├── components/          # React components
│   ├── api/                 # API client
│   └── styles/              # CSS files
├── index.html               # HTML template
├── vite.config.js           # Vite configuration
└── package.json             # Dependencies
```

## API Integration

The dev server proxies `/api/*` requests to Flask backend at `http://localhost:5000`.

In production, Flask serves the built frontend from `public/`.
EOF

echo "  ✓ Web frontend structure created"

# Step 5: Clean up old files
echo ""
echo "[5/7] Cleaning up old files..."
rm -f config.yaml.backup-* 2>/dev/null || true
rm -f server/setup_react.sh 2>/dev/null || true
rm -rf server/static/ 2>/dev/null || true
echo "  ✓ Old files removed"

# Step 6: Update .gitignore
echo ""
echo "[6/7] Updating .gitignore..."
cat > .gitignore << 'EOF'
# Virtual environment
venv/

# Python
__pycache__/
*.py[cod]
*.so
.Python
*.egg-info/

# Environment
.env
*.local

# Outputs (stored on Speedy drive)
models/
outputs/
checkpoints/
data/training/*
!data/training/README.md

# Backups
*.backup-*
*.bak

# Logs
*.log

# Frontend
web/node_modules/    # Node dependencies (inside web/)
public/              # Built frontend (generated)
web/dist/            # Alternative build output
.vite/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOF
echo "  ✓ .gitignore updated"

# Step 7: Update Flask server
echo ""
echo "[7/7] Updating Flask server configuration..."

# Backup original
cp server/api.py server/api.py.backup

# Update Flask app to serve from public/
sed -i "s/static_folder='static'/static_folder='..\/public', static_url_path=''/" server/api.py
sed -i "s/send_from_directory('static', 'index.html')/send_from_directory('..\/public', 'index.html')/" server/api.py

echo "  ✓ Flask server updated"

# Create new start scripts
echo ""
echo "Creating new startup scripts..."

cat > scripts/start_api.sh << 'EOF'
#!/bin/bash
# Start Flask API server only
cd "$(dirname "$0")/.."
source venv/bin/activate
python server/api.py
EOF
chmod +x scripts/start_api.sh

cat > scripts/start_dev.sh << 'EOF'
#!/bin/bash
# Start both API and frontend dev servers
cd "$(dirname "$0")/.."

echo "Starting Imagineer Development Environment"
echo "=========================================="
echo ""
echo "Starting Flask API on port 5000..."
source venv/bin/activate
python server/api.py &
API_PID=$!

echo "Starting Vite dev server on port 5173..."
cd web
npm run dev &
VITE_PID=$!

echo ""
echo "Both servers started!"
echo "  - API: http://localhost:5000"
echo "  - Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"

# Trap Ctrl+C and kill both processes
trap "kill $API_PID $VITE_PID 2>/dev/null" EXIT

wait
EOF
chmod +x scripts/start_dev.sh

cat > scripts/generate.sh << 'EOF'
#!/bin/bash
# Quick wrapper for image generation
cd "$(dirname "$0")/.."
source venv/bin/activate
python examples/generate.py "$@"
EOF
chmod +x scripts/generate.sh

echo "  ✓ Startup scripts created"

echo ""
echo "================================================"
echo "✓ REORGANIZATION COMPLETE!"
echo "================================================"
echo ""
echo "New structure:"
echo "  ✓ docs/          - All documentation"
echo "  ✓ scripts/       - All executable scripts"
echo "  ✓ scripts/setup/ - One-time setup scripts"
echo "  ✓ web/           - Frontend source code"
echo "  ✓ public/        - Built frontend (git ignored)"
echo ""
echo "Next steps:"
echo "  1. Install frontend dependencies:"
echo "     cd web && npm install"
echo ""
echo "  2. Start development:"
echo "     bash scripts/start_dev.sh"
echo ""
echo "  3. Or start API only:"
echo "     bash scripts/start_api.sh"
echo ""
echo "  4. Build frontend for production:"
echo "     cd web && npm run build"
echo ""
echo "Backup files saved as *.backup"
echo ""
