package com.goar.os;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Read-only durable GOAR control views; command output is isolated from both terminal workspaces. */
public final class GoarControlActivity extends Activity {
    private static final int BLACK = Color.BLACK;
    private static final int WHITE = Color.rgb(245, 245, 245);
    private static final int MUTED = Color.rgb(164, 164, 164);
    private static final int SURFACE = Color.rgb(18, 18, 18);
    private static final int STROKE = Color.rgb(70, 70, 70);
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private GoarRuntimeController runtime;
    private GoarPtyBridge session;
    private GoarTerminalView output;
    private TextView status;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        runtime = new GoarRuntimeController(this);
        setContentView(createContent());
        output.post(() -> run("goarctl status", "STATUS"));
    }

    @Override protected void onDestroy() { if (session != null) session.close(); executor.shutdownNow(); super.onDestroy(); }

    private View createContent() {
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL); page.setBackgroundColor(BLACK);
        LinearLayout header = new LinearLayout(this); header.setGravity(Gravity.CENTER_VERTICAL); header.setPadding(dp(16), dp(14), dp(16), dp(10));
        LinearLayout words = new LinearLayout(this); words.setOrientation(LinearLayout.VERTICAL);
        TextView title = text("CONTROL", 20, WHITE); title.setLetterSpacing(0.08f); words.addView(title);
        status = text("DURABLE LOCAL STATE", 10, MUTED); status.setLetterSpacing(0.08f); words.addView(status);
        header.addView(words, new LinearLayout.LayoutParams(0, -2, 1f));
        Button close = button("CONSOLE", BLACK, WHITE, STROKE); close.setOnClickListener(view -> finish()); header.addView(close, new LinearLayout.LayoutParams(dp(100), dp(42)));
        page.addView(header, new LinearLayout.LayoutParams(-1, -2));
        View line = new View(this); line.setBackgroundColor(STROKE); page.addView(line, new LinearLayout.LayoutParams(-1, dp(1)));
        LinearLayout actions = new LinearLayout(this); actions.setPadding(dp(10), dp(9), dp(10), dp(9)); actions.setBackgroundColor(SURFACE);
        addAction(actions, "STATUS", () -> run("goarctl status", "STATUS"));
        addAction(actions, "LOOPS", () -> run("goarctl loop list", "LOOPS"));
        addAction(actions, "PLAN", () -> run("goarctl plan show", "PLAN"));
        addAction(actions, "EVENTS", () -> run("goarctl events --limit 25", "EVENTS"));
        page.addView(actions, new LinearLayout.LayoutParams(-1, dp(58)));
        output = new GoarTerminalView(this); output.setInputSink(new GoarTerminalView.InputSink() { @Override public void send(String ignored) {} @Override public void resize(int rows, int columns) { if (session != null) session.resize(rows, columns); } });
        page.addView(output, new LinearLayout.LayoutParams(-1, 0, 1f));
        return page;
    }

    private synchronized void run(String command, String label) {
        if (session != null) session.close();
        status.setText(label + " · LOADING");
        executor.execute(() -> {
            try {
                GoarPtyBridge opened = runtime.openManagedCommandTerminal(command, output.terminalRows(), output.terminalColumns());
                synchronized (this) { session = opened; }
                opened.startReader(new GoarPtyBridge.Listener() {
                    @Override public void onBytes(byte[] data, int length) { runOnUiThread(() -> output.appendBytes(data, length)); }
                    @Override public void onClosed(int code) { runOnUiThread(() -> status.setText(label + " · COMPLETE")); }
                    @Override public void onError(Exception error) { runOnUiThread(() -> status.setText(label + " · ERROR")); }
                });
            } catch (Exception error) {
                runOnUiThread(() -> status.setText(label + " · ERROR"));
            }
        });
    }

    private void addAction(LinearLayout parent, String label, Runnable action) { Button button = button(label, BLACK, WHITE, STROKE); button.setOnClickListener(view -> action.run()); parent.addView(button, new LinearLayout.LayoutParams(0, dp(40), 1f)); }
    private TextView text(String value, int size, int color) { TextView result = new TextView(this); result.setText(value); result.setTextSize(size); result.setTextColor(color); return result; }
    private Button button(String value, int fill, int foreground, int stroke) { Button result = new Button(this); result.setText(value); result.setTextSize(10); result.setAllCaps(false); result.setLetterSpacing(0.06f); result.setTextColor(foreground); result.setBackground(outline(fill, stroke, dp(1))); return result; }
    private GradientDrawable outline(int fill, int stroke, int width) { GradientDrawable result = new GradientDrawable(); result.setColor(fill); result.setStroke(width, stroke); return result; }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
