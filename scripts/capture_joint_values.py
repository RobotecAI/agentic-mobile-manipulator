import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class JointStateListener(Node):
    def __init__(self):
        super().__init__("joint_state_listener")
        self.subscription = self.create_subscription(
            JointState, "/joint_states", self.listener_callback, 10
        )

    def listener_callback(self, msg):
        joint_dict = {name: pos for name, pos in zip(msg.name, msg.position)}
        print(
            "{\n"
            + ",\n".join([f'    "{k}": {v}' for k, v in joint_dict.items()])
            + "\n}"
        )
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = JointStateListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
