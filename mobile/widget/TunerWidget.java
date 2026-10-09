package com.sixstringbootcamp.app;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.widget.RemoteViews;

/**
 * Six-String home-screen widget: one tap opens the app straight into the tuner.
 * (Android home-screen widgets can't host live mic UI, so this is a launcher.)
 */
public class TunerWidget extends AppWidgetProvider {

    public static final String EXTRA_OPEN_URL = "com.sixstringbootcamp.app.OPEN_URL";
    public static final String TUNER_URL =
            "https://six-string-bootcamp-heagexcrctnpnsbnwulajg.streamlit.app/?view=tuner";

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {
            Intent intent = new Intent(context, MainActivity.class);
            intent.setAction("com.sixstringbootcamp.app.OPEN_TUNER");
            intent.putExtra(EXTRA_OPEN_URL, TUNER_URL);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);

            PendingIntent pi = PendingIntent.getActivity(
                    context, 0, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

            RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_tuner);
            views.setOnClickPendingIntent(R.id.widget_tuner_btn, pi);
            appWidgetManager.updateAppWidget(appWidgetId, views);
        }
    }
}
