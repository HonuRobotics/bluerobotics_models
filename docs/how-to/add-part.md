# Add a part

A part is one file, `bluerobotics_parts/urdf/<part>.urdf.xacro`, holding a
metadata macro (`<part>_info`) and the macro that instantiates it; the full
contract is in [Parts](../design/parts.md). Write it by hand, starting from
an existing part or from this minimal one, a 10 cm box of 0.5 kg with one
slot on top:

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://ros.org/wiki/xacro">

  <xacro:macro name="my_box_info">
    <xacro:property name="part_info" scope="parent" value="${dict(
        attach='0 0 -0.05',
        slots=dict(
            top=dict(xyz='0 0 0.05', rpy='0 0 0', accepts=['ping_singlebeam'], default='none'),
        ),
        frames=dict())}"/>
  </xacro:macro>

  <xacro:macro name="my_box"
               params="name parent xyz:='0 0 0' rpy:='0 0 0' collision:=true joint:=fixed axis:='0 0 1'">
    <xacro:my_box_info/>
    <link name="${name}">
      <inertial>
        <origin xyz="0 0 0" rpy="0 0 0"/>
        <mass value="0.5"/>
        <inertia ixx="0.000833" ixy="0" ixz="0" iyy="0.000833" iyz="0" izz="0.000833"/>
      </inertial>
      <visual>   <!-- a glTF mesh would go through <xacro:part_visual mesh="package://..."/> -->
        <geometry><box size="0.1 0.1 0.1"/></geometry>
      </visual>
      <xacro:if value="${collision}">
        <collision>
          <geometry><box size="0.1 0.1 0.1"/></geometry>
        </collision>
      </xacro:if>
    </link>
    <xacro:part_joint name="${name}" parent="${parent}" xyz="${xyz}" rpy="${rpy}"
                      joint="${joint}" axis="${axis}" attach="${part_info['attach']}"/>
    <xacro:part_slots name="${name}" items="${list(part_info['slots'].items())}"/>
    <xacro:part_frames name="${name}" items="${list(part_info['frames'].items())}"/>
  </xacro:macro>

</robot>
```

`attach` is where the part bolts on, in its own frame (here the bottom face,
so the box stands on whatever it is mounted to); the macro's `axis` default
is the part's own spin axis, used when it is fitted on a turning joint. A
propeller additionally declares `drive=dict(diameter=..., max_thrust=...,
min_thrust=..., rotation='ccw'|'cw')`, which makes the assembly mount it on a
continuous joint and the Gazebo side give it a Thruster and a thrust topic.

Then:

1. If the part has a real mesh, put it at
   `models/<part>/<part>.visual.glb` (Y-up, PBR materials embedded; see
   the mesh conventions in [Parts](../design/parts.md)) and point the
   visual at it with
   `<xacro:part_visual mesh="package://bluerobotics_parts/models/<part>/<part>.visual.glb"/>`.
2. Add the include line to `urdf/parts.xacro` (alphabetical) and, if the
   part belongs in a slot, add its type to that slot's `accepts` (and
   `default` if it is the usual occupant) in the carrying part's `_info`.
3. Verify: `colcon build --packages-select bluerobotics_parts`, then the
   probe and the review world:
   ```bash
   PARTS=$(ros2 pkg prefix --share bluerobotics_parts)
   xacro $PARTS/urdf/part_probe.urdf.xacro part:=<part> > /tmp/probe.urdf && check_urdf /tmp/probe.urdf
   ros2 run bluerobotics_parts parts_check_world.py --out $PARTS/worlds/parts_check.sdf
   gz sim $PARTS/worlds/parts_check.sdf      # right click a part: View > Collisions / Inertia / Center of Mass
   ```
4. Commit the macro (and the regenerated `worlds/parts_check.sdf`).

## Where a part goes

- **In a slot**: list its type in the slot's `accepts`; users fit it with
  `{slot: <slot>, type: <part>}`, or automatically if it is the `default`.
- **Free placed**: nothing to declare; users give `xyz`/`rpy`.
- **As a slot provider**: declare slots in its `_info` (the Ping bracket
  declares `ping`; a battery bay would declare `battery`).
