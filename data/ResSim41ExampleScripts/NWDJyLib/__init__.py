"""
Welcome to the NWD Jython Library. 
To use this library, simply make sure this is included in sys.path. 

usage example:

From NWDJyLib import cLogging
"""

'''
One option of this initialization would be to
add all subdirectories to the sys.path object.
That way, scripts using these custom modules can just use a statement like:
    import foo
And foo.py can be in any of the directories
However, I decided against this because it impairs readability.
It is better to have a statement like:
    from NWDJyLib.myPackage import foo
'''


# import os
# import sys

# curDir = os.path.dirname(__file__)
# for root, dirs, files in os.walk(curDir):
    # for d in dirs:
        # if not d in sys.path: sys.path.append(d)
