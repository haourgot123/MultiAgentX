import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const readArg = (name) => {
  const index = process.argv.indexOf(name);
  if (index === -1 || !process.argv[index + 1]) {
    throw new Error(`Missing required argument: ${name}`);
  }
  return process.argv[index + 1];
};

const inputPath = readArg('--input');
const outputPath = readArg('--output');
const thumbnailPath = readArg('--thumbnail');
const inputProps = JSON.parse(await fs.readFile(inputPath, 'utf8'));

const entryPoint = path.join(__dirname, 'src', 'index.tsx');
const serveUrl = await bundle({
  entryPoint,
  webpackOverride: (config) => config,
});

const composition = await selectComposition({
  serveUrl,
  id: 'GeneratedVideo',
  inputProps,
});

await fs.mkdir(path.dirname(outputPath), {recursive: true});

await renderMedia({
  composition,
  serveUrl,
  codec: 'h264',
  outputLocation: outputPath,
  inputProps,
  chromiumOptions: {
    ignoreCertificateErrors: true,
  },
});

await renderStill({
  composition,
  serveUrl,
  output: thumbnailPath,
  inputProps,
  frame: 0,
});
