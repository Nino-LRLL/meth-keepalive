//! Meth — entry point.
//!
//! Usage:
//!   meth            → open the GUI (single instance)
//!   meth on         → keep the system awake (CLI)
//!   meth off        → restore normal behavior (CLI)
//!   meth status     → print current state
//!   meth autostart on|off → toggle autostart
//!
//! The GUI holds a singleton (named mutex on Windows, flock on Linux).
//! CLI commands act directly on the OS state — they are idempotent and
//! safe to run while the GUI is open.

use meth::app::App;
use meth::backends::active as backend;

fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let args: Vec<String> = std::env::args().skip(1).collect();

    match args.first().map(String::as_str) {
        Some("on") => cli_set(true),
        Some("off") => cli_set(false),
        Some("status") => cli_status(),
        Some("autostart") => cli_autostart(args.get(1)),
        Some("--version") | Some("-v") => {
            println!("Meth {}", meth::ui::VERSION);
        }
        _ => run_gui(),
    }
}

fn cli_set(on: bool) {
    // Route through App::set_on so the state is persisted (last_state)
    // and restored consistently by `meth status` / the GUI after a restart.
    let mut app = App::new();
    let ok = app.set_on(on);
    if on && !ok {
        eprintln!("METH ON refusé : le keep-alive est indisponible sur cette plateforme.");
        std::process::exit(1);
    }
    println!("{}", if on { "METH ON" } else { "METH OFF" });
}

fn cli_status() {
    let mut app = App::new();
    app.poll_status();
    println!("Meth {}", meth::ui::VERSION);
    println!("Platform: {}", app.platform);
    println!("State: {}", if app.on() { "ON" } else { "OFF" });
    println!(
        "Keep-alive: {}",
        if app.keepalive_available() {
            "available"
        } else {
            "UNAVAILABLE"
        }
    );
    let power = match app.power {
        meth::app::PowerState::OnAc => "AC",
        meth::app::PowerState::OnBattery => "battery",
        meth::app::PowerState::Unknown => "unknown",
    };
    let lid = match app.lid {
        meth::app::LidState::Open => "open",
        meth::app::LidState::Closed => "closed",
        meth::app::LidState::Unknown => "unknown",
    };
    println!("Power: {power}");
    println!("Lid: {lid}");
    println!("Autostart: {}", if app.autostart { "on" } else { "off" });
    println!("Config: {}", app.config_path.display());
}

fn cli_autostart(arg: Option<&String>) {
    match arg.map(String::as_str) {
        Some("on") => {
            let mut app = App::new();
            println!(
                "Autostart: {}",
                if app.apply_autostart(true) { "enabled" } else { "FAILED" }
            );
        }
        Some("off") => {
            let mut app = App::new();
            println!(
                "Autostart: {}",
                if app.apply_autostart(false) { "disabled" } else { "FAILED" }
            );
        }
        _ => {
            eprintln!("Usage: meth autostart on|off");
            std::process::exit(2);
        }
    }
}

fn run_gui() {
    if !backend::acquire_singleton() {
        eprintln!("Meth est déjà en cours d'exécution (instance unique).");
        std::process::exit(0);
    }
    let app = App::new();
    let options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_inner_size([380.0, 560.0])
            .with_min_inner_size([340.0, 480.0])
            .with_title(format!("Meth v{}", meth::ui::VERSION))
            .with_icon(app_icon()),
        ..Default::default()
    };
    let _ = eframe::run_native(
        "Meth",
        options,
        Box::new(move |_cc| Ok(Box::new(meth::ui::MethApp::new(app)))),
    );
}

/// Embed the app icon (generated: matte-metal disc on anthracite).
fn app_icon() -> eframe::egui::IconData {
    const S: u32 = 64;
    let mut rgba = Vec::with_capacity((S * S * 4) as usize);
    for y in 0..S {
        for x in 0..S {
            let dx = x as f32 - S as f32 / 2.0;
            let dy = y as f32 - S as f32 / 2.0;
            let in_disc = (dx * dx + dy * dy).sqrt() <= S as f32 * 0.4;
            if in_disc {
                rgba.extend_from_slice(&[0x48, 0x48, 0x4d, 255]);
            } else {
                rgba.extend_from_slice(&[0x1a, 0x1a, 0x1c, 255]);
            }
        }
    }
    eframe::egui::IconData {
        rgba,
        width: S,
        height: S,
    }
}
