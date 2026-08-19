package com.goar.os;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Android-native pseudoterminal bridge. The PRoot command remains a normal
 * child process, but stdin/stdout/stderr share a PTY so prompt_toolkit and the
 * Kali shell receive a real terminal rather than a redirected log stream.
 */
public final class GoarPtyBridge implements AutoCloseable {
    public interface Listener {
        void onBytes(byte[] data, int length);
        void onClosed(int exitSignal);
        void onError(Exception error);
    }

    static {
        System.loadLibrary("goar_terminal_jni");
    }

    private final int fd;
    private final int pid;
    private final AtomicBoolean closed = new AtomicBoolean(false);
    private Thread reader;

    private GoarPtyBridge(int fd, int pid) {
        this.fd = fd;
        this.pid = pid;
    }

    public static GoarPtyBridge start(List<String> command, Map<String, String> environment,
                                      File workingDirectory, int rows, int columns) throws IOException {
        if (command == null || command.isEmpty()) {
            throw new IOException("Terminal command is empty");
        }
        List<String> serializedEnvironment = new ArrayList<>();
        for (Map.Entry<String, String> entry : environment.entrySet()) {
            serializedEnvironment.add(entry.getKey() + "=" + entry.getValue());
        }
        int[] handle = nativeSpawn(command.toArray(new String[0]),
                serializedEnvironment.toArray(new String[0]),
                workingDirectory == null ? null : workingDirectory.getAbsolutePath(), rows, columns);
        if (handle == null || handle.length != 2 || handle[0] < 0 || handle[1] <= 0) {
            throw new IOException("Could not create Kali terminal pseudoterminal");
        }
        return new GoarPtyBridge(handle[0], handle[1]);
    }

    public synchronized void startReader(Listener listener) {
        if (reader != null) return;
        reader = new Thread(() -> {
            byte[] buffer = new byte[16 * 1024];
            try {
                while (!closed.get()) {
                    int count = nativeRead(fd, buffer, 1_000);
                    if (count > 0) {
                        byte[] copy = new byte[count];
                        System.arraycopy(buffer, 0, copy, 0, count);
                        listener.onBytes(copy, count);
                    } else if (count < 0) {
                        break;
                    } else if (!nativeAlive(pid)) {
                        break;
                    }
                }
                listener.onClosed(0);
            } catch (Exception error) {
                if (!closed.get()) listener.onError(error);
            } finally {
                close();
            }
        }, "goar-pty-reader");
        reader.setDaemon(true);
        reader.start();
    }

    public synchronized void write(String value) throws IOException {
        if (closed.get()) throw new IOException("Terminal session is closed");
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        int offset = 0;
        while (offset < bytes.length) {
            byte[] remaining = new byte[bytes.length - offset];
            System.arraycopy(bytes, offset, remaining, 0, remaining.length);
            int count = nativeWrite(fd, remaining, remaining.length);
            if (count <= 0) throw new IOException("Terminal write failed");
            offset += count;
        }
    }

    public void resize(int rows, int columns) {
        if (!closed.get()) nativeResize(fd, rows, columns);
    }

    public void interrupt() {
        if (!closed.get()) nativeSignal(pid, 2); // SIGINT
    }

    public boolean isAlive() {
        return !closed.get() && nativeAlive(pid);
    }

    @Override
    public void close() {
        if (closed.compareAndSet(false, true)) {
            nativeSignal(pid, 15); // SIGTERM
            nativeClose(fd);
        }
    }

    private static native int[] nativeSpawn(String[] argv, String[] environment, String workingDirectory, int rows, int columns);
    private static native int nativeRead(int fd, byte[] target, int timeoutMs);
    private static native int nativeWrite(int fd, byte[] source, int length);
    private static native void nativeResize(int fd, int rows, int columns);
    private static native void nativeSignal(int pid, int signal);
    private static native void nativeClose(int fd);
    private static native boolean nativeAlive(int pid);
}
