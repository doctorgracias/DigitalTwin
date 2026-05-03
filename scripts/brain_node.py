#!/usr/bin/env python3
"""
brain_node.py — Центральная нода цифрового двойника лаборатории.

Подписки:
  /scan  (sensor_msgs/LaserScan)  — данные лидара для детекции стен

Публикации:
  /cmd_vel (geometry_msgs/Twist)  — команды скорости для мобильной базы

Запуск вручную (после colcon build + source):
  ros2 run lab_digital_twin brain_node
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist


# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------
NODE_NAME       = "brain_node"
SCAN_TOPIC      = "/scan"
CMD_VEL_TOPIC   = "/cmd_vel"
PUBLISH_RATE_HZ = 10          # Гц — частота публикации /cmd_vel
WALL_DISTANCE_M = 0.5         # м — порог обнаружения стены


class BrainNode(Node):
    """
    Центральный управляющий узел.
    Читает данные лазера и отправляет команды скорости.
    """

    def __init__(self) -> None:
        super().__init__(NODE_NAME)

        # ----------------------------------------------------------------
        # QoS — для совместимости с Gazebo-сенсорами
        # ----------------------------------------------------------------
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=10,
        )

        # ----------------------------------------------------------------
        # Подписчик: /scan
        # ----------------------------------------------------------------
        self._scan_sub = self.create_subscription(
            LaserScan,
            SCAN_TOPIC,
            self._scan_callback,
            sensor_qos,
        )

        # ----------------------------------------------------------------
        # Публикатор: /cmd_vel
        # ----------------------------------------------------------------
        self._cmd_pub = self.create_publisher(Twist, CMD_VEL_TOPIC, 10)

        # ----------------------------------------------------------------
        # Таймер публикации команд скорости
        # ----------------------------------------------------------------
        self._timer = self.create_timer(
            1.0 / PUBLISH_RATE_HZ,
            self._publish_cmd_vel,
        )

        # ----------------------------------------------------------------
        # Внутреннее состояние
        # ----------------------------------------------------------------
        self._latest_scan: LaserScan | None = None
        self._wall_detected: bool = False

        self.get_logger().info(
            f"[{NODE_NAME}] Нода инициализирована.\n"
            f"  Слушаю:    {SCAN_TOPIC}\n"
            f"  Публикую:  {CMD_VEL_TOPIC} @ {PUBLISH_RATE_HZ} Гц"
        )

    # ------------------------------------------------------------------
    # Обратный вызов лидара
    # ------------------------------------------------------------------
    def _scan_callback(self, msg: LaserScan) -> None:
        """Принимает LaserScan и проверяет наличие стен."""
        self._latest_scan = msg

        # Минимальная дистанция из всего скана (игнорируем nan/inf)
        valid_ranges = [
            r for r in msg.ranges
            if msg.range_min < r < msg.range_max
        ]

        if valid_ranges:
            min_dist = min(valid_ranges)
            self._wall_detected = min_dist < WALL_DISTANCE_M

            if self._wall_detected:
                self.get_logger().warn(
                    f"[{NODE_NAME}] Стена обнаружена! "
                    f"Мин. дистанция: {min_dist:.3f} м"
                )

    # ------------------------------------------------------------------
    # Публикация /cmd_vel
    # ------------------------------------------------------------------
    def _publish_cmd_vel(self) -> None:
        """
        Публикует команды скорости.
        Сейчас: нулевые команды (шаблон).
        Здесь реализуется логика навигации / объезда препятствий.
        """
        twist = Twist()

        if self._wall_detected:
            # Пример реакции: остановить движение вперёд
            twist.linear.x  = 0.0
            twist.angular.z = 0.0
            self.get_logger().debug(
                f"[{NODE_NAME}] cmd_vel: СТОП (стена рядом)"
            )
        else:
            # TODO: здесь вставить логику движения
            twist.linear.x  = 0.0   # м/с вперёд
            twist.angular.z = 0.0   # рад/с поворот

        self._cmd_pub.publish(twist)


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------
def main(args=None) -> None:
    rclpy.init(args=args)
    node = BrainNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info(f"[{NODE_NAME}] Остановка по Ctrl+C.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
