# Simulation Overview

This project uses [Open 3D Engine (O3DE)](https://github.com/o3de/o3de) to build a simulation environment featuring a mobile manipulator robot and a warehouse setting, integrated with ROS 2. O3DE provides real-time, high-fidelity graphics and physics, making it a flexible and extensible engine for robotics simulation.
Learn more at the [O3DE website](https://www.o3de.org/).

## O3DE Extensions (Gems)

The simulation environment utilizes several O3DE Gems to enhance its capabilities:

- **ROS2**: Integrates ROS 2 with O3DE, allowing communication between the simulation and ROS 2 nodes.
  More on this gem can be found [here](https://www.docs.o3de.org/docs/user-guide/gems/reference/robotics/ros2/)

Opensource gems that are maintained by the O3DE community:

- **ROS2 Robot Importer**: Facilitates the import of robot models and their associated URDF files into O3DE.
- **ROS2 Controllers**: Provides pre-built controllers for common robot types, including mobile bases and manipulators.
- **ROS2 Sensors**: Offers a variety of sensor models that can be attached to robots within the simulation.
- **SimulationInterfaces**: Supplies interfaces for adjusting simulation using ROS 2 services. More on this gem can be found [here](https://www.docs.o3de.org/docs/user-guide/gems/reference/robotics/simulationinterfaces/)

Open source gems that are maintained by Robotec.AI:

- **ROS2ScriptIntegration**: Gem that allows to publish and subscribe to a limited set of ROS 2 messages using ScriptCanvas or LUA scripting language.
- **RobotecWarehouseLaddersStairsAssets**: Gem that provides warehouse assets including ladders and stairs for building simulation environments.
- **RobotecWarehouseMiscAssets**: Gem that provides miscellaneous warehouse assets for building simulation environments.
- **RobotecWarehouseBuildingAssets**: Gem that provides building assets for constructing warehouse environments.
- **RobotecSmallContainersAssets**: Gem that provides small container assets for warehouse simulations.
- **RobotecSurveillanceCamerasAssets**: Gem that provides surveillance camera assets for security simulations.
- **RobotecGenericDecorationsAssets**: Gem that provides generic decoration assets for enhancing simulation environments.
- **RobotecWarehousePayloadAssets**: Gem that provides payload assets for warehouse simulations.
- **RobotecWarehouseFloorMarkingAssets**: Gem that provides floor marking assets for warehouse environments.
- **HumanWorker**: Gem that provides human worker models for simulating human-robot interactions in warehouse settings.
- **RobotecSpectatorCamera**: Gem that provides a spectator camera for better visualization of the simulation.
- **WheelAnimTool**: Gem that provides tools for animating wheels on mobile robots.

Gems developed specifically for this demo:

- **KairosPlus**: Gem that provides digital twin for RB-Kairos+ platform [here](https://robotnik.eu/products/mobile-robots/rb-kairos-2/).
- **LevelGem**: Gem that provides the demo environment including the mobile manipulator robot and warehouse setting.

## Simulation Environment

The simulation environment is designed to mimic a realistic warehouse setting where a mobile manipulator robot can navigate and perform tasks.
The environment includes:

- Warehouse shelves and storage areas
- Floor markings for navigation
- Various obstacles to test robot navigation and manipulation capabilities
- Surveillance cameras for monitoring the environment
- Human worker models to simulate human-robot interactions
- Miscellaneous decorations to enhance realism and add complexity to the environment
- Containers and payloads for the robot to interact with
- Building structures to create a realistic warehouse layout
- A spectator camera to provide an overview of the simulation
- A mobile manipulator robot (RB-Kairos+) equipped with sensors and controllers

## Robot Model

The robot model was obtained from Robotnik in URDF format and imported into O3DE using the ROS2 Robot Importer gem.

Robotec.AI team enhanced the original URDF model by adding:

- New visual models for base and ARM,
- Necessary adjustments for simulation performance,
- Sensors,
- A vacuum gripper for object manipulation (added in the simulation for demonstration purposes).

The robot is equipped with:

- A mobile base with mecanum wheels for omnidirectional movement
- A 6-DOF manipulator arm for performing pick-and-place tasks (UR 10)
- Two LiDAR sensors for environment mapping and obstacle detection
- An RGB-D camera for visual perception
- A vacuum gripper for object manipulation (added in the simulation for demonstration purposes)

The robot is configured as separated prefab called `rbkairos_plus.prefab` that lives in `KairosPlus` gem.
The robot's omnidirectional movement is obtained utilizing `Rigid Body Twrist Controller` component from `ROS2 Controllers` gem.
This generalized controller, moves the [PhysX rigid body](https://docs.o3de.org/docs/user-guide/components/reference/physx/rigid-body/) to the desired linear and angular velocity using a PID controller.
It allows to control the robot using `geometry_msgs/Twist` messages.
For added fidelity, the `WheelAnimTool` gem is used to animate the wheels based on the robot's movement.
It provides accurate visual movement of the wheels, enhancing the fidelity of the simulation.

The topper (manipulator arm and sensors) is [PhysX 5 articulation](https://nvidia-omniverse.github.io/PhysX/physx/5.4.0/docs/Articulations.html).
The arm is controlled using the `ROS2 Joint Trajectory Controller` component from the `ROS2 Controllers` gem.
This controller allows for control of the manipulator's joints using `trajectory_msgs/JointTrajectory` or `control_msgs/action/FollowJointTrajectory`.
The latter is used to execute motion plans generated by MoveIt 2.

The Articulation and simulated rigid body are connected using a `Fixed Joint` component from the `PhysX 5` gem.

The LiDAR sensors are simulated using the `ROS2 LiDAR Sensor` component from the `ROS2 Sensors` gem.
This component is configured as a 2D LiDAR and publishes `sensor_msgs/LaserScan`.
The RGB-D camera is simulated using the `ROS2 RGBD Camera` component from the `ROS2 Sensors` gem.
This component simulates an RGB-D camera and publishes `sensor_msgs/Image` and `sensor_msgs/CameraInfo`.
The vacuum gripper utilizes a gripper component from the `ROS2 Controllers` gem that simulates a simple vacuum gripper.
The gripper is controlled using action `control_msgs/action/GripperCommand`. More on this component can be found
[here](https://www.docs.o3de.org/docs/user-guide/interactivity/robotics/grippers/).

## Environment Setup

The warehouse environment is constructed using assets from various gems that were mentioned earlier.
A static environment that includes shelves, floor markings, and other warehouse elements is created as a prefab called
`Warehouse_30x30.prefab` that lives in `LevelGem`.
The environment has colliders and physical properties set up to ensure realistic interactions with the robot and prop objects.

## Prop Objects

The environment includes various prop objects that the robot can interact with, such as boxes and containers.
Those can be spawned using ROS 2 services provided by the `SimulationInterfaces` gem.
The prop objects are designed to have realistic physical properties, colliders and visual models.

| URI                                                                            | Description                                | Image                                                                                              |
| ------------------------------------------------------------------------------ | ------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| 'product_asset:///assets/payload/boxes/cardboardbox01_v01.spawnable'           | Standard cardboard box, version 1.         | ![](images/props/product_asset____assets_payload_boxes_cardboardbox01_v01.spawnable.jpg)           |
| 'product_asset:///assets/payload/boxes/cardboardbox01_v02d.spawnable'          | Damaged cardboard box, version 2.          | ![](images/props/product_asset____assets_payload_boxes_cardboardbox01_v02d.spawnable.jpg)          |
| 'product_asset:///assets/payload/boxes/cardboardbox01_v03.spawnable'           | Standard cardboard box, version 3.         | ![](images/props/product_asset____assets_payload_boxes_cardboardbox01_v03.spawnable.jpg)           |
| 'product_asset:///assets/payload/boxes/cardboardbox02_v01.spawnable'           | Standard cardboard box, version 2.         | ![](images/props/product_asset____assets_payload_boxes_cardboardbox02_v01.spawnable.jpg)           |
| 'product_asset:///assets/payload/boxes/cardboardbox02_v02d.spawnable'          | Damaged cardboard box, version 2.          | ![](images/props/product_asset____assets_payload_boxes_cardboardbox02_v02d.spawnable.jpg)          |
| 'product_asset:///assets/payload/boxes/cardboardbox03_v01.spawnable'           | Standard cardboard box, version 3.         | ![](images/props/product_asset____assets_payload_boxes_cardboardbox03_v01.spawnable.jpg)           |
| 'product_asset:///assets/payload/boxes/cardboardbox03_v02o.spawnable'          | Open cardboard box, version 2.             | ![](images/props/product_asset____assets_payload_boxes_cardboardbox03_v02o.spawnable.jpg)          |
| 'product_asset:///assets/payload/boxes/cardboardbox04_v01.spawnable'           | Standard cardboard box, version 4.         | ![](images/props/product_asset____assets_payload_boxes_cardboardbox04_v01.spawnable.jpg)           |
| 'product_asset:///assets/payload/boxes/cardboardbox05_v01.spawnable'           | Standard cardboard box, version 5.         | ![](images/props/product_asset____assets_payload_boxes_cardboardbox05_v01.spawnable.jpg)           |
| 'product_asset:///assets/payload/boxes/cardboardbox06_v01.spawnable'           | Standard cardboard box, version 6.         | ![](images/props/product_asset____assets_payload_boxes_cardboardbox06_v01.spawnable.jpg)           |
| 'product_asset:///assets/payload/boxes/cardboardbox07_v01.spawnable'           | Standard cardboard box, version 7.         | ![](images/props/product_asset____assets_payload_boxes_cardboardbox07_v01.spawnable.jpg)           |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox01_v01d.spawnable'  | Damaged cardboard box, version 1.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox01_v01d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox01_v02d.spawnable'  | Damaged cardboard box, version 2.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox01_v02d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox01_v03d.spawnable'  | Damaged cardboard box, version 3.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox01_v03d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox02_v01d.spawnable'  | Damaged cardboard box, version 2.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox02_v01d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox02_v02d.spawnable'  | Damaged cardboard box, version 2.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox02_v02d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox03_v01d.spawnable'  | Damaged cardboard box, version 3.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox03_v01d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox03_v02od.spawnable' | Open damaged cardboard box, version 2.     | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox03_v02od.spawnable.jpg) |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox04_v01d.spawnable'  | Damaged cardboard box, version 4.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox04_v01d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox05_v01d.spawnable'  | Damaged cardboard box, version 5.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox05_v01d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox06_v01d.spawnable'  | Damaged cardboard box, version 6.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox06_v01d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox07_v01d.spawnable'  | Damaged cardboard box, version 7.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox07_v01d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/damaged/cardboardbox08_v01d.spawnable'  | Damaged cardboard box, version 8.          | ![](images/props/product_asset____assets_payload_boxes_damaged_cardboardbox08_v01d.spawnable.jpg)  |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox01_v01t.spawnable'    | Trash cardboard box, version 1.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox01_v01t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox01_v02t.spawnable'    | Trash cardboard box, version 2.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox01_v02t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox01_v03t.spawnable'    | Trash cardboard box, version 3.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox01_v03t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox02_v01t.spawnable'    | Trash cardboard box, version 2.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox02_v01t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox02_v02t.spawnable'    | Trash cardboard box, version 2.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox02_v02t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox03_v01t.spawnable'    | Trash cardboard box, version 3.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox03_v01t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox03_v02ot.spawnable'   | Open trash cardboard box, version 2.       | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox03_v02ot.spawnable.jpg)   |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox04_v01t.spawnable'    | Trash cardboard box, version 4.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox04_v01t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox05_v01t.spawnable'    | Trash cardboard box, version 5.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox05_v01t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox06_v01t.spawnable'    | Trash cardboard box, version 6.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox06_v01t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox07_v01t.spawnable'    | Trash cardboard box, version 7.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox07_v01t.spawnable.jpg)    |
| 'product_asset:///assets/payload/boxes/trash/cardboardbox08_v01t.spawnable'    | Trash cardboard box, version 8.            | ![](images/props/product_asset____assets_payload_boxes_trash_cardboardbox08_v01t.spawnable.jpg)    |
| 'product_asset:///assets/payload/misccontainers/paintcan.spawnable'            | Paint can container.                       | ![](images/props/product_asset____assets_payload_misccontainers_paintcan.spawnable.jpg)            |
| 'product_asset:///assets/payload/misccontainers/plasticbarrel1.spawnable'      | Plastic barrel, type 1.                    | ![](images/props/product_asset____assets_payload_misccontainers_plasticbarrel1.spawnable.jpg)      |
| 'product_asset:///assets/payload/misccontainers/plasticbarrel2.spawnable'      | Plastic barrel, type 2.                    | ![](images/props/product_asset____assets_payload_misccontainers_plasticbarrel2.spawnable.jpg)      |
| 'product_asset:///assets/payload/misccontainers/plasticbucket.spawnable'       | Plastic bucket container.                  | ![](images/props/product_asset____assets_payload_misccontainers_plasticbucket.spawnable.jpg)       |
| 'product_asset:///assets/payload/misccontainers/plasticcanister.spawnable'     | Plastic canister container.                | ![](images/props/product_asset____assets_payload_misccontainers_plasticcanister.spawnable.jpg)     |
| 'product_asset:///assets/payload/oilspills/oilspill1.spawnable'                | Oil spill, type 1.                         | ![](images/props/product_asset____assets_payload_oilspills_oilspill1.spawnable.jpg)                |
| 'product_asset:///assets/payload/oilspills/oilspill2.spawnable'                | Oil spill, type 2.                         | ![](images/props/product_asset____assets_payload_oilspills_oilspill2.spawnable.jpg)                |
| 'product_asset:///assets/payload/payload.spawnable'                            | Generic payload object.                    | ![](images/props/product_asset____assets_payload_payload.spawnable.jpg)                            |
| 'product_asset:///assets/payload/stickers/aruco00.spawnable'                   | ArUco marker sticker, ID 00.               | ![](images/props/product_asset____assets_payload_stickers_aruco00.spawnable.jpg)                   |
| 'product_asset:///assets/payload/stickers/aruco01.spawnable'                   | ArUco marker sticker, ID 01.               | ![](images/props/product_asset____assets_payload_stickers_aruco01.spawnable.jpg)                   |
| 'product_asset:///assets/payload/stickers/aruco02.spawnable'                   | ArUco marker sticker, ID 02.               | ![](images/props/product_asset____assets_payload_stickers_aruco02.spawnable.jpg)                   |
| 'product_asset:///assets/payload/stickers/aruco03.spawnable'                   | ArUco marker sticker, ID 03.               | ![](images/props/product_asset____assets_payload_stickers_aruco03.spawnable.jpg)                   |
| 'product_asset:///assets/payload/stickers/aruco04.spawnable'                   | ArUco marker sticker, ID 04.               | ![](images/props/product_asset____assets_payload_stickers_aruco04.spawnable.jpg)                   |
| 'product_asset:///assets/payload/stickers/aruco05.spawnable'                   | ArUco marker sticker, ID 05.               | ![](images/props/product_asset____assets_payload_stickers_aruco05.spawnable.jpg)                   |
| 'product_asset:///assets/payload/stickers/aruco06.spawnable'                   | ArUco marker sticker, ID 06.               | ![](images/props/product_asset____assets_payload_stickers_aruco06.spawnable.jpg)                   |
| 'product_asset:///assets/payload/stickers/aruco07.spawnable'                   | ArUco marker sticker, ID 07.               | ![](images/props/product_asset____assets_payload_stickers_aruco07.spawnable.jpg)                   |
| 'product_asset:///assets/payload/stickers/aruco08.spawnable'                   | ArUco marker sticker, ID 08.               | ![](images/props/product_asset____assets_payload_stickers_aruco08.spawnable.jpg)                   |
| 'product_asset:///assets/payload/stickers/aruco09.spawnable'                   | ArUco marker sticker, ID 09.               | ![](images/props/product_asset____assets_payload_stickers_aruco09.spawnable.jpg)                   |
| 'product_asset:///assets/prefabs/carrot.spawnable'                             | Carrot prop object.                        | ![](images/props/product_asset____assets_prefabs_carrot.spawnable.jpg)                             |
| 'product_asset:///assets/prefabs/corn.spawnable'                               | Corn prop object.                          | ![](images/props/product_asset____assets_prefabs_corn.spawnable.jpg)                               |
| 'product_asset:///assets/prefabs/tomato.spawnable'                             | Tomato prop object.                        | ![](images/props/product_asset____assets_prefabs_tomato.spawnable.jpg)                             |
| 'product_asset:///assets/prefabs/yellow_cube.spawnable'                        | Yellow cube prop object.                   | ![](images/props/product_asset____assets_prefabs_yellow_cube.spawnable.jpg)                        |
| 'product_asset:///assets/rbkairos_plus.spawnable'                              | RB-Kairos+ mobile manipulator robot model. | ![](images/props/product_asset____assets_rbkairos_plus.spawnable.jpg)                              |
| 'product_asset:///assets/warehouse/assets/racks/storagerack_2x1.spawnable'     | Warehouse storage rack, 2x1 size.          | ![](images/props/product_asset____assets_warehouse_assets_racks_storagerack_2x1.spawnable.jpg)     |
| 'product_asset:///assets/warehouse/assets/tables/packingtable.spawnable'       | Warehouse packing table.                   | ![](images/props/product_asset____assets_warehouse_assets_tables_packingtable.spawnable.jpg)       |
| 'product_asset:///assets/warehouse/building/ceilinglamp_local.spawnable'       | Ceiling lamp for warehouse lighting.       | ![](images/props/product_asset____assets_warehouse_building_ceilinglamp_local.spawnable.jpg)       |
| 'product_asset:///barriers/barriercorner_visual.spawnable'                     | Barrier corner visual asset.               | ![](images/props/product_asset____barriers_barriercorner_visual.spawnable.jpg)                     |
| 'product_asset:///barriers/barrierstraight_visual.spawnable'                   | Barrier straight visual asset.             | ![](images/props/product_asset____barriers_barrierstraight_visual.spawnable.jpg)                   |
| 'product_asset:///cages/cageholder_visual.spawnable'                           | Cage holder visual asset.                  | ![](images/props/product_asset____cages_cageholder_visual.spawnable.jpg)                           |
| 'product_asset:///cages/cagewallmedium_visual.spawnable'                       | Cage wall, medium size.                    | ![](images/props/product_asset____cages_cagewallmedium_visual.spawnable.jpg)                       |
| 'product_asset:///cages/cagewallmediumholder_visual.spawnable'                 | Cage wall medium holder asset.             | ![](images/props/product_asset____cages_cagewallmediumholder_visual.spawnable.jpg)                 |
| 'product_asset:///cages/cagewallnarrow_visual.spawnable'                       | Cage wall, narrow size.                    | ![](images/props/product_asset____cages_cagewallnarrow_visual.spawnable.jpg)                       |
| 'product_asset:///cages/cagewallnarrowholder_visual.spawnable'                 | Cage wall narrow holder asset.             | ![](images/props/product_asset____cages_cagewallnarrowholder_visual.spawnable.jpg)                 |
| 'product_asset:///cages/cagewallwide_visual.spawnable'                         | Cage wall, wide size.                      | ![](images/props/product_asset____cages_cagewallwide_visual.spawnable.jpg)                         |
| 'product_asset:///cages/cagewallwideholder_visual.spawnable'                   | Cage wall wide holder asset.               | ![](images/props/product_asset____cages_cagewallwideholder_visual.spawnable.jpg)                   |
| 'product_asset:///cardboardbox/cardboardbox.spawnable'                         | Generic cardboard box.                     | ![](images/props/product_asset____cardboardbox_cardboardbox.spawnable.jpg)                         |
| 'product_asset:///cardboardboxes/cardboardbox01_v00.spawnable'                 | Cardboard box, version 00.                 | ![](images/props/product_asset____cardboardboxes_cardboardbox01_v00.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox01_v01.spawnable'                 | Cardboard box, version 01.                 | ![](images/props/product_asset____cardboardboxes_cardboardbox01_v01.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox01_v02d.spawnable'                | Damaged cardboard box, version 02.         | ![](images/props/product_asset____cardboardboxes_cardboardbox01_v02d.spawnable.jpg)                |
| 'product_asset:///cardboardboxes/cardboardbox01_v03.spawnable'                 | Cardboard box, version 03.                 | ![](images/props/product_asset____cardboardboxes_cardboardbox01_v03.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox01_v04.spawnable'                 | Cardboard box, version 04.                 | ![](images/props/product_asset____cardboardboxes_cardboardbox01_v04.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox01_v05.spawnable'                 | Cardboard box, version 05.                 | ![](images/props/product_asset____cardboardboxes_cardboardbox01_v05.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox01_v06d.spawnable'                | Damaged cardboard box, version 06.         | ![](images/props/product_asset____cardboardboxes_cardboardbox01_v06d.spawnable.jpg)                |
| 'product_asset:///cardboardboxes/cardboardbox02_v00.spawnable'                 | Cardboard box, version 02_00.              | ![](images/props/product_asset____cardboardboxes_cardboardbox02_v00.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox02_v01.spawnable'                 | Cardboard box, version 02_01.              | ![](images/props/product_asset____cardboardboxes_cardboardbox02_v01.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox02_v02d.spawnable'                | Damaged cardboard box, version 02_02.      | ![](images/props/product_asset____cardboardboxes_cardboardbox02_v02d.spawnable.jpg)                |
| 'product_asset:///cardboardboxes/cardboardbox02_v03.spawnable'                 | Cardboard box, version 02_03.              | ![](images/props/product_asset____cardboardboxes_cardboardbox02_v03.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox02_v04d.spawnable'                | Damaged cardboard box, version 02_04.      | ![](images/props/product_asset____cardboardboxes_cardboardbox02_v04d.spawnable.jpg)                |
| 'product_asset:///cardboardboxes/cardboardbox03_v01.spawnable'                 | Cardboard box, version 03_01.              | ![](images/props/product_asset____cardboardboxes_cardboardbox03_v01.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox03_v02o.spawnable'                | Open cardboard box, version 03_02.         | ![](images/props/product_asset____cardboardboxes_cardboardbox03_v02o.spawnable.jpg)                |
| 'product_asset:///cardboardboxes/cardboardbox03_v03o.spawnable'                | Open cardboard box, version 03_03.         | ![](images/props/product_asset____cardboardboxes_cardboardbox03_v03o.spawnable.jpg)                |
| 'product_asset:///cardboardboxes/cardboardbox04_v01.spawnable'                 | Cardboard box, version 04_01.              | ![](images/props/product_asset____cardboardboxes_cardboardbox04_v01.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox05_v01.spawnable'                 | Cardboard box, version 05_01.              | ![](images/props/product_asset____cardboardboxes_cardboardbox05_v01.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox06_v01.spawnable'                 | Cardboard box, version 06_01.              | ![](images/props/product_asset____cardboardboxes_cardboardbox06_v01.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox07_v01.spawnable'                 | Cardboard box, version 07_01.              | ![](images/props/product_asset____cardboardboxes_cardboardbox07_v01.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox08_v01.spawnable'                 | Cardboard box, version 08_01.              | ![](images/props/product_asset____cardboardboxes_cardboardbox08_v01.spawnable.jpg)                 |
| 'product_asset:///cardboardboxes/cardboardbox09_v01.spawnable'                 | Cardboard box, version 09_01.              | ![](images/props/product_asset____cardboardboxes_cardboardbox09_v01.spawnable.jpg)                 |
| 'product_asset:///cctvcameras/cctvcamera01/cctvcamera01.spawnable'             | CCTV camera model 01.                      | ![](images/props/product_asset____cctvcameras_cctvcamera01_cctvcamera01.spawnable.jpg)             |
| 'product_asset:///cctvcameras/cctvcamera02/cctvcamera02.spawnable'             | CCTV camera model 02.                      | ![](images/props/product_asset____cctvcameras_cctvcamera02_cctvcamera02.spawnable.jpg)             |

# ROS 2 Integration and API

The mobile manipulator robot can be controlled using standard ROS 2 messages and actions.
The robot base can be moved by publishing `geometry_msgs/Twist` messages to the `/cmd_vel` topic.

The simulator publishes sensor data from the robot's LiDAR and RGB-D camera to the appropriate ROS 2 topics.

## ROS 2 Topics

Simulator publishes and subscribes to the following ROS 2 topics:

| Topic Name                       | Message Type               | Direction  | Notes                         |
| -------------------------------- | -------------------------- | ---------- | ----------------------------- |
| /camera_image_color              | sensor_msgs/msg/Image      | Published  | Color camera image            |
| /clock                           | rosgraph_msgs/msg/Clock    | Published  | Simulation clock              |
| /color_camera_info               | sensor_msgs/msg/CameraInfo | Published  | Color camera info             |
| /fake_lidar                      | sensor_msgs/msg/LaserScan  | Published  | Simulated LiDAR (for mapping) |
| /joint_states                    | sensor_msgs/msg/JointState | Published  | UR-10 Robot joint states      |
| /rgbd_camera/camera_image_color  | sensor_msgs/msg/Image      | Published  | RGB-D color image             |
| /rgbd_camera/camera_image_depth  | sensor_msgs/msg/Image      | Published  | RGB-D depth image             |
| /rgbd_camera/camera_info         | sensor_msgs/msg/CameraInfo | Published  | RGB-D camera info             |
| /rgbd_camera/depth_camera_info   | sensor_msgs/msg/CameraInfo | Published  | RGB-D depth info              |
| /scan_front_right                | sensor_msgs/msg/LaserScan  | Published  | Front right LiDAR             |
| /scan_rear_left                  | sensor_msgs/msg/LaserScan  | Published  | Rear left LiDAR               |
| /sim/reported_points             | std_msgs/msg/String        | Published  | Simulation points             |
| /tf                              | tf2_msgs/msg/TFMessage     | Published  | Transforms                    |
| /tf_static                       | tf2_msgs/msg/TFMessage     | Published  | Static transforms             |
| /wrist_camera/camera_image_color | sensor_msgs/msg/Image      | Published  | Wrist camera image            |
| /wrist_camera/camera_info        | sensor_msgs/msg/CameraInfo | Published  | Wrist camera info             |
| /cmd_vel                         | geometry_msgs/msg/Twist    | Subscribed | Robot velocity cmd            |

It populates ROS 2 TF tree with the following frames:

| Frame Name                                | Parent Frame                      | Description                      |
| ----------------------------------------- | --------------------------------- | -------------------------------- |
| world                                     | odom                              | World frame                      |
| odom                                      |                                   | Odometry frame (parent of world) |
| egobase_footprint                         | world                             | Robot base footprint             |
| egobase_link                              | egobase_footprint                 | Main robot base link             |
| egobase_logo_left                         | egobase_link                      | Left logo on base                |
| egobase_logo_right                        | egobase_link                      | Right logo on base               |
| egobase_logo_rear                         | egobase_link                      | Rear logo on base                |
| egobase_logo_front                        | egobase_docking_contact           | Front logo on base               |
| egobase_docking_contact                   | egobase_link                      | Docking contact                  |
| egoback_left_wheel_link                   | egobase_link                      | Back left wheel                  |
| egoback_right_wheel_link                  | egobase_link                      | Back right wheel                 |
| egofront_left_wheel_link                  | egobase_link                      | Front left wheel                 |
| egofront_right_wheel_link                 | egobase_link                      | Front right wheel                |
| egorear_laser_base_link                   | egobase_link                      | Rear laser base                  |
| egorear_laser_link                        | egorear_laser_base_link           | Rear laser sensor                |
| egofront_laser_base_link                  | egobase_link                      | Front laser base                 |
| egofront_laser_link                       | egofront_laser_base_link          | Front laser sensor               |
| egofront_rgbd_camera_base_link            | egobase_link                      | RGB-D camera base                |
| egofront_rgbd_camera_link                 | egofront_rgbd_camera_base_link    | RGB-D camera link                |
| egofront_rgbd_camera_color_frame          | egofront_rgbd_camera_link         | RGB-D color frame                |
| egofront_rgbd_camera_color_optical_frame  | egofront_rgbd_camera_color_frame  | RGB-D color optical frame        |
| egofront_rgbd_camera_depth_frame          | egofront_rgbd_camera_link         | RGB-D depth frame                |
| egofront_rgbd_camera_depth_optical_frame  | egofront_rgbd_camera_depth_frame  | RGB-D depth optical frame        |
| egofront_rgbd_camera_infra1_frame         | egofront_rgbd_camera_link         | RGB-D infra1 frame               |
| egofront_rgbd_camera_infra1_optical_frame | egofront_rgbd_camera_infra1_frame | RGB-D infra1 optical frame       |
| egofront_rgbd_camera_infra2_frame         | egofront_rgbd_camera_link         | RGB-D infra2 frame               |
| egofront_rgbd_camera_infra2_optical_frame | egofront_rgbd_camera_infra2_frame | RGB-D infra2 optical frame       |
| egoimu_base_link                          | egobase_link                      | IMU base link                    |
| egoimu_link                               | egoimu_base_link                  | IMU link                         |
| egotop_cover                              | egobase_link                      | Top cover                        |
| egoarm_base_link                          | egotop_cover                      | Arm base link                    |
| egoarm_base_link_inertia                  | egoarm_base_link                  | Arm base inertia                 |
| egoarm_base                               | egoarm_base_link                  | Arm base                         |
| egoarm_shoulder_link                      | egoarm_base_link_inertia          | Arm shoulder link                |
| egoarm_upper_arm_link                     | egoarm_shoulder_link              | Arm upper arm link               |
| egoarm_forearm_link                       | egoarm_upper_arm_link             | Arm forearm link                 |
| egoarm_wrist_1_link                       | egoarm_forearm_link               | Arm wrist 1 link                 |
| egoarm_wrist_2_link                       | egoarm_wrist_1_link               | Arm wrist 2 link                 |
| egoarm_wrist_3_link                       | egoarm_wrist_2_link               | Arm wrist 3 link                 |
| egoarm_flange                             | egoarm_wrist_3_link               | Arm flange                       |
| egoarm_ft_frame                           | egoarm_wrist_3_link               | Arm force/torque frame           |
| egoarm_tool0                              | egoarm_flange                     | Arm tool0                        |
| wrist_camera                              | egoarm_wrist_2_link               | Wrist camera base                |
| wrist_camera_link                         | wrist_camera                      | Wrist camera link                |
| wrist_camera_color_frame                  | wrist_camera                      | Wrist camera color frame         |
| wrist_camera_color_optical_frame          | wrist_camera_color_frame          | Wrist camera color optical frame |

**Important Note:**

The TF tree assumes that the robot localization is not a part evaluated in the simulation.
Therefore, the `odom` frame is static and coincides with the `world` frame, and `ego_base_footprint` localization is directly
obtained from the simulation engine as ground truth. In a real-world scenario, the `odom` frame would be updated based on odometry data,
and the `world` frame would be established by a SLAM or localization system.

## ROS 2 Services

The simulator provides the following ROS 2 services for interaction:

| Service Name                              | Service Type                                       | Description                                |
| :---------------------------------------- | -------------------------------------------------- | ------------------------------------------ |
| /delete_entity                            | simulation_interfaces/srv/DeleteEntity             | Delete an entity from the simulation       |
| /get_available_worlds                     | simulation_interfaces/srv/GetAvailableWorlds       | List available simulation worlds           |
| /get_entities                             | simulation_interfaces/srv/GetEntities              | List all entities in the simulation        |
| /get_entities_states                      | simulation_interfaces/srv/GetEntitiesStates        | Get states of all entities                 |
| /get_entity_bounds                        | simulation_interfaces/srv/GetEntityBounds          | Get bounding box of an entity              |
| /get_entity_info                          | simulation_interfaces/srv/GetEntityInfo            | Get info about an entity                   |
| /get_entity_state                         | simulation_interfaces/srv/GetEntityState           | Get state of a specific entity             |
| /get_named_pose_bounds                    | simulation_interfaces/srv/GetNamedPoseBounds       | Get bounds for a named pose                |
| /get_named_poses                          | simulation_interfaces/srv/GetNamedPoses            | List named poses in the simulation         |
| /get_simulation_state                     | simulation_interfaces/srv/GetSimulationState       | Get current simulation state               |
| /get_simulator_features                   | simulation_interfaces/srv/GetSimulatorFeatures     | List supported simulator features          |
| /get_spawnables                           | simulation_interfaces/srv/GetSpawnables            | List available spawnable assets            |
| /o3de_ros2_node/describe_parameters       | rcl_interfaces/srv/DescribeParameters              | Describe node parameters                   |
| /o3de_ros2_node/get_parameter_types       | rcl_interfaces/srv/GetParameterTypes               | Get types of node parameters               |
| /o3de_ros2_node/get_parameters            | rcl_interfaces/srv/GetParameters                   | Get node parameters                        |
| /o3de_ros2_node/get_type_description      | type_description_interfaces/srv/GetTypeDescription | Get type description for a message/service |
| /o3de_ros2_node/list_parameters           | rcl_interfaces/srv/ListParameters                  | List node parameters                       |
| /o3de_ros2_node/set_parameters            | rcl_interfaces/srv/SetParameters                   | Set node parameters                        |
| /o3de_ros2_node/set_parameters_atomically | rcl_interfaces/srv/SetParametersAtomically         | Set node parameters atomically             |
| /reset_simulation                         | simulation_interfaces/srv/ResetSimulation          | Reset the simulation                       |
| /set_entity_info                          | simulation_interfaces/srv/SetEntityInfo            | Set info for an entity                     |
| /set_entity_state                         | simulation_interfaces/srv/SetEntityState           | Set state for an entity                    |
| /set_simulation_state                     | simulation_interfaces/srv/SetSimulationState       | Set simulation state                       |
| /spawn_entity                             | simulation_interfaces/srv/SpawnEntity              | Spawn an entity in the simulation          |
| /step_simulation                          | simulation_interfaces/srv/StepSimulation           | Step the simulation forward                |

## ROS 2 Actions

The simulator provides the following ROS 2 actions for advanced control:

| Action Name                                          | Action Type                                | Description                                |
| ---------------------------------------------------- | ------------------------------------------ | ------------------------------------------ |
| /gripper_server                                      | control_msgs/action/GripperCommand         | Control the robot's gripper                |
| /joint_trajectory_controller/follow_joint_trajectory | control_msgs/action/FollowJointTrajectory  | Control the manipulator joint trajectories |
| /simulate_steps                                      | simulation_interfaces/action/SimulateSteps | Step the simulation for a given duration   |

## Simulated robot stack

Robotic stack for the simulated RB-Kairos+ robot is provided in the `robotec_kairos_ur10` ROS 2 package provided with the project.
This package includes configurations for robot description, MoveIt 2 setup for motion planning, and launch files to start the simulation along with necessary ROS 2 nodes.
This package provide launch files to control robot base and manipulator. It also includes necessary resources like static map of obstacles in the warehouse environment for navigation.

## Environment Interaction

To spawn a prop object in the simulation, use the ROS 2 service `/spawn_entity` provided by the `SimulationInterfaces` gem.
The service requires the URI of the spawnable asset, as well as the desired position and orientation.
Example service call to spawn a cardboard box:

```bash
ros2 service call /spawn_entity simulation_interfaces/srv/SpawnEntity "{name: 'box1', uri: 'product_asset:///assets/payload/boxes/cardboardbox01_v01.spawnable', initial_pose: {pose:{position: {x: 14.0, y: 8.2, z: 2.5}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}"
```

More on spawning entities using this service can be found [here](https://www.docs.o3de.org/docs/user-guide/interactivity/robotics/simulation-interfaces/).
With simulation interfaces you can :

- Spawn and delete entities
- Move entities to a desired pose
- Get list of spawned entities
- Pause and resume the simulation
