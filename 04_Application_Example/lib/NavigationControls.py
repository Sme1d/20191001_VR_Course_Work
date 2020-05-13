#!/usr/bin/python3

# import avango-guacamole libraries
import avango
import avango.daemon
import avango.gua
import avango.script

# import python libraries
import random
import statistics
import time
from lib.Picker import Picker


# class realizing a spacemouse navigation on a desktop setup
class NavigationControls(avango.script.Script):
    collected_balls = 0
    start_time = None

    # input fields
    sf_input_x = avango.SFFloat()
    sf_input_x.value = 0.0

    sf_input_y = avango.SFFloat()
    sf_input_y.value = 0.0

    sf_input_z = avango.SFFloat()
    sf_input_z.value = 0.0

    sf_input_rx = avango.SFFloat()
    sf_input_rx.value = 0.0

    sf_input_ry = avango.SFFloat()
    sf_input_ry.value = 0.0

    sf_input_rz = avango.SFFloat()
    sf_input_rz.value = 0.0 

    # Storing velocity for rate control
    velocity = avango.gua.Vec3(0.0, 0.0, 0.0)
    rotation_velocity = avango.gua.Vec3(0.0, 0.0, 0.0)

    # Falling velocity
    falling_velocity = 0

    # output matrix for the figure
    sf_output_matrix = avango.gua.SFMatrix4()
    sf_output_matrix.value = avango.gua.make_identity_mat()

    sf_rotation_output_matrix = avango.gua.SFMatrix4()
    sf_rotation_output_matrix.value = avango.gua.make_identity_mat()

    def __init__(self):
        self.super(NavigationControls).__init__()
        self.scenegraph = None
        self.static_user_height = 2.0
        self.lf_time = time.time()
        self.connect_input_sensors()
        self.start_time = time.time()

    # establishes the connection to the devices registered in the daemon
    def connect_input_sensors(self):
        self.device_service = avango.daemon.DeviceService()
        self.space_navigator_sensor = avango.daemon.nodes.DeviceSensor(
            DeviceService=self.device_service)
        self.space_navigator_sensor.Station.value = 'gua-device-space'
        self.sf_input_x.connect_from(
            self.space_navigator_sensor.Value0)
        self.sf_input_y.connect_from(
            self.space_navigator_sensor.Value2)
        self.sf_input_z.connect_from(
            self.space_navigator_sensor.Value1)
        self.sf_input_rx.connect_from(
            self.space_navigator_sensor.Value3)
        self.sf_input_ry.connect_from(
            self.space_navigator_sensor.Value4)
        self.sf_input_rz.connect_from(
            self.space_navigator_sensor.Value5)

    # sets the scenegraph used for ground following
    def set_scenegraph(self, scenegraph):
        self.scenegraph = scenegraph
        self.always_evaluate(True)

    # called every frame because of self.always_evaluate(True)
    # updates sf_output_matrix by processing the inputs
    def evaluate(self):
        now = time.time()
        picker = Picker(self.scenegraph)
        temporary_sf_output_matrix_value = self.sf_output_matrix.value

        elapsed = now - self.lf_time
        self.lf_time = now
        
        # Height alignment
        vertical_pick = picker.compute_pick_result(self.scenegraph['/navigation_node/avatar'].WorldTransform.value.get_translate(), avango.gua.Vec3(0, -1, 0), 100, ['invisible'])

        self.climbing_lock = False 
        if vertical_pick and vertical_pick.Object.value.Name.value == 'ball':
            #Checking balls
            vertical_pick.Object.value.Tags.value.append('invisible')
            self.collected_balls += 1
            if self.collected_balls >= 6:
                print("Task completed in", time.time()-self.start_time,"seconds")
        elif vertical_pick and vertical_pick.Distance.value < 2:
            #Climb
            temporary_sf_output_matrix_value *= avango.gua.make_trans_mat(0,.01,0) 
            self.falling_velocity = 0
            self.climbing_lock = True
        else: 
            #Fall
            self.falling_velocity += 0.00005
            temporary_sf_output_matrix_value *= avango.gua.make_trans_mat(0,-self.falling_velocity,0)
        
        
        self.velocity.x = self.sf_input_x.value * .000025
        self.velocity.z = self.sf_input_z.value * .000025

        starting_position = self.scenegraph['/navigation_node/avatar'].WorldTransform.value 
        target_movement = avango.gua.make_trans_mat(self.velocity.x, 0, self.velocity.z)
        target_position = starting_position * target_movement
        direction = target_position.get_translate() - starting_position.get_translate()
        normalized_direction=direction
        normalized_direction.normalize()
        horizontal_pick = picker.compute_pick_result(starting_position.get_translate(), normalized_direction, 10.0, ['ball'])

        if not horizontal_pick or horizontal_pick.Distance.value > .5:
            if not self.climbing_lock:
                temporary_sf_output_matrix_value *= target_movement
            self.sf_output_matrix.value = temporary_sf_output_matrix_value 
        
        self.rotation_velocity.y = self.sf_input_ry.value * -0.0005
        rx_rotation = self.sf_input_rx.value * (90/350) - 25
        self.sf_rotation_output_matrix.value = avango.gua.make_rot_mat(rx_rotation, 1, 0, 0) 
        self.sf_output_matrix.value *= avango.gua.make_rot_mat(self.rotation_velocity.y,0,1,0)



        # Ball check
        
