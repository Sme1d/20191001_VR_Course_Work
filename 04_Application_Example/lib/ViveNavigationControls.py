#!/usr/bin/python3

# import avango-guacamole libraries
import avango
import avango.daemon
import avango.gua
import avango.script
from lib.Picker import Picker
import math


# import python libraries
import time

# class realizing a navigation on a vive setup
class ViveNavigationControls(avango.script.Script):

    # output field
    sf_output_matrix = avango.gua.SFMatrix4()
    sf_output_matrix.value = avango.gua.make_identity_mat()
    collected_balls = 0
    start_time = None


    def __init__(self):
        self.super(ViveNavigationControls).__init__()
        self.lf_time = time.time()

    # sets the controller nodes to be used for navigation
    def set_nodes(self, scenegraph, navigation_node, head_node, controller1_sensor, controller1_node):
        self.scenegraph = scenegraph
        self.navigation_node = navigation_node
        self.sf_output_matrix.value = self.navigation_node.Transform.value
        self.head_node = head_node
        self.controller1_sensor = controller1_sensor
        self.controller1_node = controller1_node
        self.always_evaluate(True)
        self.start_time = time.time()


    # called every frame because of self.always_evaluate(True)
    # updates sf_output_matrix by processing the inputs
    def get_y_rotation(self,node):
        quaternion = node.Transform.value.get_rotate()
        y_angle = math.degrees(2.0 * math.acos(quaternion.w))
        if quaternion.x > 0 and quaternion.y < 0 and quaternion.z < 0 or quaternion.x > 0 and quaternion.y < 0 and quaternion.z >0 or quaternion.x < 0 and quaternion.y < 0 and quaternion.z >0 or quaternion.x < 0 and quaternion.y < 0 and quaternion.z <0:
            y_angle =  -y_angle
        return y_angle

    def evaluate(self):
        now = time.time()
        elapsed = now - self.lf_time
        rocker_value = self.controller1_sensor.Value3.value
        button_value = self.controller1_sensor.Value1.value
        self.lf_time = now
        picker = Picker(self.scenegraph)

        # Check state change
        if button_value != 0.0:
            head_angle = self.get_y_rotation(self.head_node)
            target_position = self.navigation_node.WorldTransform.value * avango.gua.make_rot_mat(head_angle, 0, 1, 0) * avango.gua.make_trans_mat(0,0,-.005) * avango.gua.make_rot_mat(-head_angle, 0, 1, 0)
            starting_position = self.navigation_node.WorldTransform.value
            direction = target_position.get_translate() - starting_position.get_translate()
            normalized_direction=direction
            normalized_direction.normalize()
            horizontal_pick = picker.compute_pick_result(starting_position.get_translate(), normalized_direction, direction.length(), ['ball'])

            if not horizontal_pick:
                self.sf_output_matrix.value = target_position

        # Rocker Button
        if rocker_value!=0.0:
            pointer_position = self.controller1_node.WorldTransform.value.get_translate()
            head_position = self.head_node.WorldTransform.value.get_translate()
            pointer_direction=pointer_position-head_position
            pointer_direction *= 0.01


            starting_position = self.scenegraph['/navigation_node'].WorldTransform.value
            target_position = self.sf_output_matrix.value * avango.gua.make_trans_mat(pointer_direction.x,0,pointer_direction.z)
            direction = target_position.get_translate() - starting_position.get_translate()
            normalized_direction=direction
            normalized_direction.normalize()
            horizontal_pick = picker.compute_pick_result(starting_position.get_translate(), normalized_direction, direction.length(), ['ball'])

            if not horizontal_pick:
                self.sf_output_matrix.value = target_position

        # Height alignment
        vertical_pick = picker.compute_pick_result(self.scenegraph['/navigation_node'].WorldTransform.value.get_translate(), avango.gua.Vec3(0, -1, 0), 20, ['invisible'])

        if vertical_pick and vertical_pick.Object.value.Name.value == 'ball':
            vertical_pick.Object.value.Tags.value.append('invisible')
            self.collected_balls += 1
            if self.collected_balls >= 6:
                print("Task completed in", time.time()-self.start_time,"seconds")
        elif vertical_pick and vertical_pick.Distance.value <= 2:
            self.sf_output_matrix.value *= avango.gua.make_trans_mat(0,0.005,0) 
            self.falling_velocity = 0
        else:
            self.falling_velocity += 0.000007
            self.sf_output_matrix.value *= avango.gua.make_trans_mat(0,-self.falling_velocity,0)