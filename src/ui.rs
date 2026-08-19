//! Meth UI — a pure, sober matte-metal grey/black window (egui).
//!
//! The big disc is the ON/OFF control. It stays matte metal in BOTH
//! states (green reduced to a strict minimum: an 8px dot on top of the
//! disc + a thin ring + the "· ACTIF ·" label). Settings hold the
//! autostart toggle. Version is read from the crate, never hardcoded.

use std::time::Duration;

use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, Sense, Stroke, Vec2};

use crate::app::App;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

// Matte metal palette (grey-black, low contrast, pure).
const DISC_CENTER: Color32 = Color32::from_rgb(0x48, 0x48, 0x4d);
const DISC_EDGE: Color32 = Color32::from_rgb(0x15, 0x15, 0x17);
const BG_TOP: Color32 = Color32::from_rgb(0x1a, 0x1a, 0x1c);
const BG_BOTTOM: Color32 = Color32::from_rgb(0x0c, 0x0c, 0x0e);
const GREEN: Color32 = Color32::from_rgb(0x34, 0xd8, 0x68);
const TEXT: Color32 = Color32::from_rgb(0xcf, 0xcf, 0xd2);
const TEXT_DIM: Color32 = Color32::from_rgb(0x77, 0x77, 0x7d);

pub struct MethApp {
    pub app: App,
    shared: Option<std::sync::Arc<crate::app::SharedState>>,
    frame: u64,
}

impl MethApp {
    pub fn new(app: App) -> Self {
        let shared = crate::app::SharedState::new(app.on(), app.keepalive_available());
        MethApp {
            app,
            shared: Some(shared),
            frame: 0,
        }
    }

    pub fn shared(&self) -> Option<std::sync::Arc<crate::app::SharedState>> {
        self.shared.clone()
    }
}

impl eframe::App for MethApp {
    fn logic(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.frame += 1;
        self.app.maybe_poll();
        if let Some(shared) = &self.shared {
            shared.on.store(self.app.on(), std::sync::atomic::Ordering::Relaxed);
        }
        // Animate the pulse + refresh power/lid status periodically.
        ctx.request_repaint_after(Duration::from_millis(500));
    }

    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        // Matte metal background: soft anthracite → black vertical gradient.
        let full = ui.max_rect();
        let bg_painter = ui.painter();
        for i in 0..32 {
            let t = i as f32 / 31.0;
            let y0 = full.top() + full.height() * t;
            let y1 = full.top() + full.height() * (t + 1.0 / 32.0);
            let c = lerp_color(BG_TOP, BG_BOTTOM, t);
            bg_painter.rect_filled(
                Rect::from_min_max(Pos2::new(full.left(), y0), Pos2::new(full.right(), y1)),
                0.0,
                c,
            );
        }

        ui.vertical_centered(|ui| {
            ui.add_space(full.height() * 0.05);
            ui.label(
                egui::RichText::new("Meth")
                    .font(FontId::proportional(34.0))
                    .color(TEXT),
            );
            ui.add_space(4.0);
            ui.label(
                egui::RichText::new("Your AI works. The PC stays awake.")
                    .font(FontId::proportional(13.0))
                    .color(TEXT_DIM),
            );
            ui.add_space(full.height() * 0.03);
        });

        // ---- The disc (ON/OFF) -------------------------------------------
        let disc_d = (full.height() * 0.52).clamp(150.0, 230.0);
        let center = Pos2::new(full.center().x, full.top() + full.height() * 0.52);
        let disc_rect = Rect::from_center_size(center, Vec2::splat(disc_d));

        let response = ui.allocate_rect(disc_rect, Sense::click());
        let on = self.app.on();
        let pulse = ((self.frame as f32) * 0.06).sin() * 0.5 + 0.5; // 0..1

        // Outer ring (machined, thin) + disc body (matte metal).
        let painter = ui.painter();
        painter.circle_stroke(
            center,
            disc_d / 2.0,
            Stroke::new(1.5, Color32::from_rgb(0x5a, 0x5a, 0x60)),
        );
        draw_metal_disc(painter, center, disc_d / 2.0);
        // Top light edge (2px) — the only "shine".
        painter.circle_stroke(
            center,
            disc_d / 2.0 - 3.0,
            Stroke::new(2.0, Color32::from_rgb(0x6a, 0x6a, 0x70)),
        );
        // Ring accent — green only in ON, very thin.
        let ring_color = if on {
            lerp_color(GREEN, Color32::from_rgb(0x1e, 0x6a, 0x38), 0.5)
        } else {
            Color32::from_rgb(0x33, 0x33, 0x37)
        };
        painter.circle_stroke(
            center,
            disc_d / 2.0 - 7.0,
            Stroke::new(if on { 2.0 } else { 1.0 }, ring_color),
        );

        // 8px status dot on top of the disc + label.
        let dot_y = center.y - disc_d / 2.0 + 22.0;
        let dot_color = if on {
            let glow = 0.6 + 0.4 * pulse;
            Color32::from_rgb(
                (GREEN.r() as f32 * glow) as u8,
                (GREEN.g() as f32 * glow) as u8,
                (GREEN.b() as f32 * glow) as u8,
            )
        } else {
            Color32::from_rgb(0x4a, 0x4a, 0x50)
        };
        painter.circle_filled(Pos2::new(center.x, dot_y), 4.0, dot_color);
        painter.text(
            Pos2::new(center.x, dot_y + 16.0),
            Align2::CENTER_TOP,
            if on { "· ACTIF ·" } else { "· NORMAL ·" },
            FontId::proportional(13.0),
            if on { GREEN } else { TEXT_DIM },
        );

        if response.clicked() {
            self.app.set_on(!on);
        }

        // ---- Footer: settings + version -----------------------------------
        ui.add_space(full.height() * 0.08);
        ui.horizontal_centered(|ui| {
            let mut autostart = self.app.autostart;
            if ui
                .checkbox(&mut autostart, "Démarrer Meth au démarrage")
                .on_hover_text("Lancer Meth automatiquement à la connexion")
                .changed()
            {
                self.app.apply_autostart(autostart);
            }
        });
        ui.add_space(4.0);
        ui.vertical_centered(|ui| {
            let status = if !self.app.keepalive_available() {
                "keep-alive indisponible sur cette plateforme".to_string()
            } else {
                let power = match self.app.power {
                    crate::app::PowerState::OnAc => "secteur",
                    crate::app::PowerState::OnBattery => "batterie",
                    crate::app::PowerState::Unknown => "alimentation inconnue",
                };
                let lid = match self.app.lid {
                    crate::app::LidState::Open => "capot ouvert",
                    crate::app::LidState::Closed => "capot fermé",
                    crate::app::LidState::Unknown => "capot inconnu",
                };
                format!("{power} · {lid}")
            };
            ui.label(
                egui::RichText::new(status)
                    .font(FontId::proportional(11.0))
                    .color(TEXT_DIM),
            );
            ui.add_space(2.0);
            ui.label(
                egui::RichText::new(format!(
                    "Meth v{VERSION} — {platform}",
                    platform = self.app.platform
                ))
                .font(FontId::proportional(10.0))
                .color(TEXT_DIM),
            );
        });
    }

    #[cfg(feature = "glow")]
    fn on_exit(&mut self, _gl: Option<&eframe::glow::Context>) {
        self.app.shutdown();
    }

    #[cfg(not(feature = "glow"))]
    fn on_exit(&mut self) {
        self.app.shutdown();
    }
}

// ---------------------------------------------------------------------------
// Matte metal disc — radial gradient approximated by concentric rings.
// ---------------------------------------------------------------------------

fn draw_metal_disc(painter: &egui::Painter, center: Pos2, radius: f32) {
    const RINGS: usize = 40;
    for i in 0..RINGS {
        let t = i as f32 / (RINGS as f32 - 1.0); // 0 = edge → 1 = center
        let r = radius * (1.0 - t);
        let c = lerp_color(DISC_EDGE, DISC_CENTER, t * t);
        painter.circle_filled(center, r, c);
    }
}

fn lerp_color(a: Color32, b: Color32, t: f32) -> Color32 {
    let t = t.clamp(0.0, 1.0);
    Color32::from_rgb(
        (a.r() as f32 + (b.r() as f32 - a.r() as f32) * t) as u8,
        (a.g() as f32 + (b.g() as f32 - a.g() as f32) * t) as u8,
        (a.b() as f32 + (b.b() as f32 - a.b() as f32) * t) as u8,
    )
}

/// Minimal API used by the tray to keep the code together.
pub fn make_shared(on: bool, available: bool) -> std::sync::Arc<crate::app::SharedState> {
    crate::app::SharedState::new(on, available)
}
