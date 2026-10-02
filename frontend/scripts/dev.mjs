import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { root, loadEnvironment, configScript, listenConfig } from './config.mjs';

export function createFrontendServer(env = loadEnvironment()) {
  const config = configScript(env);
  const routes = new Map([
    ['/', ['index.html', 'text/html; charset=utf-8']],
    ['/index.html', ['index.html', 'text/html; charset=utf-8']],
    ['/static/app.js', ['static/app.js', 'text/javascript; charset=utf-8']],
    ['/static/style.css', ['static/style.css', 'text/css; charset=utf-8']],
  ]);
  return createServer((req, res) => {
    const path = req.url.split('?')[0];
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
    let content, type;
    if (path === '/frontend-config.js') { content = config; type = 'text/javascript; charset=utf-8'; }
    else if (routes.has(path)) {
      const [file, mime] = routes.get(path);
      try { content = readFileSync(join(root, 'src', file)); type = mime; }
      catch { res.writeHead(500); res.end('Frontend file unavailable'); return; }
    } else { res.writeHead(404); res.end('Not found'); return; }
    res.writeHead(200, {'Content-Type':type, 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff'});
    res.end(req.method === 'HEAD' ? undefined : content);
  });
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const env = loadEnvironment();
  const {host, port} = listenConfig(env);
  const server = createFrontendServer(env);
  server.on('error', error => { console.error(error.message); process.exitCode = 1; });
  server.listen(port, host, () => console.log(`Frontend listening at http://${host}:${port}`));
}
