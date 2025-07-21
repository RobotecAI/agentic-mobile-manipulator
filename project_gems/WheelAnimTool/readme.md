# WheelAnimTool Gem

## Overview

The WheelAnimTool is an O3DE gem that provides realistic wheel animation for robotic systems. This gem allows you to animate wheels based on the physics body's velocity, supporting both mecanum and differential drive configurations. The component calculates wheel speeds using kinematic models and provides visual feedback through debug drawing.

## Features

- **Multiple Drive Types**: Supports mecanum and differential drive systems
- **Physics Integration**: Automatically calculates wheel speeds based on rigid body velocity
- **Visual Debugging**: Real-time visualization of wheel speeds and robot motion
- **Configurable Parameters**: Adjustable wheel radius, roller directions, and animation types
- **Jacobian-based Kinematics**: Uses mathematical models for accurate wheel speed calculations

## Prerequisites

It requires O3DE Engine and the Eigen library for matrix operations.
```shell
sudo apt install libeigen3-dev
```

## Installation

1. Add the WheelAnimTool gem to your O3DE project by including it in your `project.json` file
2. Build your project to compile the gem
3. The gem will be available in the Entity Component Menu under the "Robotics" category

## Usage

### Basic Setup

1. **Create a Robot Entity**: Set up an entity with a rigid body component for your robot
2. **Add Components to move robot in kinematic way or use RigidBody Twist controller from ROS 2 Gem**
2. **Add Wheel Animation Component**: Add the `WheelAnimComponent` to your robot entity
3. **Configure Wheel Entities**: Create child entities for each wheel and reference them in the component
4. **Set Animation Type**: Choose between Mecanum or Differential drive types

### Component Configuration

The `WheelAnimComponent` provides the following configurable properties:

#### Wheel Entities
- **Description**: List of wheel entities to animate
- **Type**: Array of Entity IDs
- **Usage**: Reference each wheel entity that should be animated, order is not important.

#### Roller Directions
- **Description**: 2D vectors representing roller directions for each wheel
- **Type**: Array of Vector2
- **Usage**: For mecanum wheels, specify the direction of the rollers (e.g., [1,1], [1,-1], [-1,1], [-1,-1])
- **Note**: Must match the number of wheel entities and order must correspond to the wheel entities

#### Wheel Radius
- **Description**: Physical radius of the wheels
- **Type**: Float
- **Usage**: Used for converting angular velocity to linear motion

#### Animation Type
- **Description**: Type of drive system to simulate
- **Type**: Enum (Mecanum, Differential)
- **Options**:
  - `Mecanum`: For omnidirectional mecanum wheel systems
  - `Differential`: For traditional differential drive systems

#### Debug Draw
- **Description**: Enable/disable visual debugging
- **Type**: Boolean
- **Default**: true
- **Features**: Shows velocity vectors, wheel speeds, and robot state

### Animation Types

#### Mecanum Drive
Mecanum wheels allow omnidirectional movement through angled rollers. The component calculates wheel speeds using:
- Roller direction vectors for each wheel
- Robot's linear velocity (X, Y)
- Robot's angular velocity (Z)
- Wheel position relative to robot center

#### Differential Drive
Traditional two-wheel drive system where:
- Forward motion requires both wheels to rotate in the same direction
- Turning is achieved by different wheel speeds
- Only forward/backward and rotational motion are supported

## Code Structure

### Main Components

#### WheelAnimComponent (`WheelAnimComponent.h/.cpp`)
- **Location**: `Code/Source/Clients/WheelAnimComponent.h:12`
- **Purpose**: Main component class handling wheel animation logic
- **Key Methods**:
  - `OnTick()`: Updates wheel rotations based on physics body velocity
  - `CreateMecanumJacobianRow()`: Calculates kinematic mapping for mecanum wheels
  - `CreateDifferentialJacobianRow()`: Calculates kinematic mapping for differential drive

#### Module Interface (`WheelAnimToolModuleInterface.h/.cpp`)
- **Location**: `Code/Source/WheelAnimToolModuleInterface.h:16`
- **Purpose**: Gem module interface for O3DE integration

### Key Algorithms

#### Jacobian Matrix Calculation
The component uses a Jacobian matrix to transform 3D robot velocity to 1D wheel speeds:

```cpp
// For mecanum wheels
jacobianRow << rollerDirection.x(), rollerDirection.y(), (wheelPosition.x() + abs(2.0*wheelPosition.y()));

// For differential drive
jacobianRow << 1.0, 0.0, wheelPosition.y();
```

#### Wheel Speed Calculation
```cpp
Eigen::VectorXd wheelSpeeds = m_jacobian * robotState;
```

Where `robotState` contains `[linear_x, linear_y, angular_z]` velocities.

## Debug Visualization

When debug drawing is enabled, the component displays:
- **Blue Sphere**: Robot center position
- **Red Vector**: Linear velocity
- **Green Vector**: Angular velocity
- **Blue-Violet Vectors**: Individual wheel speeds
- **Yellow Spheres**: Wheel positions

## Dependencies

- **O3DE Framework**: Core engine functionality
- **Eigen Library**: Mathematical operations and matrix calculations
- **AzFramework Physics**: Rigid body integration
- **Atom Renderer**: Debug visualization

## Technical Requirements

- O3DE Engine compatible version
- Eigen mathematical library
- Entity must have a rigid body component for physics integration
- Wheel entities must be properly configured as child entities

## Example Configuration

For a typical mecanum drive robot:
```
Wheel Entities: [wheel_fl, wheel_fr, wheel_bl, wheel_br]
Roller Directions: [(1,1), (1,-1), (-1,1), (-1,-1)]
Wheel Radius: 0.1
Animation Type: Mecanum
Debug Draw: true
```

## License

This gem is licensed under Apache-2.0. See the LICENSE file for details.

## Contributing

This gem was developed by Robotec.AI for robotic simulation in O3DE. For contributions and support, please refer to the project repository.