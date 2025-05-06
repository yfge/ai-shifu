const fs = require('fs');
const path = require('path');

function getAllFiles(dir, files = []) {
  fs.readdirSync(dir).forEach(file => {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      if (!['local', 'assets'].includes(file)) {
        getAllFiles(fullPath, files);
      }
    } else if (/\.(js|jsx|ts|tsx)$/.test(file)) {
      files.push(fullPath);
    }
  });
  return files;
}

function extractKeysFromFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const regex = /t\('([a-zA-Z0-9_]+)\.([a-zA-Z0-9_.-]+)'\)/g;
  let match, keys = [];
  while ((match = regex.exec(content)) !== null) {
    keys.push(match[1] + '.' + match[2]);
  }
  return keys;
}

function setNested(obj, key, value) {
  const keys = key.split('.');
  let cur = obj;
  keys.forEach((k, idx) => {
    if (idx === keys.length - 1) {
      if (!(k in cur)) cur[k] = value;
    } else {
      if (!(k in cur)) cur[k] = {};
      cur = cur[k];
    }
  });
}

function buildNestedJson(keys, langMark) {
  const result = {};
  keys.forEach(key => setNested(result, key, langMark));
  return result;
}

function mergeJson(base, patch) {
  for (const k in patch) {
    if (typeof patch[k] === 'object' && patch[k] !== null && !Array.isArray(patch[k])) {
      if (!base[k]) base[k] = {};
      mergeJson(base[k], patch[k]);
    } else {
      if (!(k in base)) base[k] = patch[k];
    }
  }
  return base;
}

const ROOT_DIR = path.join(__dirname, '..'); // src/cook-web/src/
const LOCALE_DIR = path.join(ROOT_DIR, '../public/locales');

const files = getAllFiles(ROOT_DIR);
const allKeys = Array.from(new Set(files.flatMap(extractKeysFromFile)));

fs.readdirSync(LOCALE_DIR).forEach(file => {
  if (file.endsWith('.json') &&  file !== 'languages.json') {
    const langFile = path.join(LOCALE_DIR, file);
    const langMark = `@${file}`;
    let baseJson = {};
    if (fs.existsSync(langFile)) {
      baseJson = JSON.parse(fs.readFileSync(langFile, 'utf8'));
    }
    const patchJson = buildNestedJson(allKeys, langMark);
    const merged = mergeJson(baseJson, patchJson);
    fs.writeFileSync(langFile, JSON.stringify(merged, null, 2), 'utf8');
    console.log(`${file} updated. ${allKeys.length} keys found.`);
  }
});
