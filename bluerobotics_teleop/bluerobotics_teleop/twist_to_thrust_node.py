# Copyright 2026 Honu Robotics
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Mix a Twist into per thruster Float64 commands through a gain matrix.

The vehicle geometry lives entirely in the mixer parameters (one topic and
one gain per Twist axis per thruster), so the same node teleoperates any
thruster driven vehicle. Safety behavior:

- deadman button: releasing it zeroes every thruster immediately;
- command timeout: a stale /cmd_vel zeroes every thruster;
- EPA (end point adjustment): the thrust ceiling starts at 20% and is
  stepped in 10% increments from the D pad, so full thrust is opt in.
  The D pad is a hat axis on most pads (axis_epa) and a pair of buttons
  on some (btn_epa_up, btn_epa_down); either or both may be mapped;
- 50 Hz republish: latched commands downstream can never go stale.
"""

from geometry_msgs.msg import Twist
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Float64


def mix(gains, twist, ceiling, max_reverse, max_forward):
    """
    Thrust per thruster: the gain weighted Twist, scaled and clamped.

    `gains` is a per thruster list of (linear_x, linear_y, linear_z,
    angular_z) weights; `ceiling` is the EPA scaled forward limit. The
    clamp is against the absolute thruster envelope, not the ceiling, so
    a combined maneuver saturates exactly like the real ESC would.
    """
    lx, ly, lz, az = twist
    return [max(max_reverse,
                min(max_forward,
                    (gx * lx + gy * ly + gz * lz + gyaw * az) * ceiling))
            for gx, gy, gz, gyaw in gains]


def step_epa(current, direction, step, minimum=None):
    """One EPA click: direction +1 raises, -1 lowers, clamped to [step, 1]."""
    floor = step if minimum is None else minimum
    if direction > 0:
        return min(1.0, current + step)
    if direction < 0:
        return max(floor, current - step)
    return current


def epa_click(axis, prev_axis, buttons, prev_buttons):
    """
    Return the EPA click carried by one /joy message: +1, -1 or 0.

    `axis` and `prev_axis` are the hat axis value now and last time (None
    when no axis is mapped); a click is the value changing to beyond +-0.5,
    so a held D pad steps once. `buttons` and `prev_buttons` are (up, down)
    pressed states, a click being the rising edge of either.
    """
    up, down = buttons
    prev_up, prev_down = prev_buttons
    if up and not prev_up:
        return 1.0
    if down and not prev_down:
        return -1.0
    if axis is not None and axis != prev_axis and abs(axis) > 0.5:
        return 1.0 if axis > 0 else -1.0
    return 0.0


class TwistToThrust(Node):
    """The mixer node; all vehicle specifics come from parameters."""

    def __init__(self):
        super().__init__('twist_to_thrust')

        self.declare_parameter('thruster_topics', [''])
        self.declare_parameter('gains_linear_x', [0.0])
        self.declare_parameter('gains_linear_y', [0.0])
        self.declare_parameter('gains_linear_z', [0.0])
        self.declare_parameter('gains_angular_z', [0.0])
        # Unity: the thrusters take a normalized command, so the envelope
        # is the command range itself. The T200 limits live in the model.
        self.declare_parameter('max_thrust_forward', 1.0)
        self.declare_parameter('max_thrust_reverse', -1.0)
        self.declare_parameter('cmd_timeout_sec', 0.5)
        self.declare_parameter('btn_deadman', 5)
        self.declare_parameter('axis_epa', 7)          # -1: no hat axis
        self.declare_parameter('btn_epa_up', -1)       # -1: no button
        self.declare_parameter('btn_epa_down', -1)
        self.declare_parameter('epa_initial', 0.2)
        self.declare_parameter('epa_step', 0.1)

        topics = list(self.get_parameter('thruster_topics').value)
        columns = [list(self.get_parameter(f'gains_{axis}').value)
                   for axis in ('linear_x', 'linear_y', 'linear_z',
                                'angular_z')]
        if not topics or any(len(col) != len(topics) for col in columns):
            raise ValueError(
                'thruster_topics and every gains_* list must have the '
                'same nonzero length')
        self.gains = list(zip(*columns))

        self.max_fwd = self.get_parameter('max_thrust_forward').value
        self.max_rev = self.get_parameter('max_thrust_reverse').value
        self.timeout = self.get_parameter('cmd_timeout_sec').value
        self.btn_deadman = self.get_parameter('btn_deadman').value
        self.axis_epa = self.get_parameter('axis_epa').value
        self.btn_epa_up = self.get_parameter('btn_epa_up').value
        self.btn_epa_down = self.get_parameter('btn_epa_down').value
        self.epa_pct = self.get_parameter('epa_initial').value
        self.epa_step = self.get_parameter('epa_step').value

        self.publishers_ = [self.create_publisher(Float64, topic, 10)
                            for topic in topics]
        self.create_subscription(Twist, 'cmd_vel', self.twist_cb, 10)
        self.create_subscription(Joy, 'joy', self.joy_cb, 10)

        self.last_twist = Twist()
        self.last_twist_time = self.get_clock().now()
        self.deadman_pressed = False
        self.prev_epa_axis = 0.0
        self.prev_epa_buttons = (False, False)

        self.create_timer(0.02, self.timer_cb)

    def twist_cb(self, msg):
        self.last_twist = msg
        self.last_twist_time = self.get_clock().now()

    def joy_cb(self, msg):
        if len(msg.buttons) > self.btn_deadman:
            self.deadman_pressed = bool(msg.buttons[self.btn_deadman])
        # EPA clicks on the D pad edge, active regardless of the deadman.
        axis = (msg.axes[self.axis_epa]
                if 0 <= self.axis_epa < len(msg.axes) else None)
        buttons = tuple(
            0 <= b < len(msg.buttons) and bool(msg.buttons[b])
            for b in (self.btn_epa_up, self.btn_epa_down))
        click = epa_click(axis, self.prev_epa_axis, buttons,
                          self.prev_epa_buttons)
        if click:
            self.epa_pct = step_epa(self.epa_pct, click, self.epa_step)
            self.get_logger().info(f'EPA ceiling: {self.epa_pct:.0%}')
        self.prev_epa_axis = axis
        self.prev_epa_buttons = buttons

    def timer_cb(self):
        age = (self.get_clock().now()
               - self.last_twist_time).nanoseconds * 1e-9
        if not self.deadman_pressed or age > self.timeout:
            self.publish([0.0] * len(self.publishers_))
            return
        twist = (self.last_twist.linear.x, self.last_twist.linear.y,
                 self.last_twist.linear.z, self.last_twist.angular.z)
        ceiling = self.max_fwd * self.epa_pct
        self.publish(mix(self.gains, twist, ceiling,
                         self.max_rev, self.max_fwd))

    def publish(self, values):
        for publisher, value in zip(self.publishers_, values):
            msg = Float64()
            msg.data = float(value)
            publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TwistToThrust()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
