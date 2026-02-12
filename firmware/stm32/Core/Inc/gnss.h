/**
 * @file gnss.h
 * @brief GNSS (GPS) receiver interface
 */

#ifndef GNSS_H
#define GNSS_H

#include <stdint.h>
#include <stdbool.h>

/** GNSS fix type */
typedef enum {
    GNSS_NO_FIX = 0,
    GNSS_FIX_2D,
    GNSS_FIX_3D
} GNSS_FixType_t;

/** GNSS position data */
typedef struct {
    double latitude;
    double longitude;
    double altitude;
    float velocity_x;
    float velocity_y;
    float velocity_z;
    float speed;
    float hdop;
    uint8_t satellites;
    GNSS_FixType_t fix_type;
    uint32_t timestamp;
} GNSS_Data_t;

void GNSS_Init(void);
bool GNSS_GetPosition(double *lat, double *lon, double *alt, uint8_t *fix);
bool GNSS_GetVelocity(float *vx, float *vy, float *vz);
GNSS_Data_t GNSS_GetFullData(void);
uint8_t GNSS_GetSatelliteCount(void);
bool GNSS_HasFix(void);
void GNSS_ProcessNMEA(const char *sentence);
void GNSS_Update(void);

#endif /* GNSS_H */
