#include <QApplication>
#include <QVector>
#include <QStringList>
#include <QDebug>
#include <cstdlib>
#include <cmath>

#include "ForceView.h"

/**
 * Standalone test: creates a ForceView with a random graph and shows it.
 */

static void generateRandomGraph(int nNodes, int avgDegree,
                                QVector<int>& edges,
                                QVector<float>& pos,
                                QStringList& labels,
                                QVector<float>& radii)
{
    // Random initial positions in a circle
    float scale = std::sqrt(static_cast<float>(nNodes)) * 25.0f + 150.0f;
    pos.resize(2 * nNodes);
    labels.resize(nNodes);
    radii.resize(nNodes);

    for (int i = 0; i < nNodes; ++i) {
        float angle = static_cast<float>(i) / nNodes * 6.2831853f;
        float r = scale * (0.3f + 0.7f * static_cast<float>(std::rand()) / RAND_MAX);
        pos[2 * i]     = r * std::cos(angle);
        pos[2 * i + 1] = r * std::sin(angle);
        labels[i] = QString("N%1").arg(i);
        radii[i]  = 4.0f + static_cast<float>(std::rand() % 7);  // 4..10
    }

    // Generate random edges (simple Erdos-Renyi-like)
    edges.clear();
    float p = static_cast<float>(avgDegree) / static_cast<float>(nNodes);
    for (int i = 0; i < nNodes; ++i) {
        for (int j = i + 1; j < nNodes; ++j) {
            float r = static_cast<float>(std::rand()) / RAND_MAX;
            if (r < p) {
                edges.append(i);
                edges.append(j);
            }
        }
    }

    qDebug() << "Generated graph:" << nNodes << "nodes," << edges.size() / 2 << "edges";
}

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);

    ForceView view;
    view.setWindowTitle("ForceView C++ Test");
    view.resize(1000, 700);

    // Generate a 500-node random graph
    QVector<int>   edges;
    QVector<float> pos;
    QStringList    labels;
    QVector<float> radii;
    generateRandomGraph(500, 4, edges, pos, labels, radii);

    view.setGraph(500, edges, pos, labels, radii);

    // Connect signals for debug output
    QObject::connect(&view, &ForceView::nodeLeftClicked, [&](int idx) {
        qDebug() << "Left-clicked node:" << idx << labels[idx];
    });
    QObject::connect(&view, &ForceView::nodeHovered, [](int idx) {
        if (idx >= 0) qDebug() << "Hovered node:" << idx;
    });
    QObject::connect(&view, &ForceView::tickTimeUpdated, [](float ms) {
        // Uncomment for per-tick logging:
        // qDebug() << "Tick:" << ms << "ms";
    });
    QObject::connect(&view, &ForceView::fpsUpdated, [](float fps) {
        qDebug() << "FPS:" << fps;
    });

    view.show();
    return app.exec();
}
