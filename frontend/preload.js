const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electron", {
  // Window controls
  minimize: () => ipcRenderer.invoke("app:minimize"),
  maximize: () => ipcRenderer.invoke("app:maximize"),
  close:    () => ipcRenderer.invoke("app:close"),

  // API base URL
  getApiBase: () => ipcRenderer.invoke("app:api-base"),

  // Open external links in the default browser
  openExternal: (url) => ipcRenderer.invoke("shell:open", url),
});

/**
 * Convenience API client exposed on window.api
 * Usage:  await window.api.post("/ingest/upload", formData)
 */
contextBridge.exposeInMainWorld("api", {
  async get(endpoint) {
    const base = await ipcRenderer.invoke("app:api-base");
    const res  = await fetch(`${base}/api${endpoint}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async post(endpoint, body) {
    const base = await ipcRenderer.invoke("app:api-base");
    const res  = await fetch(`${base}/api${endpoint}`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // FormData cannot cross contextBridge — caller converts File to ArrayBuffer first
  async postFile(endpoint, fileName, fileBuffer) {
    const base = await ipcRenderer.invoke("app:api-base");
    const form = new FormData();
    form.append("file", new Blob([fileBuffer]), fileName);
    const res  = await fetch(`${base}/api${endpoint}`, {
      method: "POST",
      body:   form,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async del(endpoint) {
    const base = await ipcRenderer.invoke("app:api-base");
    const res  = await fetch(`${base}/api${endpoint}`, { method: "DELETE" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
});
