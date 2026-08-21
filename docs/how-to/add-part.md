# Add a part

A part is one file, `bluerobotics_parts/urdf/<part>.urdf.xacro`, holding a
metadata macro (`<part>_info`) and the macro that instantiates it; the full
contract is in [Parts](../design/parts.md). There are two ways to write it.

## From a modeler's SDF delivery

The modeler delivers `models/<part>/<part>.visual.glb` (PBR materials
embedded, Y-up as the glTF specification requires) and
`models/<part>/model.sdf` (the collision primitives), following the rules in
[Parts](../design/parts.md). If the mesh shows rolled 90 degrees in RViz but
fine in Gazebo, it was exported Z-up: run
`ros2 run bluerobotics_parts gltf_to_yup.py models/<part>/<part>.visual.glb`
once. Then:

1. Look at the delivery in Gazebo: scale, origin at the mesh centroid, x
   forward / y left / z up, materials, collision envelope.
   ```bash
   gz sim models/<part>/model.sdf
   ```
2. Bootstrap the macro. Inertia is estimated from the collision primitives
   (SDF auto inertia at a uniform density, scaled to `--mass` if known);
   slots, frames, the attach offset and a spin axis are seeded from flags:
   ```bash
   ros2 run bluerobotics_parts sdf_to_part.py models/<part> --mass 0.344 \
       --attach "0 0 -0.05" \
       --slot "sensor=0,0,-0.01;accepts=ping_singlebeam;default=ping_singlebeam" \
       --frame beam=0,0,-0.044
   ```
   The tool writes `urdf/<part>.urdf.xacro` once and refuses to overwrite it
   without `--force`: from here on the file is source, edit it by hand.
3. Add the include line to `urdf/parts.xacro` (alphabetical) and, if the
   part belongs in a slot, add its type to that slot's `accepts` (and
   `default` if it is the usual occupant) in the carrying part's `_info`.
4. Verify: `colcon build --packages-select bluerobotics_parts`, then the
   probe and the review world:
   ```bash
   PARTS=$(ros2 pkg prefix --share bluerobotics_parts)
   xacro $PARTS/urdf/part_probe.urdf.xacro part:=<part> > /tmp/probe.urdf && check_urdf /tmp/probe.urdf
   ros2 run bluerobotics_parts parts_check_world.py --out $PARTS/worlds/parts_check.sdf
   gz sim $PARTS/worlds/parts_check.sdf      # right click a part: View > Collisions / Inertia / Center of Mass
   ```
5. Commit the macro (and the regenerated `worlds/parts_check.sdf`).

## By hand

No SDF needed: write the file. A minimal part, a 10 cm box of 0.5 kg with
one slot on top:

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://ros.org/wiki/xacro">

  <xacro:macro name="my_box_info">
    <xacro:property name="part_info" scope="parent" value="${dict(
        attach='0 0 -0.05',
        axis='0 0 1',
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
so the box stands on whatever it is mounted to). Then steps 3 to 5 above.

## Where a part goes

- **In a slot**: list its type in the slot's `accepts`; users fit it with
  `{slot: <slot>, type: <part>}`, or automatically if it is the `default`.
- **Free placed**: nothing to declare; users give `xyz`/`rpy`.
- **As a slot provider**: declare slots in its `_info` (the Ping bracket
  declares `ping`; a battery bay would declare `battery`).
