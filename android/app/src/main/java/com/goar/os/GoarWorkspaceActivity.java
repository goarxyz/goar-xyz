package com.goar.os;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Native terminal-first workspace; there is no WebView, Flask server, or VNC path. */
public final class GoarWorkspaceActivity extends Activity {
    private static final int BLACK = Color.BLACK;
    private static final int WHITE = Color.rgb(245, 245, 245);
    private static final int MUTED = Color.rgb(164, 164, 164);
    private static final int SURFACE = Color.rgb(18, 18, 18);
    private static final int STROKE = Color.rgb(70, 70, 70);

    private final ExecutorService terminalExecutor = Executors.newSingleThreadExecutor();
    private GoarRuntimeController runtime;
    private GoarPtyBridge terminal;
    private GoarTerminalView terminalView;
    private TextView status;
    private Button reconnect;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        runtime = new GoarRuntimeController(this);
        setContentView(createContent());
        terminalView.post(this::openTerminal);
    }

    @Override
    protected void onDestroy() {
        if (terminal != null) terminal.close();
        terminalExecutor.shutdownNow();
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (terminalView != null) {
            terminalView.requestFocus();
            InputMethodManager manager = getSystemService(InputMethodManager.class);
            if (manager != null) manager.showSoftInput(terminalView, InputMethodManager.SHOW_IMPLICIT);
        }
        super.onBackPressed();
    }

    private View createContent() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(BLACK);

        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(14), dp(10), dp(14), dp(10));
        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.goar_logo);
        logo.setContentDescription("GOAR logo");
        logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        header.addView(logo, new LinearLayout.LayoutParams(dp(34), dp(34)));
        LinearLayout labels = new LinearLayout(this);
        labels.setOrientation(LinearLayout.VERTICAL);
        labels.setPadding(dp(10), 0, dp(8), 0);
        TextView title = text("GOAR", 17, WHITE);
        title.setLetterSpacing(0.10f);
        labels.addView(title);
        status = text("KALI TERMINAL · CONNECTING", 10, MUTED);
        status.setLetterSpacing(0.08f);
        labels.addView(status);
        header.addView(labels, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        Button close = button("RUNTIME", BLACK, WHITE, STROKE);
        close.setOnClickListener(view -> finish());
        header.addView(close, new LinearLayout.LayoutParams(dp(100), dp(42)));
        page.addView(header, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        View divider = new View(this);
        divider.setBackgroundColor(STROKE);
        page.addView(divider, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(1)));

        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        controls.setPadding(dp(10), dp(8), dp(10), dp(8));
        controls.setBackgroundColor(SURFACE);
        reconnect = button("RECONNECT", WHITE, BLACK, WHITE);
        reconnect.setOnClickListener(view -> openTerminal());
        controls.addView(reconnect, new LinearLayout.LayoutParams(0, dp(40), 1f));
        Button interrupt = button("CTRL-C", BLACK, WHITE, STROKE);
        interrupt.setOnClickListener(view -> { if (terminal != null) terminal.interrupt(); });
        controls.addView(interrupt, margin(new LinearLayout.LayoutParams(0, dp(40), 1f), dp(7), 0, 0, 0));
        Button clear = button("CLEAR", BLACK, WHITE, STROKE);
        clear.setOnClickListener(view -> { if (terminalView != null) terminalView.appendSystemLine("screen cleared by operator"); if (terminal != null) write("\u000c"); });
        controls.addView(clear, margin(new LinearLayout.LayoutParams(0, dp(40), 1f), dp(7), 0, 0, 0));
        page.addView(controls, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        terminalView = new GoarTerminalView(this);
        terminalView.setInputSink(new GoarTerminalView.InputSink() {
            @Override public void send(String value) { write(value); }
            @Override public void resize(int rows, int columns) { if (terminal != null) terminal.resize(rows, columns); }
        });
        page.addView(terminalView, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        return page;
    }

    private synchronized void openTerminal() {
        if (terminal != null && terminal.isAlive()) {
            terminalView.requestFocus();
            return;
        }
        if (terminal != null) terminal.close();
        reconnect.setEnabled(false);
        status.setText("KALI TERMINAL · STARTING PTY");
        terminalView.appendSystemLine("opening app-private Kali PRoot terminal…");
        terminalExecutor.execute(() -> {
            try {
                GoarPtyBridge opened = runtime.openTerminal(terminalView.terminalRows(), terminalView.terminalColumns());
                synchronized (this) { terminal = opened; }
                opened.startReader(new GoarPtyBridge.Listener() {
                    @Override public void onBytes(byte[] data, int length) { runOnUiThread(() -> terminalView.appendBytes(data, length)); }
                    @Override public void onClosed(int ignored) { runOnUiThread(() -> { status.setText("KALI TERMINAL · CLOSED"); reconnect.setEnabled(true); terminalView.appendSystemLine("terminal session closed"); }); }
                    @Override public void onError(Exception error) { runOnUiThread(() -> { status.setText("KALI TERMINAL · ERROR"); reconnect.setEnabled(true); terminalView.appendSystemLine("terminal error: " + error.getMessage()); }); }
                });
                runOnUiThread(() -> {
                    status.setText("KALI TERMINAL · PTY · LOOPS ACTIVE");
                    reconnect.setEnabled(true);
                    terminalView.requestFocus();
                    InputMethodManager manager = getSystemService(InputMethodManager.class);
                    if (manager != null) manager.showSoftInput(terminalView, InputMethodManager.SHOW_IMPLICIT);
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    status.setText("KALI TERMINAL · START FAILED");
                    reconnect.setEnabled(true);
                    terminalView.appendSystemLine("startup failed: " + (error.getMessage() == null ? error.toString() : error.getMessage()));
                });
            }
        });
    }

    private void write(String value) {
        terminalExecutor.execute(() -> {
            try {
                GoarPtyBridge session;
                synchronized (this) { session = terminal; }
                if (session != null) session.write(value);
            } catch (IOException error) {
                runOnUiThread(() -> terminalView.appendSystemLine("write failed: " + error.getMessage()));
            }
        });
    }

    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value); view.setTextSize(size); view.setTextColor(color); return view;
    }

    private Button button(String value, int fill, int foreground, int stroke) {
        Button result = new Button(this);
        result.setText(value); result.setTextSize(10); result.setAllCaps(false); result.setLetterSpacing(0.07f);
        result.setTextColor(foreground); result.setBackground(outline(fill, stroke, dp(1))); return result;
    }

    private GradientDrawable outline(int fill, int stroke, int width) {
        GradientDrawable drawable = new GradientDrawable(); drawable.setColor(fill); drawable.setStroke(width, stroke); return drawable;
    }

    private LinearLayout.LayoutParams margin(LinearLayout.LayoutParams value, int left, int top, int right, int bottom) {
        value.setMargins(left, top, right, bottom); return value;
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
