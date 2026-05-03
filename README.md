# Lab Digital Twin: Robotics Simulation Environment (ROS2 Edition)

The Lab Digital Twin project focuses on the development of a high-fidelity virtual replica of a robotics laboratory. Unlike standard demonstration scenes, this project integrates real-world geometry modeled in Blender with the ROS2 Humble framework to enable the testing of navigation algorithms in conditions that closely replicate the physical environment.

## Project Structure

The project is divided into three logical stages that bridge the gap between 3D design, physical simulation, and autonomous control.

| Stage       | Task                | Technology                 | Result                                    |
| :---------- | :------------------ | :------------------------- | :---------------------------------------- |
| **Stage 1** | 3D Modeling         | Blender + Collada (`.dae`) | Photogrammetric interior model            |
| **Stage 2** | Digital Environment | Gazebo Sim + SDF           | Virtual world with physics and collisions |
| **Stage 3** | Control Logic       | Python 3 + ROS2 Nodes      | Autonomous agent (Brain Node)             |

## Technical Stack

- **Operating System:** Ubuntu 22.04 LTS
- **Middleware:** ROS2 Humble Hawksbill
- **Simulation Engine:** Gazebo (Classic/Harmonic) for physics and sensor emulation
- **Modeling:** Blender for architectural and furniture modeling
- **Programming:** Python 3 (libraries: `rclpy`, `sensor_msgs`, `geometry_msgs`)

## Package Architecture Overview

The file structure is organized according to `ament_python` standards:

```text
lab_digital_twin/
├── launch/         # Python launch scripts for automation
├── models/         # SDF descriptions and Blender meshes
│   └── lab_interior/
│       └── meshes/ # Directory for exported .dae files
├── scripts/        # Executable Python nodes (Robot "Brain")
├── worlds/         # Gazebo world configuration (lighting, gravity)
├── setup.py        # Build configuration and resource installation
└── package.xml     # Package dependencies
```
