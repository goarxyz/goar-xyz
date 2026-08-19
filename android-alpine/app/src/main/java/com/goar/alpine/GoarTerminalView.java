package com.goar.alpine;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.os.SystemClock;
import android.text.InputType;
import android.view.Gravity;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.InputMethodManager;

import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.Arrays;

/**
 * Compact VT-compatible terminal surface for the in-app PRoot PTY. It keeps a
 * bounded scrollback buffer and supports the CSI operations prompt_toolkit and
 * Bash use for cursor placement, clearing, resizing, and alternate screens.
 */
public final class GoarTerminalView extends View {
    public interface InputSink {
        void send(String value);
        void resize(int rows, int columns);
    }

    private static final int BLACK = Color.BLACK;
    private static final int WHITE = Color.rgb(238, 238, 238);
    private static final int CURSOR = Color.rgb(180, 255, 180);
    private static final int MAX_SCROLLBACK = 4000;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.SUBPIXEL_TEXT_FLAG);
    private final ArrayDeque<String> scrollback = new ArrayDeque<>();
    private final StringBuilder csi = new StringBuilder();
    private InputSink sink;
    private char[][] cells = new char[24][80];
    private int columns = 80;
    private int rows = 24;
    private int cursorRow;
    private int cursorColumn;
    private int savedRow;
    private int savedColumn;
    private boolean cursorVisible = true;
    private boolean alternateScreen;
    private char[][] primaryCells;
    private int primaryRow;
    private int primaryColumn;
    private int parserState; // 0=text, 1=ESC, 2=CSI
    private int scrollOffset;
    private float cellWidth;
    private float baselineStep;
    private float downY;
    private boolean dragging;

    public GoarTerminalView(Context context) {
        super(context);
        setBackgroundColor(BLACK);
        setFocusableInTouchMode(true);
        setFocusable(true);
        paint.setColor(WHITE);
        paint.setTypeface(Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL));
        paint.setTextSize(sp(13));
        setPadding(dp(8), dp(8), dp(8), dp(8));
        clearScreen();
    }

    public void setInputSink(InputSink value) {
        sink = value;
        announceResize();
    }

    public int terminalRows() { return rows; }
    public int terminalColumns() { return columns; }

    public void appendBytes(byte[] data, int count) {
        accept(new String(data, 0, count, StandardCharsets.UTF_8));
        postInvalidateOnAnimation();
    }

    public void appendSystemLine(String message) {
        accept("\r\n\u001b[2m[goar] " + message + "\u001b[0m\r\n");
        postInvalidateOnAnimation();
    }

    @Override
    protected void onSizeChanged(int width, int height, int oldWidth, int oldHeight) {
        super.onSizeChanged(width, height, oldWidth, oldHeight);
        configureGeometry(width, height);
    }

    private void configureGeometry(int width, int height) {
        paint.setTextSize(sp(13));
        cellWidth = Math.max(1f, paint.measureText("M"));
        baselineStep = Math.max(1f, paint.getFontMetrics().bottom - paint.getFontMetrics().top + dp(1));
        int nextColumns = Math.max(20, (int) ((width - getPaddingLeft() - getPaddingRight()) / cellWidth));
        int nextRows = Math.max(6, (int) ((height - getPaddingTop() - getPaddingBottom()) / baselineStep));
        if (nextColumns == columns && nextRows == rows) return;
        resizeGrid(nextRows, nextColumns);
        announceResize();
    }

    private void resizeGrid(int nextRows, int nextColumns) {
        char[][] replacement = new char[nextRows][nextColumns];
        for (char[] line : replacement) Arrays.fill(line, ' ');
        int copyRows = Math.min(rows, nextRows);
        int copyColumns = Math.min(columns, nextColumns);
        for (int row = 0; row < copyRows; row++) {
            System.arraycopy(cells[Math.max(0, rows - copyRows) + row], 0,
                    replacement[Math.max(0, nextRows - copyRows) + row], 0, copyColumns);
        }
        cells = replacement;
        rows = nextRows;
        columns = nextColumns;
        cursorRow = Math.min(cursorRow, rows - 1);
        cursorColumn = Math.min(cursorColumn, columns - 1);
    }

    private void announceResize() {
        if (sink != null && getWidth() > 0 && getHeight() > 0) sink.resize(rows, columns);
    }

    private void accept(String input) {
        for (int index = 0; index < input.length(); index++) {
            char value = input.charAt(index);
            if (parserState == 0) {
                if (value == 0x1b) parserState = 1;
                else if (value == '\n') newline();
                else if (value == '\r') cursorColumn = 0;
                else if (value == '\b') cursorColumn = Math.max(0, cursorColumn - 1);
                else if (value >= 0x20 && value != 0x7f) put(value);
            } else if (parserState == 1) {
                if (value == '[') {
                    csi.setLength(0);
                    parserState = 2;
                } else if (value == '7') {
                    savedRow = cursorRow; savedColumn = cursorColumn; parserState = 0;
                } else if (value == '8') {
                    cursorRow = savedRow; cursorColumn = savedColumn; parserState = 0;
                } else {
                    parserState = 0;
                }
            } else {
                if (value >= '@' && value <= '~') {
                    applyCsi(csi.toString(), value);
                    parserState = 0;
                } else if (csi.length() < 128) {
                    csi.append(value);
                } else {
                    parserState = 0;
                }
            }
        }
    }

    private int parameter(String raw, int position, int fallback) {
        String plain = raw.startsWith("?") ? raw.substring(1) : raw;
        String[] values = plain.split(";", -1);
        if (position >= values.length || values[position].isEmpty()) return fallback;
        try { return Integer.parseInt(values[position]); } catch (NumberFormatException ignored) { return fallback; }
    }

    private void applyCsi(String raw, char operation) {
        switch (operation) {
            case 'A': cursorRow = Math.max(0, cursorRow - parameter(raw, 0, 1)); break;
            case 'B': cursorRow = Math.min(rows - 1, cursorRow + parameter(raw, 0, 1)); break;
            case 'C': cursorColumn = Math.min(columns - 1, cursorColumn + parameter(raw, 0, 1)); break;
            case 'D': cursorColumn = Math.max(0, cursorColumn - parameter(raw, 0, 1)); break;
            case 'G': cursorColumn = Math.min(columns - 1, Math.max(0, parameter(raw, 0, 1) - 1)); break;
            case 'd': cursorRow = Math.min(rows - 1, Math.max(0, parameter(raw, 0, 1) - 1)); break;
            case 'H':
            case 'f': cursorRow = Math.min(rows - 1, Math.max(0, parameter(raw, 0, 1) - 1)); cursorColumn = Math.min(columns - 1, Math.max(0, parameter(raw, 1, 1) - 1)); break;
            case 'J': if (parameter(raw, 0, 0) == 2 || parameter(raw, 0, 0) == 3) clearScreen(); else clearAfterCursor(); break;
            case 'K': clearLineAfterCursor(); break;
            case 'm': break; // Rendering remains monochrome by design while control sequences still function.
            case 's': savedRow = cursorRow; savedColumn = cursorColumn; break;
            case 'u': cursorRow = savedRow; cursorColumn = savedColumn; break;
            case 'h': if (raw.contains("1049")) enterAlternateScreen(); else if (raw.contains("25")) cursorVisible = true; break;
            case 'l': if (raw.contains("1049")) leaveAlternateScreen(); else if (raw.contains("25")) cursorVisible = false; break;
            default: break;
        }
    }

    private void put(char value) {
        cells[cursorRow][cursorColumn] = value;
        cursorColumn++;
        if (cursorColumn >= columns) newline();
    }

    private void newline() {
        cursorColumn = 0;
        cursorRow++;
        if (cursorRow >= rows) {
            if (!alternateScreen) addScrollback(new String(cells[0]));
            for (int row = 1; row < rows; row++) System.arraycopy(cells[row], 0, cells[row - 1], 0, columns);
            Arrays.fill(cells[rows - 1], ' ');
            cursorRow = rows - 1;
        }
    }

    private void addScrollback(String line) {
        scrollback.addLast(line);
        while (scrollback.size() > MAX_SCROLLBACK) scrollback.removeFirst();
    }

    private void clearScreen() {
        for (char[] row : cells) Arrays.fill(row, ' ');
        cursorRow = 0; cursorColumn = 0; scrollOffset = 0;
    }

    private void clearAfterCursor() {
        clearLineAfterCursor();
        for (int row = cursorRow + 1; row < rows; row++) Arrays.fill(cells[row], ' ');
    }

    private void clearLineAfterCursor() {
        Arrays.fill(cells[cursorRow], cursorColumn, columns, ' ');
    }

    private void enterAlternateScreen() {
        if (alternateScreen) return;
        primaryCells = cells;
        primaryRow = cursorRow;
        primaryColumn = cursorColumn;
        cells = new char[rows][columns];
        for (char[] row : cells) Arrays.fill(row, ' ');
        cursorRow = 0; cursorColumn = 0; alternateScreen = true;
    }

    private void leaveAlternateScreen() {
        if (!alternateScreen || primaryCells == null) return;
        cells = primaryCells;
        cursorRow = Math.min(primaryRow, rows - 1);
        cursorColumn = Math.min(primaryColumn, columns - 1);
        primaryCells = null;
        alternateScreen = false;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        paint.setColor(WHITE);
        float top = getPaddingTop() - paint.getFontMetrics().top;
        String[] history = scrollback.toArray(new String[0]);
        int total = history.length + rows;
        int start = Math.max(0, total - rows - scrollOffset);
        for (int visualRow = 0; visualRow < rows; visualRow++) {
            int source = start + visualRow;
            String line;
            if (source < history.length) line = history[source];
            else line = new String(cells[source - history.length]);
            canvas.drawText(line, getPaddingLeft(), top + visualRow * baselineStep, paint);
        }
        if (cursorVisible && scrollOffset == 0 && hasFocus() && (SystemClock.uptimeMillis() / 500L) % 2 == 0) {
            float x = getPaddingLeft() + cursorColumn * cellWidth;
            float y = getPaddingTop() + cursorRow * baselineStep;
            paint.setColor(CURSOR);
            canvas.drawRect(x, y, x + Math.max(1f, cellWidth), y + baselineStep - dp(1), paint);
        }
        postInvalidateDelayed(400);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                downY = event.getY(); dragging = false; requestFocus();
                ((InputMethodManager) getContext().getSystemService(Context.INPUT_METHOD_SERVICE)).showSoftInput(this, InputMethodManager.SHOW_IMPLICIT);
                return true;
            case MotionEvent.ACTION_MOVE:
                float delta = event.getY() - downY;
                if (Math.abs(delta) > baselineStep / 2f) {
                    dragging = true;
                    int amount = Math.round(-delta / baselineStep);
                    scrollOffset = Math.max(0, Math.min(scrollback.size(), scrollOffset + amount));
                    downY = event.getY(); invalidate();
                }
                return true;
            case MotionEvent.ACTION_UP:
                if (!dragging && sink != null) {
                    scrollOffset = 0;
                    invalidate();
                }
                return true;
            default: return true;
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (sink == null) return super.onKeyDown(keyCode, event);
        String mapped = keySequence(keyCode, event);
        if (mapped != null) { sink.send(mapped); return true; }
        int unicode = event.getUnicodeChar();
        if (unicode > 0 && (event.getSource() & InputDevice.SOURCE_KEYBOARD) != 0) {
            sink.send(new String(Character.toChars(unicode)));
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    private String keySequence(int keyCode, KeyEvent event) {
        switch (keyCode) {
            case KeyEvent.KEYCODE_ENTER: return "\r";
            case KeyEvent.KEYCODE_DEL: return "\u007f";
            case KeyEvent.KEYCODE_TAB: return "\t";
            case KeyEvent.KEYCODE_ESCAPE: return "\u001b";
            case KeyEvent.KEYCODE_DPAD_UP: return "\u001b[A";
            case KeyEvent.KEYCODE_DPAD_DOWN: return "\u001b[B";
            case KeyEvent.KEYCODE_DPAD_RIGHT: return "\u001b[C";
            case KeyEvent.KEYCODE_DPAD_LEFT: return "\u001b[D";
            case KeyEvent.KEYCODE_MOVE_HOME: return "\u001b[H";
            case KeyEvent.KEYCODE_MOVE_END: return "\u001b[F";
            case KeyEvent.KEYCODE_PAGE_UP: return "\u001b[5~";
            case KeyEvent.KEYCODE_PAGE_DOWN: return "\u001b[6~";
            default: return null;
        }
    }

    @Override
    public InputConnection onCreateInputConnection(EditorInfo info) {
        info.inputType = InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD;
        info.imeOptions = EditorInfo.IME_ACTION_NONE | EditorInfo.IME_FLAG_NO_EXTRACT_UI;
        return new BaseInputConnection(this, false) {
            @Override public boolean commitText(CharSequence text, int newCursorPosition) { if (sink != null) sink.send(text.toString()); return true; }
            @Override public boolean deleteSurroundingText(int beforeLength, int afterLength) { if (sink != null) sink.send("\u007f"); return true; }
            @Override public boolean sendKeyEvent(KeyEvent event) { return GoarTerminalView.this.onKeyDown(event.getKeyCode(), event); }
        };
    }

    @Override public boolean onCheckIsTextEditor() { return true; }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private float sp(int value) { return value * getResources().getDisplayMetrics().scaledDensity; }
}
