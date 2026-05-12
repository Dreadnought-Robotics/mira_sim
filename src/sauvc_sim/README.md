# Gazebo SAUVC environment

Gazebo fortress SAUVC environment with ROS2 humble
![Screenshot from 2025-11-10 15-48-32](https://hackmd.io/_uploads/SJ_Musom-l.png)


## Getting started

Build the code:
```
colcon build --symlink-install --package-select sauvc_sim
. install/setup.sh
```

Modify the demo_auv's initial position in `worlds/sauvc25.world` line 164-173
```
    <include>
      <uri>model://demo_auv</uri>

      <!-- qualification -->
      <pose>-24.6 0 -0.2 0 0 0</pose>

      <!-- final -->
      <pose>11 -11.5 -0.2 0 0 1.5708</pose>

    </include>
```

Launch the environment
```
ros2 launch sauvc_sim sauvc25_launch.py
```

Keyboard control and video capturing:
```
ros2 run sauvc_sim teleop25.py
```