from copy import deepcopy

class UnitOfInformation(object):
    def __init__(self, prefix = None, label = None, id = None):
        self.prefix = prefix
        self.label = label
        self.id = id

    def __eq__(self, other):
        return isinstance(other, UnitOfInformation) and \
                self.prefix == other.prefix and \
                self.label == other.label

    def __hash__(self):
        return hash((self.prefix, self.label))

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result
