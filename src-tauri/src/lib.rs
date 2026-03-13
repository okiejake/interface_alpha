use std::process::{Child, Command};
use std::sync::Mutex;

struct SidecarState(Mutex<Option<Child>>);

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![greet])
        .setup(|app| {
            let project_root = std::env::current_dir()?;
            let python = project_root.join("sidecar/.venv/bin/python");
            let script = project_root.join("sidecar/audio_engine.py");

            match Command::new(&python)
                .arg("-u")
                .arg(&script)
                .env("PYTHONUNBUFFERED", "1")
                .spawn()
            {
                Ok(child) => {
                    eprintln!("[sidecar] audio engine started (pid {})", child.id());
                    app.manage(SidecarState(Mutex::new(Some(child))));
                }
                Err(e) => {
                    eprintln!("[sidecar] failed to start audio engine: {e}");
                    app.manage(SidecarState(Mutex::new(None)));
                }
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.app_handle().state::<SidecarState>();
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(mut child) = guard.take() {
                        let _ = child.kill();
                        eprintln!("[sidecar] audio engine stopped");
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
