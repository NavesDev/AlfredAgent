# Changelog

## [0.3.0](https://github.com/NavesDev/AlfredAgent/compare/v0.2.1...v0.3.0) (2026-11-17)


### Features

* **desktop:** anchor the overlay to a preset, take clicks only on the card and open the result viewer ([0d7909b](https://github.com/NavesDev/AlfredAgent/commit/0d7909b76be6b535aab8d71a1c6fc8e7cfe6dd4c))
* **desktop:** render the app and tray icon from the real Strands orb ([23336e5](https://github.com/NavesDev/AlfredAgent/commit/23336e5e2afaac7976106d866f81ce65c7cbb151))
* present session results in a corner card and an expanded view ([c987f7a](https://github.com/NavesDev/AlfredAgent/commit/c987f7a5995bb45666bb66a4f7192f78e045057d))
* **server:** add result table and model (schema v5) ([b7d4907](https://github.com/NavesDev/AlfredAgent/commit/b7d49076d7649919ea79468dde24de4e18b1a5e2))
* **server:** extract readable() file guard from path_guard ([f1cf9eb](https://github.com/NavesDev/AlfredAgent/commit/f1cf9ebc5df69f44b06572e800304e318e3cd10a))
* **server:** let Alfred present several files, always in the expanded view ([2a08b4b](https://github.com/NavesDev/AlfredAgent/commit/2a08b4bca74efa503097986fd59c102e37573bac))
* **server:** let Alfred show and close results, and tell sessions how to hand them over ([91a5dbd](https://github.com/NavesDev/AlfredAgent/commit/91a5dbd09ee1f653cc58b94c6a8a8d6839b72e65))
* **server:** open a result's file or its folder for the desktop ([f130433](https://github.com/NavesDev/AlfredAgent/commit/f130433bd69e30e4543998de4bebca3ae42fbc32))
* **server:** parse APRESENTAR and GUARDAR result lines ([d300deb](https://github.com/NavesDev/AlfredAgent/commit/d300debfd3cdb50c6c5f6dbe176e841a386bec68))
* **server:** read HEAD and numstat for change reports ([24d0894](https://github.com/NavesDev/AlfredAgent/commit/24d089410b00b190e8f02dd01e1f2e3dec639ea1))
* **server:** record a session's result when its task finishes ([9b9804d](https://github.com/NavesDev/AlfredAgent/commit/9b9804db61a6fd116d372202c4401c8c418d148f))
* **server:** record, present and serve results under the read guard ([601ac1a](https://github.com/NavesDev/AlfredAgent/commit/601ac1a1a38586ea4798a0cb7e170f301e291ad7))
* **server:** serve result files isolated, without origin or network ([91eaf8f](https://github.com/NavesDev/AlfredAgent/commit/91eaf8f2165665e382551198266d7fc21926b317))
* **server:** serve results to this computer only, and add the overlay position setting ([dd52ecb](https://github.com/NavesDev/AlfredAgent/commit/dd52ecb1027109436fd2d6acb671593c9f711648))
* **web:** add the /viewer page for the expanded result window ([9a4fc40](https://github.com/NavesDev/AlfredAgent/commit/9a4fc407e5cad8ca5fc60201c110c68246500798))
* **web:** add the results feature: card, expanded view, history and their hooks ([1da82a8](https://github.com/NavesDev/AlfredAgent/commit/1da82a81c00ddba0f323a27801ddaf662ff12ee2))
* **web:** choose where the pill floats in Settings → Geral ([53ba165](https://github.com/NavesDev/AlfredAgent/commit/53ba16548d6de40e29d77247fb3d4e5a766618fd))
* **web:** render Markdown and PDF properly and redesign the expanded viewer ([8ad778d](https://github.com/NavesDev/AlfredAgent/commit/8ad778df49668676b617ccd36341b1cd22f2dc95))
* **web:** show the result card and a session's result history in the panel ([0544708](https://github.com/NavesDev/AlfredAgent/commit/05447087526b4d967703e4041905f57815301bdf))
* **web:** turn the overlay pill into the result card, anchored to the preset ([3aa4811](https://github.com/NavesDev/AlfredAgent/commit/3aa4811a22218a1b1ad7662af833ca8a9cf806b3))
* **web:** write the Alfred name in bundled Newsreader italic ([d8eec3d](https://github.com/NavesDev/AlfredAgent/commit/d8eec3d86e745b7fb7eead342edf18bc45882e05))


### Bug Fixes

* **server:** keep underscores inside result paths ([66e984f](https://github.com/NavesDev/AlfredAgent/commit/66e984fe185d197b5cffaa50f0e2e59f781078b5))
* **viewer:** smooth scrolling and an overlay scrollbar that fades in ([7a3084d](https://github.com/NavesDev/AlfredAgent/commit/7a3084d78ae15a2c9190533000c70a660d2619e4))
* **web:** hide the scrollbar under the viewer's file strip ([e9458fe](https://github.com/NavesDev/AlfredAgent/commit/e9458fe4cad6233fd8cffb5acefe8b4597d55661))
* **web:** make the overlay card clickable, leave on its own and fade in and out ([e2821cc](https://github.com/NavesDev/AlfredAgent/commit/e2821cc8c58129b3cecb540a52bc725bd13975fc))

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
