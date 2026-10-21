# LectureMind AI — Frontend

React 19 app with Tailwind CSS + Radix UI.

This is the frontend for **LectureMind AI**. See the [root README](../README.md) for setup and usage.

## Local Dev

```bash
cd frontend
npm install --legacy-peer-deps
REACT_APP_BACKEND_URL=http://localhost:8001 npm start
```

Runs on [http://localhost:3000](http://localhost:3000).

## Production Build

```bash
npm run build
```

Served via nginx (see `Dockerfile` and `nginx.conf`).

## Design system (Field Notebook)

- **Tokens:** `src/index.css` (CSS variables for Day desk and Night desk, switched by `data-theme`); Tailwind colour and font names in `tailwind.config.js` (`font-display`, `font-body`, `font-hand`, `font-mono`, token colours such as `bg-primary`, `text-destructive`, `text-amber`).
- **Button:** variants `paper`, `pen`, `quiet`; legacy variant names remain as aliases.
- **Components:** `StatusStamp` (icon plus word for lecture status), `ConfirmDialog` (destructive confirmations with a "Keep it" style cancel), `PenPlayer` (audio player, keyboard seekable), `ThemeToggle` in the desk bar.
- **Hard rules (enforced by `src/lib/__tests__/designGuards.test.js`):** never `text-accent` on its own (highlight is background only); font weights 400/700 only; four text sizes (`text-sm`, `text-base`, `text-2xl`, `.text-display`); token colours only (no palette classes, no `dark:`); regular-weight icons only; every framer-motion user honours `useReducedMotion`.
- **Tests:** `npx vitest run --pool=threads`
