# Copyright 2024-2026 NXP
# Copyright 2016 Open Source Robotics Foundation, Inc.
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

import rclpy
from rclpy.node import Node
import time
import math
from sensor_msgs.msg import Joy, LaserScan
from std_msgs.msg import String
from synapse_msgs.msg import EdgeVectors, ServerCommunication

QOS_PROFILE_DEFAULT = 10
PI = math.pi

# STEEER CONFIGURATION
class SteerConfig:
    STEER_LEFT_STEEP = 0.55
    STEER_LEFT_MEDIUM = 0.45
    STEER_LEFT_GENTLE = 0.25
    STEER_LEFT_FALLBACK = 0.40
    
    STEER_RIGHT_STEEP = -0.55
    STEER_RIGHT_MEDIUM = -0.45
    STEER_RIGHT_GENTLE = -0.25
    STEER_RIGHT_FALLBACK = -0.35

# CONTROL BOUNDS
SPEED_MIN = 0.0
SPEED_MAX = 2.0
TURN_MIN = -0.8
TURN_MAX = 0.6

FRONT_WARNING_DISTANCE = 1.6
FRONT_OBSTACLE_DISTANCE = 0.8

SLOPE_THRESHOLD = 25

# TURN TIMING CONFIGURATION  
class TurnConfig:
    HARD_STEER_TIME = 0.35
    RECOVERY_DURATION = 0.1
    STEEP_STEER_TIME = 0.35
    PRE_TURN_DURATION = 0.6

# DEFAULT VALUES
class DefaultConfig:
    TURN_SPEED_RECOVERY = 0.70
    TURN_SPEED_SINGLE_VECTOR = 0.60
    TURN_SPEED_NORMAL = 0.50
    TURN_SPEED_CRUISE = 0.75
    TURN_DURATION_DEFAULT = (0.7, 1.3)
    MIN_LANE_WIDTH = 55.0
    SECONDARY_SPEED = 0.35

    LANE_MAX_SPEED = 1.20
    LANE_MIN_SPEED = 0.45
    SPEED_REDUCTION_FACTOR = 0.45

    LANE_WIDTH_MIN_CHECK = 20

    TURN_STEER_Y = 0.6
    TURN_STEER_Z = 0.6
    TURN_DURATION_Y = 0.9
    TURN_DURATION_Z = 1.0

    BLEND_HOLD_TIME = 0.25
    BLEND_FULL_TIME = 0.30

# CONFIGURATION:
# The buggy is driven in manual mode by publishing standard controller Joy messages to /cerebri/in/joy.
# The layout is: msg.axes = [0.0, speed, 0.0, turn]
# - speed: positive for forward, negative for reverse. Range: [-1.0, 1.0]
# - turn: positive for left steer, negative for right steer. Range: [-1.0, 1.0]
# msg.buttons = [1, 0, 0, 0, 0, 0, 0, 1] (Keep buttons set to this pattern for manual override mode)

class LineFollower(Node):
    """
    Core controller Node for the B3RB buggy.
    By default, it publishes a safe drive-straight command on a timer loop.
    Implement logic inside the callbacks to steer, dodge obstacles, detect destinations,
    communicate with the server, and park.
    """
    def __init__(self):
        print("SOURCE FILE MODIFIED", flush=True)
        super().__init__('line_follower')

        # ---- Unified State Machine ----
        class State:
            LANE_FOLLOW = "lane_follow"
            WAIT_INTERSECTION = "wait_intersection"
            TURN = "turn"
            RECOVERY = "recovery"
            MISSION_COMPLETE = "mission_complete"
            WAIT_SERVER = "wait_server"

        self.State = State
        self.state = State.LANE_FOLLOW
        

        # ------------------ Subscriptions ------------------
        
        # 1. Lane Edge Vectors (from edge_vectors_publisher)
        self.subscription_vectors = self.create_subscription(
            EdgeVectors,
            '/edge_vectors',
            self.edge_vectors_callback,
            QOS_PROFILE_DEFAULT)

        # 2. LIDAR Obstacle Scanner
        self.subscription_lidar = self.create_subscription(
            LaserScan,
            '/scan',
            self.lidar_callback,
            QOS_PROFILE_DEFAULT)

        # 3. Server Communication Feedback Loop
        self.subscription_server = self.create_subscription(
            ServerCommunication,
            '/ServerCommunication',
            self.server_communication_callback,
            QOS_PROFILE_DEFAULT)

        # 4. QR Code Detections (from qr_detector)
        self.subscription_qr = self.create_subscription(
            String,
            '/qr_detection',
            self.qr_detection_callback,
            QOS_PROFILE_DEFAULT)

        # 5. Sign Board Detections (from object_recognizer)
        self.subscription_signs = self.create_subscription(
            String,
            '/sign_board_detection',
            self.sign_board_callback,
            QOS_PROFILE_DEFAULT)


        self.current_board = {}

        self.current_patient = None
        # ------------------ Publishers ------------------
        
        # Publisher to drive/steer the buggy
        self.publisher_joy = self.create_publisher(
            Joy,
            '/cerebri/in/joy',
            QOS_PROFILE_DEFAULT)

        # Publisher to send messages to the Server
        self.publisher_server = self.create_publisher(
            ServerCommunication,
            '/ServerCommunication',
            QOS_PROFILE_DEFAULT)
        # ------------------ State Variables & Timer ------------------
        
        self.last_turn = 0.0

        # Last steering command issued during a TURN — used as the no-vector fallback
        # so turn logic is decoupled from the publisher's self.target_turn value.
        self.last_turn_command = 0.0
        self.recovery_slopes = []

        # Default controls: drive straight slowly
        self.target_speed = 0.15
        self.target_turn = 0.0

        # ---------- Line Following Parameters ----------

        # Cruise speed while following the lane
        self.cruise_speed = 0.90

        # PID gains (start with only P)
        self.Kp = 0.006
        self.Kd = 0.002

        # PID state
        self.prev_error = 0.0
        self.integral = 0.0

        # Image information
        self.image_center = 0.0

        # Latest lane information
        self.lane_center = 0.0
        # Smoothed lane center
        self.filtered_lane_center = 0.0
        self.error = 0.0

        # Last measured lane width (pixels)
        self.lane_width_px = 0.0

        self.last_two_vector_center = 0.0
        self.one_vector_start_time = None

        # State variables (You can add your own state flags / state machines here)
        self.obstacle_in_front = False
        self.patient_id = None
        self.hospital_id = None
        self.current_destination = "X"
        self.current_patient = self.current_destination
        self.mission_completed = False
        self.mission_active = True

        self.get_logger().info(
            f"START DESTINATION = {self.current_destination}"
        )

        self.pause_start_time = None
        self.pause_duration = 1.0
        self.waiting_for_destination = False

        self.intersection_frames = 0
        # ---------- Server Communication ----------

        self.server_message_uid = None
        self.last_server_message = ""
        self.last_ack_uid = None

        # Buggy's rolling message UID (0-255)
        self.buggy_uid = 0

        #LIDAR
        self.lidar_override = False
        self.lidar_offset = 0.0
        self.lidar_override_steer = None

        self.lidar_enabled = True
        self.turn_recovery_frames = 0

        self.avoid_direction = None

        self.recovery_start_time = None
        self.recovery_duration = 0.1


        #turns in sign detect
        self.turn_direction = None
        self.turn_start_time = None
        self.pre_turn_start = None
        self.pre_turn_steer = 0.0




        self.turn_offset = 0

        self.turn_table = {
            "X": (DefaultConfig.TURN_SPEED_CRUISE, 1.0),
            "Y": (DefaultConfig.TURN_STEER_Y, DefaultConfig.TURN_DURATION_Y),
            "Z": (DefaultConfig.TURN_STEER_Z, DefaultConfig.TURN_DURATION_Z),
        }

        # Timer to publish drive commands at 10Hz
        self.control_timer = self.create_timer(0.1, self.publish_drive_commands)

        self.get_logger().info("Line Follower controller initialized. Safe Drive-Straight Mode active.")

    def publish_drive_commands(self):
        """Timer callback that periodically publishes the current speed and steer command."""
        msg = Joy()
        msg.buttons = [1, 0, 0, 0, 0, 0, 0, 1]  # Manual override button configuration
        msg.axes = [0.0, self.target_speed, 0.0, self.target_turn]
        self.publisher_joy.publish(msg)

    def rover_move_manual_mode(self, speed, turn):
        """Helper to immediately set control speed and steering angle."""
        self.target_speed = float(max(min(speed, SPEED_MAX), -SPEED_MAX))
        self.target_turn = float(max(min(turn, TURN_MAX), -TURN_MAX))

    # ------------------ Callback Implementations ------------------

    def edge_vectors_callback(self, message):
        """
        Receives lane boundaries from the camera vector extractor.
        
        GUIDELINE (Lane Following):
        - `message.vector_count` contains the number of active bounds seen (0, 1, or 2).
        - `message.vector_1` and `message.vector_2` contain the points defining the bounds.
        - You need to write logic to compute the centerline deviation and adjust `self.target_turn`.
        - E.g., if only one line is seen, steer away from it to keep distance; if two lines are seen,
          calculate the midpoint relative to the image width and steer to center the buggy.
        """
        # HINTS:
        # width = message.image_width
        # half_width = width / 2.0
        # For now, we do not modify self.target_turn so the buggy continues straight.

        # Hold the buggy stopped for the rest of the mission.
        if self.state == self.State.MISSION_COMPLETE:
            self.rover_move_manual_mode(0.0, 0.0)
            return

        if self.state == self.State.WAIT_SERVER:

            self.rover_move_manual_mode(
                0.0,
                0.0
            )

            return

        if self.state == "PRE_TURN":

            elapsed = time.time() - self.pre_turn_start

            if elapsed < TurnConfig.PRE_TURN_DURATION:

                self.rover_move_manual_mode(
                    self.target_speed,
                    self.pre_turn_steer
                )

                return

            self.state = self.State.TURN
            self.turn_start_time = time.time()
            self.pre_turn_start = None

            self.get_logger().info(
                f"STATE -> {self.state}"
            )

        if self.state == self.State.TURN:

            elapsed = time.time() - self.turn_start_time

            hard_steer_time = TurnConfig.HARD_STEER_TIME
            dx_available = False

            _, duration = self.turn_table.get(
                self.current_patient,
                DefaultConfig.TURN_DURATION_DEFAULT
            )

            image_center = message.image_width / 2.0

            # Default target: image centre
            desired_center = image_center

            # Guard against stale / zero lane width
            lane_half = (
                self.lane_width_px / 2.0
                if self.lane_width_px > DefaultConfig.LANE_WIDTH_MIN_CHECK
                else DefaultConfig.MIN_LANE_WIDTH
            )

            # LEFT TURN: track the leftmost visible edge + half lane width
            if self.turn_direction == "left" and message.vector_count >= 1:

                left_edge = min(
                    (
                        (message.vector_1[0].x + message.vector_1[1].x) / 2.0,
                        (message.vector_2[0].x + message.vector_2[1].x) / 2.0
                    )[:message.vector_count]
                )

                desired_center = left_edge + lane_half

            # RIGHT TURN: track the rightmost visible edge - half lane width
            elif self.turn_direction == "right" and message.vector_count >= 1:

                right_edge = max(
                    (
                        (message.vector_1[0].x + message.vector_1[1].x) / 2.0,
                        (message.vector_2[0].x + message.vector_2[1].x) / 2.0
                    )[:message.vector_count]
                )

                desired_center = right_edge - lane_half

            # STRAIGHT: keep image centre
            elif self.turn_direction == "straight":

                desired_center = image_center

            lane_center = self.calculate_lane_center(message)
            error = desired_center - lane_center
            pid_correction = self.compute_pid(error)

            self.get_logger().info(
                f"TURN={self.turn_direction} "
                f"VECTORS={message.vector_count} "
                f"DESIRED={desired_center:.1f} "
                f"LANE={lane_center:.1f} "
                f"ERROR={error:.1f} "
                f"PID={pid_correction:.3f} "
                f"GOOD={self.turn_recovery_frames}"
            )

            # Extract the single visible edge x-position (used below for 1-vector fallback)
            edge_x = None

            if message.vector_count == 1:
                dx, dy = self.get_vector_slope(message.vector_1)
                dx_available = True

                edge_x = (
                    message.vector_1[0].x +
                    message.vector_1[1].x
                ) / 2.0

            image_center = message.image_width / 2.0

            # Classify which side the single visible edge is on
            current_side = None

            if message.vector_count == 1:
                self.get_logger().info(
                    f"EDGE={edge_x:.1f} DX={dx:.1f} DY={dy:.1f}"
                )

                if dx > SLOPE_THRESHOLD:
                    current_side = "right"
                elif dx < -SLOPE_THRESHOLD:
                    current_side = "left"
                else:
                    # Line nearly vertical — fall back to midpoint position
                    if edge_x < image_center:
                        current_side = "left"
                    else:
                        current_side = "right"

            # Debug: log current edge side
            self.get_logger().info(
                f"CUR={current_side}"
            )

            # --- Vector-count-aware steering ---
            if self.turn_direction == "left":

                if message.vector_count == 2:

                    steer = SteerConfig.STEER_LEFT_STEEP + pid_correction

                elif message.vector_count == 1:

                    if current_side == "right":
                        steer = SteerConfig.STEER_LEFT_MEDIUM

                    elif current_side == "left":
                        steer = SteerConfig.STEER_LEFT_GENTLE

                    else:
                        steer = SteerConfig.STEER_LEFT_FALLBACK

                else:

                    if elapsed < hard_steer_time:

                        steer = SteerConfig.STEER_LEFT_STEEP

                    elif abs(self.last_turn_command) > 0.1:

                        steer = self.last_turn_command

                    else:

                        steer = DefaultConfig.SECONDARY_SPEED

            elif self.turn_direction == "right":

                if message.vector_count == 2:

                    steer = SteerConfig.STEER_RIGHT_STEEP + pid_correction

                elif message.vector_count == 1:

                    if current_side == "left":
                        steer = SteerConfig.STEER_RIGHT_MEDIUM

                    elif current_side == "right":
                        steer = SteerConfig.STEER_RIGHT_GENTLE

                    else:
                        steer = SteerConfig.STEER_RIGHT_FALLBACK

                else:

                    if elapsed < hard_steer_time:

                        steer = SteerConfig.STEER_RIGHT_STEEP

                    elif abs(self.last_turn_command) > 0.1:

                        steer = self.last_turn_command

                    else:

                        steer = DefaultConfig.SECONDARY_SPEED

            else:

                steer = pid_correction

            if message.vector_count == 0:
                turn_speed = DefaultConfig.TURN_SPEED_RECOVERY
            elif message.vector_count == 1:
                turn_speed = DefaultConfig.TURN_SPEED_SINGLE_VECTOR
            else:
                turn_speed = DefaultConfig.TURN_SPEED_NORMAL

            # Save before publishing so the no-vector fallback always has a fresh value
            self.last_turn_command = steer
            self.rover_move_manual_mode(turn_speed, steer)

            # Emergency timeout: never turn longer than duration + 2s
            max_turn_time = duration + 1.0

            # Count consecutive 2-vector frames; reset on any bad frame
            if message.vector_count == 2:
                self.turn_recovery_frames += 1
            else:
                self.turn_recovery_frames = 0

            # Exit turn: 3 consecutive good frames OR emergency timeout
            turn_done = self.turn_recovery_frames >= 5
            emergency = elapsed > max_turn_time

            if turn_done or emergency:
                self.get_logger().info(
                    "TURN FINISHED"
                )
                if emergency:
                    self.get_logger().warn(
                        f"TURN EMERGENCY TIMEOUT {elapsed:.2f}s "
                        f"(max={max_turn_time:.1f}s)"
                    )
                self.get_logger().info(
                    f"{self.current_patient}: completed "
                    f"{self.turn_direction.upper()} turn "
                    f"({elapsed:.2f}s, {self.turn_recovery_frames} good frames)"
                )


                self.turn_direction = None
                self.turn_recovery_frames = 0
                self.turn_offset = 0


                # Enter recovery mode — LiDAR stays OFF
                self.lidar_enabled = False
                self.recovery_slopes.clear()
                self.state = self.State.RECOVERY
                self.get_logger().info(
                    f"STATE -> {self.state}"
                )
                self.recovery_start_time = time.time()

            self.get_logger().info(
                f"TURN={self.turn_direction} "
                f"V={message.vector_count} "
                f"SIDE={current_side} "
                f"STEER={steer:.2f} "
                f"DX={dx if message.vector_count == 1 else 'NA'}"
            )
            return

        if self.state == self.State.RECOVERY:

            recovery_elapsed = (
                time.time() - self.recovery_start_time
            )

            if recovery_elapsed < self.recovery_duration:

                self.lidar_enabled = False

                # No vectors: go straight
                if message.vector_count == 0:

                    self.rover_move_manual_mode(
                        DefaultConfig.TURN_SPEED_RECOVERY,
                        0.0
                    )

                    return

                # One vector: use slope
                elif message.vector_count == 1:

                    dx, dy = self.get_vector_slope(
                        message.vector_1
                    )

                    self.recovery_slopes.append(dx)

                    if len(self.recovery_slopes) > 4:
                        self.recovery_slopes.pop(0)

                    avg_dx = sum(self.recovery_slopes) / len(
                        self.recovery_slopes
                    )

                    steer = avg_dx / 250.0

                    steer = max(
                        -0.7,
                        min(0.7, steer)
                    )

                    self.last_turn_command = steer

                    self.rover_move_manual_mode(
                        DefaultConfig.TURN_SPEED_CRUISE,
                        steer
                    )

                    self.get_logger().info(
                        f"DX={dx:.1f} AVG={avg_dx:.1f} STEER={steer:.2f}"
                    )

                    return

                # Exit immediately if lane found again
                if message.vector_count == 2:

                    self.state = self.State.LANE_FOLLOW
                    self.lidar_enabled = True
                    self.filtered_lane_center = 0.0
                    self.turn_offset = 0

                    self.get_logger().info(
                        "RECOVERY EXIT: TWO VECTORS"
                    )

                    self.get_logger().info(
                        f"STATE -> {self.state}"
                    )

                    return

            if recovery_elapsed > self.recovery_duration:

                self.state = self.State.LANE_FOLLOW
                self.lidar_enabled = True
                self.filtered_lane_center = 0.0
                self.turn_offset = 0

                self.get_logger().info(
                    "RECOVERY EXIT: TIMEOUT"
                )

                self.get_logger().info(
                    f"STATE -> {self.state}"
                )

                return

        # No lane detected
        if self.state == self.State.WAIT_INTERSECTION:

            if message.vector_count !=2:
                self.intersection_frames += 1
            else:
                self.intersection_frames = 0

            if self.intersection_frames >= 3:

                self.get_logger().info(
                    f"state={self.state}"
                )

                self.get_logger().info(
                    f"frames={self.intersection_frames}"
                )

                self.get_logger().info(
                    f"patient={self.current_patient}"
                )

                self.get_logger().info(
                    f"board={self.current_board}"
                )

                self.get_logger().info(
                    f"vectors={message.vector_count}, frames={self.intersection_frames}"
                )
                                
                direction = self.decide_turn()

                if direction is not None:

                    self.get_logger().info(
                        f"Intersection reached. Turn: {direction}"
                    )
                    self.lidar_enabled = False
                    self.get_logger().info(
                        f"LIDAR DISABLED: {self.lidar_enabled}"
                    )

                    self.turn_direction = direction
                    self.pre_turn_start = time.time()
                    self.state = "PRE_TURN"

                    self.get_logger().info(
                        f"STATE -> {self.state}"
                    )

                    turn_steer, _ = self.turn_table[self.current_patient]

                    if direction == "left":
                        self.pre_turn_steer = turn_steer / 4

                    elif direction == "right":
                        self.pre_turn_steer = -turn_steer / 6

                    else:
                        self.pre_turn_steer = 0.0



                    # Reset PID so lane-follow error doesn't carry into the turn
                    self.prev_error = 0.0
                    self.integral = 0.0

                    self.get_logger().info(
                        f"TURN STARTED: {direction}"
                    )

                    if direction == "left":
                        self.turn_offset = -80

                    elif direction == "right":
                        self.turn_offset = 80

                    else:
                        self.turn_offset = 0

                    self.intersection_frames = 0

                    return

                else:

                    self.get_logger().warn(
                        f"No turn found for patient '{self.current_patient}'. "
                        "Returning to lane follow."
                    )
                    self.state = self.State.LANE_FOLLOW
                    self.get_logger().info(
                        f"STATE -> {self.state}"
                    )
                    self.intersection_frames = 0
                    self.turn_offset = 0
        if message.vector_count == 0:
            speed = self.cruise_speed
            self.rover_move_manual_mode(
                speed,
                self.last_turn
            )
            return  

        # Compute lane center
        lane_center = self.calculate_lane_center(message)

        # Simple intersection detection
        """ if message.vector_count == 2 and self.lane_width_px > 180:
            self.at_intersection = True
        else:
            self.at_intersection = False """



        # Only smooth when both lane boundaries are visible
        if message.vector_count == 2:

            if self.filtered_lane_center == 0.0:
                self.filtered_lane_center = lane_center
            else:
                alpha = 0.7
                self.filtered_lane_center = (
                    alpha * self.filtered_lane_center +
                    (1 - alpha) * lane_center
                )

            lane_center = self.filtered_lane_center

        # Image center
        image_center = message.image_width / 2.0

        desired_center = (
            image_center
            + self.lidar_offset
            + self.turn_offset
        )
        # Tracking error
        error = desired_center - lane_center

        # Save for debugging
        self.image_center = image_center
        self.lane_center = lane_center
        self.error = error

        # PID steering
        steering = self.compute_pid(error)
        self.last_turn = steering

        self.get_logger().info(
            f"Vectors={message.vector_count} "
            f"Lane={lane_center:.1f} "
            f"Width={self.lane_width_px:.1f} "
            f"Error={error:.1f} "
            f"Steer={steering:.3f}"
        )
        # Drive forward
        max_speed = DefaultConfig.LANE_MAX_SPEED
        min_speed = DefaultConfig.LANE_MIN_SPEED

        turn = abs(steering)

        speed = max_speed - DefaultConfig.SPEED_REDUCTION_FACTOR * turn

        speed = max(min_speed, min(speed, max_speed))

        if self.lidar_override_steer is not None:

            self.get_logger().info(
                f"LIDAR OVERRIDE STEER = {self.lidar_override_steer}"
            )

            self.rover_move_manual_mode(
                DefaultConfig.TURN_SPEED_NORMAL,
                self.lidar_override_steer
            )

        else:

            self.rover_move_manual_mode(
                speed,
                steering
            )

    def choose_avoid_direction(self, distances):

        front_left = distances["front_left"]
        front_right = distances["front_right"]

        if front_left is None:
            front_left = 0.0

        if front_right is None:
            front_right = 0.0

        if front_left > front_right:
            return "left"

        return "right"

    def is_front_blocked(self, distances):

        front = distances["front"]

        if front is None:
            return False

        return front < FRONT_OBSTACLE_DISTANCE

    def get_sector_distances(self, scan):

        sectors = {
            "front_left": (15, 45),
            "front": (-15, 15),
            "front_right": (-45, -15),

            "left": (45, 120),
            "right": (-120, -45),
        }

        distances = {}

        for name, (start_deg, end_deg) in sectors.items():

            start_rad = math.radians(start_deg)
            end_rad = math.radians(end_deg)

            start_index = int(
                (start_rad - scan.angle_min)
                / scan.angle_increment
            )

            end_index = int(
                (end_rad - scan.angle_min)
                / scan.angle_increment
            )

            ranges = scan.ranges[start_index:end_index + 1]

            valid_ranges = [

                r for r in ranges

                if (
                    not math.isinf(r)
                    and not math.isnan(r)
                    and scan.range_min <= r <= scan.range_max
                )
            ]

            if len(valid_ranges) > 0:

                distances[name] = min(valid_ranges)

            else:

                distances[name] = None

        return distances

    def lidar_callback(self, msg):

        self.get_logger().info(
            f"lidar_enabled = {self.lidar_enabled}"
        )

        if not self.lidar_enabled:

            self.get_logger().info(
            "LIDAR SKIPPED"
            )

            self.lidar_offset = 0
            self.lidar_override = False
            self.lidar_override_steer = None
            self.avoid_direction = None
            return

        self.lidar_override_steer = None

        distances = self.get_sector_distances(msg)

        blocked = self.is_front_blocked(distances)

        decision = None

        if blocked:

            decision = self.choose_avoid_direction(distances)

            self.get_logger().info(
                f"OBSTACLE -> {decision}"
            )

            self.lidar_override = True
            self.avoid_direction = decision

            if decision == "right":

                diff = (distances["right"] or 0.0) - (distances["front"] or 0.0)

                steer = -(0.3 + 0.1 * diff)

                self.lidar_override_steer = max(-0.7, steer)

            else:

                diff = (distances["left"] or 0.0) - (distances["front"] or 0.0)

                steer = 0.3 + 0.1 * diff

                self.lidar_override_steer = min(0.7, steer)

        else:

            self.lidar_override = False
            self.lidar_offset = 0
            self.avoid_direction = None
            self.lidar_override_steer = None

        self.get_logger().info(

            f"\n"
            f"LEFT     : {distances['left']}\n"
            f"FRONT    : {distances['front']}\n"
            f"RIGHT    : {distances['right']}\n"
            f"BLOCKED  : {blocked}\n"
            f"DECISION : {decision}\n"

        )
        
    def server_communication_callback(self, message):
        """
        Receives coordination commands from the server.

        GUIDELINE (Server Communication):
        - Check if the message is destined for the Buggy (`message.dest == 1`).
		- Do not forget to check for ACK messages from server
        - The server communicates mission info in the `message.msg` payload string.
        - Parse server instructions (e.g., patient pickup, target hospitals).
        - Call `self.send_server_update` to report your status when you reach a checkpoint.
        """
        # Ignore packets not addressed to this buggy
        if message.dest != 1:
            return

        self.get_logger().info(
            "================ SERVER ================"
        )

        self.get_logger().info(
            f"RX | src={message.src} "
            f"uid={message.uid} "
            f"ack={message.ack} "
            f"msg='{message.msg}'"
        )

        # ACK packet from server
        if message.ack == 1:
            self.last_ack_uid = message.uid

            self.get_logger().info(
                f"ACK received for UID {message.uid}"
            )
            return

        # Store latest packet information
        self.server_message_uid = message.uid
        self.last_server_message = message.msg
        self.current_destination = message.msg
        self.current_patient = self.current_destination

        self.mission_active = True

        self.waiting_for_destination = False

        self.mission_completed = False

        self.state = self.State.LANE_FOLLOW

        self.get_logger().info(
            f"NEW DESTINATION = {self.current_destination}"
        )

        self.get_logger().info(
            f"STATE -> {self.state}"
        )

        self.send_server_update(
            text_msg="",
            ack=1,
            uid=message.uid
        )

        self.get_logger().info(
            "Mission packet received."
        )

    def send_server_update(self, text_msg="", ack=0, uid=None):
        """Send messages or acknowledgements to the server."""

        server_msg = ServerCommunication()

        server_msg.src = 1
        server_msg.dest = 2

        if uid is not None:
            server_msg.uid = uid
        else:
            server_msg.uid = self.buggy_uid
            self.buggy_uid = (self.buggy_uid + 1) % 256   # Increment buggy UID (wrap at 255)

        server_msg.ack = ack
        server_msg.msg = text_msg

        self.publisher_server.publish(server_msg)

        self.get_logger().info(
            f"TX | uid={server_msg.uid} ack={server_msg.ack} msg='{server_msg.msg}'"
        )

    def qr_detection_callback(self, message):
        """
        Receives decoded QR codes from the QR detector.
        Step 1:
        - Ignore if no mission is active.
        - Compare detected QR with current mission.
        """

        self.get_logger().info(
            "================ QR ===================="
        )

        qr_data = message.data.strip()

        qr_map = {
            "{LOC: HOSPITAL_1}": "X",
            "{LOC: HOSPITAL_2}": "Y",
            "{LOC: HOSPITAL_3}": "Z",
        }

        qr_data = qr_map.get(qr_data, qr_data)

        self.get_logger().info(
            f"QR detected: {qr_data}"
        )

        # Guard: already stopped waiting for server — ignore repeats
        if self.state == self.State.WAIT_SERVER:
            self.get_logger().info(
                "Already waiting for server. Ignoring QR."
            )
            return

        # Ignore if no active mission
        if not self.mission_active:
            self.get_logger().info(
                "No active mission. Ignoring QR."
            )
            return

        self.get_logger().info(
            f"EXPECTED = {self.current_destination}"
        )

        self.get_logger().info(
            f"SCANNED = {qr_data}"
        )

        # Compare against current mission
        if qr_data == self.current_destination:

            self.get_logger().info(
                f"Destination reached: {qr_data} -> waiting for next mission"
            )

            self.rover_move_manual_mode(
                0.0,
                0.0
            )

            self.send_server_update(
                text_msg=qr_data,
                ack=0
            )

            self.state = self.State.WAIT_SERVER
            self.waiting_for_destination = True

            self.get_logger().info(
                f"STATE -> {self.state}"
            )

        else:
            self.get_logger().info(
                f"Mission mismatch. Expected '{self.current_destination}', got '{qr_data}'"
            )


    def sign_board_callback(self, msg):

        raw = msg.data.strip()

        self.get_logger().info(
            f"SIGN RECEIVED: {raw}"
        )

        print(f"RAW SIGN MSG: '{raw}'", flush=True)

        # Ignore empty messages
        if raw == "":
            return

        new_board = {}

        for pair in raw.split(","):

            pair = pair.strip()

            # Skip invalid entries
            if ":" not in pair:

                self.get_logger().warn(
                    f"Invalid sign format: '{pair}'"
                )

                continue

            patient, direction = pair.split(":", 1)

            patient = patient.strip()
            direction = direction.strip().lower()

            # Allow only valid patients
            if patient not in ["X", "Y", "Z"]:

                self.get_logger().warn(
                    f"Unknown patient: '{patient}'"
                )

                continue

            # Allow only valid directions
            if direction not in ["left", "right", "straight"]:

                self.get_logger().warn(
                    f"Unknown direction: '{direction}'"
                )

                continue

            new_board[patient] = direction

        # Do not overwrite the old board if nothing valid was found
        if len(new_board) == 0:

            self.get_logger().warn(
                "No valid sign detected"
            )

            return

        self.current_board = new_board

        # Only arm the intersection wait when freely lane-following.
        # A sign arriving during TURN / RECOVERY must not interrupt those states.
        if self.state == self.State.LANE_FOLLOW:
            self.state = self.State.WAIT_INTERSECTION
            self.get_logger().info(
                f"STATE -> {self.state}"
            )
            self.intersection_frames = 0

        self.get_logger().info(
            f"Board saved: {self.current_board}"
        )

    def decide_turn(self):

        self.get_logger().info("DECIDE TURN CALLED")

        if self.current_patient is None:
            return None

        if self.current_patient not in self.current_board:
            return None

        direction = self.current_board[self.current_patient]

        self.get_logger().info(
            f"current_patient={self.current_patient}"
        )

        self.get_logger().info(
            f"current_board={self.current_board}"
        )

        self.get_logger().info(
            f"Board says: {self.current_patient} -> {direction}"
        )

        self.get_logger().info(
            f"Executing {direction.upper()} turn"
        )

        return direction
        
    def calculate_lane_center(self, message):
        """
        Compute the desired lane center.

        Returns:
            lane center x-coordinate in image pixels
        """

        if message.vector_count == 2:

            # Midpoint of left boundary
            left = (
                message.vector_1[0].x +
                message.vector_1[1].x
            ) / 2.0

            # Midpoint of right boundary
            right = (
                message.vector_2[0].x +
                message.vector_2[1].x
            ) / 2.0

            # Guard against noisy intersection frames producing tiny widths
            measured_width = abs(right - left)
            if measured_width > 40:
                self.lane_width_px = measured_width

            lane_center = (left + right) / 2.0

            self.last_two_vector_center = lane_center
            self.one_vector_start_time = None

            return lane_center
        elif message.vector_count == 1:

            edge_x = (
                message.vector_1[0].x +
                message.vector_1[1].x
            ) / 2.0

            image_center = message.image_width / 2.0

            """ if (
                self.state == self.State.LANE_FOLLOW
                and abs(edge_x - image_center) < 40
            ):

                self.get_logger().info(
                    "Possible T intersection: emergency right turn"
                )

                self.rover_move_manual_mode(
                    0.35,
                    -1.0
                )

                return self.last_two_vector_center """

            # Start timer when only one vector is first detected
            if self.one_vector_start_time is None:
                self.one_vector_start_time = time.time()

            elapsed = time.time() - self.one_vector_start_time

            # Hold previous centre briefly
            if (
                self.last_two_vector_center != 0.0 and
                elapsed < DefaultConfig.BLEND_HOLD_TIME
            ):
                return self.last_two_vector_center

            # ---------------- Estimate centre from one edge ----------------

            edge_x = (
                message.vector_1[0].x +
                message.vector_1[1].x
            ) / 2.0

            half_width = message.image_width / 2.0
            # Use measured lane width when available
            if self.lane_width_px > 0.0:
                lane_offset = self.lane_width_px / 2.0
            else:
                # Cold start before two edges have ever been seen
                lane_offset = 55.0

            if edge_x < half_width:
                estimated_center = edge_x + lane_offset
            else:
                estimated_center = edge_x - lane_offset

            # ---------------- Smooth transition ----------------

            if self.last_two_vector_center != 0.0:

                # Gradually move from the last known good centre
                blend = min((elapsed - DefaultConfig.BLEND_HOLD_TIME) / DefaultConfig.BLEND_FULL_TIME, 1.0)

                lane_center = (
                    (1.0 - blend) * self.last_two_vector_center +
                    blend * estimated_center
                )

                return lane_center

            # No previous two-vector measurement available
            return estimated_center
        return self.lane_center

    def get_vector_slope(self, vector):
        """
        Return (dx, dy) for a single edge vector.
        Used in TURN state to determine which way the line is leaning.
        dx > 0  → line leans right
        dx < 0  → line leans left
        """
        x1 = vector[0].x
        y1 = vector[0].y

        x2 = vector[1].x
        y2 = vector[1].y

        dx = x2 - x1
        dy = y2 - y1

        return dx, dy

    def compute_pid(self, error):
        """
        PID controller for steering.
        """

        # Integral
        self.integral += error

        # Derivative
        derivative = error - self.prev_error

        # PID output
        output = (
            self.Kp * error +
            self.Kd * derivative
        )

        self.prev_error = error

        # Clamp steering
        output = max(min(output, 1.0), -1.0)

        return output

def main(args=None):
    rclpy.init(args=args)
    node = LineFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
