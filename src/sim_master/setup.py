from setuptools import find_packages, setup

package_name = 'sim_master'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='adarsh',
    maintainer_email='adarsh@todo.todo',
    description='Simulator bridge: /master/commands -> /bluerov2/thrusters',
    license='TODO',
    entry_points={
        'console_scripts': [
            'sim_bridge = sim_master.sim_bridge:main',
        ],
    },
)
