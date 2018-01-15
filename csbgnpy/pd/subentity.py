from copy import deepcopy

from csbgnpy.pd.sv import UndefinedVar

class SubEntity(object):
    def __init__(self, id = None):
        self.id = id

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __hash__(self):
        return hash((self.__class__))

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def __lt__(self, other):
        return self.__repr__() < other.__repr__()

    def __str__(self):
        s = self.__class__.__name__ + "("
        if hasattr(self, "components"):
            s += "[" + "|".join([str(subentity) for subentity in self.components]) + "]"
        if hasattr(self, "uis"):
            s += "[" + "|".join([str(ui) for ui in self.uis]) + "]"
        if hasattr(self, "svs"):
            s += "[" + "|".join([str(sv) for sv in self.svs]) + "]"
        if hasattr(self, "label"):
            s += self.label
        s += ")"
        return s

    def __repr__(self):
        return str(self)

class StatefulSubEntity(SubEntity):
    def __init__(self, label = None, svs = None, uis = None, id = None):
        super().__init__(id)
        self.label = label
        self.svs = svs if svs else []
        self.uis = uis if uis else []

    def add_sv(self, sv):
        """Adds a state variable to the subentity

        :param sv: the state variable to be added
        :return: None
        """
        if sv not in self.svs:
            if isinstance(sv.var, UndefinedVar) and not sv.var.num:
                max = 0
                for sv2 in self.svs:
                    if isinstance(sv2.var, UndefinedVar) and sv2.var.num > max:
                        max = sv2.var.num
                max += 1
                sv.var.num = max
            self.svs.append(sv)

    def add_ui(self, ui):
        if ui not in self.uis:
            self.uis.append(ui)

    def get_ui(self, val, by_ui = False, by_id = False, by_hash = False):
        for ui in self.uis:
            if by_ui:
                if ui == val:
                    return ui
            if by_id:
                if ui.id == val:
                    return ui
            if by_hash:
                if hash(ui) == val:
                    return ui
        return None

    def get_sv(self, val, by_sv = False, by_id = False, by_hash = False):
        for sv in self.svs:
            if by_sv:
                if sv == val:
                    return sv
            if by_id:
                if sv.id == val:
                    return sv
            if by_hash:
                if hash(sv) == val:
                    return sv
        return None

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
            self.label == other.label and \
            set(self.svs) == set(other.svs) and \
            set(self.uis) == set(other.uis)

    def __hash__(self):
        return hash((self.__class__, self.label, frozenset(self.svs), frozenset(self.uis)))

class StatelessSubEntity(SubEntity):
    def __init__(self, label = None, id = None):
        super().__init__(id)
        self.label = label

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
            self.label == other.label

    def __hash__(self):
        return hash((self.__class__, self.label))

class SubUnspecifiedEntity(StatelessSubEntity):
    pass

class SubSimpleChemical(StatefulSubEntity):
    pass

class SubMacromolecule(StatefulSubEntity):
    pass

class SubNucleicAcidFeature(StatefulSubEntity):
    pass

class SubComplex(StatefulSubEntity):
    def __init__(self, label = None, svs = None, uis = None, components = None, id = None):
        super().__init__(label, svs, uis, id)
        self.components = components if components is not None else []

    def add_component(self, component):
        if component not in self.components:
            self.components.append(component)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
            self.label == other.label and \
            set(self.svs) == set(other.svs) and \
            set(self.uis) == set(other.uis) and \
            set(self.components) == set(other.components)

    def __hash__(self):
        return hash((self.__class__, self.label, frozenset(self.svs), frozenset(self.uis), frozenset(self.components)))

class SubMultimer(StatefulSubEntity):
    pass

class SubSimpleChemicalMultimer(SubMultimer):
    pass

class SubMacromoleculeMultimer(SubMultimer):
    pass

class SubNucleicAcidFeatureMultimer(SubMultimer):
    pass

class SubComplexMultimer(SubComplex, SubMultimer):
    def __init__(self, label = None, svs = None, uis = None, components = None, id = None):
        super().__init__(label, svs, uis, component, id)

    #maybe not useful:
    def __hash__(self):
        return super().__hash__()
