#include "hmiWindow.h"

#include <QApplication>
#include <rclcpp/rclcpp.hpp>

int main(int argc, char *argv[])
{
    // Create Qt Application
    QApplication a(argc, argv);

    // Create and show the HMI window
    HMIWindow w;
    w.show();

    // Run the Qt application
    int result = a.exec();

    // Shutdown ROS2
    rclcpp::shutdown();

    return result;
}
