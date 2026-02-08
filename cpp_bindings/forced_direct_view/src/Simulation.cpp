#include "Simulation.h"
#include <cmath>
#include <algorithm>

// =====================================================================
// Construction
// =====================================================================
Simulation::Simulation(PhysicsState* state)
    : m_state(state)
{}

// =====================================================================
// Force management
// =====================================================================
void Simulation::addForce(const std::string& name, std::unique_ptr<Force> force)
{
    force->initialize(m_state);
    m_forces[name] = std::move(force);
}

void Simulation::removeForce(const std::string& name)
{
    m_forces.erase(name);
}

Force* Simulation::getForce(const std::string& name) const
{
    auto it = m_forces.find(name);
    return (it != m_forces.end()) ? it->second.get() : nullptr;
}

// =====================================================================
// Tick — single simulation step
// =====================================================================
void Simulation::tick()
{
    if (m_alpha <= m_alphaMin) {
        m_active = false;
        return;
    }

    // Apply each force (modifies vel)
    for (auto& [name, force] : m_forces) {
        force->apply(m_alpha);
    }

    // Integrate velocities -> positions
    float totalSpeed = integrate();

    // Cooling
    ++m_tickCount;
    if (m_firstStarted && m_tickCount >= m_cooldownDelay) {
        m_alpha *= (1.0f - m_alphaDecay);
    }

    // Early stop when almost settled
    float avgSpeed = totalSpeed / std::max(1, m_state->nNodes);
    if (avgSpeed < 0.01f && m_alpha < 0.01f) {
        m_active = false;
    }
}

// =====================================================================
// Integrate — velocity decay, max displacement clamp, position update
// =====================================================================
float Simulation::integrate()
{
    const int   N       = m_state->nNodes;
    float*      pos     = m_state->pos.data();
    float*      vel     = m_state->vel.data();
    const auto& drag    = m_state->dragging;
    const float decay   = m_velocityDecay;
    const float dt      = m_dt;
    const float maxDisp = m_maxDisp;

    // Velocity decay (all nodes)
    for (int i = 0; i < 2 * N; ++i) {
        vel[i] *= decay;
    }

    float totalSpeed = 0.0f;

    for (int i = 0; i < N; ++i) {
        float vxi = vel[2 * i];
        float vyi = vel[2 * i + 1];

        totalSpeed += std::fabs(vxi) + std::fabs(vyi);

        // Skip dragged nodes
        if (drag[i]) continue;

        float speed = std::sqrt(vxi * vxi + vyi * vyi);
        if (speed * dt > maxDisp && speed > 1e-8f) {
            float scale = maxDisp / (speed * dt);
            vxi *= scale;
            vyi *= scale;
            vel[2 * i]     = vxi;
            vel[2 * i + 1] = vyi;
        }

        pos[2 * i]     += vxi * dt;
        pos[2 * i + 1] += vyi * dt;
    }

    return totalSpeed;
}

// =====================================================================
// Lifecycle
// =====================================================================
void Simulation::start()
{
    m_active = true;
    if (!m_firstStarted) {
        m_firstStarted = true;
    }
}

void Simulation::stop()
{
    m_active = false;
}

void Simulation::pause()
{
    m_active = false;
}

void Simulation::resume()
{
    if (m_alpha > m_alphaMin) {
        m_active = true;
    }
}

void Simulation::restart()
{
    m_alpha     = 1.0f;
    m_tickCount = 0;
    m_active    = true;
}
