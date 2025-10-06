#include "ZoomableGraphicsView.h"
#include <cmath>
#include <QDebug>
ZoomableGraphicsView::ZoomableGraphicsView(QWidget* parent)
    : QGraphicsView(parent), zoomFactor(1.15), currentZoom(1.0), panning(false), robotItem(nullptr), robotDirectionItem(nullptr)
{
    setRenderHint(QPainter::Antialiasing);
    setDragMode(QGraphicsView::NoDrag); // manual panning
    if (!scene()) {
        setScene(new QGraphicsScene(this));
    }
    mapItem = scene()->addPixmap(mapPixmap);
    setTransformationAnchor(QGraphicsView::AnchorUnderMouse);
    setResizeAnchor(QGraphicsView::AnchorViewCenter);

}

void ZoomableGraphicsView::setZoom(double factor)
{
    if (factor <= 0) return;
    double scaleFactor = factor / currentZoom;
    scale(scaleFactor, scaleFactor);
    currentZoom = factor;
}

void ZoomableGraphicsView::wheelEvent(QWheelEvent* event)
{
    const double scaleFactor = (event->angleDelta().y() > 0) ? zoomFactor : 1.0 / zoomFactor;
    QPointF oldPos = mapToScene(event->position().toPoint());
    scale(scaleFactor, scaleFactor);
    currentZoom *= scaleFactor;
    QPointF newPos = mapToScene(event->position().toPoint());
    QPointF delta = newPos - oldPos;
    translate(delta.x(), delta.y());
}

void ZoomableGraphicsView::mousePressEvent(QMouseEvent* event)
{
    if (event->button() == Qt::LeftButton) {
        panning = true;
        lastPanPoint = event->pos();
        setCursor(Qt::ClosedHandCursor);
    }
    QGraphicsView::mousePressEvent(event);
}

void ZoomableGraphicsView::mouseMoveEvent(QMouseEvent* event)
{
    if (panning) {
        QPointF delta = mapToScene(event->pos()) - mapToScene(lastPanPoint);
        lastPanPoint = event->pos();
        translate(delta.x(), delta.y());
    }
    QGraphicsView::mouseMoveEvent(event);
}

void ZoomableGraphicsView::mouseReleaseEvent(QMouseEvent* event)
{
    if (event->button() == Qt::LeftButton) {
        panning = false;
        setCursor(Qt::ArrowCursor);
    }
    QGraphicsView::mouseReleaseEvent(event);
}

std::pair<float,float> ZoomableGraphicsView::ToMapCoordinates(const float x, const float y)
{
    if (resolution <= 0) {
        return std::pair<float,float>(-1, -1); // Invalid resolution
    }
    const float xMap = (x- mapOffsetX) / resolution;
    const float yMap = (y -mapOffsetY) / resolution;
    return std::pair<float,float>(xMap, mapHeight-1-yMap);
}

std::pair<float,float> ZoomableGraphicsView::FromMapCoordinates(const float x, const float y)
{
    if (resolution <= 0) {
        return std::pair<float,float>(-1, -1); // Invalid resolution
    }
    const float xWorld = x * resolution + mapOffsetX;
    const float yWorld = (mapHeight - 1 - y) * resolution + mapOffsetY;
    return std::pair<float,float>(xWorld, yWorld);
}
void ZoomableGraphicsView::drawMap(const nav_msgs::msg::OccupancyGrid::SharedPtr msg) {
    if (mapItem) {
        scene()->removeItem(mapItem);
        delete mapItem; // The ownership of item is passed on to the caller (i.e., QGraphicsScene will no longer delete item when destroyed).
        mapItem = nullptr;
    }
    const float upscale = 10;
    resolution = msg->info.resolution / upscale; // Make resolution 10x finer for display
    mapOffsetX = msg->info.origin.position.x;
    mapOffsetY = msg->info.origin.position.y;

    // Convert occupancy grid to QImage with 10x upscaling
    mapWidth = msg->info.width * upscale;
    mapHeight = msg->info.height * upscale;
    QImage mapImage(mapWidth, mapHeight, QImage::Format_RGB888);

    for (int y = 0; y < mapHeight; ++y) {
        for (int x = 0; x < mapWidth; ++x) {
            // Map upscaled pixel back to original grid cell
            int origX = x / upscale;
            int origY = y / upscale;
            int index = origY * msg->info.width + origX;
            int8_t value = msg->data[index];

            QRgb color;
            if (value == -1) {
                // Unknown space - gray
                color = qRgb(128, 128, 128);
            } else if (value == 0) {
                // Free space - white
                color = qRgb(255, 255, 255);
            } else {
                // Occupied space - black, scaled by probability
                int intensity = 255 - (value * 255 / 100);
                color = qRgb(intensity, intensity, intensity);
            }
            mapImage.setPixel(x, mapHeight - 1 - y, color); // Flip Y axis
        }
    }
    mapPixmap = QPixmap::fromImage(mapImage);
    mapItem = scene()->addPixmap(mapPixmap);
    
    // Fit the map in view after adding it
    fitInView(mapItem, Qt::KeepAspectRatio);
}

void ZoomableGraphicsView::drawPlan(nav_msgs::msg::Path::SharedPtr msg) {
    // Remove existing path items
    if (msg->header.frame_id != "map") {
        qWarning() << "Path frame_id is not 'map'. Current implementation assumes path is in 'map' frame.";
        return;
    }
    for (auto* pathItem : pathItems) {
        scene()->removeItem(pathItem);
        delete pathItem;
    }
    pathItems.clear();
    
    if (!msg || msg->poses.empty()) {
        return;
    }
    
    // Draw path as connected line segments
    for (size_t i = 0; i < msg->poses.size() - 1; ++i) {
        const auto& pose1 = msg->poses[i].pose;
        const auto& pose2 = msg->poses[i + 1].pose;
        
        // Convert world coordinates to pixel coordinates
        const auto [x1, y1] = ToMapCoordinates(pose1.position.x, pose1.position.y);
        const auto [x2, y2] = ToMapCoordinates(pose2.position.x, pose2.position.y);
        
        // Create line segment
        auto* lineItem = scene()->addLine(x1, y1, x2, y2, QPen(Qt::green, 3));
        pathItems.append(lineItem);
    }
    
    // Optional: Draw waypoint markers
    for (const auto& pose_stamped : msg->poses) {
        const auto& pose = pose_stamped.pose;
        const auto [x, y] = ToMapCoordinates(pose.position.x, pose.position.y);
        
        // Small circle for waypoint
        float waypointRadius = 0.1; // pixels
        auto* waypointItem = scene()->addEllipse(x - waypointRadius, y - waypointRadius,
                                               waypointRadius * 2, waypointRadius * 2,
                                               QPen(Qt::green, waypointRadius), QBrush(Qt::green));
        pathItems.append(waypointItem);
    }
}


void ZoomableGraphicsView::drawRobot(float x, float y, float theta) {
    // Remove existing robot items
    if (robotItem) {
        scene()->removeItem(robotItem);
        delete robotItem;
        robotItem = nullptr;
    }
    if (robotDirectionItem) {
        scene()->removeItem(robotDirectionItem);
        delete robotDirectionItem;
        robotDirectionItem = nullptr;
    }
    
    // Convert world coordinates to pixel coordinates
    // Assuming map origin is at (0,0) and resolution is meters per pixel

    const auto [pixelX,pixelY] = ToMapCoordinates(x, y);

    // Robot body - blue circle (0.5m diameter)
    float robotRadius = 0.25f / resolution; // 0.25m radius in pixels
    robotItem = scene()->addEllipse(pixelX - robotRadius, pixelY - robotRadius,
                                   robotRadius * 2, robotRadius * 2,
                                   QPen(Qt::blue, 1), QBrush(Qt::blue));
    
    // Robot direction indicator - red line pointing in theta direction
    float arrowLength = robotRadius * 2.0f;
    float endX = pixelX + arrowLength * cos(theta);
    float endY = pixelY - arrowLength * sin(theta); // Flip Y for graphics
    
    robotDirectionItem = scene()->addLine(pixelX, pixelY, endX, endY,
                                         QPen(Qt::red, 1));
}

void ZoomableGraphicsView::contextMenuEvent(QContextMenuEvent* event)
{
    QMenu contextMenu(this);
    QAction* setGoalAction = contextMenu.addAction("Set Goal Here");
    
    QAction* selectedAction = contextMenu.exec(event->globalPos());
    
    if (selectedAction == setGoalAction) {
        // Convert screen coordinates to scene coordinates
        QPointF scenePos = mapToScene(event->pos());
        
        // Convert scene coordinates to world coordinates
        const auto [worldX, worldY] = FromMapCoordinates(scenePos.x(), scenePos.y());
        
        // Emit signal with world coordinates
        emit goalSet(worldX, worldY);
    }
}