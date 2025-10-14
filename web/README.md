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
