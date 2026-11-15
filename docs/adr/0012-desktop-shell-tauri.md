# 0012 — Desktop app: Tauri v2 wrapping the web panel

- **Status:** Accepted
- **Date:** 2026-11-14

## Context

The panel only opened in the browser: with an address bar, no tray and nothing on screen when the window was minimized. The user wants a window with its own top bar (no browser header or native buttons) and a floating voice visualizer when the app is minimized or in the tray.

A spike on the user's machine (Zorin/GNOME 46 on X11, RTX 3060) validated Tauri: transparent window with no black background, Strands in WebGL2 on WebKitGTK, always on top and click-through.

## Decision

- **Tauri v2** in `apps/desktop`, a thin Rust shell: windows, tray, single instance. No business rules.
- **Same UI:** the windows load `apps/web` served at `http://localhost:5173` (the same one the launcher already starts). No bundled web build.
- **Separate server:** the app neither starts nor stops the server; it is only a client of `/ws` and the API. A server that is down shows as "Servidor offline" on the panel.
- **Main window** without system decorations, rounded corners. `apps/web` draws the title bar when running in Tauri (`isDesktop()`): a transparent strip that drags the window, a title with the connection dot on the left and round glass buttons (minimize, maximize, close) on the right.
- **Closing hides it in the tray.** Quitting only from the tray menu.
- **Overlay:** a second transparent, undecorated, always-on-top window, outside the taskbar, that ignores the mouse, at the bottom center of the primary monitor's work area. Route `/overlay` of `apps/web`. It stays open drawing nothing; it shows the pill (mini orb + bars) when the voice is not `idle` and the main window is minimized or hidden.
- **Bars with real audio:** the `audio_level` event gets `bands` (9 voice frequency bands, 0..1), computed in the audio thread (mic and TTS). The visualizer is adapted from ElevenLabs UI's Bar Visualizer (MIT).

## Consequences

- X11 only. On Wayland, GNOME honors neither "always on top" nor window position; the overlay would not work.
- WebKitGTK instead of Chromium: small CSS and WebGL differences to watch. Plan B is Electron, a cheap switch because the whole UI lives in `apps/web`.
- Global shortcut (push-to-talk) and native notifications come later.
