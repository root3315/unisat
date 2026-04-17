/**
 * @file gnss.c
 * @brief GNSS receiver interface (u-blox) implementation
 *
 * Owns a single UBLOX_Handle_t instance configured for the DDC
 * (I2C) port at 0x42. Under SIMULATION_MODE the driver is inert —
 * UBLOX_ReadByte returns UBLOX_ERR_NO_DATA and GNSS_Update becomes
 * a no-op.
 */

#include "gnss.h"
#include "ublox.h"
#include "config.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

static GNSS_Data_t     gnss_data;
static UBLOX_Handle_t  ublox_dev = {
    .i2c_handle  = NULL,
    .addr        = UBLOX_I2C_DEFAULT_ADDR,
    .initialized = false,
};
static char    nmea_buffer[128];
static uint8_t nmea_index = 0;

void GNSS_Init(void) {
    memset(&gnss_data, 0, sizeof(gnss_data));
    gnss_data.fix_type = GNSS_NO_FIX;
    /* Return code intentionally ignored: under SIMULATION_MODE the
     * driver always succeeds; on real hardware a failure just means
     * the sensor is unreachable and GNSS_HasFix() will keep returning
     * false — the rest of the flight software handles that gracefully. */
    (void)UBLOX_Init(&ublox_dev);
}

bool GNSS_GetPosition(double *lat, double *lon, double *alt, uint8_t *fix) {
    *lat = gnss_data.latitude;
    *lon = gnss_data.longitude;
    *alt = gnss_data.altitude;
    *fix = (uint8_t)gnss_data.fix_type;
    return gnss_data.fix_type != GNSS_NO_FIX;
}

bool GNSS_GetVelocity(float *vx, float *vy, float *vz) {
    *vx = gnss_data.velocity_x;
    *vy = gnss_data.velocity_y;
    *vz = gnss_data.velocity_z;
    return gnss_data.fix_type == GNSS_FIX_3D;
}

GNSS_Data_t GNSS_GetFullData(void) {
    return gnss_data;
}

uint8_t GNSS_GetSatelliteCount(void) {
    return gnss_data.satellites;
}

bool GNSS_HasFix(void) {
    return gnss_data.fix_type != GNSS_NO_FIX;
}

/**
 * @brief Parse NMEA coordinate (ddmm.mmmm or dddmm.mmmm)
 */
static double parse_nmea_coord(const char *str, char hemisphere) {
    if (str == NULL || str[0] == '\0') return 0.0;

    double raw = atof(str);
    int degrees = (int)(raw / 100.0);
    double minutes = raw - (degrees * 100.0);
    double decimal = degrees + (minutes / 60.0);

    if (hemisphere == 'S' || hemisphere == 'W') {
        decimal = -decimal;
    }
    return decimal;
}

/**
 * @brief Parse comma-separated field from NMEA sentence
 */
static const char *get_field(const char *sentence, int field_num) {
    int current = 0;
    const char *p = sentence;

    while (*p && current < field_num) {
        if (*p == ',') current++;
        p++;
    }
    return p;
}

void GNSS_ProcessNMEA(const char *sentence) {
    if (sentence == NULL) return;

    /* Parse GGA sentence: position and fix data */
    if (strncmp(sentence, "$GNGGA", 6) == 0 ||
        strncmp(sentence, "$GPGGA", 6) == 0) {

        const char *lat_str = get_field(sentence, 2);
        const char *lat_hem = get_field(sentence, 3);
        const char *lon_str = get_field(sentence, 4);
        const char *lon_hem = get_field(sentence, 5);
        const char *fix_str = get_field(sentence, 6);
        const char *sat_str = get_field(sentence, 7);
        const char *alt_str = get_field(sentence, 9);

        int fix_quality = atoi(fix_str);
        if (fix_quality > 0) {
            gnss_data.latitude = parse_nmea_coord(lat_str, *lat_hem);
            gnss_data.longitude = parse_nmea_coord(lon_str, *lon_hem);
            gnss_data.altitude = atof(alt_str);
            gnss_data.satellites = (uint8_t)atoi(sat_str);
            gnss_data.fix_type = (fix_quality >= 2) ? GNSS_FIX_3D : GNSS_FIX_2D;
        } else {
            gnss_data.fix_type = GNSS_NO_FIX;
        }
    }

    /* Parse RMC sentence: velocity data */
    if (strncmp(sentence, "$GNRMC", 6) == 0 ||
        strncmp(sentence, "$GPRMC", 6) == 0) {

        const char *speed_str = get_field(sentence, 7);
        const char *course_str = get_field(sentence, 8);

        float speed_knots = (float)atof(speed_str);
        float course_deg = (float)atof(course_str);
        float speed_ms = speed_knots * 0.514444f;

        /* Convert to ECI-approximate velocity components */
        float course_rad = course_deg * 3.14159265f / 180.0f;
        gnss_data.velocity_x = speed_ms * sinf(course_rad);
        gnss_data.velocity_y = speed_ms * cosf(course_rad);
        gnss_data.velocity_z = 0.0f;
        gnss_data.speed = speed_ms;
    }
}

void GNSS_Update(void) {
    uint8_t byte;
    /* Drain the DDC buffer into the NMEA parser. UBLOX_ReadByte
     * returns UBLOX_OK per available byte and UBLOX_ERR_NO_DATA
     * when the buffer is empty (or always, under SIMULATION_MODE). */
    while (UBLOX_ReadByte(&ublox_dev, &byte) == UBLOX_OK) {
        if (byte == '$') {
            nmea_index = 0;
        }

        if (nmea_index < sizeof(nmea_buffer) - 1) {
            nmea_buffer[nmea_index++] = (char)byte;
        }

        if (byte == '\n') {
            nmea_buffer[nmea_index] = '\0';
            GNSS_ProcessNMEA(nmea_buffer);
            nmea_index = 0;
        }
    }
}
