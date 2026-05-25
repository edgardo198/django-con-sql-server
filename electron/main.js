const { app, BrowserWindow, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const https = require('https');
const net = require('net');
const path = require('path');

const HOST = '127.0.0.1';
const DEFAULT_PORT = Number(process.env.ELECTRON_DJANGO_PORT || 8765);
const PASSWORD_FALLBACK = '';
const ELECTRON_ENV_KEYS = new Set([
  'ELECTRON_DB_ENGINE',
  'ELECTRON_DATABASE_URL',
  'ELECTRON_SQLITE_NAME',
  'ELECTRON_POSTGRES_NAME',
  'ELECTRON_POSTGRES_HOST',
  'ELECTRON_POSTGRES_PORT',
  'ELECTRON_POSTGRES_USER',
  'ELECTRON_POSTGRES_PASSWORD',
  'DJANGO_DB_ENGINE',
  'DATABASE_URL',
  'SQLITE_NAME',
  'POSTGRES_NAME',
  'POSTGRES_HOST',
  'POSTGRES_PORT',
  'POSTGRES_USER',
  'POSTGRES_PASSWORD',
  'SYNC_REMOTE_URL',
  'SYNC_API_TOKEN',
  'DJANGO_SYNC_TOKEN',
  'SYNC_INTERVAL_SECONDS',
  'SYNC_RETRY_SECONDS',
  'SYNC_CONNECTIVITY_TIMEOUT_SECONDS',
  'SYNC_BATCH_SIZE',
  'SYNC_PULL_BATCH_SIZE',
  'SYNC_LOCK_TTL_SECONDS',
  'DJANGO_USE_DATABASE_MEDIA_STORAGE',
  'SUPERADMIN_USERNAME',
  'SUPERADMIN_EMAIL',
  'SUPERADMIN_PASSWORD',
]);

let mainWindow = null;
let djangoProcess = null;
let syncTimer = null;
let syncInFlight = false;
const logs = [];

function rememberLog(chunk) {
  const text = chunk.toString();
  logs.push(text);
  while (logs.length > 120) {
    logs.shift();
  }
}

function getProjectRoot() {
  if (app.isPackaged) {
    const packagedAppPath = path.join(process.resourcesPath, 'app');
    if (fs.existsSync(path.join(packagedAppPath, 'manage.py'))) {
      return packagedAppPath;
    }
  }

  return path.resolve(__dirname, '..');
}

function parseEnvLine(line) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith('#')) {
    return null;
  }

  const normalized = trimmed.startsWith('export ') ? trimmed.slice(7).trim() : trimmed;
  const separatorIndex = normalized.indexOf('=');
  if (separatorIndex < 1) {
    return null;
  }

  const key = normalized.slice(0, separatorIndex).trim();
  let value = normalized.slice(separatorIndex + 1).trim();

  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
    return null;
  }

  const quote = value[0];
  if ((quote === '"' || quote === "'") && value.endsWith(quote)) {
    value = value.slice(1, -1);
  }

  return { key, value };
}

function loadElectronEnvFile(filePath, options = {}) {
  if (!fs.existsSync(filePath)) {
    return;
  }

  const override = Boolean(options.override);
  const lines = fs.readFileSync(filePath, 'utf8').split(/\r?\n/);
  for (const line of lines) {
    const parsed = parseEnvLine(line);
    if (!parsed || !ELECTRON_ENV_KEYS.has(parsed.key)) {
      continue;
    }
    if (override || process.env[parsed.key] === undefined) {
      process.env[parsed.key] = parsed.value;
    }
  }
}

function loadElectronEnvironment(projectRoot) {
  loadElectronEnvFile(path.join(projectRoot, '.env'));
  loadElectronEnvFile(path.join(projectRoot, '.env.local'), { override: true });
}

function getPythonCommand(projectRoot) {
  const venvPython = process.platform === 'win32'
    ? path.join(projectRoot, 'venv', 'Scripts', 'python.exe')
    : path.join(projectRoot, 'venv', 'bin', 'python');

  if (fs.existsSync(venvPython)) {
    return { command: venvPython, args: [] };
  }

  if (process.platform === 'win32') {
    return { command: 'py', args: ['-3'] };
  }

  return { command: 'python3', args: [] };
}

function normalizeDbEngine(engine) {
  const value = (engine || 'sqlite').trim().toLowerCase();
  if (value === 'postgres' || value === 'pgsql') {
    return 'postgresql';
  }
  return value;
}

function buildDatabaseEnv(sqlitePath) {
  const engine = normalizeDbEngine(process.env.ELECTRON_DB_ENGINE || process.env.DJANGO_DB_ENGINE || 'sqlite');

  if (engine === 'postgresql') {
    return {
      DATABASE_URL: process.env.ELECTRON_DATABASE_URL || '',
      DJANGO_DB_ENGINE: 'postgresql',
      POSTGRES_NAME: process.env.ELECTRON_POSTGRES_NAME || process.env.POSTGRES_NAME || 'Tienda',
      POSTGRES_HOST: process.env.ELECTRON_POSTGRES_HOST || process.env.POSTGRES_HOST || HOST,
      POSTGRES_PORT: process.env.ELECTRON_POSTGRES_PORT || process.env.POSTGRES_PORT || '5432',
      POSTGRES_USER: process.env.ELECTRON_POSTGRES_USER || process.env.POSTGRES_USER || '',
      POSTGRES_PASSWORD: process.env.ELECTRON_POSTGRES_PASSWORD || process.env.POSTGRES_PASSWORD || '',
      SQLITE_NAME: process.env.ELECTRON_SQLITE_NAME || process.env.SQLITE_NAME || sqlitePath,
    };
  }

  return {
    DATABASE_URL: '',
    DJANGO_DB_ENGINE: 'sqlite',
    SQLITE_NAME: process.env.ELECTRON_SQLITE_NAME || process.env.SQLITE_NAME || sqlitePath,
  };
}

function buildDjangoEnv(projectRoot, port, sqlitePath) {
  const hasSyncConfig = Boolean(
    process.env.SYNC_REMOTE_URL && (process.env.SYNC_API_TOKEN || process.env.DJANGO_SYNC_TOKEN)
  );
  const databaseEnv = buildDatabaseEnv(sqlitePath);

  return {
    ...process.env,
    DJANGO_ENV: 'local',
    DJANGO_DEBUG: 'true',
    ...databaseEnv,
    DJANGO_ALLOWED_HOSTS: `${HOST},localhost`,
    DJANGO_CSRF_TRUSTED_ORIGINS: `http://${HOST}:${port},http://localhost:${port}`,
    DJANGO_SERVE_MEDIA: 'true',
    DJANGO_USE_DATABASE_MEDIA_STORAGE: process.env.DJANGO_USE_DATABASE_MEDIA_STORAGE || (hasSyncConfig ? 'true' : 'false'),
    DJANGO_SECURE_SSL_REDIRECT: 'false',
    DJANGO_SESSION_COOKIE_SECURE: 'false',
    DJANGO_CSRF_COOKIE_SECURE: 'false',
    SUPERADMIN_USERNAME: process.env.SUPERADMIN_USERNAME || 'superadmin',
    SUPERADMIN_EMAIL: process.env.SUPERADMIN_EMAIL || 'superadmin@local.test',
    SUPERADMIN_PASSWORD: process.env.SUPERADMIN_PASSWORD || PASSWORD_FALLBACK,
    PYTHONUNBUFFERED: '1',
    PORT: String(port),
  };
}

function usesSqlite(env) {
  return normalizeDbEngine(env.DJANGO_DB_ENGINE) === 'sqlite';
}

function runManage(projectRoot, env, manageArgs) {
  return new Promise((resolve, reject) => {
    const python = getPythonCommand(projectRoot);
    const child = spawn(
      python.command,
      [...python.args, 'manage.py', ...manageArgs],
      { cwd: projectRoot, env, windowsHide: true }
    );

    child.stdout.on('data', rememberLog);
    child.stderr.on('data', rememberLog);

    child.on('error', reject);
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`manage.py ${manageArgs.join(' ')} termino con codigo ${code}`));
      }
    });
  });
}

function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();

    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, HOST);
  });
}

async function findAvailablePort(startPort) {
  for (let port = startPort; port < startPort + 40; port += 1) {
    if (await isPortFree(port)) {
      return port;
    }
  }

  throw new Error(`No hay puertos libres entre ${startPort} y ${startPort + 39}.`);
}

function waitForServer(port, timeoutMs = 45000) {
  const startedAt = Date.now();

  return new Promise((resolve, reject) => {
    const check = () => {
      const request = http.get(`http://${HOST}:${port}/login/`, (response) => {
        response.resume();
        resolve();
      });

      request.on('error', () => {
        if (Date.now() - startedAt > timeoutMs) {
          reject(new Error('Django no respondio a tiempo.'));
          return;
        }
        setTimeout(check, 400);
      });

      request.setTimeout(1500, () => {
        request.destroy();
      });
    };

    check();
  });
}

function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1024,
    minHeight: 700,
    title: 'ERP Comercial',
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isLocalUrl(url, port)) {
      return { action: 'allow' };
    }

    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!isLocalUrl(url, port)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(getLoadingHtml())}`);
}

function isLocalUrl(rawUrl, port) {
  if (rawUrl.startsWith('data:text/html')) {
    return true;
  }

  try {
    const url = new URL(rawUrl);
    return url.origin === `http://${HOST}:${port}` || url.origin === `http://localhost:${port}`;
  } catch (error) {
    return false;
  }
}

function getLoadingHtml() {
  return `
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <title>ERP Comercial</title>
        <style>
          body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            color: #17211f;
            background: #f4f7f5;
            font-family: Arial, sans-serif;
          }
          main {
            width: min(420px, calc(100vw - 32px));
            padding: 28px;
            border: 1px solid #dbe5e0;
            border-radius: 8px;
            background: #ffffff;
            box-shadow: 0 18px 40px rgba(20, 32, 30, 0.08);
          }
          h1 {
            margin: 0 0 8px;
            font-size: 22px;
          }
          p {
            margin: 0;
            color: #5d6965;
            line-height: 1.5;
          }
        </style>
      </head>
      <body>
        <main>
          <h1>Iniciando ERP Comercial</h1>
          <p>Preparando Django y la base de datos local.</p>
        </main>
      </body>
    </html>
  `;
}

function startDjango(projectRoot, env, port) {
  const python = getPythonCommand(projectRoot);
  djangoProcess = spawn(
    python.command,
    [...python.args, 'manage.py', 'runserver', `${HOST}:${port}`, '--noreload'],
    { cwd: projectRoot, env, windowsHide: true }
  );

  djangoProcess.stdout.on('data', rememberLog);
  djangoProcess.stderr.on('data', rememberLog);
  djangoProcess.on('error', rememberLog);
  djangoProcess.on('close', (code) => {
    rememberLog(`Django finalizo con codigo ${code}.\n`);
    djangoProcess = null;
  });
}

function stopDjango() {
  if (syncTimer) {
    clearTimeout(syncTimer);
    syncTimer = null;
  }

  if (djangoProcess) {
    djangoProcess.kill();
    djangoProcess = null;
  }
}

function normalizeRemoteUrl(remoteUrl) {
  return remoteUrl.replace(/\/+$/, '');
}

function remoteStatusUrl(remoteUrl) {
  return `${normalizeRemoteUrl(remoteUrl)}/sync/status/`;
}

function checkRemoteSyncAvailable(remoteUrl, syncToken, timeoutMs = 10000) {
  return new Promise((resolve) => {
    let url;
    try {
      url = new URL(remoteStatusUrl(remoteUrl));
    } catch (error) {
      resolve({ ok: false, reason: 'URL remota invalida' });
      return;
    }

    const transport = url.protocol === 'https:' ? https : http;
    const request = transport.get(
      url,
      {
        headers: { 'X-Sync-Token': syncToken },
        timeout: timeoutMs,
      },
      (response) => {
        response.resume();
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve({ ok: true });
          return;
        }
        resolve({ ok: false, reason: `Render respondio HTTP ${response.statusCode}` });
      }
    );

    request.on('timeout', () => {
      request.destroy();
      resolve({ ok: false, reason: 'Render no respondio a tiempo' });
    });
    request.on('error', (error) => {
      resolve({ ok: false, reason: error.message });
    });
  });
}

function startSyncLoop(projectRoot, env) {
  const remoteUrl = env.SYNC_REMOTE_URL;
  const syncToken = env.SYNC_API_TOKEN || env.DJANGO_SYNC_TOKEN;
  if (!remoteUrl || !syncToken) {
    rememberLog('Sincronizacion remota desactivada: configure SYNC_REMOTE_URL y SYNC_API_TOKEN.\n');
    return;
  }

  const intervalSeconds = Number(env.SYNC_INTERVAL_SECONDS || 300);
  const intervalMs = Math.max(intervalSeconds, 60) * 1000;
  const retrySeconds = Number(env.SYNC_RETRY_SECONDS || 30);
  const retryMs = Math.max(retrySeconds, 15) * 1000;
  const connectivityTimeoutMs = Math.max(Number(env.SYNC_CONNECTIVITY_TIMEOUT_SECONDS || 10), 3) * 1000;

  const scheduleNext = (delayMs) => {
    if (syncTimer) {
      clearTimeout(syncTimer);
    }
    syncTimer = setTimeout(runSync, delayMs);
  };

  const runSync = async () => {
    if (syncInFlight) {
      scheduleNext(retryMs);
      return;
    }

    syncInFlight = true;
    try {
      const status = await checkRemoteSyncAvailable(remoteUrl, syncToken, connectivityTimeoutMs);
      if (!status.ok) {
        rememberLog(`Sync pausada: ${status.reason}. Reintentando en ${Math.round(retryMs / 1000)}s.\n`);
        scheduleNext(retryMs);
        return;
      }

      await runManage(projectRoot, env, ['sync_with_remote']);
      rememberLog(`Sync completada. Proximo intento en ${Math.round(intervalMs / 1000)}s.\n`);
      scheduleNext(intervalMs);
    } catch (error) {
      rememberLog(`Sync fallo: ${error.message}. Reintentando en ${Math.round(retryMs / 1000)}s.\n`);
      scheduleNext(retryMs);
    } finally {
      syncInFlight = false;
    }
  };

  scheduleNext(5000);
}

function hasRemoteSyncConfig(env) {
  return Boolean(env.SYNC_REMOTE_URL && (env.SYNC_API_TOKEN || env.DJANGO_SYNC_TOKEN));
}

async function runInitialRemotePull(projectRoot, env) {
  if (!hasRemoteSyncConfig(env)) {
    return false;
  }

  try {
    const syncToken = env.SYNC_API_TOKEN || env.DJANGO_SYNC_TOKEN;
    const timeoutMs = Math.max(Number(env.SYNC_CONNECTIVITY_TIMEOUT_SECONDS || 10), 3) * 1000;
    const status = await checkRemoteSyncAvailable(env.SYNC_REMOTE_URL, syncToken, timeoutMs);
    if (!status.ok) {
      rememberLog(`Sync inicial omitida: ${status.reason}.\n`);
      return false;
    }
    await runManage(projectRoot, env, ['sync_with_remote', '--pull-only']);
    return true;
  } catch (error) {
    rememberLog(`Sync inicial fallo: ${error.message}\n`);
    return false;
  }
}

async function bootstrap() {
  const projectRoot = getProjectRoot();
  loadElectronEnvironment(projectRoot);
  const port = await findAvailablePort(DEFAULT_PORT);
  const sqlitePath = process.env.SQLITE_NAME || path.join(projectRoot, 'local.sqlite3');
  const env = buildDjangoEnv(projectRoot, port, sqlitePath);
  const firstRun = usesSqlite(env) && !fs.existsSync(env.SQLITE_NAME);

  createWindow(port);

  try {
    await runManage(projectRoot, env, ['migrate', '--noinput']);
    await runInitialRemotePull(projectRoot, env);

    if (firstRun || process.env.ELECTRON_BOOTSTRAP_ACCESS === '1') {
      const bootstrapArgs = ['bootstrap_access'];
      if (hasRemoteSyncConfig(env)) {
        bootstrapArgs.push('--if-empty');
      }
      await runManage(projectRoot, env, bootstrapArgs);
    }

    startDjango(projectRoot, env, port);
    await waitForServer(port);

    if (mainWindow && !mainWindow.isDestroyed()) {
      await mainWindow.loadURL(`http://${HOST}:${port}/login/`);
    }

    startSyncLoop(projectRoot, env);
  } catch (error) {
    const detail = `${error.message}\n\n${logs.join('')}`;
    dialog.showErrorBox('No se pudo iniciar ERP Comercial', detail.slice(-6000));
    app.quit();
  }
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.focus();
    }
  });

  app.whenReady().then(bootstrap);
}

app.on('before-quit', stopDjango);

app.on('window-all-closed', () => {
  app.quit();
});
