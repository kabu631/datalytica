const { app, BrowserWindow, ipcMain, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");

const PORT = 8765;
const API_BASE = `http://127.0.0.1:${PORT}`;
let mainWindow;
let splashWindow;
let backendProcess;

// ── Launch FastAPI backend ────────────────────────────────────────────────────
function startBackend() {
  // First check if a backend is already running on PORT (e.g. launched manually for dev)
  const checkReq = http.get(`http://127.0.0.1:${PORT}/`, (res) => {
    if (res.statusCode === 200) {
      console.log("[Backend] Already running on port", PORT, "— skipping spawn.");
      return; // backend already up, polling will handle the rest
    }
    spawnBackend();
  });
  checkReq.on("error", () => {
    // Not running yet — spawn it
    spawnBackend();
  });
}

function spawnBackend() {
  const isDev = process.argv.includes("--dev");

  if (isDev) {
    const pythonCmd = process.platform === "win32" ? "python" : "python3";
    const backendDir = path.join(__dirname, "..", "backend");
    backendProcess = spawn(pythonCmd, ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", PORT.toString()], {
      cwd: backendDir,
      shell: true,
    });
  } else {
    // Production: launch the PyInstaller-compiled standalone exe
    const backendDir = path.join(process.resourcesPath, "backend");
    const exeName = process.platform === "win32" ? "datalytica-backend.exe" : "datalytica-backend";
    const backendExe = path.join(backendDir, exeName);
    backendProcess = spawn(backendExe, [], {
      cwd: backendDir,
      shell: false,
    });
  }

  backendProcess.stdout.on("data", (d) => console.log("[Backend]", d.toString()));
  backendProcess.stderr.on("data", (d) => console.error("[Backend ERR]", d.toString()));
  backendProcess.on("exit", (code) => console.log("[Backend] exited with code", code));
}

// ── Polling logic ─────────────────────────────────────────────────────────────
function pollBackend(onReady) {
  const interval = setInterval(() => {
    http.get(API_BASE + "/api/health", (res) => {
      if (res.statusCode === 200) {
        clearInterval(interval);
        onReady();
      }
    }).on("error", () => {
      console.log("Waiting for backend...");
    });
  }, 500);
}

// ── Create windows ────────────────────────────────────────────────────────────
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 400,
    height: 300,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Load a simple inline HTML for splash
  const splashHTML = `
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;font-family:system-ui,sans-serif;color:white;background:#534AB7;border-radius:8px;">
      <h2>Datalytica</h2>
      <p>Initializing Python Backend...</p>
    </div>
  `;
  splashWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(splashHTML)}`);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    frame: false,
    titleBarStyle: "hidden",
    backgroundColor: "#0d0f1a",
    show: false, // hide initially to prevent flash
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  mainWindow.once("ready-to-show", () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    mainWindow.show();
    if (process.argv.includes("--dev")) {
      mainWindow.webContents.openDevTools();
    }
  });
}

// ── App lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  createSplashWindow();
  startBackend();
  
  pollBackend(() => {
    createWindow();
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== "darwin") app.quit();
});

// ── IPC handlers ──────────────────────────────────────────────────────────────
ipcMain.handle("app:minimize", () => mainWindow?.minimize());
ipcMain.handle("app:maximize", () => mainWindow?.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize());
ipcMain.handle("app:close", () => app.quit());
ipcMain.handle("app:api-base", () => API_BASE);
ipcMain.handle("shell:open", (_, url) => shell.openExternal(url));
