# Changelog

## [0.2.1](https://github.com/NavesDev/AlfredAgent/compare/v0.2.0...v0.2.1) (2026-11-15)


### Bug Fixes

* **release:** bump uv.lock and Cargo.lock with the version ([6bff388](https://github.com/NavesDev/AlfredAgent/commit/6bff388f3ef9f38ec3d6ccbaeeedfccdfe82f765))
* **release:** bump uv.lock and Cargo.lock with the version ([ee0a952](https://github.com/NavesDev/AlfredAgent/commit/ee0a95264490339ece89b3944fb1dd90f0e8cc1d))

## [0.2.0](https://github.com/NavesDev/AlfredAgent/compare/v0.1.0...v0.2.0) (2026-11-15)


### Features

* self-update from release tags ([06a5bc6](https://github.com/NavesDev/AlfredAgent/commit/06a5bc6b948d96badab8ce7b04638bfa47c5ce88))
* **server:** check for new release tags and start the self-update ([545facb](https://github.com/NavesDev/AlfredAgent/commit/545facb0cee8471d9911e58248e9fbdc8c784743))
* **update:** update script that installs a release tag and rolls back on failure ([c989a02](https://github.com/NavesDev/AlfredAgent/commit/c989a0291168a43f075f64a635cb7fb7c3544104))
* **web:** updates section and a control bar pill for new releases ([92d18cb](https://github.com/NavesDev/AlfredAgent/commit/92d18cbb9b02038001cab604b520e270263a4498))

## [0.1.0](https://github.com/NavesDev/AlfredAgent/releases/tag/v0.1.0) (2026-11-15)

First release: end-to-end voice, Claude Code sessions per project, web panel and desktop app.

### Voice

* Custom **"Alfred"** wake word (`alfred.onnx`, openWakeWord) with a live score meter for tuning
* Local speech: Whisper `large-v3-turbo` transcription and Kokoro pt-BR voice, loaded on the GPU on demand with CPU fallback
* Early transcription on short pauses, a spoken acknowledgement as soon as you stop talking, start and end chimes
* Speaks only the summary line; speech queue, spoken aliases and Whisper hotwords with session names

### Main agent

* Alfred runs on the Claude Code CLI, with a resumed daily conversation and a "new conversation" button
* Reads mail, calendar, the web, the browser, home files (never secrets) and GitHub issues, with no shell or edit tools ([ADR 0003](docs/adr/0003-main-agent-without-exec-tools.md))
* Says what it is doing while it thinks

### Sessions and projects

* Named sessions in parallel (general, implementation, system), each tied to a project and a workspace
* Workspaces mirror git worktrees; `iniciar_feature` opens branch, worktree and session in one go
* Voice delegation ("tell the backend to…"), per-session queue, generated portraits and short descriptions

### Panel and desktop app

* Glass panel (visionOS style): 3D orb that reacts to the voice, transcript with timings, sessions, projects and settings
* Plan usage and limits as rings, model and effort per agent kind, MCP toggles per session
* Tauri desktop app: custom title bar, tray and a floating pill with the orb and frequency bars while Alfred listens, thinks or speaks ([ADR 0012](docs/adr/0012-desktop-shell-tauri.md))
* Desktop menu launcher (`make install-launcher`)
