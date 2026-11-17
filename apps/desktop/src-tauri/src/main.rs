// Alfred desktop shell (ADR 0012, 0014): the panel window, the voice overlay, the result viewer
// and the tray. No business logic here: every window loads apps/web, which talks to the server.

use std::{
    sync::{
        atomic::{AtomicBool, Ordering},
        Mutex,
    },
    thread,
    time::Duration,
};

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, Monitor, WebviewUrl, WebviewWindow, WebviewWindowBuilder, WindowEvent,
};

/// Overlay window size in logical pixels: room for the pill and the result card above or
/// below it. Transparent; only the visible rectangle the page reports takes the mouse.
const OVERLAY_SIZE: (f64, f64) = (340.0, 600.0);
/// Gap between what floats and the edge of the work area.
const EDGE_GAP: f64 = 8.0;
/// Share of the monitor the expanded result view takes, centered.
const VIEWER_SHARE: f64 = 0.7;
/// How often the overlay checks whether the cursor is over the visible card.
const CURSOR_POLL: Duration = Duration::from_millis(40);
/// Where everything that floats anchors (Settings → Geral). Mirrors OverlayPosition on the
/// server; the first one is the default.
const PRESETS: [&str; 6] = [
    "top_right",
    "top_center",
    "top_left",
    "bottom_right",
    "bottom_center",
    "bottom_left",
];

/// The preset the overlay was opened at.
static PRESET: Mutex<&str> = Mutex::new(PRESETS[0]);
/// The rectangle of the overlay that takes the mouse (logical, inside the window), if any.
static HIT_RECT: Mutex<Option<Rect>> = Mutex::new(None);
/// Set while the overlay is being rebuilt at a new preset.
static REBUILDING: AtomicBool = AtomicBool::new(false);

/// x, y, width, height in logical pixels.
type Rect = (f64, f64, f64, f64);

fn panel(app: &AppHandle) -> Option<WebviewWindow> {
    app.get_webview_window("main")
}

fn show_panel(app: &AppHandle) {
    if let Some(w) = panel(app) {
        let _ = w.unminimize();
        let _ = w.show();
        let _ = w.set_focus();
    }
}

fn toggle_panel(app: &AppHandle) {
    if let Some(w) = panel(app) {
        let in_sight = w.is_visible().unwrap_or(false) && !w.is_minimized().unwrap_or(false);
        if in_sight {
            let _ = w.hide();
        } else {
            show_panel(app);
        }
    }
}

fn preset_now() -> &'static str {
    *PRESET.lock().unwrap_or_else(|e| e.into_inner())
}

/// "bottom_center" -> ("bottom", "center"); None for anything that is not a preset.
fn split(preset: &str) -> Option<(&'static str, &'static str)> {
    let known = PRESETS.iter().find(|p| **p == preset)?;
    known.split_once('_')
}

/// The top-left of a `size` box anchored at (`edge`, `align`) inside `area`, EDGE_GAP away
/// from the edges it touches.
fn anchored(area: Rect, size: (f64, f64), edge: &str, align: &str) -> (f64, f64) {
    let (ax, ay, aw, ah) = area;
    let (w, h) = size;
    let x = match align {
        "left" => ax + EDGE_GAP,
        "center" => ax + (aw - w) / 2.0,
        _ => ax + aw - EDGE_GAP - w,
    };
    let y = if edge == "top" {
        ay + EDGE_GAP
    } else {
        ay + ah - EDGE_GAP - h
    };
    (x, y)
}

/// A monitor's work area (screen minus top bar and docks), logical pixels.
fn work_area(m: &Monitor) -> Rect {
    let scale = m.scale_factor();
    let (p, s) = (m.work_area().position, m.work_area().size);
    let (p, s) = (p.to_logical::<f64>(scale), s.to_logical::<f64>(scale));
    (p.x, p.y, s.width, s.height)
}

/// The voice overlay: transparent, always on top, on every workspace, never focused. Clicks
/// pass through except over the rectangle the page reports (`set_hit_rect`).
/// Built here rather than in tauri.conf.json so it opens at its preset already; GNOME ignores a
/// move made after the window maps.
fn create_overlay(app: &AppHandle) -> tauri::Result<()> {
    let (edge, align) = split(preset_now()).unwrap_or(("top", "right"));
    let (x, y) = app
        .primary_monitor()?
        .map(|m| anchored(work_area(&m), OVERLAY_SIZE, edge, align))
        .unwrap_or((0.0, 0.0));
    let (width, height) = OVERLAY_SIZE;
    let overlay = WebviewWindowBuilder::new(app, "overlay", WebviewUrl::App("overlay".into()))
        .title("Alfred voz")
        .inner_size(width, height)
        .position(x, y)
        .transparent(true)
        .decorations(false)
        .always_on_top(true)
        .visible_on_all_workspaces(true)
        .skip_taskbar(true)
        .resizable(false)
        .shadow(false)
        .focused(false)
        .focusable(false)
        .build()?;
    overlay.set_ignore_cursor_events(true)
}

/// The overlay's content origin in logical pixels (the inner position; the outer one sits
/// 40px off on GTK).
fn overlay_origin(overlay: &WebviewWindow) -> Option<(f64, f64)> {
    let scale = overlay.scale_factor().ok()?;
    let p = overlay.inner_position().ok()?.to_logical::<f64>(scale);
    Some((p.x, p.y))
}

fn cursor_over_hit_rect(app: &AppHandle, overlay: &WebviewWindow) -> bool {
    let Some((rx, ry, rw, rh)) = *HIT_RECT.lock().unwrap_or_else(|e| e.into_inner()) else {
        return false;
    };
    let (Ok(cursor), Ok(scale), Some((ox, oy))) = (
        app.cursor_position(),
        overlay.scale_factor(),
        overlay_origin(overlay),
    ) else {
        return false;
    };
    let c = cursor.to_logical::<f64>(scale);
    let (x, y) = (ox + rx, oy + ry);
    c.x >= x && c.y >= y && c.x < x + rw && c.y < y + rh
}

/// The overlay takes the mouse only while the cursor is over the visible card; everywhere
/// else clicks go through to the windows below.
fn watch_cursor(app: AppHandle) {
    thread::spawn(move || {
        let mut grabbing = false;
        loop {
            thread::sleep(CURSOR_POLL);
            let Some(overlay) = app.get_webview_window("overlay") else {
                grabbing = false;
                continue;
            };
            let want = cursor_over_hit_rect(&app, &overlay);
            if want != grabbing && overlay.set_ignore_cursor_events(!want).is_ok() {
                grabbing = want;
            }
        }
    });
}

/// The overlay page reports what it shows that takes the mouse: the card, or nothing.
#[tauri::command]
fn set_hit_rect(rect: Option<[f64; 4]>) {
    *HIT_RECT.lock().unwrap_or_else(|e| e.into_inner()) = rect.map(|[x, y, w, h]| (x, y, w, h));
}

/// Where the overlay is anchored, so the page lines the pill and the card up with it.
#[tauri::command]
fn overlay_anchor() -> serde_json::Value {
    let preset = preset_now();
    let (edge, align) = split(preset).unwrap_or(("top", "right"));
    serde_json::json!({ "preset": preset, "edge": edge, "align": align })
}

/// Moves everything that floats to another preset by building the overlay again there
/// (Mutter ignores a move after the window maps). An unknown preset changes nothing.
#[tauri::command]
fn set_overlay_position(app: AppHandle, preset: String) {
    let Some(known) = PRESETS.iter().find(|p| **p == preset) else {
        eprintln!("alfred: unknown overlay position {preset:?}, ignored");
        return;
    };
    if *known == preset_now() || REBUILDING.swap(true, Ordering::SeqCst) {
        return;
    }
    *PRESET.lock().unwrap_or_else(|e| e.into_inner()) = known;
    let handle = app.clone();
    // The overlay itself may be the caller: rebuild after this command returns.
    let _ = app.run_on_main_thread(move || {
        *HIT_RECT.lock().unwrap_or_else(|e| e.into_inner()) = None;
        if let Some(old) = handle.get_webview_window("overlay") {
            let _ = old.destroy();
        }
        if let Err(e) = create_overlay(&handle) {
            eprintln!("alfred: could not rebuild the overlay: {e}");
        }
        REBUILDING.store(false, Ordering::SeqCst);
    });
}

/// Kinetic wheel scrolling: WebKitGTK jumps a whole step per wheel notch unless it is on.
fn smooth_scrolling(window: &WebviewWindow) {
    #[cfg(target_os = "linux")]
    let _ = window.with_webview(|webview| {
        use webkit2gtk::{SettingsExt, WebViewExt};
        if let Some(settings) = webview.inner().settings() {
            settings.set_enable_smooth_scrolling(true);
        }
    });
    #[cfg(not(target_os = "linux"))]
    let _ = window;
}

/// The expanded result view: a glass window over 70% of the overlay's monitor, centered,
/// built in place. Opened again, it shows the new result and takes focus.
#[tauri::command]
async fn open_viewer(app: AppHandle, result_id: u32, index: u32) -> Result<(), String> {
    let route = format!("viewer?id={result_id}&i={index}");
    if let Some(viewer) = app.get_webview_window("viewer") {
        let mut url = viewer.url().map_err(|e| e.to_string())?;
        url.set_path("/viewer");
        url.set_query(Some(&format!("id={result_id}&i={index}")));
        viewer.navigate(url).map_err(|e| e.to_string())?;
        let _ = viewer.show();
        return viewer.set_focus().map_err(|e| e.to_string());
    }
    let monitor = app
        .get_webview_window("overlay")
        .and_then(|o| o.current_monitor().ok().flatten())
        .or(app.primary_monitor().map_err(|e| e.to_string())?);
    let area = monitor
        .as_ref()
        .map(work_area)
        .unwrap_or((0.0, 0.0, 1280.0, 800.0));
    let size = (area.2 * VIEWER_SHARE, area.3 * VIEWER_SHARE);
    let (x, y) = (
        area.0 + (area.2 - size.0) / 2.0,
        area.1 + (area.3 - size.1) / 2.0,
    );
    WebviewWindowBuilder::new(&app, "viewer", WebviewUrl::App(route.into()))
        .title("Alfred")
        .inner_size(size.0, size.1)
        .position(x, y)
        .transparent(true)
        .decorations(false)
        .always_on_top(true)
        .skip_taskbar(true)
        .shadow(false)
        .focused(true)
        .build()
        .map(|viewer| smooth_scrolling(&viewer))
        .map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            show_panel(app)
        }))
        .setup(|app| {
            if let Some(w) = panel(app.handle()) {
                smooth_scrolling(&w);
            }
            create_overlay(app.handle())?;
            watch_cursor(app.handle().clone());

            let open = MenuItem::with_id(app, "open", "Abrir Alfred", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Sair", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &quit])?;
            TrayIconBuilder::with_id("alfred")
                .icon(app.default_window_icon().cloned().expect("bundle icon"))
                .tooltip("Alfred")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => show_panel(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        toggle_panel(tray.app_handle());
                    }
                })
                .build(app)?;
            Ok(())
        })
        .on_window_event(|window, event| {
            // Closing the panel only hides it in the tray; "Sair" in the tray menu quits.
            if let WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {
                    api.prevent_close();
                    let _ = window.hide();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            set_hit_rect,
            overlay_anchor,
            set_overlay_position,
            open_viewer
        ])
        .run(tauri::generate_context!())
        .expect("error while running the Alfred desktop app");
}

#[cfg(test)]
mod tests {
    use super::*;

    const AREA: Rect = (0.0, 32.0, 1920.0, 1048.0);

    #[test]
    fn presets_anchor_at_the_edges_with_a_gap() {
        let size = (340.0, 600.0);
        assert_eq!(anchored(AREA, size, "top", "right"), (1572.0, 40.0));
        assert_eq!(anchored(AREA, size, "top", "left"), (8.0, 40.0));
        assert_eq!(anchored(AREA, size, "bottom", "center"), (790.0, 472.0));
    }

    #[test]
    fn only_known_presets_split() {
        assert_eq!(split("bottom_center"), Some(("bottom", "center")));
        assert_eq!(split("top_right"), Some(("top", "right")));
        assert_eq!(split("meio"), None);
        assert_eq!(split(""), None);
    }
}
