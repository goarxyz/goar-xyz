package com.goar.os;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Full-screen local operator workspace. GOAR and the shared noVNC computer are
 * separate, explicit views of the same loopback-only backend.
 */
public final class GoarWorkspaceActivity extends Activity {
    private static final int BLACK = Color.BLACK;
    private static final int WHITE = Color.rgb(245, 245, 245);
    private static final int MUTED = Color.rgb(164, 164, 164);
    private static final int SURFACE = Color.rgb(18, 18, 18);
    private static final int STROKE = Color.rgb(70, 70, 70);
    private static final String GOAR_URL = "http://127.0.0.1:8080/";
    // The local websockify service is the verified direct noVNC path. It
    // avoids Flask/Gunicorn WebSocket-upgrade limitations on the GOAR port.
    private static final String COMPUTER_URL = "http://127.0.0.1:6080/vnc.html?autoconnect=true&reconnect=true&resize=scale&path=websockify";

    private WebView webView;
    private TextView modeLabel;
    private Button goarButton;
    private Button computerButton;
    private final ExecutorService runtimeExecutor = Executors.newSingleThreadExecutor();

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(createContent());
        showGoar();
    }

    @Override
    protected void onDestroy() {
        runtimeExecutor.shutdownNow();
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }

    private View createContent() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(BLACK);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(14), dp(10), dp(14), dp(10));
        header.setBackgroundColor(BLACK);

        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.goar_logo);
        logo.setContentDescription("GOAR logo");
        logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        header.addView(logo, new LinearLayout.LayoutParams(dp(36), dp(36)));

        LinearLayout titleColumn = new LinearLayout(this);
        titleColumn.setOrientation(LinearLayout.VERTICAL);
        titleColumn.setPadding(dp(10), 0, dp(8), 0);
        TextView title = text("GOAR", 17, WHITE);
        title.setLetterSpacing(0.10f);
        titleColumn.addView(title);
        modeLabel = text("LOCAL OPERATOR", 10, MUTED);
        modeLabel.setLetterSpacing(0.08f);
        titleColumn.addView(modeLabel);
        header.addView(titleColumn, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        Button runtime = button("RUNTIME", BLACK, WHITE, STROKE);
        runtime.setOnClickListener(view -> finish());
        header.addView(runtime, new LinearLayout.LayoutParams(dp(100), dp(42)));
        page.addView(header, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        View divider = new View(this);
        divider.setBackgroundColor(STROKE);
        page.addView(divider, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(1)));

        LinearLayout modes = new LinearLayout(this);
        modes.setOrientation(LinearLayout.HORIZONTAL);
        modes.setPadding(dp(14), dp(10), dp(14), dp(10));
        modes.setBackgroundColor(SURFACE);
        goarButton = button("GOAR", WHITE, BLACK, WHITE);
        goarButton.setOnClickListener(view -> showGoar());
        modes.addView(goarButton, new LinearLayout.LayoutParams(0, dp(42), 1f));
        computerButton = button("COMPUTER", BLACK, WHITE, STROKE);
        computerButton.setOnClickListener(view -> showComputer());
        modes.addView(computerButton, withMargins(new LinearLayout.LayoutParams(0, dp(42), 1f), dp(8), 0, 0, 0));
        page.addView(modes, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        webView = new WebView(this);
        webView.setBackgroundColor(BLACK);
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setAllowFileAccess(false);
        webView.getSettings().setAllowContentAccess(false);
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
            webView.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
            }
        });
        page.addView(webView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        return page;
    }

    private void showGoar() {
        modeLabel.setText("LOCAL OPERATOR · 127.0.0.1");
        select(goarButton, true);
        select(computerButton, false);
        webView.loadUrl(GOAR_URL);
    }

    private void showComputer() {
        modeLabel.setText("STARTING SHARED COMPUTER · VNC");
        select(goarButton, false);
        select(computerButton, true);
        computerButton.setEnabled(false);
        webView.loadDataWithBaseURL(null,
                "<html><body style='background:#000;color:#f5f5f5;font-family:sans-serif;text-align:center;padding-top:30vh'>Starting local computer…</body></html>",
                "text/html", "UTF-8", null);
        runtimeExecutor.execute(() -> {
            boolean started = false;
            try {
                HttpURLConnection connection = (HttpURLConnection) new URL("http://127.0.0.1:8080/v1/desktop/start").openConnection();
                connection.setRequestMethod("POST");
                connection.setDoOutput(true);
                connection.setConnectTimeout(8_000);
                connection.setReadTimeout(30_000);
                connection.getOutputStream().close();
                started = connection.getResponseCode() == 200;
                connection.disconnect();
            } catch (Exception ignored) {
                started = false;
            }
            final boolean ready = started;
            runOnUiThread(() -> {
                computerButton.setEnabled(true);
                if (ready) {
                    modeLabel.setText("SHARED COMPUTER · VNC");
                    webView.loadUrl(COMPUTER_URL);
                } else {
                    modeLabel.setText("COMPUTER UNAVAILABLE · RETURN TO RUNTIME");
                    webView.loadDataWithBaseURL(null,
                            "<html><body style='background:#000;color:#f5f5f5;font-family:sans-serif;text-align:center;padding:30vh 10vw'>The local computer did not start. Return to Runtime, start GOAR, and try again.</body></html>",
                            "text/html", "UTF-8", null);
                }
            });
        });
    }

    private void select(Button button, boolean selected) {
        button.setTextColor(selected ? BLACK : WHITE);
        button.setBackground(outline(selected ? WHITE : BLACK, selected ? WHITE : STROKE, dp(1)));
    }

    private Button button(String value, int fill, int foreground, int stroke) {
        Button button = new Button(this);
        button.setText(value);
        button.setTextSize(11);
        button.setAllCaps(false);
        button.setLetterSpacing(0.08f);
        button.setTextColor(foreground);
        button.setBackground(outline(fill, stroke, dp(1)));
        return button;
    }

    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        return view;
    }

    private GradientDrawable outline(int fill, int stroke, int width) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setStroke(width, stroke);
        return drawable;
    }

    private LinearLayout.LayoutParams withMargins(LinearLayout.LayoutParams params, int left, int top, int right, int bottom) {
        params.setMargins(left, top, right, bottom);
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
