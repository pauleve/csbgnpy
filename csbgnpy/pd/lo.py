from copy import deepcopy

class LogicalOperator(object):
    """The class to model logical operators"""
    def __init__(self, children = None, id = None):
        self.children = children if children else []
        self.id = id


    def add_child(self, child):
        """Adds a child to the logical operator

        :param child: the child to be added
        :return None
        """
        if child not in self.children:
            self.children.append(child)


    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
        sorted(self.children) == sorted(other.children)

    def __str__(self):
        s = self.__class__.__name__
        s += "(["
        s += "|".join(sorted([str(child) for child in self.children]))
        s += "])"
        return s

    def __lt__(self, other):
        return str(self) < str(other)

    def __gt__(self, other):
        return str(self) > str(other)

class AndOperator(LogicalOperator):
    """The class to model and operators"""
    pass

class OrOperator(LogicalOperator):
    """The class to model or operators"""
    pass

class NotOperator(LogicalOperator):
    """The class to model not operators"""
    pass
