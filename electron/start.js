const { spawn } = require('child_process');
const path = require('path');

const electronPath = require('electron');
const projectRoot = path.resolve(__dirname, '..');
const env = { ...process.env };
const userArgs = process.argv.slice(2);
const electronArgs = userArgs.some((arg) => arg === '--version' || arg === '-v')
  ? userArgs
  : [projectRoot, ...userArgs];

delete env.ELECTRON_RUN_AS_NODE;

const child = spawn(
  electronPath,
  electronArgs,
  {
    cwd: projectRoot,
    env,
    stdio: 'inherit',
    windowsHide: false,
  }
);

child.on('exit', (code) => {
  process.exit(code || 0);
});

child.on('error', (error) => {
  console.error(error);
  process.exit(1);
});
