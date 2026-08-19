package com.goar.os;

import android.Manifest;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

/**
 * Native installation and runtime-status screen. The actual GOAR workspace is
 * intentionally hosted by GoarWorkspaceActivity so install controls and the
 * local operator UI never compete for the same screen.
 */
public final class MainActivity extends Activity {
    private static final int REQUEST_NOTIFICATION = 101;
    private static final int BLACK = Color.BLACK;
    private static final int WHITE = Color.rgb(245, 245, 245);
    private static final int MUTED = Color.rgb(164, 164, 164);
    private static final int SURFACE = Color.rgb(18, 18, 18);
    private static final int STROKE = Color.rgb(70, 70, 70);

    private TextView status;
    private TextView stateLabel;
    private ProgressBar progress;
    private EditText manifestUrl;
    private Button installButton;
    private Button startButton;
    private Button workspaceButton;

    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String stage = intent.getStringExtra(GoarRuntimeController.EXTRA_STAGE);
            int percent = intent.getIntExtra(GoarRuntimeController.EXTRA_PERCENT, 0);
            String detail = intent.getStringExtra(GoarRuntimeController.EXTRA_DETAIL);
            updateStatus(stage, percent, detail);
            if ("running".equals(stage)) {
                openWorkspace();
            }
        }
    };

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQUEST_NOTIFICATION);
        }
        setContentView(createContent());
        GoarRuntimeController controller = new GoarRuntimeController(this);
        manifestUrl.setText(controller.configuredManifestUrl());
        updateStatus(controller.isInstalled() ? "installed" : "setup", 0,
                controller.isInstalled()
                        ? "The verified Alpine backend is installed locally."
                        : "Install the verified full GOAR backend to this device.");
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

    private View createContent() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BLACK);

        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setGravity(Gravity.CENTER_HORIZONTAL);
        page.setPadding(dp(24), dp(34), dp(24), dp(28));
        page.setBackgroundColor(BLACK);
        scroll.addView(page, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.MATCH_PARENT));

        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.goar_logo);
        logo.setContentDescription("GOAR logo");
        logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        page.addView(logo, centered(dp(96), dp(96)));

        TextView product = text("GOAR OS", 30, WHITE);
        product.setLetterSpacing(0.08f);
        product.setGravity(Gravity.CENTER);
        page.addView(product, withMargins(matchWrap(), 0, dp(18), 0, 0));

        TextView edition = text("LOCAL OPERATOR · PRIVATE ROOTFS", 11, MUTED);
        edition.setLetterSpacing(0.10f);
        edition.setGravity(Gravity.CENTER);
        page.addView(edition, withMargins(matchWrap(), 0, dp(8), 0, dp(26)));

        page.addView(divider(), matchWrapHeight(dp(1)));

        TextView section = text("BACKEND INSTALLATION", 12, WHITE);
        section.setLetterSpacing(0.10f);
        page.addView(section, withMargins(matchWrap(), 0, dp(26), 0, dp(10)));

        stateLabel = text("", 12, MUTED);
        stateLabel.setLetterSpacing(0.08f);
        page.addView(stateLabel, matchWrap());

        status = text("", 15, WHITE);
        status.setLineSpacing(dp(3), 1f);
        page.addView(status, withMargins(matchWrap(), 0, dp(7), 0, dp(16)));

        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgressTintList(android.content.res.ColorStateList.valueOf(WHITE));
        progress.setBackgroundTintList(android.content.res.ColorStateList.valueOf(STROKE));
        page.addView(progress, matchWrapHeight(dp(4)));

        TextView manifestLabel = text("ROOTFS MANIFEST", 11, MUTED);
        manifestLabel.setLetterSpacing(0.10f);
        page.addView(manifestLabel, withMargins(matchWrap(), 0, dp(26), 0, dp(8)));

        manifestUrl = new EditText(this);
        manifestUrl.setSingleLine(true);
        manifestUrl.setTextColor(WHITE);
        manifestUrl.setTextSize(12);
        manifestUrl.setHintTextColor(MUTED);
        manifestUrl.setHint("https://…/goar-rootfs-arm64-v8a.json");
        manifestUrl.setSelectAllOnFocus(false);
        manifestUrl.setPadding(dp(14), dp(10), dp(14), dp(10));
        manifestUrl.setBackground(outline(SURFACE, STROKE, dp(1)));
        page.addView(manifestUrl, matchWrap());

        installButton = button("INSTALL & START", WHITE, BLACK, WHITE);
        installButton.setOnClickListener(view -> requestSetup());
        page.addView(installButton, withMargins(matchWrapHeight(dp(54)), 0, dp(20), 0, 0));

        startButton = button("START INSTALLED BACKEND", BLACK, WHITE, STROKE);
        startButton.setOnClickListener(view -> requestStart());
        page.addView(startButton, withMargins(matchWrapHeight(dp(54)), 0, dp(10), 0, 0));

        workspaceButton = button("OPEN WORKSPACE", BLACK, WHITE, STROKE);
        workspaceButton.setOnClickListener(view -> openWorkspace());
        page.addView(workspaceButton, withMargins(matchWrapHeight(dp(54)), 0, dp(10), 0, 0));

        TextView privacy = text("The backend, workspace, state, and temporary files remain in GOAR OS app-private storage. The local backend can make normal outbound network connections.", 12, MUTED);
        privacy.setGravity(Gravity.CENTER);
        privacy.setLineSpacing(dp(3), 1f);
        page.addView(privacy, withMargins(matchWrap(), 0, dp(28), 0, 0));

        TextView stop = text("STOP LOCAL BACKEND", 12, MUTED);
        stop.setGravity(Gravity.CENTER);
        stop.setLetterSpacing(0.08f);
        stop.setPadding(dp(8), dp(20), dp(8), dp(8));
        stop.setOnClickListener(view -> {
            Intent intent = new Intent(this, GoarRuntimeService.class).setAction(GoarRuntimeService.ACTION_STOP);
            startService(intent);
            updateStatus("stopping", 0, "Stopping the local backend");
        });
        page.addView(stop, matchWrap());
        return scroll;
    }

    private void requestSetup() {
        String endpoint = manifestUrl.getText().toString().trim();
        try {
            new GoarRuntimeController(this).setManifestUrl(endpoint);
        } catch (IllegalArgumentException error) {
            updateStatus("error", 0, error.getMessage());
            return;
        }
        Intent intent = new Intent(this, GoarRuntimeService.class)
                .setAction(GoarRuntimeService.ACTION_SETUP_AND_START)
                .putExtra(GoarRuntimeService.EXTRA_MANIFEST_URL, endpoint);
        startRuntimeService(intent);
        updateStatus("manifest", 0, "Preparing verified full-backend download");
    }

    private void requestStart() {
        Intent intent = new Intent(this, GoarRuntimeService.class).setAction(GoarRuntimeService.ACTION_START);
        startRuntimeService(intent);
        updateStatus("starting", 0, "Starting the installed GOAR backend");
    }

    private void startRuntimeService(Intent intent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent);
        } else {
            startService(intent);
        }
    }

    private void openWorkspace() {
        startActivity(new Intent(this, GoarWorkspaceActivity.class));
    }

    private void updateStatus(String stage, int percent, String detail) {
        int bounded = Math.max(0, Math.min(100, percent));
        progress.setProgress(bounded);
        String heading = stage == null ? "STATUS" : stage.replace('_', ' ').toUpperCase();
        stateLabel.setText(heading + (bounded > 0 ? " · " + bounded + "%" : ""));
        status.setText(detail == null ? "" : detail);
        boolean running = "running".equals(stage);
        boolean installed = "installed".equals(stage) || running;
        installButton.setEnabled(!running);
        startButton.setEnabled(installed && !running);
        workspaceButton.setEnabled(running || installed);
        installButton.setAlpha(running ? 0.5f : 1f);
        startButton.setAlpha(startButton.isEnabled() ? 1f : 0.45f);
        workspaceButton.setAlpha(workspaceButton.isEnabled() ? 1f : 0.45f);
    }

    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        return view;
    }

    private Button button(String value, int fill, int foreground, int stroke) {
        Button button = new Button(this);
        button.setText(value);
        button.setTextColor(foreground);
        button.setTextSize(13);
        button.setAllCaps(false);
        button.setLetterSpacing(0.06f);
        button.setBackground(outline(fill, stroke, dp(1)));
        return button;
    }

    private View divider() {
        View line = new View(this);
        line.setBackgroundColor(STROKE);
        return line;
    }

    private GradientDrawable outline(int fill, int stroke, int width) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setStroke(width, stroke);
        return drawable;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams matchWrapHeight(int height) {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, height);
    }

    private LinearLayout.LayoutParams centered(int width, int height) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(width, height);
        params.gravity = Gravity.CENTER_HORIZONTAL;
        return params;
    }

    private LinearLayout.LayoutParams withMargins(LinearLayout.LayoutParams params, int left, int top, int right, int bottom) {
        params.setMargins(left, top, right, bottom);
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
