# Frontend App — SF Eats (The Infatuation Map)

## What it does

A Progressive Web App that shows all Infatuation-reviewed SF restaurants on Google Maps.
Core feature: **proximity sorting** — find the closest restaurant when you're out and about.

## Quick Start

```bash
cd app

# Copy and fill in your Google Maps API key
cp .env.example .env.local
# Edit .env.local with your key

# Install dependencies
npm install

# Run dev server
npm run dev
```

Or press **Ctrl+Shift+B** in VS Code (default task = dev server).

## Features

- 📍 **Near Me** — GPS-based proximity sorting with distance display
- 🎚️ **Adjustable radius** — 1 to 50 mile slider (default 15 mi)
- 🔍 **Search** — filter by name, address, cuisine, or neighborhood
- 🏷️ **Tag & neighborhood filters** — chip-based filtering
- 📱 **Installable PWA** — works offline, add to home screen on mobile
- 🗺️ **Marker clustering** — handles 200+ pins without visual clutter

## API Key Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/google/maps-apis)
2. Create a project and enable **Maps JavaScript API**
3. Create an API key and add it to `.env.local`:

   ```
   VITE_GOOGLE_MAPS_API_KEY=AIza...
   ```

4. Restrict the key to your domain + Maps JS API for security
