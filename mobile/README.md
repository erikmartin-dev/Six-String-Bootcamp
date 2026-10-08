# Six-String Bootcamp — Android/iOS wrapper

Capacitor native shell around the hosted Six-String Bootcamp web app
(Streamlit). The app itself runs on your server; this repo builds the
installable phone apps that load it.

## Before the first build

1. **Ship the web app to a server** with HTTPS (see your hosting docs). Note the final URL.
2. **Point the wrapper at it**: edit `capacitor.config.ts` → `server.url`
   (default placeholder: `https://sixstringbootcamp.com`), then
   `npx cap sync android`.

## Builds (all free, in the cloud)

Push to `main` and GitHub Actions builds automatically:

- **Debug APK** (`six-string-bootcamp-debug` artifact) — sideload to your
  phone and test today. No signing needed.
- **Release AAB** — only runs once signing secrets exist (see below). This
  is the file you upload to Google Play.

## Release signing (one-time)

On any machine with Java (your Ubuntu proot works):

```
keytool -genkeypair -v -keystore upload.keystore -alias sixstring \
  -keyalg RSA -keysize 2048 -validity 10000
```

Back the keystore up somewhere safe (losing it = new app listing). Then in
GitHub: repo Settings → Secrets → Actions, add:

- `KEYSTORE_BASE64` — `base64 -w0 upload.keystore`
- `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`

The next push builds a signed release AAB.

## iOS

`npx cap add ios` needs Xcode (a Mac). Planned route: Expo EAS cloud build
or the full React Native rebuild — no Mac required.

## Permissions

- `INTERNET` — loads the hosted app.
- `RECORD_AUDIO` — the in-app tuner uses the microphone.
