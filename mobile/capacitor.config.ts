import type { CapacitorConfig } from '@capacitor/cli';

// Six-String Bootcamp — native wrapper around the hosted Streamlit app.
// BEFORE FIRST BUILD: set server.url to your production domain below.
const config: CapacitorConfig = {
  appId: 'com.sixstringbootcamp.app',
  appName: 'Six-String Bootcamp',
  webDir: 'www',
  server: {
    // Live app URL. The www/index.html fallback only shows if this is unreachable.
    url: 'https://six-string-bootcamp-heagexcrctnpnsbnwulajg.streamlit.app',
    cleartext: false,
  },
  android: {
    // Keep the WebView from zooming the fretboard on double-tap
    allowMixedContent: false,
  },
};

export default config;
