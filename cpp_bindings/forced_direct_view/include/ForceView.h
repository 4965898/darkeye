#ifndef FORCEVIEW_H
#define FORCEVIEW_H

#include <QGraphicsView>
#include <QGraphicsScene>
#include <QTimer>
#include <QVector>
#include <QStringList>
#include <QRectF>
#include <QGraphicsLineItem>

#include <memory>
#include <vector>

#include "PhysicsState.h"
#include "Simulation.h"
#include "NodeLayer.h"

#ifdef BINDINGS_BUILD
#  define FORCEVIEW_EXPORT Q_DECL_EXPORT
#else
#  define FORCEVIEW_EXPORT Q_DECL_IMPORT
#endif

/**
 * ForceView — QGraphicsView that owns a force-directed simulation + renderer.
 *
 * Public API designed for Python (via Shiboken): call setGraph() with flat
 * arrays, connect to Qt signals for business events.
 *
 * Merges the roles of the Python ForceView + ForceGraphController,
 * eliminating multi-process IPC entirely.
 */
class FORCEVIEW_EXPORT ForceView : public QGraphicsView
{
    Q_OBJECT

public:
    explicit ForceView(QWidget* parent = nullptr);
    ~ForceView() override;

    // ======================== Graph Data ========================
    /**
     * Load / replace graph.  All arrays are flat and ordered by node index.
     *
     * @param nNodes  Number of nodes.
     * @param edges   Flat [src0, dst0, src1, dst1, …], length 2*E.
     * @param pos     Flat [x0, y0, x1, y1, …], length 2*N.
     * @param labels  Length N (display name per node).
     * @param radii   Length N (display radius per node).
     */
    void setGraph(int nNodes,
                  const QVector<int>&   edges,
                  const QVector<float>& pos,
                  const QStringList&    labels,
                  const QVector<float>& radii);

    // ======================== Simulation Control ========================
    void pauseSimulation();
    void resumeSimulation();
    void restartSimulation();

    // ======================== Force Parameters ========================
    void setManyBodyStrength(float value);
    void setCenterStrength(float value);
    void setLinkStrength(float value);
    void setLinkDistance(float value);

    // ======================== Visual Parameters ========================
    void setRadiusFactor(float f);
    void setSideWidthFactor(float f);
    void setTextThresholdFactor(float f);

    // ======================== Misc ========================
    void setDragging(int index, bool dragging);
    void setCenterNodeIndex(int index);
    QRectF getContentRect() const;

signals:
    void nodeLeftClicked(int index);
    void nodeRightClicked(int index);
    void nodeHovered(int index);
    void nodePressed(int index);
    void nodeReleased(int index);
    void scaleChanged(float scale);
    void fpsUpdated(float fps);
    void paintTimeUpdated(float ms);
    void tickTimeUpdated(float ms);
    void simulationStarted();
    void simulationStopped();

protected:
    void wheelEvent(QWheelEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;
    void scrollContentsBy(int dx, int dy) override;
    void closeEvent(QCloseEvent* event) override;

private slots:
    void onSimTick();
    void onRenderTick();
    void maybeStopRenderTimer();

    // NodeLayer signal forwarders
    void onNodePressed(int index);
    void onNodeDragged(int index);
    void onNodeReleased(int index);
    void onNodeLeftClicked(int index);
    void onNodeRightClicked(int index);
    void onNodeHovered(int index);

private:
    void setupTimers();
    void ensureRenderTimerRunning();
    void requestRenderActivity();
    void rebuildSimulation();    // (re-)create Simulation + Forces from current params
    void connectNodeLayer();

    // ---- Owned objects ----
    QGraphicsScene* m_scene     = nullptr;
    NodeLayer*      m_nodeLayer = nullptr;   // owned by scene

    std::unique_ptr<PhysicsState> m_physicsState;
    std::unique_ptr<Simulation>   m_simulation;

    // ---- Graph metadata (used for neighbor lookup, etc.) ----
    std::vector<std::vector<int>> m_neighbors;

    // ---- Timers ----
    QTimer* m_simTimer    = nullptr;   // 16 ms — drives simulation tick
    QTimer* m_renderTimer = nullptr;   // 16 ms — drives repaint
    QTimer* m_idleTimer   = nullptr;   // 1000 ms single-shot — stops render when idle
    bool    m_renderActive = false;

    // ---- View state ----
    float m_scaleFactor = 1.0f;
    int   m_centerNodeIndex = -1;

    // ---- Force parameters ----
    float m_manyBodyStrength = 10000.0f;
    float m_linkStrength     = 0.3f;
    float m_linkDistance      = 30.0f;
    float m_centerStrength   = 0.01f;

    bool m_simActive = false;

    // Coordinate axis items (for show_coordinate_sys — retained for compat)
    QList<QGraphicsLineItem*> m_axisItems;
};

#endif // FORCEVIEW_H
