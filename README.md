# CodeAlpha Robotics & Automation Internship Projects

An overview, system architecture, kinematic modeling, and ROS/Gazebo simulation workspace for all tasks developed during the Robotics & Automation Internship at **CodeAlpha**.

---

## 📌 Project Overview

This repository encompasses three core project tasks focusing on Industry 4.0 smart manufacturing, kinematic analysis, trajectory control, and automated AI quality inspection:

- **Task 1:** 4-DOF Manipulator design, Denavit-Hartenberg (D-H) kinematic modeling, and Industry 4.0 integration architecture.
- **Task 2:** Full ROS/Gazebo simulation package featuring custom URDF specifications, dynamic controllers, and smooth trajectory planning.
- **Task 3:** Computer vision and AI-driven quality inspection package for automated defect detection and vision-guided robotic sorting.

---

## 📁 Repository Directory Structure

```text
CodeAlpa_Robotics_Automation/
├── CodeAlpha_Task1/
│   ├── 01_4DOF_Arm_Isometric.png
│   └── CodeAlpha_Task1_Robotics_Manufacturing_Industry4.pdf
├── CodeAlpha_Task2_Package/
│   └── Task2_Simulation/
│       ├── launch/
│       ├── urdf/
│       ├── config/
│       ├── src/
│       ├── CMakeLists.txt
│       └── package.xml
├── CodeAlpha_Task3_Package/
│   ├── config/
│   ├── launch/
│   ├── scripts/
│   ├── src/
│   ├── CMakeLists.txt
│   └── package.xml
├── 01_4DOF_Arm_Isometric.png
├── CodeAlpha_Task1_Robotics_Manufacturing_Industry4.pdf
└── README.md

```

---

## 🛠️ Task Summaries & Technical Details

### 1️⃣ Task 1: 4-DOF Robotic Arm for Smart Manufacturing & Industry 4.0

* **Directory:** `CodeAlpha_Task1/`
* **Focus:** Kinematic Analysis, CAD Model, & Industry 4.0 Architecture

#### Key Features

* **Joint Architecture:** 4-DOF manipulator (Base Revolute, Shoulder Pitch, Elbow Pitch, Wrist Roll/Pitch).
* **Kinematic Formulation:** Forward and Inverse Kinematics computed using standard Denavit-Hartenberg (D-H) parameters to resolve end-effector spatial coordinates $(X, Y, Z)$.
* **Industry 4.0 Setup:** Integrated IoT feedback loops, real-time sensor monitoring, and automated pick-and-place logic.
* **Key Artifacts:**
* `01_4DOF_Arm_Isometric.png`: 3D CAD visualization.
* `CodeAlpha_Task1_Robotics_Manufacturing_Industry4.pdf`: Detailed technical report.



---

### 2️⃣ Task 2: Simulation, Dynamics & Trajectory Control Package

* **Directory:** `CodeAlpha_Task2_Package/Task2_Simulation/`
* **Focus:** ROS / Gazebo Physics Simulation & Trajectory Control

#### Key Features

* **URDF / Xacro Modeling:** Comprehensive robot description including mass, inertial matrices, collision geometry, and joint limits.
* **Gazebo Physics Integration:** Real-time physical simulation configured with `ros_control` interfaces (`position_controllers`, `joint_state_controller`).
* **Trajectory Planning:** Smooth trajectory execution using polynomial velocity profiles for collision-free workspace movement.

---

### 3️⃣ Task 3: AI-Based Quality Inspection & Vision Automation Package

* **Directory:** `CodeAlpha_Task3_Package/`
* **Focus:** Computer Vision, Defect Detection, & Vision-Guided Actuation

#### Key Features

* **Computer Vision Pipeline:** Real-time visual processing using OpenCV/AI model frameworks for object detection, classification, and surface defect analysis.
* **Closed-Loop Sorting:** Real-time messaging between image processing nodes and manipulator control nodes for automated pass/fail material routing.
* **ROS Architecture:** Synchronized topic publishers/subscribers managing camera streams (`sensor_msgs/Image`) and target coordinates.

---

## 🚀 Build & Run Instructions

### Prerequisites

* **OS:** Ubuntu 20.04 LTS / 22.04 LTS
* **Middleware:** ROS Noetic / ROS 2
* **Simulator:** Gazebo 11
* **Dependencies:**
```bash
sudo apt install ros-$ROS_DISTRO-gazebo-ros-pkgs ros-$ROS_DISTRO-ros-control ros-$ROS_DISTRO-ros-controllers
pip install opencv-python numpy matplotlib

```



### Build Workspace

1. Clone the repository:
```bash
git clone [https://github.com/meetumeshagrawal-dot/CodeAlpa_Robotics_Automation.git](https://github.com/meetumeshagrawal-dot/CodeAlpa_Robotics_Automation.git)
cd CodeAlpa_Robotics_Automation

```


2. Copy ROS packages to your workspace and build:
```bash
cp -r CodeAlpha_Task2_Package/Task2_Simulation ~/catkin_ws/src/
cp -r CodeAlpha_Task3_Package ~/catkin_ws/src/
cd ~/catkin_ws
catkin_make
source devel/setup.bash

```


3. Launch Gazebo Simulation (Task 2):
```bash
roslaunch Task2_Simulation gazebo.launch

```


4. Launch Vision Quality Inspection (Task 3):
```bash
roslaunch CodeAlpha_Task3_Package inspection.launch

```



---

## 👤 Author

**Meet Agrawal**

* GitHub: [@meetumeshagrawal-dot](https://github.com/meetumeshagrawal-dot)
* Internship Domain: Robotics & Automation at **CodeAlpha**

```

```
