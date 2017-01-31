#!/usr/bin/env python

# Node:             turtlebot_key_publisher
# Publish to:       turtlebot_command_key
# Description:      wait for input from keyboard and publish each key to 'turtlebot_command_key'.
#                   Event-driven, no polling.

import rospy
from std_msgs.msg import String


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


def getKeyFromKeyboard():
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [])
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''

    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key



if __name__=="__main__":
    settings = termios.tcgetattr(sys.stdin)

    rospy.init_node('turtlebot_key_publisher')
    pubKey = rospy.Publisher('turtlebot_command_key', String, queue_size=5)

    try:
        print msg
        while(1):
            key = getKeyFromKeyboard()
            if key == 'q':
                break

            print "pubKey_1: " + str(key)
            if key != '':
                pubKey.publish(key)

    except KeyboardInterrupt:
        print "Keyboard Interrupt"
        pass

    # termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)

