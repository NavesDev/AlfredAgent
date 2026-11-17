# Panel visual direction

Redesign of the web panel in Apple's glass style (visionOS). This document guides the implementation; the mockups show each screen. On-screen labels stay in pt-BR.

## Principles

- **Glass over a blurred room:** translucent panels float over a dark background with out-of-focus shapes.
- **One living element per screen:** Alfred's orb. Everything else is quiet.
- **Neutral:** graphite background, no yellow and no blue. Color comes only from states and session pictures.
- **Pills and circles:** round icon buttons, pill controls, generously rounded corners.
- **Little information at a time:** grouped lists like the iPhone Settings app; detail only on the open card.

## References

- **Orb:** [Strands](https://reactbits.dev/animations/strands), from React Bits (MIT + Commons Clause: fine to use in the app, not to resell the component). Plain WebGL2, no dependencies; it has `listening` and `level` props for the voice.
- **Material, lists and controls:** visionOS and iOS Settings.
- **Plan usage:** Apple Watch–style rings, in settings and in the control bar (small ring with the % and the window).
- **Taste Skill:** a single animated element per screen.

## Colors

| Token | Value | Use |
|---|---|---|
| `--page` | `#0a0a0c` | page background |
| room background | gradient `#19191c` → `#09090b`, shapes `#3c3c42`, `#8a8a94`, `#2a2a30`, `#303036` with a 60px blur | behind the panels |
| `--ink` | `#f5f5f7` | main text |
| `--ink-2` | `rgba(235,235,245,.62)` | secondary text |
| `--ink-3` | `rgba(235,235,245,.36)` | hints, placeholders |
| `--fill` / `--fill-on` | `rgba(255,255,255,.10)` / `.22` | control / selected background |
| `--blue` | `#0a84ff` | links, focus, speaking |
| `--teal` | `#64d2ff` | session working |
| `--orange` | `#ff9f0a` | waiting for you, context above 60% |
| `--green` | `#30d158` | on, done |
| red | `#ff453a` | delete, context above 80% |

## Glass material

```css
.glass {
  background: linear-gradient(180deg, rgba(255,255,255,.16), rgba(255,255,255,.05)), rgba(118,118,128,.24);
  backdrop-filter: blur(40px) saturate(170%);
  border: 1px solid rgba(255,255,255,.14);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.22), 0 24px 60px rgba(0,0,0,.35);
}
```

- Lists and fields inside the glass: `rgba(0,0,0,.16–.2)`.
- Radii: panel 30px, card 24px, list row 14–16px, pill controls (999px).
- Dropdowns use the glass `Picker`, never a native `<select>` (WebKitGTK draws it white).

## Typography

- Apple's system font when available; otherwise Inter (`-apple-system, 'SF Pro Text', 'Inter', system-ui`).
- Page titles: 22–28px, weight 700, `letter-spacing: -.02em`.
- Body: 13–14px, weight 500 on names.
- Section labels: 13px, uppercase, weight 600, `--ink-2`.
- Numbers aligned with `tabular-nums`.
- **Display:** the "Alfred" name on the title bar only, in Newsreader italic (`opsz` 72), token `--font-display`, bundled with `@fontsource-variable/newsreader` (works offline).

## Alfred's orb

- Strands with glass, default spectral palette, centered on the Painel screen.
- Voice states (`useVoice`):

| State | `listening` | `level` | `speed` | `energy` |
|---|---|---|---|---|
| Idle | no | 0 | 0.5 | 0.4 |
| Listening | yes | microphone level | 1 | 0.8 |
| Thinking | no | 0.3 | 1.8 | 0.6 |
| Speaking | yes | speech level | 1.1 | 0.9 |

- **No WebGL2** (desktop app visualizer, some VMs): CSS orb with blurred colored bands, same palette. Strands shows nothing on its own when WebGL is missing, so the fallback is mandatory.
- Removed from the panel: `three`, `@react-three/fiber` and the old orb.

## Components

- **Navigation bar:** vertical pill on the left with round icons (Painel, Projetos, Configurações).
- **Control bar (ornament):** pill at the bottom with microphone, state and meter, model picker, new conversation, transcript and the usage ring.
- **Speech bubble:** pill with Alfred's avatar and its last sentence.
- **Grouped list:** rows with a colored square icon (8px radius), name, detail and value on the right, split by a thin line.
- **Segmented control, on/off switch (green), value popup and stepper** following iOS.
- **State ring on the session picture:** spinning blue while working; orange with a dot while waiting for you.

## Screens

- **Painel (Window layout):** navigation | session list | orb, bubble and control bar | session card or transcript.
- **Session card** (in the style of "Now Playing"): big picture, name, project and branch, state, task with progress, permission request with Deny and Allow, context, model, subagents, and actions (clear, talk to, delete).
- **Projects:** cards like albums; the cover combines the project initial and the session pictures, with a badge for who is working or waiting. Shows the description, the aliases and the counts. The last card is "Novo projeto".
- **Project:** side panel with mark, name, description, spoken names and "Apagar projeto". Main panel with workspaces (description and sessions in each, worktrees indented) and the project's sessions.
- **Settings:** side bar like Settings, with Usage and limits (rings and spend per session), Models, Open sessions and MCPs (switches and "Desligar/Ligar todos").

## Motion

- Only the orb, the working ring and the meters move.
- 200ms transitions; cards grow 2% on hover.
- `prefers-reduced-motion` turns animations off.

## Mockups

- [Painel, Window and Ornaments layouts](https://claude.ai/artifact/9v7ZF6iShWm7TTdPC7hWcE)
- [Sessions, with the three picture options](https://claude.ai/artifact/VZXzh69Zen2HUiJtNBvyEs)
- [Projects, Project and Settings](https://claude.ai/artifact/TRisX7cDuLVeakNfrFvKVL)
- [Font, icon and result presentation (v3)](https://claude.ai/artifact/1v5NGLoRGVnSA8s3kJML4j)
- [Result states, history and pill position](https://claude.ai/artifact/PWfYEnrmR3vCHgRi1jrpLf)

## Decisions

- **Session pictures:** 3D portrait. Until the portrait exists, the session shows the monogram (initials on a gradient that is stable per name). Generation: [ADR 0009](adr/0009-session-portraits-via-mcp.md).
- **Map figures:** removed, along with the "agent size on the map" option (`figure_scale`).
- **Permissions:** the card has no Deny/Allow; confirmation stays by voice, as the SPEC says.

## Desktop app

- **Title bar:** 40px transparent strip over the room that drags the window (double click maximizes). Connection dot + "Alfred" on the left; 28px round glass buttons (minimize, maximize/restore, close) on the right. Only shows in Tauri.
- **Window:** 12px corners, no corners when maximized.
- **Floating visualizer:** dark glass pill with the mini CSS orb (32px) and 9 rounded white bars, like the [Bar Visualizer](https://ui.elevenlabs.io/docs/components/bar-visualizer) from ElevenLabs UI (MIT). Listening and speaking: each bar's height follows its frequency band. Thinking: low bars with a wave passing through. Enters with a fade and scale. It cannot be dragged: its spot is a preset in Settings → Geral ("Posição da pílula": corners and center, top or bottom, 8px from the work area's edge; default top right).
- **Icon:** a frame of the real Strands orb (`apps/web/icon.html`, rendered by `apps/desktop/render_icon.mjs`), circular mask with a soft edge, transparent background; same icon on the dock and the tray.

## Results

References: Dynamic Island / Live Activities (card), Quick Look (expanded view), lightbox `@hirael/lightbox` (Shoogle, MIT).

- **Card:** the pill grows into a 300px card in its corner (it grows down when anchored on top, up when at the bottom); 22px corners, solid dark surface (`surface` utility, `#161619`): it floats over any desktop, where translucent glass turned grey. Header: mini orb, session name and time, "1 de N", close (✕). Body by type: image/GIF 16:9 `cover`, muted looping video, report (summary and up to 3 changed files with +/−, then "+N"), document preview. Buttons: "Ampliar" (primary), "Abrir no app", "Pasta" (desktop only).
- **Behavior:** never takes keyboard focus; leaves after 30s without interaction (hover pauses); a new result replaces it. With the panel in sight the same card shows at the panel's top right instead.
- **Expanded view:** a separate window, 70% of the monitor, centered, in the panel's own look: the opaque graphite room as background (never the desktop showing through), a 56px title bar that drags the window (mini orb, file name, session · time · kind and size; "Abrir no app" and "Pasta" as glass pills; round glass close with red hover), 22px window corners; the slide on a dark panel (`#141417`, 24px corners, for contrast with white text): text, reports and PDF in a centered column up to 860px; images and video keep their own size and shape, centered with room around them and no panel; a file without preview is a small centered card; and a glass ornament pill at the bottom with ‹, one chip per file (icon or round thumbnail and its name), "1 de N" and ›. Esc and the arrow keys work too.
- **Documents:** Markdown and reports at 15px in a 720px measure (`prose-result` utility); YAML front matter dropped, Obsidian `[[links]]` shown as text and callouts as a bold title. PDF pages fill the width up to 900px.
- **States:** loading shimmer in the media slot; a missing file shows "Arquivo não existe mais" without open buttons; an unknown type is a file card whose main button is "Abrir no app"; HTML carries an "Isolado" badge; long Markdown fades out at the bottom of the card.
- **Types:** PDF through `pdfjs-dist` (first page on the card, every page expanded); Markdown through `react-markdown` + `remark-gfm` without raw HTML; HTML in a sandboxed iframe without same-origin; text up to 1 MB in a monospaced block; anything else a file card with "Abrir no app".
- **Other device:** title, summary and report text only, with "Arquivos só no computador".
- **History:** under the session card, the session's results with a thumbnail and time; a missing file shows "Arquivo não existe mais".
