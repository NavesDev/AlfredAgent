// Alfred desktop shell (ADR 0012): the panel window, the voice overlay and the tray.
// No business logic here: both windows load apps/web, which talks to the server.

use std::{
    fs,
    path::PathBuf,
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
    App, AppHandle, LogicalPosition, Manager, Monitor, WebviewUrl, WebviewWindow,
    WebviewWindowBuilder, WindowEvent,
};

/// Overlay window size in logical pixels; GTK will not make it smaller than 200x200.
const OVERLAY_SIZE: (f64, f64) = (200.0, 200.0);
/// The voice pill (same size as VoicePill.tsx), in logical pixels.
const PILL_SIZE: (f64, f64) = (148.0, 48.0);
/// Gap between the pill and the screen edge in its default top-right spot.
const EDGE_GAP: f64 = 8.0;
/// Where the pill was last dragged to, inside the app's config dir.
const PILL_POSITION_FILE: &str = "overlay-position.json";
/// How often the overlay checks whether the cursor is over the pill.
const CURSOR_POLL: Duration = Duration::from_millis(40);

/// Set by the overlay page while the pill is on screen.
static PILL_SHOWN: AtomicBool = AtomicBool::new(false);
/// Where the pill sits inside the overlay window (logical), fixed when the window opens.
static PILL_OFFSET: Mutex<(f64, f64)> = Mutex::new((0.0, 0.0));

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

fn pill_position_file(app: &AppHandle) -> Option<PathBuf> {
    let dir = app.path().app_config_dir().ok()?;
    Some(dir.join(PILL_POSITION_FILE))
}

fn pill_offset_now() -> (f64, f64) {
    *PILL_OFFSET.lock().unwrap_or_else(|e| e.into_inner())
}

/// The work area (screen minus top bar and docks) of the monitor under a point, or of the
/// first monitor when the point is off every screen. Logical pixels.
fn work_area_at(monitors: &[Monitor], x: f64, y: f64) -> Option<Rect> {
    let area = |m: &Monitor| {
        let scale = m.scale_factor();
        let (p, s) = (m.work_area().position, m.work_area().size);
        let (p, s) = (p.to_logical::<f64>(scale), s.to_logical::<f64>(scale));
        (p.x, p.y, s.width, s.height)
    };
    let contains = |a: &Rect| x >= a.0 && y >= a.1 && x < a.0 + a.2 && y < a.1 + a.3;
    let areas: Vec<Rect> = monitors.iter().map(area).collect();
    areas
        .iter()
        .copied()
        .find(contains)
        .or(areas.first().copied())
}

/// The top-left that keeps `rect` whole inside `area`.
fn clamp_into(rect: Rect, area: Rect) -> (f64, f64) {
    let (x, y, w, h) = rect;
    let (ax, ay, aw, ah) = area;
    (
        x.clamp(ax, (ax + aw - w).max(ax)),
        y.clamp(ay, (ay + ah - h).max(ay)),
    )
}

/// The pill clamped whole into the work area under its centre: it can never leave the screen.
fn pill_on_screen(monitors: &[Monitor], x: f64, y: f64) -> (f64, f64) {
    let (w, h) = PILL_SIZE;
    match work_area_at(monitors, x + w / 2.0, y + h / 2.0) {
        Some(area) => clamp_into((x, y, w, h), area),
        None => (x, y),
    }
}

fn saved_pill(app: &App) -> Option<(f64, f64)> {
    let text = fs::read_to_string(pill_position_file(app.handle())?).ok()?;
    let [x, y]: [f64; 2] = serde_json::from_str(&text).ok()?;
    Some((x, y))
}

fn save_pill(app: &AppHandle, (x, y): (f64, f64)) {
    let Some(file) = pill_position_file(app) else {
        return;
    };
    if let Some(dir) = file.parent() {
        let _ = fs::create_dir_all(dir);
    }
    let _ = fs::write(file, format!("[{x}, {y}]"));
}

/// Where the overlay opens (logical) and where the pill sits inside it. The pill goes back
/// where it was left (default: top-right, near the tray icons). The window itself must open
/// whole on screen (Mutter moves it otherwise), so near an edge the pill shifts inside it.
fn overlay_layout(app: &App) -> tauri::Result<((f64, f64), (f64, f64))> {
    let monitors = app.available_monitors()?;
    let (pw, ph) = PILL_SIZE;
    let (ww, wh) = OVERLAY_SIZE;
    let default = app
        .primary_monitor()?
        .and_then(|m| {
            let p = m.work_area().position.to_logical::<f64>(m.scale_factor());
            let s = m.work_area().size.to_logical::<f64>(m.scale_factor());
            Some((p.x + s.width - EDGE_GAP - pw, p.y + EDGE_GAP))
        })
        .unwrap_or((0.0, 0.0));
    let (px, py) = saved_pill(app).unwrap_or(default);
    let (px, py) = pill_on_screen(&monitors, px, py);
    let Some(area) = work_area_at(&monitors, px + pw / 2.0, py + ph / 2.0) else {
        return Ok(((px, py), (0.0, 0.0)));
    };
    let preferred = (px - (ww - EDGE_GAP - pw), py - EDGE_GAP);
    let (wx, wy) = clamp_into((preferred.0, preferred.1, ww, wh), area);
    Ok(((wx, wy), (px - wx, py - wy)))
}

/// The page asks where to draw the pill inside the window.
#[tauri::command]
fn pill_offset() -> (f64, f64) {
    pill_offset_now()
}

/// Called by the overlay page when the pill appears or goes away.
#[tauri::command]
fn set_pill_shown(shown: bool) {
    PILL_SHOWN.store(shown, Ordering::Relaxed);
}

/// The overlay's content origin in logical pixels. On GTK the outer position (and the one
/// `Moved` carries) sits 40px off; the inner one is what `set_position` places.
fn overlay_origin(overlay: &WebviewWindow) -> Option<(f64, f64)> {
    let scale = overlay.scale_factor().ok()?;
    let p = overlay.inner_position().ok()?.to_logical::<f64>(scale);
    Some((p.x, p.y))
}

fn cursor_over_pill(app: &AppHandle, overlay: &WebviewWindow) -> bool {
    let (Ok(cursor), Ok(scale), Some((ox, oy))) = (
        app.cursor_position(),
        overlay.scale_factor(),
        overlay_origin(overlay),
    ) else {
        return false;
    };
    let (dx, dy) = pill_offset_now();
    let (w, h) = PILL_SIZE;
    let c = cursor.to_logical::<f64>(scale);
    let (x, y) = (ox + dx, oy + dy);
    c.x >= x && c.y >= y && c.x < x + w && c.y < y + h
}

/// The overlay takes the mouse only while the cursor is over the visible pill (to drag it);
/// everywhere else, and while the pill is hidden, clicks go through to the windows below.
fn watch_cursor(app: AppHandle) {
    thread::spawn(move || {
        let mut grabbing = false;
        loop {
            thread::sleep(CURSOR_POLL);
            let Some(overlay) = app.get_webview_window("overlay") else {
                continue;
            };
            let want = PILL_SHOWN.load(Ordering::Relaxed) && cursor_over_pill(&app, &overlay);
            if want != grabbing && overlay.set_ignore_cursor_events(!want).is_ok() {
                grabbing = want;
            }
        }
    });
}

/// The pill was dragged: pull it back if it left the screen, and remember the spot.
fn on_overlay_moved(overlay: &tauri::Window) {
    let Some(webview) = overlay.app_handle().get_webview_window("overlay") else {
        return;
    };
    let Some((ox, oy)) = overlay_origin(&webview) else {
        return;
    };
    let (dx, dy) = pill_offset_now();
    let monitors = overlay.available_monitors().unwrap_or_default();
    let (px, py) = pill_on_screen(&monitors, ox + dx, oy + dy);
    if (px, py) != (ox + dx, oy + dy) {
        let _ = overlay.set_position(LogicalPosition::new(px - dx, py - dy));
    }
    save_pill(overlay.app_handle(), (px, py));
}

/// The voice overlay: transparent, always on top, on every workspace; clicks pass through
/// except over the visible pill (`watch_cursor`), which can be dragged (`on_overlay_moved`).
/// Built here rather than in tauri.conf.json so the position is set before the window maps;
/// GNOME ignores a move made afterwards.
fn create_overlay(app: &App) -> tauri::Result<()> {
    let ((x, y), offset) = overlay_layout(app)?;
    *PILL_OFFSET.lock().unwrap_or_else(|e| e.into_inner()) = offset;
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
        .build()?;
    overlay.set_ignore_cursor_events(true)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            show_panel(app)
        }))
        .setup(|app| {
            create_overlay(app)?;
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
        .on_window_event(|window, event| match event {
            // Closing the panel only hides it in the tray; "Sair" in the tray menu quits.
            WindowEvent::CloseRequested { api, .. } if window.label() == "main" => {
                api.prevent_close();
                let _ = window.hide();
            }
            // The pill was dragged: keep it on screen and open it there next time.
            WindowEvent::Moved(_) if window.label() == "overlay" => on_overlay_moved(window),
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![pill_offset, set_pill_shown])
        .run(tauri::generate_context!())
        .expect("error while running the Alfred desktop app");
}
