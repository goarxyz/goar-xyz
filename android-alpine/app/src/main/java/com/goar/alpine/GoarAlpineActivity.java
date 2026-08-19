package com.goar.alpine;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.TextView;

/**
 * The Alpine edition intentionally exposes one surface only: the upstream
 * Mistral Vibe Textual TUI inside a native PTY. Installation progress is an
 * overlay, never text injected into the guest terminal stream.
 */
public final class GoarAlpineActivity extends Activity {
    private static final int BLACK = Color.BLACK;
    private static final int WHITE = Color.rgb(238, 238, 238);
    private static final int MUTED = Color.rgb(160, 160, 160);

    private GoarRuntimeController runtime;
    private GoarTerminalView terminal;
    private TextView installOverlay;
    private GoarPtyBridge terminalSession;
    private boolean installRequested;
    private boolean terminalStarting;

    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String stage = intent.getStringExtra(GoarRuntimeController.EXTRA_STAGE);
            int percent = intent.getIntExtra(GoarRuntimeController.EXTRA_PERCENT, 0);
            String detail = intent.getStringExtra(GoarRuntimeController.EXTRA_DETAIL);
            if ("running".equals(stage)) {
                showInstallOverlay(null);
                startTerminal();
            } else if ("error".equals(stage)) {
                installRequested = false;
                showInstallOverlay(detail == null ? "Installation failed" : detail);
            } else {
                String prefix = detail == null ? "Preparing private Alpine terminal" : detail;
                showInstallOverlay(percent > 0 ? prefix + "\n\n" + percent + "%" : prefix);
            }
        }
    };

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        runtime = new GoarRuntimeController(this);
        hideSystemBars();
        setContentView(createContent());
        if (runtime.isInstalled()) {
            showInstallOverlay(null);
            terminal.post(this::startTerminal);
        } else {
            showInstallOverlay("Preparing private Alpine terminal");
            requestInstall();
        }
    }

    @Override
    protected void onStart() {
        super.onStart();
        IntentFilter filter = new IntentFilter(GoarRuntimeController.ACTION_STATUS);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(statusReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(statusReceiver, filter);
        }
    }

    @Override
    protected void onStop() {
        unregisterReceiver(statusReceiver);
        super.onStop();
    }

    @Override
    protected void onResume() {
        super.onResume();
        hideSystemBars();
        if (runtime != null && runtime.isInstalled() && terminalSession == null && !terminalStarting) {
            terminal.post(this::startTerminal);
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemBars();
    }

    @Override
    protected void onDestroy() {
        if (isFinishing() && terminalSession != null) {
            terminalSession.close();
            terminalSession = null;
        }
        super.onDestroy();
    }

    private View createContent() {
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(BLACK);
        terminal = new GoarTerminalView(this);
        root.addView(terminal, new FrameLayout.LayoutParams(-1, -1));

        installOverlay = new TextView(this);
        installOverlay.setTextColor(MUTED);
        installOverlay.setTextSize(13);
        installOverlay.setGravity(Gravity.CENTER);
        installOverlay.setLetterSpacing(0.05f);
        installOverlay.setLineSpacing(dp(5), 1f);
        installOverlay.setPadding(dp(28), dp(28), dp(28), dp(28));
        root.addView(installOverlay, new FrameLayout.LayoutParams(-1, -1));
        return root;
    }

    private void requestInstall() {
        if (installRequested) return;
        installRequested = true;
        Intent intent = new Intent(this, GoarRuntimeService.class)
                .setAction(GoarRuntimeService.ACTION_INSTALL);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent);
        } else {
            startService(intent);
        }
    }

    private void startTerminal() {
        if (terminalStarting || terminalSession != null || !runtime.isInstalled()) return;
        terminalStarting = true;
        try {
            GoarPtyBridge session = runtime.openVibeTerminal(
                    terminal.terminalRows(), terminal.terminalColumns());
            terminal.setInputSink(new GoarTerminalView.InputSink() {
                @Override
                public void send(String value) {
                    try {
                        session.write(value);
                    } catch (Exception ignored) {
                        // The session-close callback updates the visible state.
                    }
                }

                @Override
                public void resize(int rows, int columns) {
                    session.resize(rows, columns);
                }
            });
            terminalSession = session;
            showInstallOverlay(null);
            terminal.requestFocus();
            session.startReader(new GoarPtyBridge.Listener() {
                @Override
                public void onBytes(byte[] data, int length) {
                    runOnUiThread(() -> terminal.appendBytes(data, length));
                }

                @Override
                public void onClosed(int exitSignal) {
                    runOnUiThread(() -> {
                        terminalSession = null;
                        terminalStarting = false;
                        showInstallOverlay("Terminal session ended");
                    });
                }

                @Override
                public void onError(Exception error) {
                    runOnUiThread(() -> {
                        terminalSession = null;
                        terminalStarting = false;
                        showInstallOverlay(error.getMessage() == null ? "Terminal failed" : error.getMessage());
                    });
                }
            });
        } catch (Exception error) {
            terminalStarting = false;
            showInstallOverlay(error.getMessage() == null ? "Terminal failed to start" : error.getMessage());
        }
    }

    private void showInstallOverlay(String message) {
        if (message == null || message.trim().isEmpty()) {
            installOverlay.setVisibility(View.GONE);
        } else {
            installOverlay.setText(message);
            installOverlay.setVisibility(View.VISIBLE);
        }
    }

    @SuppressWarnings("deprecation")
    private void hideSystemBars() {
        getWindow().setStatusBarColor(BLACK);
        getWindow().setNavigationBarColor(BLACK);
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
