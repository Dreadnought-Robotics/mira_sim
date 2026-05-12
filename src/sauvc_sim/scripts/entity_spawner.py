#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from ros_gz_interfaces.srv import SpawnEntity
from ros_gz_interfaces.msg import EntityFactory
from geometry_msgs.msg import Pose, Point, Quaternion
import random
import os
import time
from ament_index_python.packages import get_package_share_directory


class EntitySpawner(Node):
    def __init__(self):
        super().__init__('entity_spawner')
        
        # Create service client for spawning entities
        self.spawn_client = self.create_client(SpawnEntity, '/world/pool_world/create')
        
        # Wait for service to be available
        while not self.spawn_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for spawn service...')
        
        self.get_logger().info('Spawn service is ready!')
        
        # Define fixed drum positions from original world file
        self.drum_positions = [
            (-3.0, 10.0, -2.2),   # Position 0
            (-1.0, 10.0, -2.2),   # Position 1
            (1.0, 10.0, -2.2),    # Position 2
            (3.0, 10.0, -2.2),    # Position 3
        ]
        
        # Store gate position for orange flare alignment
        self.gate_x_position = None
        
        # Define entity configurations with customizable spawn ranges
        # Format: (model_name, count, x_range, y_range, z_offset)
        self.entity_configs = [
            # Gate - spawn first to get x position
            ('gate', 1, (0, 22), (-0.5, -0.5), -2.2),
            
            # Orange flare - will be adjusted after gate spawn
            ('orange_flare', 1, (-3, 25), (-8.5, -4.5), -2.2),
            
            # Other flares - spawn scattered around pool
            ('yellow_flare', 1, (4, 24), (0, 12), -2.2),
            ('blue_flare', 1, (4, 24), (0, 12), -2.2),
            ('red_flare', 1, (4, 24), (0, 12), -2.2),
        ]
        
        self.models_path = os.path.join(get_package_share_directory('sauvc_sim'), 'models')
        
    def load_sdf_file(self, model_name):
        """Load SDF file content for a given model"""
        sdf_path = os.path.join(self.models_path, model_name, 'model.sdf')
        
        if not os.path.exists(sdf_path):
            self.get_logger().error(f'SDF file not found: {sdf_path}')
            return None
            
        try:
            with open(sdf_path, 'r') as f:
                return f.read()
        except Exception as e:
            self.get_logger().error(f'Error reading SDF file: {e}')
            return None
    
    def spawn_entity(self, model_name, entity_name, x, y, z, roll=0.0, pitch=0.0, yaw=0.0):
        """Spawn a single entity at specified pose"""
        sdf_content = self.load_sdf_file(model_name)
        
        if sdf_content is None:
            return False
        
        request = SpawnEntity.Request()
        
        # Create EntityFactory message
        entity_factory = EntityFactory()
        entity_factory.name = entity_name
        entity_factory.allow_renaming = False
        entity_factory.sdf = sdf_content
        
        # Set pose
        pose = Pose()
        pose.position = Point(x=x, y=y, z=z)
        pose.orientation = Quaternion(x=0.0, y=0.0, z=0.0, w=1.0)
        entity_factory.pose = pose
        
        entity_factory.relative_to = "world"
        
        request.entity_factory = entity_factory
        
        future = self.spawn_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        
        if future.result() is not None:
            if future.result().success:
                self.get_logger().info(f'Successfully spawned {entity_name} at ({x:.2f}, {y:.2f}, {z:.2f})')
                return True
            else:
                self.get_logger().error(f'Failed to spawn {entity_name}')
                return False
        else:
            self.get_logger().error(f'Service call failed for {entity_name}')
            return False
    
    def spawn_drums_at_fixed_positions(self):
        """Spawn drums at the four fixed positions, with blue drum at random position"""
        # Shuffle positions to randomize drum placement
        positions = self.drum_positions.copy()
        random.shuffle(positions)
        
        # Blue drum gets the first position (random due to shuffle)
        self.get_logger().info('Spawning blue drum...')
        x, y, z = positions[0]
        if self.spawn_entity('blue_drum', 'blue_drum', x, y, z):
            self.get_logger().info(f'Blue drum spawned at position ({x}, {y}, {z})')
        
        time.sleep(0.2)
        
        # Red drums get the remaining three positions
        self.get_logger().info('Spawning 3 red drums...')
        for i in range(3):
            x, y, z = positions[i + 1]
            entity_name = f'red_drum{i}'
            if self.spawn_entity('red_drum', entity_name, x, y, z):
                self.get_logger().info(f'{entity_name} spawned at position ({x}, {y}, {z})')
            time.sleep(0.2)
    
    def spawn_all_entities(self):
        """Spawn all configured entities"""
        spawned_count = 0
        failed_count = 0
        
        # First spawn drums at fixed positions
        self.spawn_drums_at_fixed_positions()
        spawned_count += 4  # 1 blue + 3 red
        
        # Then spawn other entities
        for model_name, count, x_range, y_range, z_offset in self.entity_configs:
            self.get_logger().info(f'Spawning {count} {model_name}(s)...')
            
            for i in range(count):
                # Special handling for orange flare - align x with gate
                if model_name == 'orange_flare' and self.gate_x_position is not None:
                    # Use gate's x position with small tolerance (±2.5m)
                    x = self.gate_x_position + random.uniform(-2.5, 2.5)
                    self.get_logger().info(f'Orange flare x aligned with gate: {x:.2f}')
                else:
                    # Generate random position within specified range
                    x = random.uniform(x_range[0], x_range[1])
                
                y = random.uniform(y_range[0], y_range[1])
                z = z_offset
                
                # Create unique entity name
                entity_name = f'{model_name}_{i}' if count > 1 else model_name
                
                # Spawn the entity
                if self.spawn_entity(model_name, entity_name, x, y, z):
                    spawned_count += 1
                    
                    # Store gate position for orange flare alignment
                    if model_name == 'gate':
                        self.gate_x_position = x
                        self.get_logger().info(f'Gate x position saved: {x:.2f}')
                else:
                    failed_count += 1
                
                # Small delay between spawns to avoid overwhelming Gazebo
                time.sleep(0.2)
        
        self.get_logger().info(f'Spawning complete! Success: {spawned_count}, Failed: {failed_count}')
    
    def spawn_custom_entity(self, model_name, x_range, y_range, z=-2.2, count=1):
        """
        Spawn custom entity with specified ranges
        
        Args:
            model_name: Name of the model to spawn
            x_range: Tuple (min_x, max_x)
            y_range: Tuple (min_y, max_y)
            z: Z coordinate (default: -2.2 for pool floor)
            count: Number of entities to spawn
        """
        for i in range(count):
            x = random.uniform(x_range[0], x_range[1])
            y = random.uniform(y_range[0], y_range[1])
            entity_name = f'{model_name}_custom_{i}' if count > 1 else f'{model_name}_custom'
            self.spawn_entity(model_name, entity_name, x, y, z)
            time.sleep(0.2)


def main(args=None):
    rclpy.init(args=args)
    
    spawner = EntitySpawner()
    
    # Spawn all configured entities
    spawner.spawn_all_entities()
    
    # Example: Spawn additional custom entities
    # spawner.spawn_custom_entity('golf_ball', x_range=(8, 12), y_range=(8, 12), count=3)
    
    # Keep node alive for a bit then shutdown
    time.sleep(1.0)
    spawner.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()