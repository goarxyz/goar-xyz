package com.goar.os;

import android.Manifest;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

public final class MainActivity extends Activity {
    private static final int REQUEST_NOTIFICATION = 101;
    private TextView status;
    private ProgressBar progress;
    private EditText manifestUrl;
    private WebView webView;
    private LinearLayout controlPanel;
    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String stage = intent.getStringExtra(GoarRuntimeController.EXTRA_STAGE);
            int percent = intent.getIntExtra(GoarRuntimeController.EXTRA_PERCENT, 0);
            String detail = intent.getStringExtra(GoarRuntimeController.EXTRA_DETAIL);
            updateStatus(stage, percent, detail);
            if ("running".equals(stage)) {
                openGoar();
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
                        ? "GOAR rootfs is installed. Start the local backend when ready."
                        : "Download the complete Alpine GOAR backend to begin.");
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
        controlPanel = new LinearLayout(this);
        controlPanel.setOrientation(LinearLayout.VERTICAL);
        controlPanel.setPadding(dp(20), dp(24), dp(20), dp(24));
        controlPanel.setBackgroundColor(Color.rgb(11, 16, 32));
        scroll.addView(controlPanel);

        TextView title = text("GOAR OS", 28, Color.WHITE);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        controlPanel.addView(title, matchWrap());
        TextView subtitle = text("Full Alpine backend in a private Android PRoot sandbox", 15, Color.rgb(190, 204, 235));
        subtitle.setGravity(Gravity.CENTER_HORIZONTAL);
        controlPanel.addView(subtitle, withMargins(matchWrap(), 0, dp(6), 0, dp(20)));

        TextView network = text("The rootfs has normal outbound network access for providers, browsing, downloads, and API calls. Its files, workspace, state, and temporary data remain inside this app.", 14, Color.rgb(211, 220, 240));
        controlPanel.addView(network, withMargins(matchWrap(), 0, 0, 0, dp(18)));

        TextView endpointLabel = text("Rootfs manifest URL", 14, Color.WHITE);
        controlPanel.addView(endpointLabel, matchWrap());
        manifestUrl = new EditText(this);
        manifestUrl.setSingleLine(true);
        manifestUrl.setTextColor(Color.WHITE);
        manifestUrl.setTextSize(13);
        manifestUrl.setHintTextColor(Color.rgb(155, 170, 205));
        manifestUrl.setHint("https://…/goar-rootfs-arm64-v8a.json");
        manifestUrl.setBackgroundColor(Color.rgb(26, 36, 66));
        manifestUrl.setPadding(dp(12), dp(10), dp(12), dp(10));
        controlPanel.addView(manifestUrl, withMargins(matchWrap(), 0, dp(6), 0, dp(16)));

        Button setup = button("Download full GOAR backend and start", Color.rgb(32, 87, 212));
        setup.setOnClickListener(view -> requestSetup());
        controlPanel.addView(setup, matchWrap());

        Button start = button("Start installed backend", Color.rgb(35, 125, 89));
        start.setOnClickListener(view -> requestStart());
        controlPanel.addView(start, withMargins(matchWrap(), 0, dp(10), 0, 0));

        Button open = button("Open local GOAR interface", Color.rgb(81, 62, 170));
        open.setOnClickListener(view -> openGoar());
        controlPanel.addView(open, withMargins(matchWrap(), 0, dp(10), 0, 0));

        Button stop = button("Stop local backend", Color.rgb(135, 48, 58));
        stop.setOnClickListener(view -> {
            Intent intent = new Intent(this, GoarRuntimeService.class).setAction(GoarRuntimeService.ACTION_STOP);
            startService(intent);
        });
        controlPanel.addView(stop, withMargins(matchWrap(), 0, dp(10), 0, dp(18)));

        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        controlPanel.addView(progress, matchWrap());
        status = text("", 14, Color.rgb(218, 225, 244));
        controlPanel.addView(status, withMargins(matchWrap(), 0, dp(10), 0, 0));

        webView = new WebView(this);
        webView.setVisibility(View.GONE);
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setAllowFileAccess(false);
        webView.getSettings().setAllowContentAccess(false);
        webView.setWebViewClient(new WebViewClient());
        controlPanel.addView(webView, withMargins(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(620)), 0, dp(20), 0, 0));
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

    private void openGoar() {
        webView.setVisibility(View.VISIBLE);
        webView.loadUrl("http://127.0.0.1:8080/");
    }

    private void updateStatus(String stage, int percent, String detail) {
        progress.setProgress(Math.max(0, Math.min(100, percent)));
        String title = stage == null ? "status" : stage.replace('_', ' ');
        status.setText(title.toUpperCase() + "\n" + (detail == null ? "" : detail));
    }

    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        return view;
    }

    private Button button(String value, int color) {
        Button button = new Button(this);
        button.setText(value);
        button.setTextColor(Color.WHITE);
        button.setTextSize(14);
        button.setAllCaps(false);
        button.setBackgroundColor(color);
        button.setPadding(dp(8), dp(12), dp(8), dp(12));
        return button;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams withMargins(LinearLayout.LayoutParams params, int left, int top, int right, int bottom) {
        params.setMargins(left, top, right, bottom);
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
