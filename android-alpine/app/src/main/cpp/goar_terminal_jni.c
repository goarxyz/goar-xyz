#include <jni.h>
#include <android/log.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pty.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

#define TAG "GoarPty"
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, TAG, __VA_ARGS__)

static char **strings_to_vector(JNIEnv *env, jobjectArray values) {
    if (values == NULL) return NULL;
    jsize count = (*env)->GetArrayLength(env, values);
    char **result = calloc((size_t) count + 1, sizeof(char *));
    if (result == NULL) return NULL;
    for (jsize index = 0; index < count; ++index) {
        jstring value = (jstring) (*env)->GetObjectArrayElement(env, values, index);
        if (value == NULL) continue;
        const char *raw = (*env)->GetStringUTFChars(env, value, NULL);
        if (raw != NULL) {
            result[index] = strdup(raw);
            (*env)->ReleaseStringUTFChars(env, value, raw);
        }
        (*env)->DeleteLocalRef(env, value);
    }
    return result;
}

static void free_vector(char **values) {
    if (values == NULL) return;
    for (size_t index = 0; values[index] != NULL; ++index) free(values[index]);
    free(values);
}

JNIEXPORT jintArray JNICALL
Java_com_goar_os_GoarPtyBridge_nativeSpawn(
        JNIEnv *env, jclass clazz, jobjectArray argv_values, jobjectArray env_values,
        jstring cwd_value, jint rows, jint columns) {
    (void) clazz;
    char **argv = strings_to_vector(env, argv_values);
    char **environment = strings_to_vector(env, env_values);
    if (argv == NULL || argv[0] == NULL) {
        free_vector(argv);
        free_vector(environment);
        return NULL;
    }
    const char *cwd = cwd_value == NULL ? NULL : (*env)->GetStringUTFChars(env, cwd_value, NULL);
    int master = -1;
    int slave = -1;
    struct winsize size = {0};
    size.ws_row = (unsigned short) (rows > 0 ? rows : 24);
    size.ws_col = (unsigned short) (columns > 0 ? columns : 80);
    if (openpty(&master, &slave, NULL, NULL, &size) != 0) {
        LOGE("openpty failed: %s", strerror(errno));
        if (cwd != NULL) (*env)->ReleaseStringUTFChars(env, cwd_value, cwd);
        free_vector(argv);
        free_vector(environment);
        return NULL;
    }
    pid_t child = fork();
    if (child == 0) {
        setsid();
        ioctl(slave, TIOCSCTTY, 0);
        dup2(slave, STDIN_FILENO);
        dup2(slave, STDOUT_FILENO);
        dup2(slave, STDERR_FILENO);
        if (master >= 0) close(master);
        if (slave > STDERR_FILENO) close(slave);
        if (cwd != NULL && chdir(cwd) != 0) _exit(126);
        clearenv();
        if (environment != NULL) {
            for (size_t index = 0; environment[index] != NULL; ++index) {
                char *equals = strchr(environment[index], '=');
                if (equals != NULL) {
                    *equals = '\0';
                    setenv(environment[index], equals + 1, 1);
                    *equals = '=';
                }
            }
        }
        execv(argv[0], argv);
        _exit(127);
    }
    if (cwd != NULL) (*env)->ReleaseStringUTFChars(env, cwd_value, cwd);
    close(slave);
    free_vector(argv);
    free_vector(environment);
    if (child < 0) {
        LOGE("fork failed: %s", strerror(errno));
        close(master);
        return NULL;
    }
    jint values[2] = {(jint) master, (jint) child};
    jintArray result = (*env)->NewIntArray(env, 2);
    if (result != NULL) (*env)->SetIntArrayRegion(env, result, 0, 2, values);
    return result;
}

JNIEXPORT jint JNICALL
Java_com_goar_os_GoarPtyBridge_nativeRead(JNIEnv *env, jclass clazz, jint fd, jbyteArray target, jint timeout_ms) {
    (void) clazz;
    struct pollfd poll_fd = {.fd = fd, .events = POLLIN, .revents = 0};
    int ready = poll(&poll_fd, 1, timeout_ms < 0 ? -1 : timeout_ms);
    if (ready <= 0) return ready;
    jsize length = (*env)->GetArrayLength(env, target);
    jbyte *bytes = (*env)->GetByteArrayElements(env, target, NULL);
    if (bytes == NULL) return -1;
    ssize_t read_count = read(fd, bytes, (size_t) length);
    (*env)->ReleaseByteArrayElements(env, target, bytes, read_count > 0 ? 0 : JNI_ABORT);
    if (read_count < 0 && (errno == EIO || errno == EINTR)) return 0;
    return (jint) read_count;
}

JNIEXPORT jint JNICALL
Java_com_goar_os_GoarPtyBridge_nativeWrite(JNIEnv *env, jclass clazz, jint fd, jbyteArray source, jint length) {
    (void) clazz;
    jsize available = (*env)->GetArrayLength(env, source);
    jsize count = length < available ? length : available;
    jbyte *bytes = (*env)->GetByteArrayElements(env, source, NULL);
    if (bytes == NULL) return -1;
    ssize_t written = write(fd, bytes, (size_t) count);
    (*env)->ReleaseByteArrayElements(env, source, bytes, JNI_ABORT);
    return (jint) written;
}

JNIEXPORT void JNICALL
Java_com_goar_os_GoarPtyBridge_nativeResize(JNIEnv *env, jclass clazz, jint fd, jint rows, jint columns) {
    (void) env; (void) clazz;
    struct winsize size = {0};
    size.ws_row = (unsigned short) (rows > 0 ? rows : 24);
    size.ws_col = (unsigned short) (columns > 0 ? columns : 80);
    ioctl(fd, TIOCSWINSZ, &size);
}

JNIEXPORT void JNICALL
Java_com_goar_os_GoarPtyBridge_nativeSignal(JNIEnv *env, jclass clazz, jint pid, jint signal_value) {
    (void) env; (void) clazz;
    if (pid > 0) kill((pid_t) pid, signal_value);
}

JNIEXPORT void JNICALL
Java_com_goar_os_GoarPtyBridge_nativeClose(JNIEnv *env, jclass clazz, jint fd) {
    (void) env; (void) clazz;
    if (fd >= 0) close(fd);
}

JNIEXPORT jboolean JNICALL
Java_com_goar_os_GoarPtyBridge_nativeAlive(JNIEnv *env, jclass clazz, jint pid) {
    (void) env; (void) clazz;
    if (pid <= 0) return JNI_FALSE;
    int status = 0;
    pid_t result = waitpid((pid_t) pid, &status, WNOHANG);
    return result == 0 ? JNI_TRUE : JNI_FALSE;
}
