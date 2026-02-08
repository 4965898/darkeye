#ifndef FORCES_H
#define FORCES_H

#include "PhysicsState.h"
#include <string>

// ---------------------------------------------------------------------------
// Force – abstract base
// ---------------------------------------------------------------------------
class Force
{
public:
    virtual ~Force() = default;

    virtual void initialize(PhysicsState* state) { m_state = state; }
    virtual void apply(float alpha) = 0;

protected:
    PhysicsState* m_state = nullptr;
};

// ---------------------------------------------------------------------------
// CenterForce – pulls every node toward (cx, cy)   O(N)
// ---------------------------------------------------------------------------
class CenterForce : public Force
{
public:
    CenterForce(float cx = 0.0f, float cy = 0.0f, float strength = 0.1f);

    void apply(float alpha) override;

    void setStrength(float s) { m_strength = s; }
    float strength() const    { return m_strength; }

private:
    float m_cx;
    float m_cy;
    float m_strength;
};

// ---------------------------------------------------------------------------
// LinkForce – spring between connected nodes   O(E)
// ---------------------------------------------------------------------------
class LinkForce : public Force
{
public:
    LinkForce(float k = 0.02f, float distance = 30.0f);

    void apply(float alpha) override;

    void setK(float k)            { m_k = k; }
    float k() const               { return m_k; }
    void setDistance(float d)      { m_distance = d; }
    float distance() const        { return m_distance; }

private:
    float m_k;
    float m_distance;
};

// ---------------------------------------------------------------------------
// ManyBodyForce – pairwise repulsion   O(N^2)
//   Uses block-tiled kernel for N < 2000, plain parallel for larger N.
// ---------------------------------------------------------------------------
class ManyBodyForce : public Force
{
public:
    ManyBodyForce(float strength = 100.0f, float cutoff2 = 40000.0f);

    void apply(float alpha) override;

    void setStrength(float s) { m_strength = s; }
    float strength() const    { return m_strength; }

private:
    // Block-tiled kernel (mirrors Python manybody_block_kernel)
    void applyBlock(float alpha, int blockSize);

    // Parallel kernel for larger graphs
    void applyParallel(float alpha);

    float m_strength;
    float m_cutoff2;
};

#endif // FORCES_H
