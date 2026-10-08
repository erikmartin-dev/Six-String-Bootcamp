// Patches the generated Android manifest after `npx cap add android`:
// adds microphone permission for the in-app tuner.
const fs = require('fs');
const p = 'android/app/src/main/AndroidManifest.xml';
let s = fs.readFileSync(p, 'utf8');
if (!s.includes('RECORD_AUDIO')) {
  s = s.replace(
    '<uses-permission android:name="android.permission.INTERNET" />',
    '<uses-permission android:name="android.permission.INTERNET" />\n' +
    '    <uses-permission android:name="android.permission.RECORD_AUDIO" />\n' +
    '    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />'
  );
  fs.writeFileSync(p, s);
  console.log('manifest patched: mic permission added');
} else {
  console.log('manifest already patched');
}
