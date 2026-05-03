"""
setup.py для пакета lab_digital_twin (ament_python).

Ключевые моменты data_files:
  - Все ресурсы (meshes, worlds, models, launch, config) копируются
    в share/<package_name>/... при выполнении `colcon build`.
  - На Windows пути внутри glob/os.path работают корректно,
    но при передаче в ROS2/Gazebo используется forward-slash.
"""

import os
from glob import glob
from setuptools import find_packages, setup

PACKAGE_NAME = "lab_digital_twin"


def collect_files(source_dir: str, dest_prefix: str) -> list[tuple]:
    """
    Рекурсивно собирает все файлы из source_dir и возвращает список
    кортежей (dest_dir, [files]) для data_files.
    """
    result = []
    for root, _dirs, files in os.walk(source_dir):
        if not files:
            continue
        # Относительный путь от корня пакета
        rel_path = os.path.relpath(root, start=".")
        # forward-slash для совместимости
        dest = os.path.join(dest_prefix, rel_path).replace("\\", "/")
        file_paths = [
            os.path.join(root, f).replace("\\", "/") for f in files
        ]
        result.append((dest, file_paths))
    return result


setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        # ----------------------------------------------------------------
        # Обязательные записи ament
        # ----------------------------------------------------------------
        (
            "share/ament_index/resource_index/packages",
            [f"resource/{PACKAGE_NAME}"],
        ),
        (
            f"share/{PACKAGE_NAME}",
            ["package.xml"],
        ),

        # ----------------------------------------------------------------
        # Launch-файлы
        # ----------------------------------------------------------------
        (
            f"share/{PACKAGE_NAME}/launch",
            glob("launch/*.launch.py"),
        ),

        # ----------------------------------------------------------------
        # World-файлы Gazebo
        # ----------------------------------------------------------------
        (
            f"share/{PACKAGE_NAME}/worlds",
            glob("worlds/*.world"),
        ),

        # ----------------------------------------------------------------
        # Meshes (.dae, .stl, .obj и т.д.) — рекурсивно
        # ----------------------------------------------------------------
        *collect_files(
            "models/lab_interior/meshes",
            f"share/{PACKAGE_NAME}/models/lab_interior/meshes",
        ),

        # ----------------------------------------------------------------
        # SDF-модели и model.config — рекурсивно по всей папке models/
        # ----------------------------------------------------------------
        *collect_files(
            "models",
            f"share/{PACKAGE_NAME}/models",
        ),

        # ----------------------------------------------------------------
        # Конфигурационные YAML-файлы (параметры нод)
        # ----------------------------------------------------------------
        (
            f"share/{PACKAGE_NAME}/config",
            glob("config/*.yaml"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,

    # ----------------------------------------------------------------
    # Метаданные пакета
    # ----------------------------------------------------------------
    maintainer="Lab Digital Twin Team",
    maintainer_email="robot@lab.local",
    description="Цифровой двойник лаборатории робототехники (ROS2 Humble + Gazebo)",
    license="MIT",

    # ----------------------------------------------------------------
    # Тесты
    # ----------------------------------------------------------------
    tests_require=["pytest"],

    # ----------------------------------------------------------------
    # Точки входа — исполняемые ноды
    # ----------------------------------------------------------------
    entry_points={
        "console_scripts": [
            # ros2 run lab_digital_twin brain_node
            f"brain_node = {PACKAGE_NAME}.scripts.brain_node:main",
        ],
    },
)
