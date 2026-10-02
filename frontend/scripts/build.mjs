import { mkdirSync, copyFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { root, loadEnvironment, configScript } from './config.mjs';

export function build(env = loadEnvironment(), output = join(root, 'dist')) {
  const config = configScript(env); // Validate before writing any build output.
  mkdirSync(join(output, 'static'), {recursive:true});
  copyFileSync(join(root, 'src/index.html'), join(output, 'index.html'));
  for (const file of ['app.js', 'style.css']) {
    copyFileSync(join(root, 'src/static', file), join(output, 'static', file));
  }
  writeFileSync(join(output, 'frontend-config.js'), config);
  return output;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  build(); console.log('Frontend built in dist/');
}
