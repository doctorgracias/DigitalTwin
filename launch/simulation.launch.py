"""
simulation.launch.py — Запускает Gazebo с миром лаборатории и brain_node.

Использование:
  ros2 launch lab_digital_twin simulation.launch.py

Опциональные аргументы:
  world:=<путь>       — переопределить world-файл
  gui:=false          — запустить Gazebo без GUI (headless)
  verbose:=true       — подробный вывод Gazebo
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:

    # ------------------------------------------------------------------
    # Пути к пакетам
    # ------------------------------------------------------------------
    pkg_share = get_package_share_directory("lab_digital_twin")
    gazebo_ros_share = get_package_share_directory("gazebo_ros")

    default_world_path = os.path.join(pkg_share, "worlds", "lab_scene.world")

    # Путь к папке с моделями — передаём в Gazebo через переменную окружения
    models_path = os.path.join(pkg_share, "models")

    # ------------------------------------------------------------------
    # Аргументы запуска (можно переопределить из командной строки)
    # ------------------------------------------------------------------
    world_arg = DeclareLaunchArgument(
        "world",
        default_value=default_world_path,
        description="Полный путь к .world файлу Gazebo",
    )

    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="true",
        description="Запустить Gazebo GUI (true/false)",
    )

    verbose_arg = DeclareLaunchArgument(
        "verbose",
        default_value="false",
        description="Подробный вывод Gazebo",
    )

    # ------------------------------------------------------------------
    # Установка GAZEBO_MODEL_PATH
    # ------------------------------------------------------------------
    # На Windows используем WSL/ament-переменные; на Linux — os.environ
    existing_model_path = os.environ.get("GAZEBO_MODEL_PATH", "")
    os.environ["GAZEBO_MODEL_PATH"] = (
        f"{models_path}:{existing_model_path}"
        if existing_model_path
        else models_path
    )

    # ------------------------------------------------------------------
    # Запуск Gazebo (через стандартный launch из gazebo_ros)
    # ------------------------------------------------------------------
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_share, "launch", "gazebo.launch.py")
        ),
        launch_arguments={
            "world":   LaunchConfiguration("world"),
            "gui":     LaunchConfiguration("gui"),
            "verbose": LaunchConfiguration("verbose"),
        }.items(),
    )

    # ------------------------------------------------------------------
    # Нода brain_node
    # ------------------------------------------------------------------
    brain_node = Node(
        package="lab_digital_twin",
        executable="brain_node",
        name="brain_node",
        output="screen",
        emulate_tty=True,
        parameters=[
            # Можно добавить параметры из YAML:
            # os.path.join(pkg_share, "config", "brain_params.yaml")
        ],
    )

    # ------------------------------------------------------------------
    # Лог-сообщение при старте
    # ------------------------------------------------------------------
    startup_log = LogInfo(
        msg=(
            "\n"
            "╔══════════════════════════════════════════════╗\n"
            "║   Lab Digital Twin — запуск симуляции        ║\n"
            "╚══════════════════════════════════════════════╝\n"
        )
    )

    return LaunchDescription(
        [
            world_arg,
            gui_arg,
            verbose_arg,
            startup_log,
            gazebo_launch,
            brain_node,
        ]
    )
