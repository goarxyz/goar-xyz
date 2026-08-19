package com.goar.os;

import android.content.Context;
import android.content.SharedPreferences;
import android.net.ConnectivityManager;
import android.net.LinkProperties;
import android.net.Network;
import android.os.Build;
import android.system.Os;
import android.util.Log;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.RandomAccessFile;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.zip.GZIPInputStream;

/**
 * Installs and runs GOAR entirely below Context#getFilesDir(). The only host
 * paths PRoot receives are Android's /dev and /proc; workspace, service data,
 * temporary data, rootfs, and logs remain inside the app sandbox.
 */
public final class GoarRuntimeController {
    public interface Reporter {
        void onUpdate(String stage, int percent, String detail);
    }

    public static final String ACTION_STATUS = "com.goar.os.RUNTIME_STATUS";
    public static final String EXTRA_STAGE = "stage";
    public static final String EXTRA_PERCENT = "percent";
    public static final String EXTRA_DETAIL = "detail";
    public static final String DEFAULT_MANIFEST_URL = BuildConfig.DEFAULT_MANIFEST_URL;
    private static final String TAG = "GoarRuntime";
    private static final int CONNECT_TIMEOUT_MS = 20_000;
    private static final int READ_TIMEOUT_MS = 60_000;

    private final Context context;
    private final File baseDir;
    private final File rootfsDir;
    private final File stateDir;
    private final File workspaceDir;
    private final File tmpDir;
    private final File cacheDir;
    private final File logFile;
    private final File resolverFile;
    // Android removes version suffixes from packaged JNI filenames. PRoot is
    // linked against libtalloc.so.2, so materialize that exact soname below the
    // app-private GOAR directory before launching it.
    private final File nativeRuntimeDir;
    private final SharedPreferences preferences;
    private Process process;

    public GoarRuntimeController(Context context) {
        this.context = context.getApplicationContext();
        this.baseDir = new File(this.context.getFilesDir(), "goar");
        this.rootfsDir = new File(baseDir, "rootfs");
        this.stateDir = new File(baseDir, "state");
        this.workspaceDir = new File(baseDir, "workspace");
        this.tmpDir = new File(baseDir, "tmp");
        this.cacheDir = new File(baseDir, "cache");
        this.logFile = new File(baseDir, "goar.log");
        this.resolverFile = new File(baseDir, "resolv.conf");
        this.nativeRuntimeDir = new File(baseDir, "native-runtime");
        this.preferences = this.context.getSharedPreferences("goar_runtime", Context.MODE_PRIVATE);
    }

    public synchronized boolean isInstalled() {
        return new File(rootfsDir, ".goar-rootfs.json").isFile()
                && new File(rootfsDir, "opt/goar/goar.py").isFile()
                && new File(rootfsDir, "usr/local/bin/goar-serve").isFile();
    }

    public synchronized boolean isRunning() {
        return process != null && process.isAlive();
    }

    public synchronized String configuredManifestUrl() {
        return preferences.getString("manifest_url", DEFAULT_MANIFEST_URL);
    }

    public synchronized void setManifestUrl(String url) {
        requireHttpUrl(url, "manifest URL");
        preferences.edit().putString("manifest_url", url.trim()).apply();
    }

    public synchronized void install(Reporter reporter) throws Exception {
        install(configuredManifestUrl(), reporter);
    }

    public synchronized void install(String manifestUrl, Reporter reporter) throws Exception {
        requireHttpUrl(manifestUrl, "manifest URL");
        ensureDirectories();
        report(reporter, "manifest", 0, "Downloading rootfs manifest");
        JSONObject manifest = new JSONObject(readText(manifestUrl, 256 * 1024));
        String architecture = manifest.optString("architecture", "");
        String expectedArchitecture = BuildConfig.TARGET_ROOTFS_ARCH;
        if (!expectedArchitecture.equals(architecture)) {
            throw new IOException("This APK requires a " + expectedArchitecture + " rootfs, received: " + architecture);
        }
        String rootfsUrl = manifest.getString("rootfs_url");
        String expectedSha256 = manifest.getString("rootfs_sha256").toLowerCase(Locale.US);
        long expectedSize = manifest.optLong("rootfs_size", -1L);
        requireHttpUrl(rootfsUrl, "rootfs URL");
        if (!expectedSha256.matches("[0-9a-f]{64}")) {
            throw new IOException("Manifest rootfs_sha256 must be a SHA-256 digest");
        }

        File archivePart = new File(cacheDir, "goar-rootfs.tar.gz.part");
        File archive = new File(cacheDir, "goar-rootfs.tar.gz");
        report(reporter, "download", 0, "Downloading full GOAR rootfs");
        download(rootfsUrl, archivePart, expectedSize, reporter);
        String actualSha256 = sha256(archivePart);
        if (!expectedSha256.equals(actualSha256)) {
            archivePart.delete();
            throw new IOException("Rootfs integrity check failed");
        }
        atomicMove(archivePart, archive);

        File pending = new File(baseDir, "rootfs.pending");
        deleteRecursively(pending);
        if (!pending.mkdirs()) {
            throw new IOException("Could not create rootfs staging directory");
        }
        report(reporter, "extract", 0, "Extracting GOAR rootfs into the app sandbox");
        extractTarGz(archive, pending, reporter);
        writeText(new File(pending, ".goar-rootfs.json"), manifest.toString());
        deleteRecursively(rootfsDir);
        atomicMove(pending, rootfsDir);
        preferences.edit().putString("rootfs_sha256", actualSha256).apply();
        report(reporter, "installed", 100, "GOAR backend installed and verified");
    }

    public synchronized void start(Reporter reporter) throws Exception {
        if (!isInstalled()) {
            throw new IOException("GOAR rootfs has not been installed");
        }
        if (isRunning()) {
            report(reporter, "running", 100, "GOAR is already running");
            return;
        }
        ensureDirectories();
        writeResolver();
        // The contained Playwright driver uses this app-private host path to
        // locate its bundled Node driver when PRoot launches it.
        writeText(new File(rootfsDir, "etc/goar/host-rootfs-path"), rootfsDir.getAbsolutePath() + "\n");
        File nativeDirectory = new File(context.getApplicationInfo().nativeLibraryDir);
        // This matching four-file set is built from the Kai-pinned Termux
        // PRoot revision: primary executable, arm64 loader, armv7 tracee
        // loader, and talloc. Do not substitute the old libgoar_* payload.
        File proot = new File(nativeDirectory, "libproot.so");
        File loader = new File(nativeDirectory, "libproot-loader.so");
        File loader32 = new File(nativeDirectory, "libproot-loader32.so");
        File talloc = new File(nativeDirectory, "libtalloc.so");
        if (!proot.canExecute() || !loader.canExecute() || !loader32.canExecute() || !talloc.isFile()) {
            throw new IOException("The complete dual-loader PRoot bootstrap is unavailable for this device ABI");
        }
        File runtimeLibraryDirectory = prepareNativeRuntimeLibraries(talloc);

        report(reporter, "starting", 0, "Starting the contained GOAR backend");
        List<String> command = new ArrayList<>();
        command.add(proot.getAbsolutePath());
        command.add("-0");
        command.add("-r");
        command.add(rootfsDir.getAbsolutePath());
        command.add("-b");
        command.add(stateDir.getAbsolutePath() + ":/data/goar");
        command.add("-b");
        command.add(workspaceDir.getAbsolutePath() + ":/data/workspace");
        command.add("-b");
        command.add(tmpDir.getAbsolutePath() + ":/tmp");
        command.add("-b");
        command.add(resolverFile.getAbsolutePath() + ":/etc/resolv.conf");
        command.add("-b");
        command.add("/dev");
        command.add("-b");
        command.add("/proc");
        command.add("-b");
        command.add("/sys");
        command.add("-w");
        command.add("/data/workspace");
        command.add("/bin/sh");
        command.add("-lc");
        command.add("export GOAR_HOME=/data/goar GOAR_WORKSPACE=/data/workspace "
                + "GOAR_HOST=127.0.0.1 GOAR_PORT=8080 GOAR_AUTO_INSTALL_DESKTOP=0; "
                + "exec /usr/local/bin/goar-serve");

        ProcessBuilder builder = new ProcessBuilder(command)
                .directory(rootfsDir)
                .redirectErrorStream(true)
                .redirectOutput(ProcessBuilder.Redirect.appendTo(logFile));
        builder.environment().clear();
        builder.environment().put("HOME", "/data/goar");
        builder.environment().put("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin");
        builder.environment().put("TERM", "xterm-256color");
        builder.environment().put("LANG", "C.UTF-8");
        builder.environment().put("TMPDIR", "/tmp");
        builder.environment().put("PROOT_TMP_DIR", tmpDir.getAbsolutePath());
        builder.environment().put("PROOT_LOADER", loader.getAbsolutePath());
        // Android's extracted JNI library keeps the primary executable and
        // both tracee loaders runnable. The app-private directory supplies the
        // versioned talloc soname requested by the matching PRoot binary.
        builder.environment().put(
                "LD_LIBRARY_PATH",
                runtimeLibraryDirectory.getAbsolutePath() + File.pathSeparator + nativeDirectory.getAbsolutePath()
        );
        builder.environment().put("GOAR_ANDROID_SANDBOX", "1");
        builder.environment().put("GOAR_NATIVE_LIBRARIES", nativeDirectory.getAbsolutePath());
        process = builder.start();
        waitForHealth(reporter);
        report(reporter, "running", 100, "GOAR is ready at http://127.0.0.1:8080/");
    }

    public synchronized void stop() {
        if (process != null) {
            process.destroy();
            try {
                Thread.sleep(300);
            } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            }
            if (process.isAlive()) {
                process.destroyForcibly();
            }
            process = null;
        }
    }

    public File logFile() {
        return logFile;
    }

    private void waitForHealth(Reporter reporter) throws Exception {
        long deadline = System.currentTimeMillis() + 75_000L;
        IOException latest = null;
        while (System.currentTimeMillis() < deadline) {
            if (process == null || !process.isAlive()) {
                throw startupFailure("GOAR exited during startup");
            }
            try {
                HttpURLConnection connection = (HttpURLConnection) new URL("http://127.0.0.1:8080/health").openConnection();
                connection.setConnectTimeout(2_000);
                connection.setReadTimeout(2_000);
                if (connection.getResponseCode() == 200) {
                    connection.disconnect();
                    return;
                }
                connection.disconnect();
            } catch (IOException error) {
                latest = error;
            }
            report(reporter, "starting", 0, "Waiting for GOAR backend");
            Thread.sleep(800);
        }
        throw startupFailure("GOAR did not become ready", latest);
    }

    /**
     * Android users cannot ordinarily browse app-private files. Include a small,
     * bounded tail of the PRoot/backend log in the reported exception so a launch
     * failure can be diagnosed from the installation screen without weakening
     * storage isolation.
     */
    private IOException startupFailure(String message) {
        return startupFailure(message, null);
    }

    private IOException startupFailure(String message, IOException cause) {
        String tail = readLogTail();
        String detail = tail.isEmpty() ? message : message + ": " + tail;
        return cause == null ? new IOException(detail) : new IOException(detail, cause);
    }

    private String readLogTail() {
        if (!logFile.isFile()) {
            return "";
        }
        final int maximumBytes = 12 * 1024;
        try (RandomAccessFile input = new RandomAccessFile(logFile, "r")) {
            long start = Math.max(0L, input.length() - maximumBytes);
            input.seek(start);
            byte[] bytes = new byte[(int) (input.length() - start)];
            input.readFully(bytes);
            String tail = new String(bytes, StandardCharsets.UTF_8).trim();
            return tail.length() > 2_000 ? tail.substring(tail.length() - 2_000) : tail;
        } catch (IOException ignored) {
            return "";
        }
    }

    private void writeResolver() throws IOException {
        StringBuilder contents = new StringBuilder();
        ConnectivityManager manager = (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
        if (manager != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Network active = manager.getActiveNetwork();
            LinkProperties properties = active == null ? null : manager.getLinkProperties(active);
            if (properties != null) {
                for (InetAddress address : properties.getDnsServers()) {
                    contents.append("nameserver ").append(address.getHostAddress()).append('\n');
                }
            }
        }
        if (contents.length() == 0) {
            contents.append("nameserver 1.1.1.1\n");
            contents.append("nameserver 8.8.8.8\n");
        }
        writeText(resolverFile, contents.toString());
    }

    private void download(String url, File destination, long expectedSize, Reporter reporter) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setInstanceFollowRedirects(true);
        connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
        connection.setReadTimeout(READ_TIMEOUT_MS);
        connection.setRequestProperty("Accept-Encoding", "identity");
        int status = connection.getResponseCode();
        if (status < 200 || status >= 300) {
            throw new IOException("Rootfs download failed with HTTP " + status);
        }
        long total = expectedSize > 0 ? expectedSize : connection.getContentLengthLong();
        long copied = 0;
        byte[] buffer = new byte[64 * 1024];
        try (InputStream input = new BufferedInputStream(connection.getInputStream());
             BufferedOutputStream output = new BufferedOutputStream(new FileOutputStream(destination))) {
            int count;
            while ((count = input.read(buffer)) != -1) {
                output.write(buffer, 0, count);
                copied += count;
                int percent = total > 0 ? (int) Math.min(99, copied * 100L / total) : 0;
                report(reporter, "download", percent, formatBytes(copied) + " downloaded");
            }
        } finally {
            connection.disconnect();
        }
        if (expectedSize > 0 && copied != expectedSize) {
            throw new IOException("Rootfs download size did not match manifest");
        }
    }

    private void extractTarGz(File archive, File destination, Reporter reporter) throws Exception {
        long archiveLength = archive.length();
        long consumed = 0;
        byte[] header = new byte[512];
        try (InputStream file = new BufferedInputStream(new FileInputStream(archive));
             GZIPInputStream gzip = new GZIPInputStream(file)) {
            String pendingLongName = null;
            String pendingLongLink = null;
            List<PendingHardLink> pendingHardLinks = new ArrayList<>();
            while (true) {
                readFully(gzip, header, 0, header.length);
                consumed += header.length;
                if (allZero(header)) {
                    break;
                }
                String headerName = tarString(header, 0, 100);
                String prefix = tarString(header, 345, 155);
                if (!prefix.isEmpty()) {
                    headerName = prefix + "/" + headerName;
                }
                long size = tarNumber(header, 124, 12);
                int mode = (int) tarNumber(header, 100, 8);
                byte type = header[156];

                // GNU tar writes an L/K metadata record before any path or link
                // target longer than the fixed USTAR header fields. The prior
                // implementation skipped this record, then extracted the next
                // file using its truncated path, which collided with directories
                // such as Python __pycache__ in the full Alpine rootfs.
                if (type == 'L' || type == 'K') {
                    String extendedValue = readTarText(gzip, size);
                    consumed += size;
                    long padding = (512 - (size % 512)) % 512;
                    if (padding > 0) {
                        skipExactly(gzip, padding);
                        consumed += padding;
                    }
                    if (type == 'L') {
                        pendingLongName = extendedValue;
                    } else {
                        pendingLongLink = extendedValue;
                    }
                    continue;
                }

                String name = pendingLongName == null ? headerName : pendingLongName;
                String linkTarget = pendingLongLink == null ? tarString(header, 157, 100) : pendingLongLink;
                pendingLongName = null;
                pendingLongLink = null;
                File output = safeTarFile(destination, name);
                boolean deferredHardLink = false;
                if (type == '5') {
                    if (!output.isDirectory() && !output.mkdirs()) {
                        throw new IOException("Could not create directory " + name);
                    }
                } else if (type == '2') {
                    File parent = output.getParentFile();
                    if (parent != null && !parent.isDirectory() && !parent.mkdirs()) {
                        throw new IOException("Could not create parent for " + name);
                    }
                    validateSymbolicLinkTarget(destination, output, linkTarget);
                    Files.deleteIfExists(output.toPath());
                    Files.createSymbolicLink(output.toPath(), java.nio.file.Paths.get(linkTarget));
                } else if (type == '1') {
                    File target = safeTarFile(destination, linkTarget);
                    File parent = output.getParentFile();
                    if (parent != null && !parent.isDirectory() && !parent.mkdirs()) {
                        throw new IOException("Could not create parent for " + name);
                    }
                    // GNU tar may record a hard link before its regular-file
                    // target. Android's Files.createLink cannot create such a
                    // forward reference, so finish it after the archive pass.
                    if (target.isFile()) {
                        materializeHardLink(output, target, mode);
                    } else {
                        pendingHardLinks.add(new PendingHardLink(name, output, target, mode));
                        deferredHardLink = true;
                    }
                } else if (type == 0 || type == '0') {
                    File parent = output.getParentFile();
                    if (parent != null && !parent.isDirectory() && !parent.mkdirs()) {
                        throw new IOException("Could not create parent for " + name);
                    }
                    try (BufferedOutputStream outputStream = new BufferedOutputStream(new FileOutputStream(output))) {
                        copyExactly(gzip, outputStream, size);
                    }
                    consumed += size;
                } else {
                    skipExactly(gzip, size);
                    consumed += size;
                }
                long padding = (512 - (size % 512)) % 512;
                if (padding > 0) {
                    skipExactly(gzip, padding);
                    consumed += padding;
                }
                if (!deferredHardLink) {
                    setMode(output, mode, type == '5');
                }
                int percent = archiveLength > 0 ? (int) Math.min(99, consumed * 100L / archiveLength) : 0;
                report(reporter, "extract", percent, "Installing " + name);
            }
            materializePendingHardLinks(pendingHardLinks);
        }
    }

    private static final class PendingHardLink {
        final String archiveName;
        final File output;
        final File target;
        final int mode;

        PendingHardLink(String archiveName, File output, File target, int mode) {
            this.archiveName = archiveName;
            this.output = output;
            this.target = target;
            this.mode = mode;
        }
    }

    private static void materializePendingHardLinks(List<PendingHardLink> pending) throws IOException {
        for (PendingHardLink link : pending) {
            if (!link.target.isFile()) {
                throw new IOException("Hard-link target was not present in rootfs archive: " + link.archiveName);
            }
            materializeHardLink(link.output, link.target, link.mode);
        }
    }

    private static void materializeHardLink(File output, File target, int mode) throws IOException {
        Files.deleteIfExists(output.toPath());
        try {
            Files.createLink(output.toPath(), target.toPath());
        } catch (UnsupportedOperationException | IOException linkFailure) {
            // App-private filesystems normally support hard links. If a device
            // filesystem rejects them, preserve the archive payload safely by
            // making a regular copy instead of failing an otherwise valid rootfs.
            try (InputStream input = new BufferedInputStream(new FileInputStream(target));
                 BufferedOutputStream stream = new BufferedOutputStream(new FileOutputStream(output))) {
                byte[] buffer = new byte[64 * 1024];
                int read;
                while ((read = input.read(buffer)) != -1) {
                    stream.write(buffer, 0, read);
                }
            }
        }
        setMode(output, mode, false);
    }

    private static void readFully(InputStream stream, byte[] buffer, int offset, int length) throws IOException {
        int read = 0;
        while (read < length) {
            int amount = stream.read(buffer, offset + read, length - read);
            if (amount < 0) {
                throw new IOException("Unexpected end of rootfs archive");
            }
            read += amount;
        }
    }

    private static String readTarText(InputStream input, long length) throws IOException {
        if (length < 0 || length > 1024 * 1024) {
            throw new IOException("Unexpectedly large tar extended-path record");
        }
        byte[] value = new byte[(int) length];
        readFully(input, value, 0, value.length);
        int end = value.length;
        while (end > 0 && (value[end - 1] == 0 || value[end - 1] == '\n')) {
            end--;
        }
        return new String(value, 0, end, StandardCharsets.UTF_8);
    }

    private static void copyExactly(InputStream input, BufferedOutputStream output, long length) throws IOException {
        byte[] buffer = new byte[64 * 1024];
        long remaining = length;
        while (remaining > 0) {
            int read = input.read(buffer, 0, (int) Math.min(buffer.length, remaining));
            if (read < 0) {
                throw new IOException("Unexpected end of rootfs payload");
            }
            output.write(buffer, 0, read);
            remaining -= read;
        }
    }

    private static void skipExactly(InputStream input, long length) throws IOException {
        long remaining = length;
        byte[] buffer = new byte[4096];
        while (remaining > 0) {
            long skipped = input.skip(remaining);
            if (skipped <= 0) {
                int read = input.read(buffer, 0, (int) Math.min(buffer.length, remaining));
                if (read < 0) {
                    throw new IOException("Unexpected end of rootfs archive");
                }
                skipped = read;
            }
            remaining -= skipped;
        }
    }

    private static String tarString(byte[] header, int offset, int length) {
        int end = offset;
        while (end < offset + length && header[end] != 0) {
            end++;
        }
        return new String(header, offset, end - offset, StandardCharsets.UTF_8).trim();
    }

    private static long tarNumber(byte[] header, int offset, int length) {
        String number = tarString(header, offset, length).trim();
        if (number.isEmpty()) {
            return 0L;
        }
        return Long.parseLong(number.replaceAll("[^0-7]", ""), 8);
    }

    private static boolean allZero(byte[] bytes) {
        for (byte value : bytes) {
            if (value != 0) {
                return false;
            }
        }
        return true;
    }

    private static void validateSymbolicLinkTarget(File root, File link, String target) throws IOException {
        if (target.isEmpty() || target.indexOf('\\') >= 0) {
            throw new IOException("Unsafe symbolic link in rootfs archive");
        }
        // Absolute links are intentional guest-root paths (for example,
        // /bin/sh -> /bin/busybox). PRoot resolves them below its -r rootfs,
        // not against Android's host filesystem.
        if (target.startsWith("/")) {
            return;
        }
        java.nio.file.Path rootPath = root.getCanonicalFile().toPath();
        java.nio.file.Path resolved = link.getParentFile().toPath().resolve(target).normalize();
        if (!resolved.startsWith(rootPath)) {
            throw new IOException("Symbolic link escapes rootfs: " + target);
        }
    }

    private static File safeTarFile(File root, String name) throws IOException {
        if (name.isEmpty() || name.startsWith("/") || name.contains("\\") || name.contains("../")) {
            throw new IOException("Unsafe path in rootfs archive: " + name);
        }
        File canonicalRoot = root.getCanonicalFile();
        File output = new File(canonicalRoot, name).getCanonicalFile();
        // GNU tar archives conventionally begin with a ./ directory header.
        // Accept that exact root marker, but continue to reject every other
        // entry that resolves outside the app-private extraction directory.
        if (output.equals(canonicalRoot) && (".".equals(name) || "./".equals(name))) {
            return output;
        }
        if (!output.getPath().startsWith(canonicalRoot.getPath() + File.separator)) {
            throw new IOException("Rootfs archive path escapes sandbox: " + name);
        }
        return output;
    }

    private static void setMode(File file, int mode, boolean directory) {
        if (mode == 0) {
            return;
        }
        try {
            Os.chmod(file.getAbsolutePath(), mode & 0777);
        } catch (Exception ignored) {
            if (!directory && (mode & 0100) != 0) {
                file.setExecutable(true, true);
            }
        }
    }

    /**
     * PRoot requests the talloc soname (`libtalloc.so.2`), whereas Android
     * packages JNI libraries without that version suffix. Copying the packaged
     * library to an app-private compatibility directory gives Bionic a real
     * filename matching the requested soname without weakening the sandbox or
     * relying on a symlink in the native library directory.
     */
    private File prepareNativeRuntimeLibraries(File packagedTalloc) throws IOException {
        if (!nativeRuntimeDir.isDirectory() && !nativeRuntimeDir.mkdirs()) {
            throw new IOException("Could not create PRoot native runtime directory");
        }
        File versionedTalloc = new File(nativeRuntimeDir, "libtalloc.so.2");
        if (!versionedTalloc.isFile() || versionedTalloc.length() != packagedTalloc.length()) {
            File pending = new File(nativeRuntimeDir, "libtalloc.so.2.pending");
            if (pending.exists() && !pending.delete()) {
                throw new IOException("Could not replace pending PRoot native library");
            }
            try (InputStream input = new BufferedInputStream(new FileInputStream(packagedTalloc));
                 BufferedOutputStream output = new BufferedOutputStream(new FileOutputStream(pending))) {
                byte[] buffer = new byte[64 * 1024];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    output.write(buffer, 0, count);
                }
            }
            setMode(pending, 0755, false);
            atomicMove(pending, versionedTalloc);
        }
        if (!versionedTalloc.isFile()) {
            throw new IOException("Could not prepare libtalloc.so.2 for PRoot");
        }
        return nativeRuntimeDir;
    }

    private static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[128 * 1024];
        try (InputStream input = new BufferedInputStream(new FileInputStream(file))) {
            int count;
            while ((count = input.read(buffer)) != -1) {
                digest.update(buffer, 0, count);
            }
        }
        StringBuilder value = new StringBuilder(64);
        for (byte b : digest.digest()) {
            value.append(String.format(Locale.US, "%02x", b));
        }
        return value.toString();
    }

    private static void atomicMove(File source, File destination) throws IOException {
        if (destination.exists() && !deleteRecursively(destination)) {
            throw new IOException("Could not replace " + destination.getName());
        }
        if (!source.renameTo(destination)) {
            throw new IOException("Could not move " + source.getName());
        }
    }

    private static boolean deleteRecursively(File file) {
        if (!file.exists()) {
            return true;
        }
        if (file.isDirectory() && !Files.isSymbolicLink(file.toPath())) {
            File[] children = file.listFiles();
            if (children != null) {
                for (File child : children) {
                    if (!deleteRecursively(child)) {
                        return false;
                    }
                }
            }
        }
        return file.delete();
    }

    private void ensureDirectories() throws IOException {
        for (File directory : new File[]{baseDir, stateDir, workspaceDir, tmpDir, cacheDir, nativeRuntimeDir}) {
            if (!directory.isDirectory() && !directory.mkdirs()) {
                throw new IOException("Could not create " + directory.getAbsolutePath());
            }
        }
    }

    private static String readText(String url, int maximumBytes) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
        connection.setReadTimeout(READ_TIMEOUT_MS);
        connection.setInstanceFollowRedirects(true);
        if (connection.getResponseCode() != 200) {
            throw new IOException("Manifest download failed with HTTP " + connection.getResponseCode());
        }
        StringBuilder text = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
            char[] buffer = new char[4096];
            int count;
            while ((count = reader.read(buffer)) != -1) {
                text.append(buffer, 0, count);
                if (text.length() > maximumBytes) {
                    throw new IOException("Manifest is unexpectedly large");
                }
            }
        } finally {
            connection.disconnect();
        }
        return text.toString();
    }

    private static void writeText(File file, String value) throws IOException {
        File parent = file.getParentFile();
        if (parent != null && !parent.isDirectory() && !parent.mkdirs()) {
            throw new IOException("Could not create " + parent.getAbsolutePath());
        }
        try (FileOutputStream output = new FileOutputStream(file, false)) {
            output.write(value.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static void requireHttpUrl(String value, String label) {
        if (value == null || !(value.startsWith("https://") || value.startsWith("http://"))) {
            throw new IllegalArgumentException("A valid HTTP(S) " + label + " is required");
        }
    }

    private static String formatBytes(long bytes) {
        if (bytes < 1024 * 1024) {
            return String.format(Locale.US, "%.1f KiB", bytes / 1024.0);
        }
        return String.format(Locale.US, "%.1f MiB", bytes / (1024.0 * 1024.0));
    }

    private static void report(Reporter reporter, String stage, int percent, String detail) {
        if (reporter != null) {
            reporter.onUpdate(stage, percent, detail);
        }
        Log.i(TAG, stage + ": " + detail);
    }
}
