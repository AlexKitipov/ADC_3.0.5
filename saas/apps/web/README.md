# ADC Trading Frontend

Vite-powered React frontend for the ADC Trading Platform.

## Available scripts

- `npm run dev` starts the Vite development server.
- `npm run build` compiles TypeScript and creates a production build.
- `npm run preview` serves the production build locally.
- `npm run lint` runs ESLint across TypeScript and React source files.

Set `VITE_API_URL` to point the frontend at a non-local backend. It defaults to `http://localhost:8000/api/v1`, the canonical versioned API base path.

Keep the `/api/v1` suffix in local, staging, and production deployments so the frontend calls the same route family that the backend registers.
