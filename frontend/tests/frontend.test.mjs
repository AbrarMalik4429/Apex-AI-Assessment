import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { once } from 'node:events';
import { publicConfig, configScript, listenConfig } from '../scripts/config.mjs';
import { build } from '../scripts/build.mjs';
import { createFrontendServer } from '../scripts/dev.mjs';

const env = {FRONTEND_API_BASE_URL:'https://api.example.test', FRONTEND_FONT_URL:'', GROQ_API_KEY:'private-test-key', DATABASE_URL:'private-test-database'};
test('build publishes only website assets and allowlisted public configuration', () => {
  const output = mkdtempSync(join(tmpdir(), 'apex-frontend-'));
  build(env, output);
  assert.deepEqual(readdirSync(output).sort(), ['frontend-config.js','index.html','static']);
  assert.deepEqual(readdirSync(join(output,'static')).sort(), ['app.js','style.css']);
  const config = readFileSync(join(output,'frontend-config.js'),'utf8');
  assert.ok(config.includes(env.FRONTEND_API_BASE_URL));
  assert.ok(!config.includes('private-test'));
  assert.deepEqual(publicConfig(env), {apiBaseUrl:env.FRONTEND_API_BASE_URL,fontUrl:''});
});
test('missing or unsafe API addresses fail clearly instead of using the frontend origin', () => {
  for (const value of ['', 'javascript:alert(1)', 'https://user:secret@example.test', 'https://example.test?key=secret']) {
    assert.throws(() => configScript({FRONTEND_API_BASE_URL:value}));
  }
  assert.throws(() => listenConfig({FRONTEND_HOST:'127.0.0.1',FRONTEND_PORT:'70000'}));
});
test('independent dev server serves assets and never exposes local env or backend files', async () => {
  const server = createFrontendServer(env);
  server.listen(0,'127.0.0.1'); await once(server,'listening');
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    assert.equal((await fetch(base+'/')).status,200);
    assert.equal((await fetch(base+'/static/app.js')).status,200);
    assert.ok((await (await fetch(base+'/frontend-config.js')).text()).includes(env.FRONTEND_API_BASE_URL));
    for (const path of ['/.env','/../.env','/knowledge-base/chunks.jsonl','/app/main.py','/assistant/message']) {
      assert.equal((await fetch(base+path)).status,404);
    }
  } finally { server.closeAllConnections(); await new Promise(resolve=>server.close(resolve)); }
});
