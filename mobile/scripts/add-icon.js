// Injects the Six-String Bootcamp launcher icon into the generated Android project.
// Runs after `npx cap add android` (see .github/workflows/android.yml).
// The native android/ dir is regenerated on every CI run, so the icon
// sources live in mobile/icon/ and get copied in here.
const fs = require('fs');
const path = require('path');

const ANDROID = 'android/app/src/main';
const ICON = 'icon';

function copy(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  console.log('copied', src, '->', dest);
}

const densities = ['mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi'];

// 1. Legacy launcher icons
for (const d of densities) {
  copy(`${ICON}/mipmap-${d}/ic_launcher.png`,
       `${ANDROID}/res/mipmap-${d}/ic_launcher.png`);
}

// 2. Adaptive-icon foregrounds (white background + mark)
for (const d of densities) {
  copy(`${ICON}/foreground-${d}/ic_launcher_foreground.png`,
       `${ANDROID}/res/mipmap-${d}/ic_launcher_foreground.png`);
}

// 3. Background color (white, matches the icon)
{
  const dest = `${ANDROID}/res/values/colors.xml`;
  let s = fs.existsSync(dest)
    ? fs.readFileSync(dest, 'utf8')
    : '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n</resources>\n';
  if (!s.includes('name="ic_launcher_background"')) {
    s = s.replace('</resources>',
      '    <color name="ic_launcher_background">#FFFFFF</color>\n</resources>');
    fs.writeFileSync(dest, s);
    console.log('colors.xml merged: ic_launcher_background added');
  } else {
    console.log('colors.xml already has ic_launcher_background');
  }
}

// 4. Adaptive-icon XML (API 26+)
{
  const xml =
    '<?xml version="1.0" encoding="utf-8"?>\n' +
    '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n' +
    '    <background android:drawable="@color/ic_launcher_background"/>\n' +
    '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n' +
    '</adaptive-icon>\n';
  const dest = `${ANDROID}/res/mipmap-anydpi-v26/ic_launcher.xml`;
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, xml);
  console.log('wrote', dest);
}

// 5. Manifest: point the launcher icon at the new artwork
{
  const manifest = `${ANDROID}/AndroidManifest.xml`;
  let s = fs.readFileSync(manifest, 'utf8');
  if (s.includes('@mipmap/ic_launcher')) {
    console.log('manifest already references @mipmap/ic_launcher');
  } else if (s.includes('<application')) {
    s = s.replace(/<application([^>]*)>/,
      '<application$1 android:icon="@mipmap/ic_launcher" android:roundIcon="@mipmap/ic_launcher">');
    fs.writeFileSync(manifest, s);
    console.log('manifest patched: launcher icon set');
  } else {
    throw new Error('AndroidManifest.xml has no <application> — cannot set launcher icon');
  }
}
