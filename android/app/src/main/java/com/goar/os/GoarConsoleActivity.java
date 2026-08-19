package com.goar.os;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Native monochrome navigation shell. Each operator workflow owns a separate screen. */
public final class GoarConsoleActivity extends Activity {
    private static final int BLACK = Color.BLACK;
    private static final int WHITE = Color.rgb(245, 245, 245);
    private static final int MUTED = Color.rgb(164, 164, 164);
    private static final int SURFACE = Color.rgb(18, 18, 18);
    private static final int STROKE = Color.rgb(70, 70, 70);

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (!new GoarRuntimeController(this).isInstalled()) {
            finish();
            return;
        }
        setContentView(createContent());
    }

    private View createContent() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BLACK);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(18), dp(22), dp(18), dp(28));
        page.setBackgroundColor(BLACK);
        scroll.addView(page, new ScrollView.LayoutParams(-1, -1));

        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.goar_logo);
        logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        header.addView(logo, new LinearLayout.LayoutParams(dp(46), dp(46)));
        LinearLayout words = new LinearLayout(this);
        words.setOrientation(LinearLayout.VERTICAL);
        words.setPadding(dp(12), 0, 0, 0);
        TextView title = text("GOAR OPERATOR", 22, WHITE);
        title.setLetterSpacing(0.08f);
        words.addView(title);
        TextView subtitle = text("KALI PRoot · LOCAL CONTROL PLANE", 10, MUTED);
        subtitle.setLetterSpacing(0.08f);
        words.addView(subtitle);
        header.addView(words, new LinearLayout.LayoutParams(0, -2, 1f));
        Button runtime = button("RUNTIME", BLACK, WHITE, STROKE);
        runtime.setOnClickListener(view -> startActivity(new Intent(this, MainActivity.class)));
        header.addView(runtime, new LinearLayout.LayoutParams(dp(104), dp(42)));
        page.addView(header, new LinearLayout.LayoutParams(-1, -2));

        page.addView(divider(), margin(new LinearLayout.LayoutParams(-1, dp(1)), 0, dp(18), 0, dp(14)));
        TextView note = text("Choose a separate workspace. Direct Terminal never receives agent, package, or control-panel output.", 12, MUTED);
        note.setLineSpacing(dp(3), 1f);
        page.addView(note, margin(new LinearLayout.LayoutParams(-1, -2), 0, 0, 0, dp(16)));

        addCard(page, "TERMINAL", "Clean direct Kali shell for your own commands and scripts.", () -> openWorkspace(GoarWorkspaceActivity.MODE_TERMINAL));
        addCard(page, "AGENT CHAT", "Dedicated GOAR/VibeHack conversation with plans, tools, and checkpoints.", () -> openWorkspace(GoarWorkspaceActivity.MODE_AGENT));
        addCard(page, "CONTROL", "Inspect durable sessions, plans, loops, checkpoints, and events.", () -> startActivity(new Intent(this, GoarControlActivity.class)));
        addCard(page, "KALI PACKAGES", "Review and run explicit APT installs in a separate package workspace.", () -> startActivity(new Intent(this, GoarPackageActivity.class)));
        addCard(page, "CONFIGURATION", "Set provider key, model, and local operator preferences.", () -> startActivity(new Intent(this, GoarConfigActivity.class)));
        addCard(page, "RUNTIME", "Backend installation, manifest source, status, and durable service controls.", () -> startActivity(new Intent(this, MainActivity.class)));
        return scroll;
    }

    private void openWorkspace(String mode) {
        Intent intent = new Intent(this, GoarWorkspaceActivity.class).putExtra(GoarWorkspaceActivity.EXTRA_MODE, mode);
        startActivity(intent);
    }

    private void addCard(LinearLayout page, String heading, String detail, Runnable action) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(15), dp(13), dp(15), dp(13));
        card.setBackground(outline(SURFACE, STROKE, dp(1)));
        TextView title = text(heading, 14, WHITE);
        title.setLetterSpacing(0.09f);
        card.addView(title);
        TextView body = text(detail, 12, MUTED);
        body.setLineSpacing(dp(2), 1f);
        card.addView(body, margin(new LinearLayout.LayoutParams(-1, -2), 0, dp(5), 0, 0));
        card.setOnClickListener(view -> action.run());
        page.addView(card, margin(new LinearLayout.LayoutParams(-1, -2), 0, 0, 0, dp(9)));
    }

    private TextView text(String value, int size, int color) {
        TextView result = new TextView(this); result.setText(value); result.setTextSize(size); result.setTextColor(color); return result;
    }
    private Button button(String value, int fill, int foreground, int stroke) {
        Button result = new Button(this); result.setText(value); result.setTextSize(10); result.setAllCaps(false); result.setLetterSpacing(0.07f); result.setTextColor(foreground); result.setBackground(outline(fill, stroke, dp(1))); return result;
    }
    private View divider() { View view = new View(this); view.setBackgroundColor(STROKE); return view; }
    private GradientDrawable outline(int fill, int stroke, int width) { GradientDrawable result = new GradientDrawable(); result.setColor(fill); result.setStroke(width, stroke); return result; }
    private LinearLayout.LayoutParams margin(LinearLayout.LayoutParams params, int left, int top, int right, int bottom) { params.setMargins(left, top, right, bottom); return params; }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
