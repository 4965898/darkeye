#include "NodeLayer.h"

#include <QPainter>
#include <QGraphicsScene>
#include <QGraphicsView>
#include <QGraphicsSceneMouseEvent>
#include <QGraphicsSceneHoverEvent>
#include <QStyleOptionGraphicsItem>
#include <QTransform>
#include <QLineF>
#include <QCursor>
#include <Qt>

#include <cmath>
#include <algorithm>
#include <chrono>
#include <limits>

// Utility: current time in seconds (high-res)
static double nowSec()
{
    using clock = std::chrono::high_resolution_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

// =====================================================================
// Construction / Reset
// =====================================================================

NodeLayer::NodeLayer(PhysicsState* state,
                     const QVector<float>& showRadii,
                     const QStringList& labels,
                     const std::vector<std::vector<int>>& neighbors,
                     QGraphicsItem* parent)
    : QGraphicsObject(parent)
    , m_state(state)
    , m_showRadiiBase(showRadii)
    , m_labels(labels)
    , m_neighbors(neighbors)
    , m_font("Microsoft YaHei", 5)
    , m_fontMetrics(m_font)
{
    m_fontHeight = m_fontMetrics.height();

    int N = m_state->nNodes;
    m_neighborMask.assign(N, 0);
    m_lastNeighborMask.clear();

    setZValue(1);
    setCursor(Qt::ArrowCursor);
    setAcceptedMouseButtons(Qt::LeftButton | Qt::RightButton);
    setAcceptHoverEvents(true);
    setFlag(QGraphicsItem::ItemIsSelectable, false);
    setFlag(QGraphicsItem::ItemIsMovable, false);

    updateFactor();
    initStaticTextCache();

    m_lastFpsTime = nowSec();
}

void NodeLayer::reset(PhysicsState* state,
                      const QVector<float>& showRadii,
                      const QStringList& labels,
                      const std::vector<std::vector<int>>& neighbors)
{
    m_state         = state;
    m_showRadiiBase = showRadii;
    m_labels        = labels;
    m_neighbors     = neighbors;

    int N = m_state->nNodes;
    m_neighborMask.assign(N, 0);
    m_lastNeighborMask.clear();

    m_hoverIndex     = -1;
    m_lastHoverIndex = -1;
    m_selectedIndex  = -1;
    m_dragging       = false;
    m_hoverGlobal    = 0.0f;

    m_lastDimEdges.clear();
    m_lastHighlightEdges.clear();

    m_staticTextCache.clear();

    m_radiusFactor = 1.0f;
    updateFactor();
    initStaticTextCache();

    m_boundingDirty = true;
}

// =====================================================================
// Factor update
// =====================================================================

void NodeLayer::updateFactor()
{
    m_sideWidth = m_sideWidthBase * m_sideWidthFactor;

    int N = m_showRadiiBase.size();
    m_showRadii.resize(N);
    for (int i = 0; i < N; ++i)
        m_showRadii[i] = m_showRadiiBase[i] * m_radiusFactor;

    m_textThresholdOff  = m_textThresholdBase * m_textThresholdFactor;
    m_textThresholdShow = m_textThresholdOff * 1.5f;

    m_boundingDirty = true;
}

// =====================================================================
// Static text cache
// =====================================================================

void NodeLayer::initStaticTextCache()
{
    m_staticTextCache.clear();
    for (int i = 0; i < m_labels.size(); ++i) {
        std::string key = m_labels[i].toStdString();
        if (m_staticTextCache.count(key)) continue;
        QStaticText st(m_labels[i]);
        st.prepare(QTransform(), m_font);
        float w = static_cast<float>(st.size().width());
        m_staticTextCache[key] = {st, w};
    }
}

// =====================================================================
// Bounding rect
// =====================================================================

QRectF NodeLayer::boundingRect() const
{
    if (!m_boundingDirty)
        return m_cachedBounding;

    int N = m_state->nNodes;
    if (N == 0) {
        m_cachedBounding = QRectF();
        m_boundingDirty = false;
        return m_cachedBounding;
    }

    const float* pos = m_state->pos.data();
    float minX = pos[0], maxX = pos[0];
    float minY = pos[1], maxY = pos[1];
    for (int i = 1; i < N; ++i) {
        float x = pos[2 * i], y = pos[2 * i + 1];
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
    }

    // Same padding as Python: *3 and +-100
    minX = minX * 3.0f - 100.0f;
    maxX = maxX * 3.0f + 100.0f;
    minY = minY * 3.0f - 100.0f;
    maxY = maxY * 3.0f + 100.0f;

    m_cachedBounding = QRectF(minX, minY, maxX - minX, maxY - minY);
    m_boundingDirty = false;
    return m_cachedBounding;
}

// =====================================================================
// Visibility culling
// =====================================================================

void NodeLayer::updateVisibleMask()
{
    const int N = m_state->nNodes;
    if (N == 0) {
        m_visibleIndices.clear();
        m_visibleEdges.clear();
        return;
    }

    // Find visible rect in item coordinates
    QRectF visRect;
    QGraphicsScene* sc = scene();
    QList<QGraphicsView*> views = sc ? sc->views() : QList<QGraphicsView*>();
    if (!views.isEmpty()) {
        QGraphicsView* v = views.first();
        QRectF sceneRect = v->mapToScene(v->viewport()->rect()).boundingRect();
        visRect = mapRectFromScene(sceneRect);
    } else {
        visRect = boundingRect();
    }
    visRect.adjust(-50, -50, 50, 50);

    const float* pos = m_state->pos.data();

    // Node culling
    m_visibleIndices.clear();
    m_visibleIndices.reserve(N);
    std::vector<uint8_t> nodeMask(N, 0);

    for (int i = 0; i < N; ++i) {
        float x = pos[2 * i];
        float y = pos[2 * i + 1];
        float r = (i < m_showRadii.size()) ? m_showRadii[i] : 5.0f;
        if (x + r >= visRect.left() && x - r <= visRect.right() &&
            y + r >= visRect.top()  && y - r <= visRect.bottom())
        {
            m_visibleIndices.push_back(i);
            nodeMask[i] = 1;
        }
    }

    // Edge culling: keep edge if either endpoint is visible
    const int E = m_state->edgeCount();
    const int* edges = m_state->edges.data();
    m_visibleEdges.clear();
    m_visibleEdges.reserve(E * 2);
    for (int e = 0; e < E; ++e) {
        int s = edges[2 * e];
        int d = edges[2 * e + 1];
        if (nodeMask[s] || nodeMask[d]) {
            m_visibleEdges.push_back(s);
            m_visibleEdges.push_back(d);
        }
    }

    m_boundingDirty = true;
}

// =====================================================================
// Hover animation
// =====================================================================

void NodeLayer::advanceHover()
{
    float target = (m_hoverIndex != -1) ? 1.0f : 0.0f;
    if (target > m_hoverGlobal)
        m_hoverGlobal = std::min(1.0f, m_hoverGlobal + m_hoverStep);
    else if (target < m_hoverGlobal)
        m_hoverGlobal = std::max(0.0f, m_hoverGlobal - m_hoverStep);
}

// =====================================================================
// Color mix
// =====================================================================

QColor NodeLayer::mixColor(const QColor& c1, const QColor& c2, float t)
{
    if (t <= 0.0f) return c1;
    if (t >= 1.0f) return c2;
    int r = c1.red()   + static_cast<int>((c2.red()   - c1.red())   * t);
    int g = c1.green() + static_cast<int>((c2.green() - c1.green()) * t);
    int b = c1.blue()  + static_cast<int>((c2.blue()  - c1.blue())  * t);
    int a = c1.alpha() + static_cast<int>((c2.alpha() - c1.alpha()) * t);
    return QColor(r, g, b, a);
}

// =====================================================================
// paint()
// =====================================================================

void NodeLayer::paint(QPainter* painter,
                      const QStyleOptionGraphicsItem* /*option*/,
                      QWidget* /*widget*/)
{
    double start = nowSec();

    drawEdges(painter);
    drawNodesAndText(painter);

    float elapsed = static_cast<float>((nowSec() - start) * 1000.0);
    emit paintTimeReady(elapsed);
    updateFps();
}

// =====================================================================
// drawEdges
// =====================================================================

void NodeLayer::drawEdges(QPainter* painter)
{
    const int VE = static_cast<int>(m_visibleEdges.size()) / 2;
    if (VE == 0) return;

    const float* pos   = m_state->pos.data();
    const int*   vedge = m_visibleEdges.data();
    const int    hover = m_hoverIndex;
    const float  t     = m_hoverGlobal;

    if (hover == -1) {
        // ---- No hover node ----
        if (t <= 0.0f) {
            // Default: all edges same color
            painter->setPen(QPen(m_edgeColor, m_sideWidth));
            QVector<QLineF> lines;
            lines.reserve(VE);
            for (int e = 0; e < VE; ++e) {
                int s = vedge[2 * e], d = vedge[2 * e + 1];
                lines.append(QLineF(pos[2*s], pos[2*s+1], pos[2*d], pos[2*d+1]));
            }
            painter->drawLines(lines);
        } else {
            // Fading out from previous hover: draw dim + highlight separately
            // Dim edges
            if (!m_lastDimEdges.empty()) {
                QColor color = mixColor(m_edgeColor, m_edgeDimColor, t);
                painter->setPen(QPen(color, m_sideWidth));
                int nDim = static_cast<int>(m_lastDimEdges.size()) / 2;
                QVector<QLineF> lines;
                lines.reserve(nDim);
                for (int e = 0; e < nDim; ++e) {
                    int s = m_lastDimEdges[2*e], d = m_lastDimEdges[2*e+1];
                    lines.append(QLineF(pos[2*s], pos[2*s+1], pos[2*d], pos[2*d+1]));
                }
                painter->drawLines(lines);
            }
            // Highlight edges
            if (!m_lastHighlightEdges.empty()) {
                QColor color = mixColor(m_edgeColor, m_hoverColor, t);
                painter->setPen(QPen(color, m_sideWidth));
                int nHi = static_cast<int>(m_lastHighlightEdges.size()) / 2;
                QVector<QLineF> lines;
                lines.reserve(nHi);
                for (int e = 0; e < nHi; ++e) {
                    int s = m_lastHighlightEdges[2*e], d = m_lastHighlightEdges[2*e+1];
                    lines.append(QLineF(pos[2*s], pos[2*s+1], pos[2*d], pos[2*d+1]));
                }
                painter->drawLines(lines);
            }
        }
    } else {
        // ---- Hover is active: split into highlight / dim ----
        m_lastDimEdges.clear();
        m_lastHighlightEdges.clear();

        for (int e = 0; e < VE; ++e) {
            int s = vedge[2 * e], d = vedge[2 * e + 1];
            if (s == hover || d == hover) {
                m_lastHighlightEdges.push_back(s);
                m_lastHighlightEdges.push_back(d);
            } else {
                m_lastDimEdges.push_back(s);
                m_lastDimEdges.push_back(d);
            }
        }

        // Draw dim edges
        if (!m_lastDimEdges.empty()) {
            QColor color = mixColor(m_edgeColor, m_edgeDimColor, t);
            painter->setPen(QPen(color, m_sideWidth));
            int nDim = static_cast<int>(m_lastDimEdges.size()) / 2;
            QVector<QLineF> lines;
            lines.reserve(nDim);
            for (int e = 0; e < nDim; ++e) {
                int s = m_lastDimEdges[2*e], d = m_lastDimEdges[2*e+1];
                lines.append(QLineF(pos[2*s], pos[2*s+1], pos[2*d], pos[2*d+1]));
            }
            painter->drawLines(lines);
        }

        // Draw highlight edges
        if (!m_lastHighlightEdges.empty()) {
            QColor color = mixColor(m_edgeColor, m_hoverColor, t);
            painter->setPen(QPen(color, m_sideWidth));
            int nHi = static_cast<int>(m_lastHighlightEdges.size()) / 2;
            QVector<QLineF> lines;
            lines.reserve(nHi);
            for (int e = 0; e < nHi; ++e) {
                int s = m_lastHighlightEdges[2*e], d = m_lastHighlightEdges[2*e+1];
                lines.append(QLineF(pos[2*s], pos[2*s+1], pos[2*d], pos[2*d+1]));
            }
            painter->drawLines(lines);
        }
    }
}

// =====================================================================
// drawNodesAndText
// =====================================================================

void NodeLayer::drawNodesAndText(QPainter* painter)
{
    const float* pos = m_state->pos.data();
    const float  t   = m_hoverGlobal;
    const int    N   = m_state->nNodes;

    // Pre-compute groups of indices
    std::vector<int> groupBase, groupDim, groupHover, groupHighlight;

    // Determine scene scale (zoom level)
    float scale = 1.0f;
    QGraphicsScene* sc = scene();
    QList<QGraphicsView*> views = sc ? sc->views() : QList<QGraphicsView*>();
    if (!views.isEmpty())
        scale = static_cast<float>(views.first()->transform().m11());

    // ---- Group classification ----
    const int vis = static_cast<int>(m_visibleIndices.size());

    if (m_hoverIndex != -1) {
        // Active hover
        for (int vi = 0; vi < vis; ++vi) {
            int idx = m_visibleIndices[vi];
            if (idx == m_hoverIndex) {
                groupHover.push_back(idx);
            } else if (idx == m_centerNodeIndex && idx != m_hoverIndex) {
                groupHighlight.push_back(idx);
            } else if (idx < (int)m_neighborMask.size() && m_neighborMask[idx]
                        && idx != m_centerNodeIndex) {
                groupBase.push_back(idx);
            } else {
                groupDim.push_back(idx);
            }
        }
    } else if (t <= 0.0f) {
        // No hover, no transition
        for (int vi = 0; vi < vis; ++vi) {
            int idx = m_visibleIndices[vi];
            if (idx == m_centerNodeIndex)
                groupHighlight.push_back(idx);
            else
                groupBase.push_back(idx);
        }
    } else {
        // Fading out from hover
        for (int vi = 0; vi < vis; ++vi) {
            int idx = m_visibleIndices[vi];
            if (idx == m_lastHoverIndex) {
                groupHover.push_back(idx);
            } else if (idx == m_centerNodeIndex) {
                groupHighlight.push_back(idx);
            } else if (idx < (int)m_lastNeighborMask.size() && m_lastNeighborMask[idx]
                        && idx != m_centerNodeIndex) {
                groupBase.push_back(idx);
            } else {
                groupDim.push_back(idx);
            }
        }
    }

    // ---- Pre-compute brushes ----
    QBrush brushBase(m_baseColor);
    QBrush brushDim   = brushBase;
    QBrush brushHover = brushBase;
    QBrush brushHighlight(m_highlightColor);

    if (m_hoverIndex != -1 || t > 0.0f) {
        brushHover = QBrush(mixColor(m_baseColor, m_hoverColor, t));
        brushDim   = QBrush(mixColor(m_baseColor, m_dimColor,   t));
    }

    painter->setPen(Qt::NoPen);

    // Helper lambda: draw circle for node i
    auto drawNode = [&](int i, const QBrush& brush, float rScale) {
        float x = pos[2 * i], y = pos[2 * i + 1];
        float r = (i < m_showRadii.size()) ? m_showRadii[i] * rScale : 5.0f;
        painter->setBrush(brush);
        painter->drawEllipse(QPointF(x, y), r, r);
    };

    // 1. Base (neighbors or normal)
    for (int i : groupBase)      drawNode(i, brushBase, 1.0f);
    // 2. Dim
    for (int i : groupDim)       drawNode(i, brushDim,  1.0f);
    // 3. Highlight (center node)
    for (int i : groupHighlight) drawNode(i, brushHighlight, 1.2f);
    // 4. Hover
    for (int i : groupHover)     drawNode(i, brushHover, 1.1f);

    // ===================== Text (LOD) =====================
    if (scale > m_textThresholdOff) {
        bool prevTextAA = painter->testRenderHint(QPainter::TextAntialiasing);
        float factor = 1.0f;
        if (scale < m_textThresholdShow) {
            painter->setRenderHint(QPainter::TextAntialiasing, false);
            factor = (scale - m_textThresholdOff)
                   / (m_textThresholdShow - m_textThresholdOff);
        }
        int baseAlpha = static_cast<int>(255.0f * factor);

        painter->setFont(m_font);
        QColor colorText("#5C5C5C");

        // Lambda: draw label for node i
        auto drawLabel = [&](int i, int alpha, float rScale) {
            if (i < 0 || i >= m_labels.size()) return;
            std::string key = m_labels[i].toStdString();
            auto it = m_staticTextCache.find(key);
            if (it == m_staticTextCache.end()) return;
            const auto& [st, w] = it->second;
            float x = pos[2 * i], y = pos[2 * i + 1];
            float r = (i < m_showRadii.size()) ? m_showRadii[i] * rScale : 5.0f;
            colorText.setAlpha(alpha);
            painter->setPen(QPen(colorText));
            painter->drawStaticText(QPointF(x - w / 2.0f, y + r), st);
        };

        // Base group
        for (int i : groupBase)      drawLabel(i, baseAlpha, 1.0f);

        // Hover group (when hoverIndex == -1, these are fading from last hover)
        if (m_hoverIndex == -1) {
            for (int i : groupHover) drawLabel(i, baseAlpha, 1.0f);
        }

        // Highlight group
        for (int i : groupHighlight) drawLabel(i, baseAlpha, 1.2f);

        // Dim group (faded alpha)
        float fade = 1.0f - 0.7f * t;
        int alphaDim = static_cast<int>(baseAlpha * fade);
        for (int i : groupDim) drawLabel(i, alphaDim, 1.0f);

        painter->setRenderHint(QPainter::TextAntialiasing, prevTextAA);
    }

    // ===================== Hovered node label (override LOD) =====================
    if (m_hoverIndex != -1 && m_hoverIndex < m_labels.size()) {
        int i = m_hoverIndex;
        float x = pos[2 * i], y = pos[2 * i + 1];
        float r = (i < m_showRadii.size()) ? m_showRadii[i] : 5.0f;
        QString text = m_labels[i];
        float ht = m_hoverGlobal;

        QFont font(m_font);
        float baseSize = m_font.pointSizeF();
        if (baseSize <= 0) baseSize = static_cast<float>(m_font.pointSize());

        float targetSize = baseSize * (1.0f + ht * 2.0f);
        float sizeFactor;
        if (scale > 0.0f && scale <= 1.0f)
            sizeFactor = 1.0f / scale;
        else
            sizeFactor = 1.0f / (scale * 2.0f) + 0.5f;

        font.setPointSizeF(targetSize * sizeFactor);

        QFontMetrics fm(font);
        int w = fm.horizontalAdvance(text);
        QRect rect = fm.boundingRect(text);
        QColor color("#5C5C5C");
        painter->setPen(QPen(color));
        painter->setFont(font);
        float offsetY = (m_fontHeight * (0.2f * ht + 1.0f)) / scale;
        float yBase = y + r - rect.top() + offsetY;
        painter->drawText(QPointF(x - w / 2.0f, yBase), text);
    }
}

// =====================================================================
// Mouse interaction
// =====================================================================

void NodeLayer::mousePressEvent(QGraphicsSceneMouseEvent* event)
{
    const int N = m_state->nNodes;
    if (N == 0) {
        QGraphicsObject::mousePressEvent(event);
        return;
    }

    float cx = static_cast<float>(event->pos().x());
    float cy = static_cast<float>(event->pos().y());
    const float* pos = m_state->pos.data();

    if (m_visibleIndices.empty()) {
        m_selectedIndex = -1;
        setFlag(QGraphicsItem::ItemIsSelectable, false);
        QGraphicsObject::mousePressEvent(event);
        return;
    }

    // Find closest visible node
    int bestLocal = -1;
    float bestDist2 = std::numeric_limits<float>::max();
    for (int vi = 0; vi < (int)m_visibleIndices.size(); ++vi) {
        int idx = m_visibleIndices[vi];
        float dx = pos[2 * idx] - cx;
        float dy = pos[2 * idx + 1] - cy;
        float d2 = dx * dx + dy * dy;
        if (d2 < bestDist2) { bestDist2 = d2; bestLocal = idx; }
    }

    if (bestLocal >= 0) {
        float r = (bestLocal < m_showRadii.size()) ? m_showRadii[bestLocal] : 5.0f;
        if (bestDist2 < r * r) {
            m_selectedIndex = bestLocal;
            m_dragOffsetX = pos[2 * bestLocal] - cx;
            m_dragOffsetY = pos[2 * bestLocal + 1] - cy;
            m_hoverIndex = bestLocal;
            update();
            emit nodePressed(bestLocal);
            setFlag(QGraphicsItem::ItemIsSelectable, true);
            event->accept();

            QGraphicsObject::mousePressEvent(event);
            return;
        }
    }

    m_selectedIndex = -1;
    setFlag(QGraphicsItem::ItemIsSelectable, false);
    event->ignore(); // Let view handle pan
}

void NodeLayer::mouseMoveEvent(QGraphicsSceneMouseEvent* event)
{
    if (m_selectedIndex >= 0) {
        float nx = static_cast<float>(event->pos().x()) + m_dragOffsetX;
        float ny = static_cast<float>(event->pos().y()) + m_dragOffsetY;
        m_state->px(m_selectedIndex) = nx;
        m_state->py(m_selectedIndex) = ny;
        emit nodeDragged(m_selectedIndex);
        m_dragging = true;
        setCursor(Qt::ClosedHandCursor);
        update();
    }
}

void NodeLayer::mouseReleaseEvent(QGraphicsSceneMouseEvent* event)
{
    if (!m_dragging) {
        if (m_hoverIndex != -1) {
            if (event->button() == Qt::LeftButton)
                emit nodeLeftClicked(m_hoverIndex);
            if (event->button() == Qt::RightButton)
                emit nodeRightClicked(m_hoverIndex);
        }
    }

    m_dragging = false;
    setFlag(QGraphicsItem::ItemIsSelectable, false);
    int idx = m_selectedIndex;
    if (idx >= 0)
        emit nodeReleased(idx);
    m_selectedIndex = -1;
    setCursor(Qt::ArrowCursor);

    QGraphicsObject::mouseReleaseEvent(event);
}

void NodeLayer::hoverMoveEvent(QGraphicsSceneHoverEvent* event)
{
    const int N = m_state->nNodes;
    if (N == 0) {
        QGraphicsObject::hoverMoveEvent(event);
        return;
    }

    float px = static_cast<float>(event->pos().x());
    float py = static_cast<float>(event->pos().y());
    const float* pos = m_state->pos.data();

    if (m_visibleIndices.empty()) {
        QGraphicsObject::hoverMoveEvent(event);
        return;
    }

    int bestIdx = -1;
    float bestDist2 = std::numeric_limits<float>::max();
    for (int idx : m_visibleIndices) {
        float dx = pos[2 * idx] - px;
        float dy = pos[2 * idx + 1] - py;
        float d2 = dx * dx + dy * dy;
        if (d2 < bestDist2) { bestDist2 = d2; bestIdx = idx; }
    }

    if (bestIdx >= 0) {
        float r = (bestIdx < m_showRadii.size()) ? m_showRadii[bestIdx] : 5.0f;
        if (bestDist2 < r * r) {
            if (bestIdx != m_hoverIndex) {
                m_hoverIndex = bestIdx;
                m_lastHoverIndex = bestIdx;

                // Update neighbor mask
                m_neighborMask.assign(N, 0);
                if (bestIdx < (int)m_neighbors.size()) {
                    for (int nb : m_neighbors[bestIdx])
                        if (nb >= 0 && nb < N) m_neighborMask[nb] = 1;
                }
                m_neighborMask[bestIdx] = 0; // self not a neighbor
                m_lastNeighborMask = m_neighborMask;

                emit nodeHovered(bestIdx);
            }
            update();
        } else {
            if (m_hoverIndex != -1) {
                m_lastHoverIndex = m_hoverIndex;
                m_hoverIndex = -1;
                emit nodeHovered(-1);
                update();
            }
        }
    }

    QGraphicsObject::hoverMoveEvent(event);
}

// =====================================================================
// FPS tracking
// =====================================================================

void NodeLayer::updateFps()
{
    ++m_frameCount;
    double now = nowSec();
    if (now - m_lastFpsTime >= 1.0) {
        m_currentFps = static_cast<float>(m_frameCount / (now - m_lastFpsTime));
        m_frameCount = 0;
        m_lastFpsTime = now;
        emit fpsReady(m_currentFps);
    }
}
