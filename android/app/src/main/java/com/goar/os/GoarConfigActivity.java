package com.goar.os;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** App-private provider configuration, intentionally independent of the terminal and agent chat. */
public final class GoarConfigActivity extends Activity {
    private static final int BLACK = Color.BLACK;
    private static final int WHITE = Color.rgb(245, 245, 245);
    private static final int MUTED = Color.rgb(164, 164, 164);
    private static final int SURFACE = Color.rgb(18, 18, 18);
    private static final int STROKE = Color.rgb(70, 70, 70);
    private GoarRuntimeController runtime;
    private EditText key;
    private EditText model;
    private TextView status;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        runtime = new GoarRuntimeController(this);
        setContentView(createContent());
    }

    private View createContent() {
        ScrollView scroll = new ScrollView(this); scroll.setFillViewport(true); scroll.setBackgroundColor(BLACK);
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL); page.setPadding(dp(18), dp(22), dp(18), dp(28)); page.setBackgroundColor(BLACK);
        scroll.addView(page, new ScrollView.LayoutParams(-1, -1));
        page.addView(header("CONFIGURATION", "APP-PRIVATE AGENT SETTINGS"));
        TextView note = text("The provider key is never shown after saving. It is stored only in GOAR OS private storage and loaded by Agent Chat, not by Direct Terminal.", 12, MUTED);
        note.setLineSpacing(dp(3), 1f); page.addView(note, margin(new LinearLayout.LayoutParams(-1, -2), 0, dp(20), 0, dp(18)));
        page.addView(label("PROVIDER API KEY"));
        key = field("Paste a new key to set or replace it");
        key.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        page.addView(key, margin(new LinearLayout.LayoutParams(-1, -2), 0, dp(7), 0, dp(16)));
        page.addView(label("MODEL"));
        model = field("Provider model identifier");
        model.setText(runtime.configuredAgentModel());
        page.addView(model, margin(new LinearLayout.LayoutParams(-1, -2), 0, dp(7), 0, dp(18)));
        Button save = button("SAVE APP-PRIVATE CONFIGURATION", WHITE, BLACK, WHITE);
        save.setOnClickListener(view -> save());
        page.addView(save, new LinearLayout.LayoutParams(-1, dp(52)));
        status = text(runtime.hasAgentApiKey() ? "Provider key is configured." : "No provider key has been configured yet.", 12, MUTED);
        status.setLineSpacing(dp(3), 1f); page.addView(status, margin(new LinearLayout.LayoutParams(-1, -2), 0, dp(16), 0, 0));
        return scroll;
    }

    private void save() {
        try {
            runtime.saveAgentConfiguration(key.getText().toString(), model.getText().toString());
            key.setText("");
            status.setText(runtime.hasAgentApiKey() ? "Saved. Provider key is configured in private storage." : "Saved model preference. Add a provider key to use Agent Chat.");
        } catch (Exception error) {
            status.setText("Configuration error: " + (error.getMessage() == null ? error.toString() : error.getMessage()));
        }
    }

    private View header(String title, String subtitle) { LinearLayout block = new LinearLayout(this); block.setOrientation(LinearLayout.VERTICAL); TextView a = text(title, 22, WHITE); a.setLetterSpacing(0.08f); block.addView(a); TextView b = text(subtitle, 10, MUTED); b.setLetterSpacing(0.08f); block.addView(b); return block; }
    private TextView label(String value) { TextView result = text(value, 11, MUTED); result.setLetterSpacing(0.09f); return result; }
    private EditText field(String hint) { EditText result = new EditText(this); result.setSingleLine(true); result.setTextColor(WHITE); result.setTextSize(13); result.setHintTextColor(MUTED); result.setHint(hint); result.setPadding(dp(13), dp(10), dp(13), dp(10)); result.setBackground(outline(SURFACE, STROKE, dp(1))); return result; }
    private TextView text(String value, int size, int color) { TextView result = new TextView(this); result.setText(value); result.setTextSize(size); result.setTextColor(color); return result; }
    private Button button(String value, int fill, int foreground, int stroke) { Button result = new Button(this); result.setText(value); result.setTextSize(11); result.setAllCaps(false); result.setLetterSpacing(0.06f); result.setTextColor(foreground); result.setBackground(outline(fill, stroke, dp(1))); return result; }
    private GradientDrawable outline(int fill, int stroke, int width) { GradientDrawable result = new GradientDrawable(); result.setColor(fill); result.setStroke(width, stroke); return result; }
    private LinearLayout.LayoutParams margin(LinearLayout.LayoutParams params, int left, int top, int right, int bottom) { params.setMargins(left, top, right, bottom); return params; }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
