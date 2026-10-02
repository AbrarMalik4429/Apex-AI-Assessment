import { readFileSync, existsSync } from 'node:fs';
import { parseEnv } from 'node:util';
import { fileURLToPath } from 'node:url';

export const root = fileURLToPath(new URL('../', import.meta.url));

export function loadEnvironment(env = process.env, directory = root) {
  const path = directory + '/.env';
  const local = existsSync(path) ? parseEnv(readFileSync(path, 'utf8')) : {};
  return { ...local, ...env };
}

function serviceUrl(value, name, required = false) {
  if (!value?.trim()) {
    if (required) throw new Error(`${name} is required. Set it in frontend/.env or the hosting environment.`);
    return '';
  }
  let url;
  try { url = new URL(value.trim()); } catch { throw new Error(`${name} must be an absolute HTTP(S) URL.`); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.hash) {
    throw new Error(`${name} must be an HTTP(S) URL without credentials or a fragment.`);
  }
  if (name === 'FRONTEND_API_BASE_URL' && url.search) throw new Error(`${name} cannot contain a query.`);
  return name === 'FRONTEND_API_BASE_URL' ? url.href.replace(/\/$/, '') : url.href;
}

export function publicConfig(env) {
  // Explicit allowlist. No other environment variables can enter the browser bundle.
  return {
    apiBaseUrl: serviceUrl(env.FRONTEND_API_BASE_URL, 'FRONTEND_API_BASE_URL', true),
    fontUrl: serviceUrl(env.FRONTEND_FONT_URL, 'FRONTEND_FONT_URL'),
  };
}
export function configScript(env) {
  return `window.APP_CONFIG = Object.freeze(${JSON.stringify(publicConfig(env))});\n`;
}
export function listenConfig(env) {
  const host = env.FRONTEND_HOST?.trim();
  const port = Number(env.FRONTEND_PORT);
  if (!host || !Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('Set FRONTEND_HOST and FRONTEND_PORT (1-65535) in frontend/.env.');
  }
  return {host, port};
}
