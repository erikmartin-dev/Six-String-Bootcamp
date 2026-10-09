// Injects the home-screen tuner widget into the generated Android project.
// Runs after `npx cap add android` (see .github/workflows/android.yml).
// The native android/ dir is regenerated on every CI run, so the widget
// sources live in mobile/widget/ and get copied in here.
const fs = require('fs');
const path = require('path');

const ANDROID = 'android/app/src/main';
const WIDGET = 'widget';
const PKG = 'com/sixstringbootcamp/app';

function copy(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  console.log('copied', src, '->', dest);
}

// 1. Widget provider (AppWidgetProvider)
copy(`${WIDGET}/TunerWidget.java`, `${ANDROID}/java/${PKG}/TunerWidget.java`);
// 2. MainActivity with widget deep-link support (replaces generated stub)
copy(`${WIDGET}/MainActivity.java`, `${ANDROID}/java/${PKG}/MainActivity.java`);
// 3. Widget resources
copy(`${WIDGET}/res/layout/widget_tuner.xml`, `${ANDROID}/res/layout/widget_tuner.xml`);
copy(`${WIDGET}/res/xml/tuner_widget_info.xml`, `${ANDROID}/res/xml/tuner_widget_info.xml`);

// 4. Manifest: register the widget receiver
const manifest = `${ANDROID}/AndroidManifest.xml`;
let s = fs.readFileSync(manifest, 'utf8');
if (!s.includes('.TunerWidget')) {
  const receiver =
    '        <receiver android:name=".TunerWidget" android:exported="false">\n' +
    '            <intent-filter>\n' +
    '                <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />\n' +
    '            </intent-filter>\n' +
    '            <meta-data android:name="android.appwidget.provider"\n' +
    '                android:resource="@xml/tuner_widget_info" />\n' +
    '        </receiver>\n';
  if (!s.includes('</application>')) {
    throw new Error('AndroidManifest.xml has no </application> — cannot inject widget receiver');
  }
  s = s.replace('</application>', receiver + '    </application>');
  fs.writeFileSync(manifest, s);
  console.log('manifest patched: TunerWidget receiver added');
} else {
  console.log('manifest already has TunerWidget');
}
