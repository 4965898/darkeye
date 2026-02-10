#ifndef PHYSICSSTATE_H
#define PHYSICSSTATE_H

#include <vector>
#include <cstdint>
#include <atomic>
#include <algorithm>

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

    std::vector<float> renderPosA;
    std::vector<float> renderPosB;
    std::atomic<int> renderIndex{0};

    std::vector<float> dragPos;

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
        renderPosA.assign(2 * n, 0.0f);
        renderPosB.assign(2 * n, 0.0f);
        renderIndex.store(0, std::memory_order_release);
        dragPos.assign(2 * n, 0.0f);
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

    const float* renderPosData() const
    {
        int idx = renderIndex.load(std::memory_order_acquire);
        return (idx == 0) ? renderPosA.data() : renderPosB.data();
    }

    void syncRenderPosFromPos()
    {
        if (renderPosA.size() != pos.size()) {
            renderPosA.resize(pos.size());
            renderPosB.resize(pos.size());
        }
        std::copy(pos.begin(), pos.end(), renderPosA.begin());
        std::copy(pos.begin(), pos.end(), renderPosB.begin());
        renderIndex.store(0, std::memory_order_release);
    }

    void publishRenderPos()
    {
        int front = renderIndex.load(std::memory_order_acquire);
        int back = 1 - front;
        auto& dst = (back == 0) ? renderPosA : renderPosB;
        if (dst.size() != pos.size())
            dst.resize(pos.size());
        std::copy(pos.begin(), pos.end(), dst.begin());
        renderIndex.store(back, std::memory_order_release);
    }

    void syncDragPosFromPos()
    {
        if (dragPos.size() != pos.size())
            dragPos.resize(pos.size());
        std::copy(pos.begin(), pos.end(), dragPos.begin());
    }

    void setDragPos(int i, float x, float y)
    {
        if (i < 0 || i >= nNodes) return;
        dragPos[2 * i]     = x;
        dragPos[2 * i + 1] = y;
    }

    void updateRenderPosAt(int i, float x, float y)
    {
        if (i < 0 || i >= nNodes) return;
        int idx = renderIndex.load(std::memory_order_acquire);
        auto& buf = (idx == 0) ? renderPosA : renderPosB;
        if (buf.size() < pos.size())
            buf.resize(pos.size());
        buf[2 * i]     = x;
        buf[2 * i + 1] = y;
    }

    // ---- 运行时修改图结构的辅助方法 ----

    /** 添加一个新节点，返回新节点的索引 */
    int addNode(float x = 0.0f, float y = 0.0f)
    {
        int newIndex = nNodes++;
        pos.resize(2 * nNodes);
        vel.resize(2 * nNodes);
        mass.push_back(1.0f);
        dragging.push_back(0);
        renderPosA.resize(2 * nNodes);
        renderPosB.resize(2 * nNodes);
        dragPos.resize(2 * nNodes);
        pos[2 * newIndex] = x;
        pos[2 * newIndex + 1] = y;
        vel[2 * newIndex] = 0.0f;
        vel[2 * newIndex + 1] = 0.0f;
        renderPosA[2 * newIndex] = x;
        renderPosA[2 * newIndex + 1] = y;
        renderPosB[2 * newIndex] = x;
        renderPosB[2 * newIndex + 1] = y;
        dragPos[2 * newIndex] = x;
        dragPos[2 * newIndex + 1] = y;
        return newIndex;
    }

    /** 删除指定索引的节点（返回是否成功） */
    bool removeNode(int index)
    {
        if (index < 0 || index >= nNodes) return false;

        // 移动最后一个节点到删除位置，保持数组连续
        int last = nNodes - 1;
        if (index != last) {
            pos[2 * index] = pos[2 * last];
            pos[2 * index + 1] = pos[2 * last + 1];
            vel[2 * index] = vel[2 * last];
            vel[2 * index + 1] = vel[2 * last + 1];
            mass[index] = mass[last];
            dragging[index] = dragging[last];
            renderPosA[2 * index] = renderPosA[2 * last];
            renderPosA[2 * index + 1] = renderPosA[2 * last + 1];
            renderPosB[2 * index] = renderPosB[2 * last];
            renderPosB[2 * index + 1] = renderPosB[2 * last + 1];
            dragPos[2 * index] = dragPos[2 * last];
            dragPos[2 * index + 1] = dragPos[2 * last + 1];
        }

        nNodes--;
        pos.resize(2 * nNodes);
        vel.resize(2 * nNodes);
        mass.resize(nNodes);
        dragging.resize(nNodes);
        renderPosA.resize(2 * nNodes);
        renderPosB.resize(2 * nNodes);
        dragPos.resize(2 * nNodes);

        // 移除所有连接到该节点的边
        auto it = std::remove_if(edges.begin(), edges.end(),
            [index](int id) { return id == index; });
        edges.erase(it, edges.end());

        // 更新所有大于删除索引的边端点（因为节点被移动了）
        for (size_t i = 0; i < edges.size(); ++i) {
            if (edges[i] > index) edges[i]--;
        }

        return true;
    }

    /** 添加一条边（u, v 为节点索引，返回是否成功） */
    bool addEdge(int u, int v)
    {
        if (u < 0 || u >= nNodes || v < 0 || v >= nNodes || u == v) return false;

        // 检查是否已存在
        for (size_t i = 0; i < edges.size(); i += 2) {
            if ((edges[i] == u && edges[i + 1] == v) ||
                (edges[i] == v && edges[i + 1] == u)) {
                return false;
            }
        }

        edges.push_back(u);
        edges.push_back(v);
        return true;
    }

    /** 删除一条边（u, v 为节点索引，返回是否成功） */
    bool removeEdge(int u, int v)
    {
        if (u < 0 || u >= nNodes || v < 0 || v >= nNodes) return false;

        // 查找并删除边（检查两个方向）
        for (size_t i = 0; i < edges.size(); i += 2) {
            if ((edges[i] == u && edges[i + 1] == v) ||
                (edges[i] == v && edges[i + 1] == u)) {
                // 删除这两个元素
                edges.erase(edges.begin() + i, edges.begin() + i + 2);
                return true;
            }
        }

        return false;
    }
};

#endif // PHYSICSSTATE_H
