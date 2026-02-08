#ifndef PHYSICSSTATE_H
#define PHYSICSSTATE_H

#include <vector>
#include <cstdint>

/**
 * PhysicsState — flat arrays holding the physical state of a force-directed graph.
 *
 * All per-node arrays are indexed 0..nNodes-1.
 * pos / vel are interleaved: [x0,y0, x1,y1, …], length 2*nNodes.
 * edges is interleaved: [src0,dst0, src1,dst1, …], length 2*edgeCount.
 */
struct PhysicsState
{
    int nNodes = 0;

    // positions  – flat [x0,y0, x1,y1, ...], size 2*nNodes
    std::vector<float> pos;

    // velocities – flat [x0,y0, x1,y1, ...], size 2*nNodes
    std::vector<float> vel;

    // per-node mass, size nNodes (default 1.0)
    std::vector<float> mass;

    // per-node dragging flag, size nNodes
    std::vector<uint8_t> dragging;   // 0 or 1 (avoid std::vector<bool> proxy)

    // edge list – flat [src0,dst0, src1,dst1, ...], size 2*E
    std::vector<int> edges;

    // ---- helpers ---------------------------------------------------------

    int edgeCount() const { return static_cast<int>(edges.size()) / 2; }

    /** Allocate / reset all arrays for nNodes nodes and the given edge list.
     *  pos is NOT zeroed — caller must fill it (e.g. from Python initial layout).
     */
    void init(int n, const std::vector<int>& edgeList)
    {
        nNodes = n;
        pos.resize(2 * n);
        vel.assign(2 * n, 0.0f);
        mass.assign(n, 1.0f);
        dragging.assign(n, 0);
        edges = edgeList;
    }

    // Convenience: pos accessors (no bounds check for speed)
    float  px(int i) const { return pos[2 * i];     }
    float  py(int i) const { return pos[2 * i + 1]; }
    float& px(int i)       { return pos[2 * i];     }
    float& py(int i)       { return pos[2 * i + 1]; }

    float  vx(int i) const { return vel[2 * i];     }
    float  vy(int i) const { return vel[2 * i + 1]; }
    float& vx(int i)       { return vel[2 * i];     }
    float& vy(int i)       { return vel[2 * i + 1]; }
};

#endif // PHYSICSSTATE_H
