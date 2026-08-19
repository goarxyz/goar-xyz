package com.goar.os;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class GoarRuntimeService extends Service {
    public static final String ACTION_SETUP_AND_START = "com.goar.os.action.SETUP_AND_START";
    public static final String ACTION_START = "com.goar.os.action.START";
    public static final String ACTION_STOP = "com.goar.os.action.STOP";
    public static final String EXTRA_MANIFEST_URL = "manifest_url";
    private static final String CHANNEL_ID = "goar_runtime";
    private static final int NOTIFICATION_ID = 1001;

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private GoarRuntimeController runtime;
    private Process loopDaemon;

    @Override
    public void onCreate() {
        super.onCreate();
        runtime = new GoarRuntimeController(this);
        createChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? ACTION_START : intent.getAction();
        if (ACTION_STOP.equals(action)) {
            stopLoopDaemon();
            emit("stopped", 0, "GOAR terminal service has stopped");
            stopForeground(STOP_FOREGROUND_REMOVE);
            stopSelf();
            return START_NOT_STICKY;
        }
        startForeground(NOTIFICATION_ID, notification("Preparing contained Kali terminal"));
        String requestedManifest = intent == null ? null : intent.getStringExtra(EXTRA_MANIFEST_URL);
        executor.execute(() -> run(action, requestedManifest));
        return START_STICKY;
    }

    private void run(String action, String requestedManifest) {
        try {
            if (ACTION_SETUP_AND_START.equals(action)) {
                if (requestedManifest != null && !requestedManifest.trim().isEmpty()) {
                    runtime.setManifestUrl(requestedManifest.trim());
                }
                runtime.install(this::emit);
            }
            if (!runtime.isInstalled()) {
                throw new IllegalStateException("Kali terminal rootfs is not installed");
            }
            ensureLoopDaemon();
            emit("running", 100, "Kali terminal and durable GOAR loops are active. Open Workspace to begin.");
        } catch (Exception error) {
            emit("error", 0, error.getMessage() == null ? error.toString() : error.getMessage());
            stopForeground(STOP_FOREGROUND_DETACH);
        }
    }

    private synchronized void ensureLoopDaemon() throws Exception {
        if (loopDaemon != null && loopDaemon.isAlive()) {
            return;
        }
        stopLoopDaemon();
        loopDaemon = runtime.startDurableLoopDaemon();
    }

    private synchronized void stopLoopDaemon() {
        if (loopDaemon == null) {
            return;
        }
        loopDaemon.destroy();
        try {
            Thread.sleep(500);
        } catch (InterruptedException ignored) {
            Thread.currentThread().interrupt();
        }
        if (loopDaemon.isAlive()) {
            loopDaemon.destroyForcibly();
        }
        loopDaemon = null;
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
                    "GOAR runtime",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Keeps the local GOAR Kali terminal sandbox available");
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
        }
    }

    private Notification notification(String detail) {
        return new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentTitle("GOAR OS")
                .setContentText(detail)
                .setOngoing(true)
                .build();
    }

    @Override
    public void onDestroy() {
        stopLoopDaemon();
        executor.shutdownNow();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
