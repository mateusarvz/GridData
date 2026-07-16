import { execSync } from 'child_process';
import os from 'os';

console.log('==> Starting pre-build permission check...');
if (os.platform() !== 'win32') {
  try {
    console.log('Applying execute permissions to node_modules binaries for Linux/Render...');
    execSync('chmod -R +x node_modules/.bin node_modules/vite/bin node_modules/typescript/bin 2>/dev/null || true', { stdio: 'inherit' });
  } catch (e) {
    console.warn('Warning: Failed to set permissions:', e.message);
  }
}

console.log('==> Running TypeScript compilation (tsc -b)...');
execSync('npx tsc -b', { stdio: 'inherit' });

console.log('==> Running Vite build (vite build)...');
execSync('npx vite build', { stdio: 'inherit' });
