#!/usr/bin/env python

# Copyright (c) 2011, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the Willow Garage, Inc. nor the names of its
#      contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Mathematically, a "twist" is a six-dimensional velocity (see Wikipedia).
# The Twist message represents just such a velocity. By convention, robots listen on the /cmd_vel topic for Twist messages,
# and then respond appropriately. That is, you fill in a Twist message with the velocity values you want,
# and publish it to /cmd_vel. The robot (actually the ROS node that implements the hardware driver for your robot)
# listens on /cmd_vel and then translates the velocities in those messages into wheel speeds.
#
# Of course, most robots can't travel in six degrees of freedom; the Turtlebot only has two
# (linear speed and angular speed), so most of the values are ignored.


import rospy

from geometry_msgs.msg import Twist

import sys, select, termios, tty

msg = """
Control Your Turtlebot!
---------------------------
Moving around:
   u    i    o
   j    k    l
   m    ,    .

q/z : increase/decrease max speeds by 10%
w/x : increase/decrease only linear speed by 10%
e/c : increase/decrease only angular speed by 10%
space key, k : force stop
anything else : stop smoothly

CTRL-C to quit
"""

moveBindings = {
        'i':(1,0),
        'o':(1,-1),
        'j':(0,1),
        'l':(0,-1),
        'u':(1,1),
        ',':(-1,0),
        '.':(-1,1),
        'm':(-1,-1),
           }

speedBindings={
        'q':(1.1,1.1),
        'z':(.9,.9),
        'w':(1.1,1),
        'x':(.9,1),
        'e':(1,1.1),
        'c':(1,.9),
          }

def vels(speed,turn):
    return "currently:\tspeed %s\tturn %s " % (speed,turn)


def getKeyFromKeyboard():
    """Waits for a single keypress on stdin.

    This is a silly function to call if you need to do it a lot because it has
    to store stdin's current setup, setup stdin for reading single keystrokes
    then read the single keystroke then revert stdin back after reading the
    keystroke.

    Returns the character of the key that was pressed (zero on
    KeyboardInterrupt which can happen when a signal gets handled)

    """
    import termios, fcntl, sys, os
    fd = sys.stdin.fileno()
    # save old state
    flags_save = fcntl.fcntl(fd, fcntl.F_GETFL)
    attrs_save = termios.tcgetattr(fd)
    # make raw - the way to do this comes from the termios(3) man page.
    attrs = list(attrs_save) # copy the stored version to update
    # iflag
    attrs[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK
                  | termios.ISTRIP | termios.INLCR | termios. IGNCR
                  | termios.ICRNL | termios.IXON )
    # oflag
    attrs[1] &= ~termios.OPOST
    # cflag
    attrs[2] &= ~(termios.CSIZE | termios. PARENB)
    attrs[2] |= termios.CS8
    # lflag
    attrs[3] &= ~(termios.ECHONL | termios.ECHO | termios.ICANON
                  | termios.ISIG | termios.IEXTEN)
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    # turn off non-blocking
    fcntl.fcntl(fd, fcntl.F_SETFL, flags_save & ~os.O_NONBLOCK)
    # read a single keystroke
    try:
        ret = sys.stdin.read(1) # returns a single character
    except KeyboardInterrupt:
        ret = 0
    finally:
        # restore old state
        termios.tcsetattr(fd, termios.TCSAFLUSH, attrs_save)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags_save)
    print "key pressed: " + str(ret)
    return ret

def publishCommandKeyBak():
    settings = termios.tcgetattr(sys.stdin)
    rospy.init_node('turtlebot_controller')
    pub = rospy.Publisher('~cmd_vel', Twist, queue_size=5)

    x = 0
    th = 0
    status = 0
    count = 0
    acc = 0.1
    target_speed = 0
    target_turn = 0
    control_speed = 0
    control_turn = 0
    speed = .2
    turn = 1
    try:
        print msg
        print vels(speed,turn)
        while(1):
            key = getKeyFromKeyboard()
            if key in moveBindings.keys():
                x = moveBindings[key][0]
                th = moveBindings[key][1]
                count = 0
            elif key in speedBindings.keys():
                speed = speed * speedBindings[key][0]
                turn = turn * speedBindings[key][1]
                count = 0

                print vels(speed,turn)
                if (status == 14):
                    print msg
                status = (status + 1) % 15
            elif key == ' ' or key == 'k' :
                x = 0
                th = 0
                control_speed = 0
                control_turn = 0
            else:
                count = count + 1
                if count > 4:
                    x = 0
                    th = 0
                if (key == '\x03'):
                    break

            target_speed = speed * x
            target_turn = turn * th

            if target_speed > control_speed:
                control_speed = min( target_speed, control_speed + 0.02 )
            elif target_speed < control_speed:
                control_speed = max( target_speed, control_speed - 0.02 )
            else:
                control_speed = target_speed

            if target_turn > control_turn:
                control_turn = min( target_turn, control_turn + 0.1 )
            elif target_turn < control_turn:
                control_turn = max( target_turn, control_turn - 0.1 )
            else:
                control_turn = target_turn

            twist = Twist()
            twist.linear.x = control_speed; twist.linear.y = 0; twist.linear.z = 0
            twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = control_turn
            pub.publish(twist)

            print("loop: {0}".format(count))
            print("target: vx: {0}, wz: {1}".format(target_speed, target_turn))
            print("publihsed: vx: {0}, wz: {1}".format(twist.linear.x, twist.angular.z))

    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)
    except ValueError:
        print "Could not convert data to an integer."
    except:
        print "Unexpected error:", sys.exc_info()[0]

    finally:
        twist = Twist()
        twist.linear.x = 0; twist.linear.y = 0; twist.linear.z = 0
        twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = 0
        pub.publish(twist)

    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)




def publishCommandKey():
    rospy.init_node('turtlebot_controller')
    pub = rospy.Publisher('~cmd_vel', Twist, queue_size=5)

    x = 0
    th = 0
    status = 0
    count = 0
    acc = 0.1
    target_speed = 0
    target_turn = 0
    control_speed = 0
    control_turn = 0
    speed = .2
    turn = 1
    try:
        print msg
        print vels(speed,turn)
        while(1):
            key = getKeyFromKeyboard()
            if key in moveBindings.keys():
                x = moveBindings[key][0]
                th = moveBindings[key][1]
                count = 0
            elif key in speedBindings.keys():
                speed = speed * speedBindings[key][0]
                turn = turn * speedBindings[key][1]
                count = 0

                print vels(speed,turn)
                if (status == 14):
                    print msg
                status = (status + 1) % 15
            elif key == ' ' or key == 'k' :
                x = 0
                th = 0
                control_speed = 0
                control_turn = 0
            else:
                count = count + 1
                if count > 4:
                    x = 0
                    th = 0
                if (key == '\x03'):
                    break

            target_speed = speed * x
            target_turn = turn * th

            if target_speed > control_speed:
                control_speed = min( target_speed, control_speed + 0.02 )
            elif target_speed < control_speed:
                control_speed = max( target_speed, control_speed - 0.02 )
            else:
                control_speed = target_speed

            if target_turn > control_turn:
                control_turn = min( target_turn, control_turn + 0.1 )
            elif target_turn < control_turn:
                control_turn = max( target_turn, control_turn - 0.1 )
            else:
                control_turn = target_turn

            twist = Twist()
            twist.linear.x = control_speed; twist.linear.y = 0; twist.linear.z = 0
            twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = control_turn
            pub.publish(twist)

            print("loop: {0}".format(count))
            print("target: vx: {0}, wz: {1}".format(target_speed, target_turn))
            print("publihsed: vx: {0}, wz: {1}".format(twist.linear.x, twist.angular.z))

    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)
    except ValueError:
        print "Could not convert data to an integer."
    except:
        print "Unexpected error:", sys.exc_info()[0]

    finally:
        twist = Twist()
        twist.linear.x = 0; twist.linear.y = 0; twist.linear.z = 0
        twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = 0
        pub.publish(twist)

    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)



# def publishCommandKey():
#
#     # global speed
#     # global turn
#
#     settings = termios.tcgetattr(sys.stdin)
#
#     rospy.init_node('turtlebot_controller')
#     pub = rospy.Publisher('~cmd_vel', Twist, queue_size=5)
#
#     x = 0
#     th = 0
#     status = 0
#     count = 0
#     acc = 0.1
#     target_speed = 0
#     target_turn = 0
#     control_speed = 0
#     control_turn = 0
#     try:
#         print msg
#         print vels(speed,turn)
#         while(1):
#             key = getKeyFromKeyboard()
#             if key in moveBindings.keys():
#                 x = moveBindings[key][0]
#                 th = moveBindings[key][1]
#                 count = 0
#             elif key in speedBindings.keys():
#                 speed = speed * speedBindings[key][0]
#                 turn = turn * speedBindings[key][1]
#                 count = 0
#
#                 print vels(speed,turn)
#                 if (status == 14):
#                     print msg
#                 status = (status + 1) % 15
#             elif key == ' ' or key == 'k' :
#                 x = 0
#                 th = 0
#                 control_speed = 0
#                 control_turn = 0
#             else:
#                 count = count + 1
#                 if count > 4:
#                     x = 0
#                     th = 0
#                 if (key == '\x03'):
#                     break
#
#             target_speed = speed * x
#             target_turn = turn * th
#
#             if target_speed > control_speed:
#                 control_speed = min( target_speed, control_speed + 0.02 )
#             elif target_speed < control_speed:
#                 control_speed = max( target_speed, control_speed - 0.02 )
#             else:
#                 control_speed = target_speed
#
#             if target_turn > control_turn:
#                 control_turn = min( target_turn, control_turn + 0.1 )
#             elif target_turn < control_turn:
#                 control_turn = max( target_turn, control_turn - 0.1 )
#             else:
#                 control_turn = target_turn
#
#             twist = Twist()
#             twist.linear.x = control_speed; twist.linear.y = 0; twist.linear.z = 0
#             twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = control_turn
#             pub.publish(twist)
#
#             print("loop: {0}".format(count))
#             print("target: vx: {0}, wz: {1}".format(target_speed, target_turn))
#             print("publihsed: vx: {0}, wz: {1}".format(twist.linear.x, twist.angular.z))
#
    # except IOError as e:
    #     print "I/O error({0}): {1}".format(e.errno, e.strerror)
    # except ValueError:
    #     print "Could not convert data to an integer."
    # except:
    #     print "Unexpected error:", sys.exc_info()[0]
#
#     finally:
#         twist = Twist()
#         twist.linear.x = 0; twist.linear.y = 0; twist.linear.z = 0
#         twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = 0
#         pub.publish(twist)
#
#     termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)


if __name__=="__main__":
    publishingToWheels()
