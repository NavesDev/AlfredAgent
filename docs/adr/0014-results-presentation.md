# 0014 — Results shown from the home under the read guard

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

When a session finished, Alfred only spoke its summary. Seeing the generated image, the test video or what changed in the code meant finding and opening the file by hand. Deciding with an extra model call whether to show something would spend tokens on every task.

## Decision

- **The producer decides, in its final reply:** besides `RESUMO:`, a session may end with `APRESENTAR: <items>` (record and show) or `GUARDAR: <items>` (record only). Items are separated by `;`: an absolute path or `relatório`. No lines, nothing recorded. The sessions' prompts say when: media or a generated document is shown, a code change shows a report, a read-only or trivial task records nothing.
- **Change report:** the reply text without control lines plus `git diff --numstat` from the `HEAD` the task started at to the tree at the end, only inside a git checkout.
- **Alfred shows on request:** the `apresentar` tool shows a session's last result or files Alfred found (`caminhos`, up to 20, one result of `source = alfred`; a file it may not read refuses the set), always in the expanded view: the user asked for it. The card is only for a session's own `APRESENTAR:` line when it finishes a task; `fechar_apresentacao` closes it.
- **Same guard as Alfred's reads (ADR 0011):** a file enters a result only if it is inside the home, resolved through symlinks, and does not match the secret rules. The guard runs when the result is recorded and again on every request for the file; anything outside is dropped and logged.
- **Files never leave the computer:** `GET /api/results/{id}/files/{i}` answers only loopback clients (403 otherwise). A panel opened from another device shows title, summary and report text only. The API never returns a file's path.
- **The server opens files:** "Abrir no app" and "Pasta" call `POST /api/results/{id}/files/{i}/open` (loopback only, guard checked again); the server runs `xdg-open`, or `org.freedesktop.FileManager1.ShowItems` over D-Bus to show it in its folder. The desktop shell needs no opener plugin nor a file scope.
- **Presentation:** `result_presented` on the bus. With the panel out of sight the overlay pill grows into the card; with it in sight, the panel shows the card. The expanded view is its own window. The overlay is bigger (340×600) and only the visible rectangle the page reports takes the mouse.
- **One anchor for everything that floats:** the overlay opens at a preset from Settings (`overlay_position`); the pill is no longer dragged.

## Consequences

- Showing a result costs no extra model call.
- A session that ignores the prompt rule shows nothing; the user can still ask Alfred.
- Untrusted documents render isolated: Markdown without raw HTML, HTML in a sandbox without same-origin, PDF drawn by pdf.js.
- Changing the position preset recreates the overlay window (Mutter ignores moves after the window maps).
- Result rows are capped at 30 per session; files are never deleted by Alfred.
