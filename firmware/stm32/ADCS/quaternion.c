/**
 * @file quaternion.c
 * @brief Full quaternion math library implementation
 */

#include "quaternion.h"
#include <math.h>

Quaternion_t Quat_Identity(void) {
    return (Quaternion_t){1.0f, 0.0f, 0.0f, 0.0f};
}

Quaternion_t Quat_Multiply(Quaternion_t a, Quaternion_t b) {
    Quaternion_t r;
    r.w = a.w*b.w - a.x*b.x - a.y*b.y - a.z*b.z;
    r.x = a.w*b.x + a.x*b.w + a.y*b.z - a.z*b.y;
    r.y = a.w*b.y - a.x*b.z + a.y*b.w + a.z*b.x;
    r.z = a.w*b.z + a.x*b.y - a.y*b.x + a.z*b.w;
    return r;
}

Quaternion_t Quat_Conjugate(Quaternion_t q) {
    return (Quaternion_t){q.w, -q.x, -q.y, -q.z};
}

float Quat_Norm(Quaternion_t q) {
    return sqrtf(q.w*q.w + q.x*q.x + q.y*q.y + q.z*q.z);
}

Quaternion_t Quat_Normalize(Quaternion_t q) {
    float n = Quat_Norm(q);
    if (n < 1e-10f) return Quat_Identity();
    float inv = 1.0f / n;
    return (Quaternion_t){q.w*inv, q.x*inv, q.y*inv, q.z*inv};
}

Quaternion_t Quat_Inverse(Quaternion_t q) {
    float norm_sq = q.w*q.w + q.x*q.x + q.y*q.y + q.z*q.z;
    if (norm_sq < 1e-10f) return Quat_Identity();
    float inv = 1.0f / norm_sq;
    return (Quaternion_t){q.w*inv, -q.x*inv, -q.y*inv, -q.z*inv};
}

Quaternion_t Quat_FromEuler(EulerAngles_t e) {
    float cr = cosf(e.roll * 0.5f),  sr = sinf(e.roll * 0.5f);
    float cp = cosf(e.pitch * 0.5f), sp = sinf(e.pitch * 0.5f);
    float cy = cosf(e.yaw * 0.5f),   sy = sinf(e.yaw * 0.5f);

    Quaternion_t q;
    q.w = cr*cp*cy + sr*sp*sy;
    q.x = sr*cp*cy - cr*sp*sy;
    q.y = cr*sp*cy + sr*cp*sy;
    q.z = cr*cp*sy - sr*sp*cy;
    return Quat_Normalize(q);
}

EulerAngles_t Quat_ToEuler(Quaternion_t q) {
    EulerAngles_t e;

    /* Roll (x-axis rotation) */
    float sinr_cosp = 2.0f * (q.w*q.x + q.y*q.z);
    float cosr_cosp = 1.0f - 2.0f * (q.x*q.x + q.y*q.y);
    e.roll = atan2f(sinr_cosp, cosr_cosp);

    /* Pitch (y-axis rotation) */
    float sinp = 2.0f * (q.w*q.y - q.z*q.x);
    if (fabsf(sinp) >= 1.0f)
        e.pitch = copysignf(3.14159265f / 2.0f, sinp);
    else
        e.pitch = asinf(sinp);

    /* Yaw (z-axis rotation) */
    float siny_cosp = 2.0f * (q.w*q.z + q.x*q.y);
    float cosy_cosp = 1.0f - 2.0f * (q.y*q.y + q.z*q.z);
    e.yaw = atan2f(siny_cosp, cosy_cosp);

    return e;
}

DCM_t Quat_ToDCM(Quaternion_t q) {
    DCM_t dcm;
    float xx = q.x*q.x, yy = q.y*q.y, zz = q.z*q.z;
    float xy = q.x*q.y, xz = q.x*q.z, yz = q.y*q.z;
    float wx = q.w*q.x, wy = q.w*q.y, wz = q.w*q.z;

    dcm.m[0][0] = 1.0f - 2.0f*(yy + zz);
    dcm.m[0][1] = 2.0f*(xy - wz);
    dcm.m[0][2] = 2.0f*(xz + wy);
    dcm.m[1][0] = 2.0f*(xy + wz);
    dcm.m[1][1] = 1.0f - 2.0f*(xx + zz);
    dcm.m[1][2] = 2.0f*(yz - wx);
    dcm.m[2][0] = 2.0f*(xz - wy);
    dcm.m[2][1] = 2.0f*(yz + wx);
    dcm.m[2][2] = 1.0f - 2.0f*(xx + yy);

    return dcm;
}

Quaternion_t Quat_FromDCM(DCM_t dcm) {
    Quaternion_t q;
    float trace = dcm.m[0][0] + dcm.m[1][1] + dcm.m[2][2];

    if (trace > 0.0f) {
        float s = 0.5f / sqrtf(trace + 1.0f);
        q.w = 0.25f / s;
        q.x = (dcm.m[2][1] - dcm.m[1][2]) * s;
        q.y = (dcm.m[0][2] - dcm.m[2][0]) * s;
        q.z = (dcm.m[1][0] - dcm.m[0][1]) * s;
    } else if (dcm.m[0][0] > dcm.m[1][1] && dcm.m[0][0] > dcm.m[2][2]) {
        float s = 2.0f * sqrtf(1.0f + dcm.m[0][0] - dcm.m[1][1] - dcm.m[2][2]);
        q.w = (dcm.m[2][1] - dcm.m[1][2]) / s;
        q.x = 0.25f * s;
        q.y = (dcm.m[0][1] + dcm.m[1][0]) / s;
        q.z = (dcm.m[0][2] + dcm.m[2][0]) / s;
    } else if (dcm.m[1][1] > dcm.m[2][2]) {
        float s = 2.0f * sqrtf(1.0f + dcm.m[1][1] - dcm.m[0][0] - dcm.m[2][2]);
        q.w = (dcm.m[0][2] - dcm.m[2][0]) / s;
        q.x = (dcm.m[0][1] + dcm.m[1][0]) / s;
        q.y = 0.25f * s;
        q.z = (dcm.m[1][2] + dcm.m[2][1]) / s;
    } else {
        float s = 2.0f * sqrtf(1.0f + dcm.m[2][2] - dcm.m[0][0] - dcm.m[1][1]);
        q.w = (dcm.m[1][0] - dcm.m[0][1]) / s;
        q.x = (dcm.m[0][2] + dcm.m[2][0]) / s;
        q.y = (dcm.m[1][2] + dcm.m[2][1]) / s;
        q.z = 0.25f * s;
    }

    return Quat_Normalize(q);
}

Quaternion_t Quat_FromAxisAngle(float axis[3], float angle) {
    float half = angle * 0.5f;
    float s = sinf(half);
    float n = sqrtf(axis[0]*axis[0] + axis[1]*axis[1] + axis[2]*axis[2]);
    if (n < 1e-10f) return Quat_Identity();
    float inv = s / n;

    return Quat_Normalize((Quaternion_t){
        cosf(half), axis[0]*inv, axis[1]*inv, axis[2]*inv
    });
}

/**
 * @brief Kinematic equation: dq/dt = 0.5 * q * omega_quat
 */
Quaternion_t Quat_Integrate(Quaternion_t q, float omega[3], float dt) {
    Quaternion_t omega_q = {0.0f, omega[0], omega[1], omega[2]};
    Quaternion_t qdot = Quat_Multiply(q, omega_q);

    q.w += 0.5f * qdot.w * dt;
    q.x += 0.5f * qdot.x * dt;
    q.y += 0.5f * qdot.y * dt;
    q.z += 0.5f * qdot.z * dt;

    return Quat_Normalize(q);
}

Quaternion_t Quat_Error(Quaternion_t current, Quaternion_t target) {
    Quaternion_t target_inv = Quat_Inverse(target);
    Quaternion_t err = Quat_Multiply(target_inv, current);

    /* Ensure shortest path */
    if (err.w < 0.0f) {
        err.w = -err.w;
        err.x = -err.x;
        err.y = -err.y;
        err.z = -err.z;
    }

    return err;
}

void Quat_RotateVector(Quaternion_t q, const float v_in[3], float v_out[3]) {
    Quaternion_t v = {0.0f, v_in[0], v_in[1], v_in[2]};
    Quaternion_t q_conj = Quat_Conjugate(q);
    Quaternion_t result = Quat_Multiply(Quat_Multiply(q, v), q_conj);
    v_out[0] = result.x;
    v_out[1] = result.y;
    v_out[2] = result.z;
}
