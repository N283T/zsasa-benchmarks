#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    const char *coord = argc > 1 ? argv[1] : "1145.4261487.1441862.471";
    char fixed[25];
    double x = 0.0, y = 0.0, z = 0.0;
    int parsed = 0;

    strncpy(fixed, coord, 24);
    fixed[24] = '\0';
    parsed = sscanf(fixed, "%lf%lf%lf", &x, &y, &z);

    printf("input:  %s\n", fixed);
    printf("sscanf parsed fields: %d\n", parsed);
    printf("x=%.12g y=%.12g z=%.12g\n", x, y, z);
    return parsed == 3 ? 0 : 1;
}
