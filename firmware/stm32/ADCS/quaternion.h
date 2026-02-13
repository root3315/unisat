/**
 * @file quaternion.h
 * @brief Quaternion mathematics library for attitude representation
 */

#ifndef QUATERNION_H
#define QUATERNION_H

#include <stdint.h>

/** Quaternion: q = [w, x, y, z] where w is scalar part */
typedef struct {
    float w, x, y, z;
} Quaternion_t;

/** 3x3 Direction Cosine Matrix */
typedef struct {
    float m[3][3];
} DCM_t;

/** Euler angles (radians): roll, pitch, yaw */
typedef struct {
    float roll;
    float pitch;
    float yaw;
} EulerAngles_t;

Quaternion_t Quat_Identity(void);
Quaternion_t Quat_Multiply(Quaternion_t a, Quaternion_t b);
Quaternion_t Quat_Conjugate(Quaternion_t q);
Quaternion_t Quat_Inverse(Quaternion_t q);
Quaternion_t Quat_Normalize(Quaternion_t q);
float Quat_Norm(Quaternion_t q);
Quaternion_t Quat_FromEuler(EulerAngles_t euler);
EulerAngles_t Quat_ToEuler(Quaternion_t q);
DCM_t Quat_ToDCM(Quaternion_t q);
Quaternion_t Quat_FromDCM(DCM_t dcm);
Quaternion_t Quat_FromAxisAngle(float axis[3], float angle);
Quaternion_t Quat_Integrate(Quaternion_t q, float omega[3], float dt);
Quaternion_t Quat_Error(Quaternion_t current, Quaternion_t target);
void Quat_RotateVector(Quaternion_t q, const float v_in[3], float v_out[3]);

#endif /* QUATERNION_H */
