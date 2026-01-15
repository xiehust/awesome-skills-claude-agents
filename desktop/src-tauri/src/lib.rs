use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;
use tokio::sync::Mutex;

// Backend state management
struct BackendState {
    child: Option<CommandChild>,
    port: u16,
    running: bool,
}

impl Default for BackendState {
    fn default() -> Self {
        Self {
            child: None,
            port: 8000,
            running: false,
        }
    }
}

type SharedBackendState = Arc<Mutex<BackendState>>;

#[derive(Serialize, Deserialize)]
pub struct BackendStatus {
    running: bool,
    port: u16,
}

#[derive(Serialize, Deserialize)]
pub struct CLIStatus {
    installed: bool,
    path: Option<String>,
    version: Option<String>,
    node_installed: bool,
    npm_installed: bool,
}

// Start the Python backend sidecar
#[tauri::command]
async fn start_backend(
    app: tauri::AppHandle,
    state: tauri::State<'_, SharedBackendState>,
) -> Result<u16, String> {
    // Check if already running (short lock)
    {
        let backend = state.lock().await;
        if backend.running {
            return Ok(backend.port);
        }
    }

    // Find an available port
    let port = portpicker::pick_unused_port().unwrap_or(8000);

    // Start the sidecar
    let sidecar = app
        .shell()
        .sidecar("python-backend")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?
        .args(["--port", &port.to_string()]);

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

    // Store the child process (short lock)
    {
        let mut backend = state.lock().await;
        backend.child = Some(child);
        backend.port = port;
        backend.running = true;
    }

    // Spawn a task to handle sidecar output
    let app_handle = app.clone();
    let state_clone = state.inner().clone();
    tauri::async_runtime::spawn(async move {
        use tauri_plugin_shell::process::CommandEvent;
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let _ = app_handle.emit("backend-log", String::from_utf8_lossy(&line).to_string());
                }
                CommandEvent::Stderr(line) => {
                    let _ = app_handle.emit("backend-error", String::from_utf8_lossy(&line).to_string());
                }
                CommandEvent::Terminated(payload) => {
                    let _ = app_handle.emit("backend-terminated", payload.code);
                    // Update state when backend terminates
                    let mut backend = state_clone.lock().await;
                    backend.running = false;
                    backend.child = None;
                    break;
                }
                _ => {}
            }
        }
    });

    // Wait a bit for the backend to start
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

    Ok(port)
}

// Stop the Python backend
#[tauri::command]
async fn stop_backend(state: tauri::State<'_, SharedBackendState>) -> Result<(), String> {
    let mut backend = state.lock().await;

    if let Some(child) = backend.child.take() {
        child.kill().map_err(|e| format!("Failed to kill backend: {}", e))?;
    }

    backend.running = false;
    Ok(())
}

// Get backend status
#[tauri::command]
async fn get_backend_status(state: tauri::State<'_, SharedBackendState>) -> Result<BackendStatus, String> {
    let backend = state.lock().await;
    Ok(BackendStatus {
        running: backend.running,
        port: backend.port,
    })
}

// Get backend port
#[tauri::command]
async fn get_backend_port(state: tauri::State<'_, SharedBackendState>) -> Result<u16, String> {
    let backend = state.lock().await;
    Ok(backend.port)
}

// Check Claude Code CLI status
#[tauri::command]
async fn check_claude_cli() -> Result<CLIStatus, String> {
    use std::process::Command;

    // Check if claude is installed
    let claude_check = Command::new("which")
        .arg("claude")
        .output();

    let (installed, path) = match claude_check {
        Ok(output) if output.status.success() => {
            let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
            (true, Some(path))
        }
        _ => (false, None),
    };

    // Get version if installed
    let version = if installed {
        Command::new("claude")
            .arg("--version")
            .output()
            .ok()
            .and_then(|o| {
                if o.status.success() {
                    Some(String::from_utf8_lossy(&o.stdout).trim().to_string())
                } else {
                    None
                }
            })
    } else {
        None
    };

    // Check Node.js
    let node_installed = Command::new("which")
        .arg("node")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);

    // Check npm
    let npm_installed = Command::new("which")
        .arg("npm")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);

    Ok(CLIStatus {
        installed,
        path,
        version,
        node_installed,
        npm_installed,
    })
}

// Install Claude Code CLI
#[tauri::command]
async fn install_claude_cli() -> Result<String, String> {
    use std::process::Command;

    let output = Command::new("npm")
        .args(["install", "-g", "@anthropic-ai/claude-code"])
        .output()
        .map_err(|e| format!("Failed to run npm: {}", e))?;

    if output.status.success() {
        Ok("Claude Code CLI installed successfully".to_string())
    } else {
        Err(format!(
            "Installation failed: {}",
            String::from_utf8_lossy(&output.stderr)
        ))
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .manage(Arc::new(Mutex::new(BackendState::default())))
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            get_backend_status,
            get_backend_port,
            check_claude_cli,
            install_claude_cli,
        ])
        .setup(|app| {
            // Auto-start backend on app launch
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                // Give UI time to load
                tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;

                // Try to start backend
                let state = app_handle.state::<SharedBackendState>();
                let mut backend = state.lock().await;
                let port = portpicker::pick_unused_port().unwrap_or(8000);
                backend.port = port;
                // Note: Actual sidecar start will be triggered from frontend
                // to allow for proper error handling in UI
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
