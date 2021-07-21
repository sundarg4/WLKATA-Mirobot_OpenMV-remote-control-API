# Bjorn and Sundar

import json, rpc, struct, math, time,sys, traceback,string,ast
import numpy as np
from scipy.spatial import distance as dist
from matplotlib import pyplot as plt
import plotille
from mirobot import Mirobot

class remote_control():
    '''
        A class to execute remote procedure calls
    
    ...

    Attributes
    ----------
    CAMERA_ONE_PORT : str
        portname for camera one
    CAMERA_TWO_PORT : str
        portname for camera two
    MIROBOT_ONE_PORT : str
        portname for mirobot one
    MIROBOT_TWO_PORT : str
        portname for mirobot two
    Methods:
    --------
    To be continued
    '''

    def __init__(self):
        self.CAMERA_ONE_PORT = "/dev/ttyACM_OpenMV1"
        self.CAMERA_TWO_PORT = "/dev/ttyACM_OpenMV2"
        self.MIROBOT_ONE_PORT = "/dev/ttyUSB_Mirobot1"
        self.MIROBOT_TWO_PORT = "/dev/ttyUSB_Mirobot2"
        self.window_size = 100
        self.prev_cx = [-1] * 25
        self.prev_cy = [-1] * 25
        self.prev_area = [-1] * 25
        self.prev_rotation_angle = [-1] * 25
        self.color = []
        self.april_tags = {}

    def get_camera(self, port):
        '''Returns the rpc interface representing the openMV camera connected to the port.
        
                Paramters:
                    port (str): a string representation of the port connected to the camera
                    
                Returns:
                    interface (rpc.rpc_usb_vcp_master): Interface to interact with openMV
        '''
        return rpc.rpc_usb_vcp_master(port)

    def exe_get_data(self, interface):
        try:
            result = interface.call("get_data",  send_timeout=10000, recv_timeout=10000) 

            if result is not None and len(result):
                e = struct.unpack('{}s'.format(len(result)), result)
                #data = ast.literal_eval(e)
                #print(data)     
                for element in e:
                    string_element = str(bytes(element).decode("utf8"))
                    if "apriltag" in string_element:
                        y = string_element.split("apriltag")[0]
                        data = ast.literal_eval(y)
                        self.update_data(data)
                        apriltag_str = string_element.split("apriltag")[1]
                        self.april_tags = ast.literal_eval(apriltag_str)
            else:
                print("No data broooo")
                #return None

        except:
            traceback.print_exc(file=sys.stdout)
            print("No data this time")

    def update_data(self, data):
        w=0.10

        window_size = len(data)
        cx = [0] * window_size
        cy = [0] * window_size
        area = [0] * window_size
        rotation_angle = [0] * window_size

        for blob_count,blob_list in enumerate(data):
            for count, element in enumerate(blob_list):
                if(count == 0):
                    if(self.prev_cx[blob_count] == -1):
                        self.prev_cx[blob_count] = element
                    cx[blob_count] = int((w * element) + ((1-w) * self.prev_cx[blob_count]))
                    self.prev_cx[blob_count] = cx[blob_count]
                elif(count == 1):
                    if(self.prev_cy[blob_count] == -1):
                        self.prev_cy[blob_count] = element
                    cy[blob_count] = int((w * element) + ((1-w) * self.prev_cy[blob_count]))
                    self.prev_cy[blob_count] = cy[blob_count]
                elif(count == 2):
                    if(self.prev_area[blob_count] == -1):
                        self.prev_area[blob_count] = element
                    area[blob_count] = int((w * element) + ((1-w) * self.prev_area[blob_count]))
                    self.prev_area[blob_count] = area[blob_count]
                elif(count == 3):
                    corner_list = self.order_points(np.array(element))
                    angle = self.get_angle_of_rotation(corner_list.tolist())
                    if(self.prev_rotation_angle[blob_count] == -1):
                        self.prev_rotation_angle[blob_count] = angle
                    rotation_angle[blob_count] = int((w * angle) + ((1-w) * self.prev_rotation_angle[blob_count]))
                    self.prev_rotation_angle[blob_count] = rotation_angle[blob_count]
                elif(count == 4):
                    self.color.append(element)
               
    def order_points(self, pts):
	    # sort the points based on their x-coordinates
	    xSorted = pts[np.argsort(pts[:, 0]), :]
	    # grab the left-most and right-most points from the sorted
	    # x-roodinate points
	    leftMost = xSorted[:2, :]
	    rightMost = xSorted[2:, :]
	    # now, sort the left-most coordinates according to their
	    # y-coordinates so we can grab the top-left and bottom-left
	    # points, respectively
	    leftMost = leftMost[np.argsort(leftMost[:, 1]), :]
	    (tl, bl) = leftMost
	    # now that we have the top-left coordinate, use it as an
	    # anchor to calculate the Euclidean distance between the
	    # top-left and right-most points; by the Pythagorean
	    # theorem, the point with the largest distance will be
	    # our bottom-right point
	    D = dist.cdist(tl[np.newaxis], rightMost, "euclidean")[0]
	    (br, tr) = rightMost[np.argsort(D)[::-1], :]
	    # return the coordinates in top-left, top-right,
	    # bottom-right, and bottom-left order
	    return np.array([tl, tr, br, bl], dtype="float32")
 
    def get_angle_of_rotation(self, corners):
        ctx,cty = corners[0]
        crx,cry = corners[1] 

        angle = math.atan2(cry - cty, crx - ctx)
        #angle = math.atan2(cty - cry, ctx - crx)
        degrees = abs(angle * (180 / math.pi) )
        #print(str(degrees))
        return degrees
    
    def rescale(self, x_camera, y_camera, tag_corners, offset_positive_x=0, offset_positive_y=0, offset_negative_x=0, offset_negative_y=0):
        '''
            Transforms the coordinates from camera frame to robot frame.
            Camera coordinate system and robot coordinate system is reversed,
            thus will the x-axis of the camera be the y-axis of the robot, and the
            y-axis of the camera will be the x-axis of the robot.

            The center of the robot is not exactly the center of the plate, and because of 
            that there is a need to calibrate the offset for positive roboy_y and negative
            robot_y differently.

            Parameters
                x_camera (float) : The cameras x position
                y_camera (float) : The cameras y position
        '''
        robot_y = self.rescale_x(x_camera, tag_corners)
        robot_x = self.rescale_y(y_camera, tag_corners)
        
        # Correction of offset
        #if robot_y < 0:
        #    robot_y = robot_y + 5
        #    robot_x = robot_x + 20
        #else:
        #    robot_x = robot_x + 20

        if robot_y < 0:
            robot_y = robot_y + offset_negative_y
            robot_x = robot_x + offset_negative_x
        else:
            robot_x = robot_x + offset_positive_x
        
        return robot_x, robot_y
        
    def rescale_x(self, val, tag_corners):
        out_min = -129 #-125 #-129 ##-144
        out_max = 123 #127 # 123 ##138

        in_min = tag_corners[0][0] * 2
        in_max = tag_corners[1][0] * 2
        
        if (in_min - in_max) != 0:
            return out_min + (val - in_min) * ((out_max - out_min) / (in_max - in_min))
        else:
            raise ZeroDivisionError
          
    def rescale_y(self, val, tag_corners):
        out_min = 104 #100
        out_max = 294 #290
        
        in_min = tag_corners[0][1] * 2
        in_max = tag_corners[3][1] * 2
        
        if (in_min - in_max) != 0:      
            return out_min + (val - in_min) * ((out_max - out_min) / (in_max - in_min))
        else:
            raise ZeroDivisionError
 
    def get_tag_corners(self):
        center_list = []
        for tag_id,tag in self.april_tags.items():
            center_list.append((tag.get('cx'),tag.get('cy')))
        
        # The four corners of a april tag
        tag_corners = (self.order_points(np.array(center_list))).tolist()
        return tag_corners

    def draw_blob_map(self, x,y):
        plt.grid(True)
        axes = plt.gca()
        axes.set_xlim([0,250])
        axes.set_ylim([0,350])
        plt.scatter(x,y)
        plt.show()
        
    def draw(self, cx_list, cy_list):
        cx = np.array(cx_list)
        cy = []

        for element in cy_list:
            cy.append(element * -1)
        
        cy_converted = np.array(cy)

        fig = plotille.Figure()
        fig.width = 40
        fig.height = 10
        fig.set_x_limits(min_=0, max_=350)
        fig.set_y_limits(min_=-180, max_=0)
        fig.scatter(cx,cy_converted)

        print(fig.show(legend=False))
    
    def init_robot(self, port=None):
        '''Initializing the robot before use with the homing routine
                Parameters:
                    portname (str): a string representation of the port used by the Mirobot
                
                Returns:
                    None
        '''
        if port:
            with Mirobot(portname = port, debug=True) as m:
                #m.set_speed(750)
                m.home_simultaneous()
                m.send_msg('M3S1000')
                time.sleep(2)
                m.send_msg('M3S0')
                time.sleep(2)
        else:
            print("Must spesify a valid port.")
  
    def go_to_resting_point(self, port=None, speed=750):
        '''
          Moves the Mirobot to its resting point. 
          (cx = 133, cy = 0, cz = 80, rx = 0, ry = 0, rz = 0)
        '''
        if port:
            with Mirobot(portname = port, debug=True) as m:
                m.unlock_shaft()
                m.go_to_cartesian_lin(133,0,80,0,0,0, speed)
        else:
            print("Must spesify a valid port.")
    
    def pick_up_cartesian(self, x, y, z, rx=0, ry=0, rz=0, port=None, speed=750, is_cube=True):
        '''
            Moves the robot to the given cartesian coordinates and picks up the
            object using the suction cup. Then moves to the zero position and releases 
            the object.

            Parameters:
                x (float) : float value for the mirobots x coordinate
                y (float) : float value for the mirobots y coordinate
                z (float) : float value for the mirobots z coordinate
                rx (float) : float value for the mirobots rx coordinate
                ry (float) : float value for the mirobots ry coordinate
                rz (float) : float value for the mirobots rz coordinate

                port (str) : The protname connected to the robot being operated on.

                speed (int) : The speed of movement for the robot. Ranges from 0 - 2000.
                              Not recommended to run below 500. Default set to 750.
                
                is_cube (bool) : True if a cube, false if a rectangle.
            
            Returns
                I dont know - have to find out...
        '''
        
        X_MIN, X_MAX, Y_MIN, Y_MAX, Z_MIN, Z_MAX = self.get_soft_limits(is_cube)
        
        if (not x < X_MIN or not x > X_MAX or not y < Y_MIN or not y > Y_MAX 
            or not z < Z_MIN or not z > Z_MAX):
            
            with Mirobot(portname=port, debug=True) as m:
                try:
                    m.unlock_shaft()              
                    time.sleep(1)
                    m.go_to_cartesian_lin(x,y,z,rx,ry,rz, speed)
                    m.send_msg('M3S1000')
                    time.sleep(1)
                    m.go_to_zero()
                    m.send_msg('M3S0')
                    time.sleep(1)
                except KeyboardInterrupt:
                    m.send_msg('!')
                    print("Im so interrupted")
        else:
            print("Can't operate on theese coordinates.")
    
    def get_soft_limits(self, is_cube):
        '''
            Gets the soft limits for the robots working space.
            Only Z_MIN is different depending on which object
            is to be picked up.

            Parameters
                is_cube (bool) : True if a cube, False if a rectangle.

            Returns
                X_MIN (int), X_MAX (int), Y_MIN (int), Y_MAX (int), Z_MIN (int), Z_MAX (int)
        '''
        X_MIN = 133
        X_MAX = 290
        Y_MIN = -125
        Y_MAX = 125
        Z_MIN = 100
        Z_MAX = 231

        if is_cube:
            Z_MIN = 58
            return X_MIN, X_MAX, Y_MIN, Y_MAX, Z_MIN, Z_MAX
        
        elif not is_cube:
            Z_MIN = 10
            return X_MIN, X_MAX, Y_MIN, Y_MAX, Z_MIN, Z_MAX
            
    def fill_data_list(self, interface):
        '''
            Storing the values of a 100 frames to be processed.

            parameters
                interface (rpc.rpc_usb_vcp_master) : The openMV camera used.
            
            Returns
                None 
        '''
        for i in range(100):
            self.exe_get_data(interface)    

    def clear_data_list(self):
        '''Clears the data_list before next call'''
        self.data_list.clear()

    

    def find_mode(sample):
        #c = Counter(sample)
        return max(set(sample), key=sample.count)

    def find_mean(sample):
        #c = Counter(sample)
        return int(sum(sample) / len(sample))
 
    def select_nth(n, items):
        pivot = items[0]

        lesser = [item for item in items if item < pivot]
        if len(lesser) > n:
            return select_nth(n, lesser)
        n -= len(lesser)

        numequal = items.count(pivot)
        if numequal > n:
            return pivot
        n -= numequal

        greater = [item for item in items if item > pivot]
        return select_nth(n, greater)

    def median(items):
        if len(items) % 2:
            return select_nth(len(items)//2, items)

        else:
            left  = select_nth((len(items)-1) // 2, items)
            right = select_nth((len(items)+1) // 2, items)

            return (left + right) / 2
