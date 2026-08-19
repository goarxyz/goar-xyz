package com.goar.alpine;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Performs only the verified rootfs installation. The user's Mistral Vibe TUI
 * is owned by the foreground terminal activity; this service never creates a
 * second guest process, agent loop, or background network task.
 */
public final class GoarRuntimeService extends Service {
    public static final String ACTION_INSTALL = "com.goar.alpine.action.INSTALL";
    public static final String EXTRA_MANIFEST_URL = "manifest_url";
    private static final String CHANNEL_ID = "goar_alpine_install";
    private static final int NOTIFICATION_ID = 2001;

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private GoarRuntimeController runtime;

    @Override
    public void onCreate() {
        super.onCreate();
        runtime = new GoarRuntimeController(this);
        createChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForeground(NOTIFICATION_ID, notification("Preparing private Alpine terminal"));
        String requestedManifest = intent == null ? null : intent.getStringExtra(EXTRA_MANIFEST_URL);
        executor.execute(() -> installIfNeeded(requestedManifest));
        return START_NOT_STICKY;
    }

    private void installIfNeeded(String requestedManifest) {
        try {
            if (requestedManifest != null && !requestedManifest.trim().isEmpty()) {
                runtime.setManifestUrl(requestedManifest.trim());
            }
            if (!runtime.isInstalled()) {
                runtime.install(this::emit);
            }
            emit("running", 100, "Private Alpine terminal ready");
        } catch (Exception error) {
            emit("error", 0, error.getMessage() == null ? error.toString() : error.getMessage());
        } finally {
            stopForeground(STOP_FOREGROUND_REMOVE);
            stopSelf();
        }
    }

    private void emit(String stage, int percent, String detail) {
        Intent update = new Intent(GoarRuntimeController.ACTION_STATUS)
                .setPackage(getPackageName())
                .putExtra(GoarRuntimeController.EXTRA_STAGE, stage)
                .putExtra(GoarRuntimeController.EXTRA_PERCENT, percent)
                .putExtra(GoarRuntimeController.EXTRA_DETAIL, detail);
        sendBroadcast(update);
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager != null && !"error".equals(stage)) {
            manager.notify(NOTIFICATION_ID, notification(detail));
        }
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "GOAR Alpine installation",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Shows only verified Alpine rootfs installation progress");
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
        }
    }

    private Notification notification(String detail) {
        return new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentTitle("GOAR Alpine Private Vibe")
                .setContentText(detail)
                .setOngoing(true)
                .build();
    }

    @Override
    public void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
