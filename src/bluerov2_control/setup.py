import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'bluerov2_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['resource/best.pt']),
        ('share/' + package_name, ['resource/calibration_data.json']),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=[
        'setuptools',
        'ultralytics',
        'opencv-python',
        'numpy'
    ],

    zip_safe=True,
    maintainer='adarsh',
    maintainer_email='adarsh@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'motion_controller = bluerov2_control.motion_controller:main',
            'mission_script = bluerov2_control.mission_script:main',
            'docking_p1 = bluerov2_control.docking_p1:main',
            'docking_p2_perception = bluerov2_control.docking_p2_perception:main',
            'docking_p2_controller = bluerov2_control.docking_p2_controller:main',
        ],
    },
)
