# Copyright (c) 2015 Ultimaker B.V.
# Uranium is released under the terms of the AGPLv3 or higher.

##      The point of a SceneNodeDecorator is that it can be added to a SceneNode, where it then provides decorations
#       Decorations are functions of a SceneNodeDecorator that can be called (except for functions already defined
#       in SceneNodeDecorator).
#       \sa SceneNode
class SceneNodeDecorator:
    def __init__(self):
        super().__init__()
        self._node = None
        
    def setNode(self, node):
        self._node = node

    def getNode(self):
        return self._node

    def __deepcopy__(self, memo):
        raise NotImplementedError("Subclass {0} of SceneNodeDecorator should implement their own __deepcopy__() method.".format(str(self)))
