# Blender assemblies

The modeler's assembly scenes: each vehicle's chassis with its parts (T200 thrusters and props on the BlueROV2, props on the BlueBoat) placed where they sit on the real vehicle. They are the source of truth for the slot poses in the chassis xacros.

| File | Vehicle | Xacro it drives |
|---|---|---|
| `bluerov2_assembly.blend` | BlueROV2 (standard, six thrusters) | `../urdf/bluerov2_chassis.urdf.xacro`: `thruster_N`, `thruster_body_N` |
| `blueboat_assembly.blend` | BlueBoat | `../urdf/blueboat_chassis.urdf.xacro`: `prop_port`, `prop_stbd` |

A change to a part's placement is made in both the `.blend` and the xacro, in the same pull request, so the two never drift apart.

Reading a pose from the scene: take the part instance's translation and rotation relative to the untransformed chassis, and map Blender's axes to the link's (x = −Blender y, y = Blender x, z = Blender z), then apply the datum offset given in the xacro's header. The BlueBoat's current prop poses were read from a glTF export of the assembly (PR #83), with the glTF mapping (x = glTF z, y = glTF x, z = glTF y); read them from this file from now on.

The files are stored with Git LFS and marked lockable, so they check out read-only. Run `git lfs lock <file>` before editing one, and `git lfs unlock <file>` once the change is merged; the lock tells the others the file is being edited, since a `.blend` cannot be merged. Without Git LFS installed you get small pointer files instead; nothing in the build reads these files.
