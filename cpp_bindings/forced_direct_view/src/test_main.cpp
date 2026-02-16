#include <QApplication>
#include <QVector>
#include <QStringList>
#include <QDebug>
#include <cstdlib>
#include <cmath>


#include "ForceViewOpenGL.h"

/**
 * Standalone test: creates a ForceView (or ForceViewOpenGL with --opengl) with a random graph.
 */

static void generateRandomGraph(int nNodes, int avgDegree,
                                QVector<int>& edges,
                                QVector<float>& pos,
                                QStringList& id,
                                QStringList& labels,
                                QVector<float>& radii)
{
    // Random initial positions in a circle
    float scale = std::sqrt(static_cast<float>(nNodes)) * 25.0f + 150.0f;
    pos.resize(2 * nNodes);
    id.resize(nNodes);
    labels.resize(nNodes);
    radii.resize(nNodes);

    for (int i = 0; i < nNodes; ++i) {
        float angle = static_cast<float>(i) / nNodes * 6.2831853f;
        float r = scale * (0.3f + 0.7f * static_cast<float>(std::rand()) / RAND_MAX);
        pos[2 * i]     = r * std::cos(angle);
        pos[2 * i + 1] = r * std::sin(angle);
        id[i] = QString("ID%1").arg(i);
        labels[i] = QString("N%1").arg(i);
        radii[i]  = 4.0f + static_cast<float>(std::rand() % 7);  // 4..10
    }

    // Generate random edges (Poisson-distributed connections per node, matching graph.py)
    edges.clear();
    for (int i = 0; i < nNodes; ++i) {
        // -log(1 - rand) * mean, rounded (exponential approx to Poisson)
        float u = static_cast<float>(std::rand()) / (RAND_MAX + 1.0f);
        int numConnections = static_cast<int>(std::round(-std::log(1.0f - u) * avgDegree));
        for (int k = 0; k < numConnections; ++k) {
            int target = std::rand() % nNodes;
            if (target != i) {
                edges.append(i);
                edges.append(target);
            }
        }
    }

    qDebug() << "Generated graph:" << nNodes << "nodes," << edges.size() / 2 << "edges";
}

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);

    //bool useOpenGL = (argc > 1 && QString::fromUtf8(argv[1]) == QStringLiteral("--opengl"));
    bool useOpenGL = true;
    // Generate a nodenum-node random graph
    QVector<int>   edges;
    QVector<float> pos;
    QStringList    ids;
    QStringList    labels;
    QVector<float> radii;
    int nodenum = 1900;
    generateRandomGraph(nodenum, 1, edges, pos, ids, labels, radii);

    QVector<QColor> nodeColors(nodenum);
    for (int i = 0; i < nodenum; ++i)
        nodeColors[i] = QColor(std::rand() % 256, std::rand() % 256, std::rand() % 256);
        //nodeColors[i] = QColor("#5C5C5C");


    ForceViewOpenGL view;
    view.setWindowTitle("ForceView OpenGL Test");
    view.resize(1000, 700);
    view.setGraph(nodenum, edges, pos, ids, labels, radii, nodeColors);
    QObject::connect(&view, &ForceViewOpenGL::nodeLeftClicked, [](const QString& nodeId) { qDebug() << "Left-clicked node: id[" << nodeId << "]"; });
    QObject::connect(&view, &ForceViewOpenGL::nodeHovered, [](const QString& nodeId) { if (!nodeId.isEmpty()) qDebug() << "Hovered node: id:" << nodeId; });
    QObject::connect(&view, &ForceViewOpenGL::fpsUpdated, [](float fps) { qDebug() << "FPS:" << fps; });
    view.show();
    return app.exec();

    
    
    return app.exec();
}
