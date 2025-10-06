#pragma once
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <nav_msgs/msg/path.hpp>
#include <QGraphicsView>
#include <QGraphicsPixmapItem>
#include <QGraphicsEllipseItem>
#include <QGraphicsLineItem>
#include <QGraphicsScene>
#include <QList>
#include <QWheelEvent>
#include <QMouseEvent>
#include <QPainter>
#include <QContextMenuEvent>
#include <QMenu>
#include <QAction>

class ZoomableGraphicsView : public QGraphicsView
{
    Q_OBJECT

public:
    // Standard Qt constructor
    explicit ZoomableGraphicsView(QWidget* parent = nullptr);


    // Programmatically set zoom (absolute)
    void setZoom(double factor);
    double getZoom() const { return currentZoom; }

    void drawMap(const nav_msgs::msg::OccupancyGrid::SharedPtr msg);

    void drawRobot(float x, float y, float theta);
    void drawPlan(nav_msgs::msg::Path::SharedPtr msg);

    std::pair<float,float> ToMapCoordinates(const float x, const float y);
    std::pair<float,float> FromMapCoordinates(const float x, const float y);
signals:
    void goalSet(float x, float y);

protected:
    void wheelEvent(QWheelEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;
    void mouseMoveEvent(QMouseEvent* event) override;
    void mouseReleaseEvent(QMouseEvent* event) override;
    void contextMenuEvent(QContextMenuEvent* event) override;

private:

    double zoomFactor;
    double currentZoom;
    bool panning;
    QPoint lastPanPoint;
    QPixmap mapPixmap;
    QGraphicsPixmapItem *mapItem;
    QGraphicsEllipseItem *robotItem;
    QGraphicsLineItem *robotDirectionItem;
    QList<QGraphicsItem*> pathItems;
    double resolution; // meters per pixel
    int mapWidth;  // in pixels
    int mapHeight; // in pixels
    float mapOffsetX; // in meters
    float mapOffsetY; // in meters

};
