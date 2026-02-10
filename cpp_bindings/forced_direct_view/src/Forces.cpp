#include "Forces.h"
#include <cmath>
#include <algorithm>


// =====================================================================
// CenterForce
// =====================================================================
CenterForce::CenterForce(float cx, float cy, float strength)
    : m_cx(cx), m_cy(cy), m_strength(strength)
{}

void CenterForce::apply(float alpha)
{
    const int N = m_state->nNodes;
    const float sa = m_strength * alpha;
    float* vel = m_state->vel.data();
    const float* pos = m_state->pos.data();

    for (int i = 0; i < N; ++i) {
        float dx = m_cx - pos[2 * i];
        float dy = m_cy - pos[2 * i + 1];
        vel[2 * i]     += dx * sa;
        vel[2 * i + 1] += dy * sa;
    }
}

// =====================================================================
// LinkForce
// =====================================================================
LinkForce::LinkForce(float k, float distance)
    : m_k(k), m_distance(distance)
{}

void LinkForce::apply(float alpha)
{
    const int E = m_state->edgeCount();
    if (E == 0) return;

    const int*   edges = m_state->edges.data();
    const float* pos   = m_state->pos.data();
    float*       vel   = m_state->vel.data();
    const float  ka    = m_k * alpha;
    const float  dist  = m_distance;

    for (int e = 0; e < E; ++e) {
        int s = edges[2 * e];
        int d = edges[2 * e + 1];

        float dx = pos[2 * d]     - pos[2 * s];
        float dy = pos[2 * d + 1] - pos[2 * s + 1];
        float len = std::sqrt(dx * dx + dy * dy) + 1e-6f;
        float f   = (len - dist) / len * ka;

        float fx = dx * f;
        float fy = dy * f;

        vel[2 * s]     += fx;
        vel[2 * s + 1] += fy;
        vel[2 * d]     -= fx;
        vel[2 * d + 1] -= fy;
    }
}

// =====================================================================
// ManyBodyForce
// =====================================================================
ManyBodyForce::ManyBodyForce(float strength, float cutoff2)
    : m_strength(strength), m_cutoff2(cutoff2)
{}

void ManyBodyForce::apply(float alpha)
{
    const int N = m_state->nNodes;
    if (N < 2) return;

    if (N < 2000) {
        applyBlock(alpha, 256);
        //applyParallel(alpha);
    } else {
        applyParallel(alpha);
    }
}

// Block-tiled O(N^2) — mirrors Python manybody_block_kernel
void ManyBodyForce::applyBlock(float alpha, int block)
{
    const int    N        = m_state->nNodes;
    const float* pos      = m_state->pos.data();
    const float* mass     = m_state->mass.data();
    float*       vel      = m_state->vel.data();
    const float  strength = m_strength;
    const float  cutoff2  = m_cutoff2;

    for (int i0 = 0; i0 < N; i0 += block) {
        int i1 = std::min(i0 + block, N);
        for (int j0 = 0; j0 < N; j0 += block) {
            int j1 = std::min(j0 + block, N);
            for (int i = i0; i < i1; ++i) {
                float xi = pos[2 * i];
                float yi = pos[2 * i + 1];
                float mi = mass[i];
                for (int j = j0; j < j1; ++j) {
                    // Skip symmetric half when in the same block
                    if (i0 == j0 && i >= j) continue;

                    float dx = xi - pos[2 * j];
                    float dy = yi - pos[2 * j + 1];
                    float dist2 = dx * dx + dy * dy + 1e-6f;
                    if (dist2 >= cutoff2) continue;

                    float mj = mass[j];
                    float s  = strength * mi * mj / dist2;
                    float invd = 1.0f / std::sqrt(dist2);
                    float fx = s * dx * invd * alpha;
                    float fy = s * dy * invd * alpha;

                    vel[2 * i]     += fx;
                    vel[2 * i + 1] += fy;
                    vel[2 * j]     -= fx;
                    vel[2 * j + 1] -= fy;
                }
            }
        }
    }
}

// Parallel kernel for N >= 2000
void ManyBodyForce::applyParallel(float alpha)
{
    const int    N        = m_state->nNodes;
    const float* pos      = m_state->pos.data();
    const float* mass     = m_state->mass.data();
    float*       vel      = m_state->vel.data();
    const float  strength = m_strength;
    const float  cutoff2  = m_cutoff2;

    // Each thread accumulates its own force for node i, then writes.
    // This avoids race conditions on vel[j] — only vel[i] is written per i.

#pragma omp parallel for schedule(static)
    for (int i = 0; i < N; ++i) {
        float xi = pos[2 * i];
        float yi = pos[2 * i + 1];
        float mi = mass[i];

        float fx_sum = 0.0f;
        float fy_sum = 0.0f;

        for (int j = 0; j < N; ++j) {
            if (i == j) continue;

            float dx = xi - pos[2 * j];
            float dy = yi - pos[2 * j + 1];
            float dist2 = dx * dx + dy * dy + 1e-6f;
            if (dist2 >= cutoff2) continue;

            float s = strength * mi * mass[j] / dist2;
            float invd = 1.0f / std::sqrt(dist2);

            fx_sum += s * dx * invd * alpha;
            fy_sum += s * dy * invd * alpha;
        }

        vel[2 * i]     += fx_sum;
        vel[2 * i + 1] += fy_sum;
    }
}

// =====================================================================
// CollisionForce
// =====================================================================
CollisionForce::CollisionForce(float radius, float strength)
    : m_radius(radius), m_strength(strength)
{}

void CollisionForce::apply(float alpha)
{
    const int N = m_state->nNodes;
    if (N < 2) return;

    if (N < 2000) {
        const float* pos = m_state->pos.data();
        float*       vel = m_state->vel.data();
        const float  R   = m_radius;
        const float  sa  = m_strength * alpha;
        const float  eps = 1e-6f;

        for (int i = 0; i < N; ++i) {
            float xi = pos[2 * i];
            float yi = pos[2 * i + 1];
            float fx_sum = 0.0f;
            float fy_sum = 0.0f;

            for (int j = 0; j < N; ++j) {
                if (i == j) continue;
                float dx = xi - pos[2 * j];
                float dy = yi - pos[2 * j + 1];
                float dist = std::sqrt(dx * dx + dy * dy) + eps;
                if (dist >= R) continue;

                float overlap = R - dist;
                float f = sa * overlap / dist;
                fx_sum += f * dx;
                fy_sum += f * dy;
            }

            vel[2 * i]     += fx_sum;
            vel[2 * i + 1] += fy_sum;
        }
    } else {
        applyParallel(alpha);
    }
}

void CollisionForce::applyParallel(float alpha)
{
    const int    N        = m_state->nNodes;
    const float* pos      = m_state->pos.data();
    float*       vel      = m_state->vel.data();
    const float  R        = m_radius;
    const float  sa       = m_strength * alpha;
    const float  eps      = 1e-6f;

#pragma omp parallel for schedule(static)
    for (int i = 0; i < N; ++i) {
        float xi = pos[2 * i];
        float yi = pos[2 * i + 1];
        float fx_sum = 0.0f;
        float fy_sum = 0.0f;

        for (int j = 0; j < N; ++j) {
            if (i == j) continue;
            float dx = xi - pos[2 * j];
            float dy = yi - pos[2 * j + 1];
            float dist = std::sqrt(dx * dx + dy * dy) + eps;
            if (dist >= R) continue;

            float overlap = R - dist;
            float f = sa * overlap / dist;
            fx_sum += f * dx;
            fy_sum += f * dy;
        }

        vel[2 * i]     += fx_sum;
        vel[2 * i + 1] += fy_sum;
    }
}
