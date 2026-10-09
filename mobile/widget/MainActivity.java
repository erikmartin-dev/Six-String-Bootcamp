package com.sixstringbootcamp.app;

import android.content.Intent;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

/**
 * Capacitor BridgeActivity with home-screen widget deep-link support.
 * The tuner widget launches us with an "open_url" extra; we load it in the
 * WebView once the bridge is ready.
 */
public class MainActivity extends BridgeActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        handleWidgetLink(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleWidgetLink(intent);
    }

    private void handleWidgetLink(final Intent intent) {
        if (intent == null || !intent.hasExtra(TunerWidget.EXTRA_OPEN_URL)) {
            return;
        }
        final String url = intent.getStringExtra(TunerWidget.EXTRA_OPEN_URL);
        if (url == null || url.isEmpty()) {
            return;
        }
        // Let the bridge finish its initial load, then jump to the tuner.
        new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(
                new Runnable() {
                    @Override
                    public void run() {
                        try {
                            if (bridge != null && bridge.getWebView() != null) {
                                bridge.getWebView().loadUrl(url);
                            }
                        } catch (Exception ignored) {
                        }
                    }
                },
                1500);
    }
}
