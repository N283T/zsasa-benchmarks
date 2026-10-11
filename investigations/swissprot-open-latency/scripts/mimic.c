// Reproduces a batch tool's per-file system-call sequence. Read-only on the inputs.
#include <dirent.h>
#include <fcntl.h>
#include <pthread.h>
#include <pthread/qos.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static char **paths;
static int n_paths;
static atomic_int next_idx;
static const char *mode = "read"; // none | read | read4k | stdio | mmap
static int spin_mem_mb = 0;
static int stat_ahead = -1, vm_churn = 0, vm_churn_mb = 4;
static int prestat = 0, qos = 0, statonly = 0;
static int do_fstat = 0, do_stat_first = 0, spin_us = 0, write_bytes = 0, write_fd = -1, spin_before = 0;
static pthread_mutex_t out_mu = PTHREAD_MUTEX_INITIALIZER;
static _Atomic double t_open, t_data, t_close, t_write;

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}
static double thread_cpu(void) {
    struct timespec ts;
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}
static void add(_Atomic double *acc, double v) {
    double old = atomic_load(acc);
    while (!atomic_compare_exchange_weak(acc, &old, old + v)) {}
}
static __thread unsigned char *spin_buf;
static void spin(int us) {
    double end = thread_cpu() + us * 1e-6;
    volatile double x = 1.0;
    if (spin_mem_mb) {
        size_t len = (size_t)spin_mem_mb << 20;
        if (!spin_buf) { spin_buf = malloc(len); memset(spin_buf, 1, len); }
        unsigned long s = 88172645463325252UL;
        volatile unsigned long acc = 0;
        while (thread_cpu() < end)
            for (int i = 0; i < 2000; i++) {
                s ^= s << 13; s ^= s >> 7; s ^= s << 17;
                size_t k = s % len;
                acc += spin_buf[k];
                spin_buf[k] = (unsigned char)acc;
            }
        return;
    }
    while (thread_cpu() < end)
        for (int i = 0; i < 2000; i++) x = x * 1.0000001 + 0.5;
}

static void *worker(void *arg) {
    (void)arg;
    if (qos == 1) pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0);
    if (qos == 2) pthread_set_qos_class_self_np(QOS_CLASS_BACKGROUND, 0);
    if (qos == 3) pthread_set_qos_class_self_np(QOS_CLASS_USER_INITIATED, 0);
    if (qos == 4) pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
    char *buf = malloc(1 << 20), *outbuf = NULL;
    if (write_bytes) { outbuf = malloc(write_bytes); memset(outbuf, 'x', write_bytes); outbuf[write_bytes - 1] = '\n'; }
    double lo = 0, ld = 0, lc = 0, lw = 0;
    for (;;) {
        int i = atomic_fetch_add(&next_idx, 1);
        if (i >= n_paths) break;
        const char *p = paths[i];
        struct stat st;
        if (spin_before) spin(spin_us);
        if (do_stat_first) stat(p, &st);
        if (stat_ahead >= 0 && i + stat_ahead < n_paths) stat(paths[i + stat_ahead], &st);
        if (statonly) { stat(p, &st); continue; }
        double t0 = now();
        int fd = -1;
        FILE *f = NULL;
        if (!strcmp(mode, "stdio")) { f = fopen(p, "rb"); if (!f) { perror(p); exit(1); } }
        else { fd = open(p, O_RDONLY | O_CLOEXEC); if (fd < 0) { perror(p); exit(1); } }
        double t1 = now();
        volatile unsigned long sum = 0;
        if (f) {
            while (fgets(buf, 256, f)) sum += (unsigned char)buf[0];
        } else {
            if (do_fstat || !strcmp(mode, "mmap") || !strcmp(mode, "read")) fstat(fd, &st);
            if (!strcmp(mode, "read")) {
                char *data = malloc(st.st_size + 1);
                ssize_t got, total = 0;
                while (total < st.st_size && (got = read(fd, data + total, st.st_size - total)) > 0) total += got;
                for (off_t k = 0; k < total; k += 64) sum += (unsigned char)data[k];
                free(data);
            } else if (!strcmp(mode, "readbuf")) {
                ssize_t got, total = 0;
                while ((got = read(fd, buf + total, (1 << 20) - total)) > 0) total += got;
                for (off_t k = 0; k < total; k += 64) sum += (unsigned char)buf[k];
            } else if (!strcmp(mode, "read64k")) {
                ssize_t got; size_t total = 0;
                while ((got = read(fd, buf + (total % (1 << 19)), 65536)) > 0) total += got;
                sum += (unsigned char)buf[0];
            } else if (!strcmp(mode, "read4k")) {
                ssize_t got;
                while ((got = read(fd, buf, 4096)) > 0) sum += (unsigned char)buf[0];
            } else if (!strcmp(mode, "mmap")) {
                unsigned char *m = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
                if (m == MAP_FAILED) { perror("mmap"); exit(1); }
                for (off_t k = 0; k < st.st_size; k += 64) sum += m[k];
                munmap(m, st.st_size);
            }
        }
        double t2 = now();
        for (int c = 0; c < vm_churn; c++) {
            size_t len = (size_t)vm_churn_mb << 20;
            unsigned char *a = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
            for (size_t k = 0; k < len; k += 16384) a[k] = 1;
            munmap(a, len);
        }
        if (f) fclose(f); else close(fd);
        double t3 = now();
        if (!spin_before && spin_us) spin(spin_us);
        double t4 = now();
        if (write_bytes) {
            pthread_mutex_lock(&out_mu);
            if (write(write_fd, outbuf, write_bytes) < 0) perror("write");
            pthread_mutex_unlock(&out_mu);
        }
        double t5 = now();
        lo += t1 - t0; ld += t2 - t1; lc += t3 - t2; lw += t5 - t4;
    }
    add(&t_open, lo); add(&t_data, ld); add(&t_close, lc); add(&t_write, lw);
    return NULL;
}

static int cmp(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }

int main(int argc, char **argv) {
    const char *dir = argv[1];
    int threads = 10, sorted = 1;
    const char *out = NULL;
    for (int i = 2; i < argc; i++) {
        if (!strncmp(argv[i], "--mode=", 7)) mode = argv[i] + 7;
        else if (!strcmp(argv[i], "--fstat")) do_fstat = 1;
        else if (!strcmp(argv[i], "--stat-first")) do_stat_first = 1;
        else if (!strcmp(argv[i], "--spin-before")) spin_before = 1;
        else if (!strncmp(argv[i], "--spin-us=", 10)) spin_us = atoi(argv[i] + 10);
        else if (!strncmp(argv[i], "--write-bytes=", 14)) write_bytes = atoi(argv[i] + 14);
        else if (!strncmp(argv[i], "--out=", 6)) out = argv[i] + 6;
        else if (!strncmp(argv[i], "--threads=", 10)) threads = atoi(argv[i] + 10);
        else if (!strcmp(argv[i], "--unsorted")) sorted = 0;
        else if (!strcmp(argv[i], "--prestat")) prestat = 1;
        else if (!strncmp(argv[i], "--iopol=", 8)) {
            const char *v = argv[i] + 8;
            int pol = !strcmp(v, "passive") ? IOPOL_PASSIVE : !strcmp(v, "utility") ? IOPOL_UTILITY : !strcmp(v, "throttle") ? IOPOL_THROTTLE : !strcmp(v, "important") ? IOPOL_IMPORTANT : IOPOL_STANDARD;
            if (setiopolicy_np(IOPOL_TYPE_DISK, IOPOL_SCOPE_PROCESS, pol) != 0) { perror("setiopolicy_np"); return 1; }
        }
        else if (!strncmp(argv[i], "--spin-mem=", 11)) spin_mem_mb = atoi(argv[i] + 11);
        else if (!strncmp(argv[i], "--vm-churn=", 11)) vm_churn = atoi(argv[i] + 11);
        else if (!strncmp(argv[i], "--vm-churn-mb=", 14)) vm_churn_mb = atoi(argv[i] + 14);
        else if (!strncmp(argv[i], "--stat-ahead=", 13)) stat_ahead = atoi(argv[i] + 13);
        else if (!strcmp(argv[i], "--stat-only")) statonly = 1;
        else if (!strncmp(argv[i], "--qos=", 6)) qos = !strcmp(argv[i] + 6, "utility") ? 1 : !strcmp(argv[i] + 6, "background") ? 2 : !strcmp(argv[i] + 6, "initiated") ? 3 : 4;
        else { fprintf(stderr, "unknown option %s\n", argv[i]); return 2; }
    }
    DIR *d = opendir(dir);
    if (!d) { perror(dir); return 1; }
    int cap = 1 << 14;
    paths = malloc(cap * sizeof *paths);
    struct dirent *e;
    while ((e = readdir(d))) {
        if (e->d_name[0] == '.') continue;
        if (n_paths == cap) paths = realloc(paths, (cap *= 2) * sizeof *paths);
        size_t len = strlen(dir) + strlen(e->d_name) + 2;
        paths[n_paths] = malloc(len);
        snprintf(paths[n_paths++], len, "%s/%s", dir, e->d_name);
    }
    closedir(d);
    if (sorted) qsort(paths, n_paths, sizeof *paths, cmp);
    if (write_bytes) { write_fd = open(out, O_WRONLY | O_CREAT | O_TRUNC, 0644); if (write_fd < 0) { perror(out); return 1; } }
    double tp = now();
    if (prestat) { struct stat st; for (int i = 0; i < n_paths; i++) stat(paths[i], &st); fprintf(stderr, "prestat %.3f s\n", now() - tp); }
    pthread_t *ts = malloc(threads * sizeof *ts);
    double t0 = now();
    for (int i = 0; i < threads; i++) pthread_create(&ts[i], NULL, worker, NULL);
    for (int i = 0; i < threads; i++) pthread_join(ts[i], NULL);
    double wall = now() - t0;
    fprintf(stderr, "MIMIC files=%d wall=%.3f open_ms=%.3f data_ms=%.3f close_ms=%.3f write_ms=%.3f\n", n_paths, wall,
            t_open / n_paths * 1e3, t_data / n_paths * 1e3, t_close / n_paths * 1e3, t_write / n_paths * 1e3);
    return 0;
}
