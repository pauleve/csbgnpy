from enum import Enum
from math import atan2
from math import pi
import libsbgnpy.libsbgn as libsbgn
from csbgnpy.utils import *
from csbgnpy.pd.compartment import *
from csbgnpy.pd.entity import *
from csbgnpy.pd.subentity import *
from csbgnpy.pd.process import *
from csbgnpy.pd.modulation import *
from csbgnpy.pd.lo import *
from csbgnpy.pd.sv import *
from csbgnpy.pd.ui import *
from csbgnpy.pd.network import Network
from csbgnpy.pd.io.utils import *

def atan2pi(y, x):
    a = atan2(y, x)
    if a < 0:
        a = a + 2 * pi
    return a

def obj_from_coll(obj, coll):
    for o in coll:
        if o == obj:
            return o
    return None

def read(*filenames):
    net = Network()
    compartments = set([])
    entities = set([])
    los = []
    processes = []
    modulations = set([])
    for filename in filenames:
        dids = {}
        sbgn = libsbgn.parse(filename, silence=True)
        sbgnmap = sbgn.get_map()
        for glyph in sbgnmap.get_glyph(): # making compartments
            if glyph.get_class().name == "COMPARTMENT":
                comp = _make_compartment_from_glyph(glyph)
                if comp not in compartments:
                    compartments.add(comp)
                    dids[comp.id] = comp
                else:
                    dids[comp.id] = obj_from_coll(comp, compartments)
        for glyph in sbgnmap.get_glyph():
            if glyph.get_class().name in [attribute.name for attribute in list(EntityEnum)]:
                entity = _make_entity_from_glyph(glyph, dids)
                if entity not in entities:
                    entities.add(entity)
                    dids[entity.id] = entity
                else:
                    dids[entity.id] = obj_from_coll(entity, entities)
            elif glyph.get_class().name in [attribute.name for attribute in list(LogicalOperatorEnum)]:
                op  = _make_lo_node_from_glyph(glyph)
                los.append(op)
                dids[op.id] = op
            elif glyph.get_class().name in [attribute.name for attribute in list(ProcessEnum)]:
                proc = _make_process_node_from_glyph(glyph)
                processes.append(proc)
                dids[proc.id] = proc
        for arc in sbgnmap.get_arc(): # making modulations
            if arc.get_class().name == "CONSUMPTION":
                _make_reactant_from_arc(arc, dids)
            elif arc.get_class().name == "PRODUCTION":
                _make_product_from_arc(arc, dids)
            elif arc.get_class().name == "LOGIC_ARC":
                _make_lo_child_from_arc(arc, dids)
            elif arc.get_class().name in [attribute.name for attribute in list(ModulationEnum)]:
                mod = _make_modulation_from_arc(arc, dids)
                modulations.add(mod)
    processes = set(processes)
    los = set(los)
    for op in los:
        for i, child in enumerate(op.children):
            if isinstance(child, LogicalOperator):
                op.children[i] = obj_from_coll(child, los)
    for mod in modulations:
        if isinstance(mod.source, LogicalOperator):
            mod.source = obj_from_coll(mod.source, los)
        mod.target = obj_from_coll(mod.target, processes)
    net.entities = list(entities)
    net.compartments = list(compartments)
    net.processes = list(processes)
    net.los = list(los)
    net.modulations = list(modulations)
    return net

def _make_ui_from_glyph(glyph):
    ui = UnitOfInformation()
    ui.id = glyph.get_id()
    if glyph.get_label() is not None:
        glabel = glyph.get_label().get_text()
        if ':' in glabel:
            ui.prefix = glabel.split(':')[0]
            ui.label = glabel.split(':')[1]
        else:
            ui.label = glabel
    return ui

def _make_sv_from_glyph(glyph, i):
    sv = StateVariable()
    sv.id = glyph.get_id()
    if glyph.get_state() is not None:
        sv.val = glyph.get_state().get_value()
        if glyph.get_state().get_variable() is None:
            sv.var = UndefinedVar(i)
        else:
            sv.var = glyph.get_state().get_variable()
    else:
        sv.var = UndefinedVar(i)
    return sv

def _make_compartment_from_glyph(glyph):
    comp = Compartment()
    comp.id = glyph.get_id()
    if glyph.get_label():
        if glyph.get_label().get_text():
            comp.label = glyph.get_label().get_text()
    return comp

def _make_entity_from_glyph(glyph, dids):
    entity = EntityEnum[glyph.get_class().name].value()
    entity.id = glyph.get_id()
    lsvs = []
    if glyph.get_label():
        if glyph.get_label().get_text():
            entity.label = glyph.get_label().get_text()
    comp_id = glyph.get_compartmentRef()
    if comp_id is not None:
        entity.compartment = dids[comp_id]
    for subglyph in glyph.get_glyph():
        if subglyph.get_class().name in [attribute.name for attribute in list(EntityEnum)]:
            subentity = _make_subentity_from_glyph(subglyph)
            entity.add_component(subentity)
        elif subglyph.get_class().name == "UNIT_OF_INFORMATION":
            ui = _make_ui_from_glyph(subglyph)
            entity.add_ui(ui)
        elif subglyph.get_class().name == "STATE_VARIABLE":
            lsvs.append(subglyph)
    if lsvs:
        i = 1
        center = (glyph.bbox.x + glyph.bbox.w / 2, glyph.bbox.y + glyph.bbox.h / 2)
        lsorted = sorted(lsvs, key = lambda g: atan2pi(-(g.bbox.y + g.bbox.h / 2 - center[1]), g.bbox.x + g.bbox.w / 2 - center[0]))
        for subglyph in lsorted:
            sv = _make_sv_from_glyph(subglyph, i)
            if isinstance(sv.var, UndefinedVar):
                i += 1
            entity.add_sv(sv)
    return entity

def _make_subentity_from_glyph(glyph):
    entity = SubEntityEnum["SUB_{}".format(glyph.get_class().name)].value()
    entity.id = glyph.get_id()
    lsvs = []
    if glyph.get_label() is not None:
        entity.label = glyph.get_label().get_text()
    comp_id = glyph.get_compartmentRef()
    for subglyph in glyph.get_glyph():
        if subglyph.get_class().name in [attribute.name for attribute in list(EntityEnum)]:
            subentity = _make_subentity_from_glyph(subglyph)
            entity.add_component(subentity)
        elif subglyph.get_class().name == "UNIT_OF_INFORMATION":
            ui = _make_ui_from_glyph(subglyph)
            entity.add_ui(ui)
        elif subglyph.get_class().name == "STATE_VARIABLE":
            lsvs.append(subglyph)
    if lsvs:
        i = 1
        center = (glyph.bbox.x + glyph.bbox.w / 2, glyph.bbox.y + glyph.bbox.h / 2)
        lsorted = sorted(lsvs, key = lambda g: atan2pi(-(g.bbox.y + g.bbox.h / 2 - center[1]), g.bbox.x + g.bbox.w / 2 - center[0]))
        for subglyph in lsorted:
            sv = _make_sv_from_glyph(subglyph, i)
            if isinstance(sv.var, UndefinedVar):
                i += 1
            entity.add_sv(sv)
    return entity

def _make_lo_node_from_glyph(glyph):
    op = LogicalOperatorEnum[glyph.get_class().name].value()
    op.id = glyph.get_id()
    return op

def _make_lo_child_from_arc(arc, dids):
    source_id = arc.get_source()
    target_id = arc.get_target()
    dids[target_id].add_child(dids[source_id])

"""Still have to take into account stoech !"""
def _make_process_node_from_glyph(glyph):
    proc = ProcessEnum[glyph.get_class().name].value()
    proc.id = glyph.get_id()
    if glyph.get_label() is not None:
        proc.label = glyph.get_label().get_text()
    return proc

def _make_reactant_from_arc(arc, dids):
    source_id = arc.get_source()
    target_id = arc.get_target()
    dids[target_id].add_reactant(dids[source_id])

def _make_product_from_arc(arc, dids):
    source_id = arc.get_source()
    target_id = arc.get_target()
    dids[source_id].add_product(dids[target_id])

def _make_modulation_from_arc(arc, dids):
    modulation = ModulationEnum[arc.get_class().name].value()
    source_id = arc.get_source()
    target_id = arc.get_target()
    modulation.source = dids[source_id]
    modulation.target = dids[target_id]
    return modulation

def _make_glyph_from_compartment(comp):
    g = libsbgn.glyph()
    g.set_class(libsbgn.GlyphClass.COMPARTMENT)
    g.set_id(comp.id)
    label = libsbgn.label()
    label.set_text(comp.label)
    g.set_label(label)
    bbox = libsbgn.bbox(0, 0, 0, 0)
    g.set_bbox(bbox)
    return g

def _make_glyph_from_entity(entity, dids):
    g = libsbgn.glyph()
    g.set_class(libsbgn.GlyphClass[EntityEnum(entity.__class__).name])
    g.set_id(entity.id)
    if hasattr(entity, "label"):
        label = libsbgn.label()
        label.set_text(entity.label)
    # else:
        # label.set_text("")
        g.set_label(label)
    if hasattr(entity, "compartment"):
        if entity.compartment is not None:
            g.set_compartmentRef(dids[entity.compartment])
    if hasattr(entity, "components"):
        for subentity in entity.components:
            gc = _make_glyph_from_subentity(subentity, dids)
            g.add_glyph(gc)
    if hasattr(entity, "svs"):
        defsvs = [sv for sv in entity.svs if not isinstance(sv.var, UndefinedVar)]
        undefsvs = sorted([sv for sv in entity.svs if isinstance(sv.var, UndefinedVar)], key = lambda sv: sv.var.num)
        svs = defsvs + undefsvs
        for sv in svs:
            gsv = libsbgn.glyph()
            gsv.set_id(sv.id)
            gsv.set_class(libsbgn.GlyphClass["STATE_VARIABLE"])
            if isinstance(sv.var, UndefinedVar):
                var = None
                bbox = libsbgn.bbox((len(undefsvs) - sv.var.num) * 0.01, 0, 0, 0)
            else:
                var = sv.var
                bbox = libsbgn.bbox(0, 0, 0, 0)
            gsv.set_state(libsbgn.stateType(sv.val, var))
            gsv.set_bbox(bbox)
            g.add_glyph(gsv)
    if hasattr(entity, "uis"):
        for ui in entity.uis:
            gui = libsbgn.glyph()
            gui.set_id(ui.id)
            gui.set_class(libsbgn.GlyphClass["UNIT_OF_INFORMATION"])
            label = libsbgn.label()
            if ui.prefix is not None:
                label.set_text(ui.prefix + ':' + ui.label)
            else:
                label.set_text(ui.label)
            gui.set_label(label)
            bbox = libsbgn.bbox(0, 0, 0, 0)
            gui.set_bbox(bbox)
            g.add_glyph(gui)
    bbox = libsbgn.bbox(0, 0, 0, 0)
    g.set_bbox(bbox)
    return g

def _make_glyph_from_subentity(entity, dids):
    g = libsbgn.glyph()
    g.set_class(libsbgn.GlyphClass[SubEntityEnum(entity.__class__).name[4:]])
    g.set_id(entity.id)
    if hasattr(entity, "label"):
        label = libsbgn.label()
        label.set_text(entity.label)
    # else:
        # label.set_text("")
        g.set_label(label)
    if hasattr(entity, "components"):
        for subentity in entity.components:
            gc = _make_glyph_from_subentity(subentity, dids)
            g.add_glyph(gc)
    if hasattr(entity, "svs"):
        defsvs = [sv for sv in entity.svs if not isinstance(sv.var, UndefinedVar)]
        undefsvs = sorted([sv for sv in entity.svs if isinstance(sv.var, UndefinedVar)], key = lambda sv: sv.var.num)
        svs = defsvs + undefsvs
        for sv in svs:
            gsv = libsbgn.glyph()
            gsv.set_id(sv.id)
            gsv.set_class(libsbgn.GlyphClass["STATE_VARIABLE"])
            if isinstance(sv.var, UndefinedVar):
                var = None
                bbox = libsbgn.bbox((len(undefsvs) - sv.var.num) * 0.01, 0, 0, 0)
            else:
                var = sv.var
                bbox = libsbgn.bbox(0, 0, 0, 0)
            gsv.set_state(libsbgn.stateType(sv.val, var))
            gsv.set_bbox(bbox)
            g.add_glyph(gsv)
    if hasattr(entity, "uis"):
        for ui in entity.uis:
            gui = libsbgn.glyph()
            gui.set_id(ui.id)
            gui.set_class(libsbgn.GlyphClass["UNIT_OF_INFORMATION"])
            label = libsbgn.label()
            if ui.prefix is not None:
                label.set_text(ui.prefix + ':' + ui.label)
            else:
                label.set_text(ui.label)
            gui.set_label(label)
            bbox = libsbgn.bbox(0, 0, 0, 0)
            gui.set_bbox(bbox)
            g.add_glyph(gui)
    bbox = libsbgn.bbox(0, 0, 0, 0)
    g.set_bbox(bbox)
    return g

def _make_glyph_from_lo(op):
    g = libsbgn.glyph()
    g.set_class(libsbgn.GlyphClass[LogicalOperatorEnum(op.__class__).name])
    g.set_id(op.id)
    bbox = libsbgn.bbox(0, 0, 0, 0)
    g.set_bbox(bbox)
    return g

def _make_glyph_from_process(process):
    g = libsbgn.glyph()
    g.set_class(libsbgn.GlyphClass[ProcessEnum(process.__class__).name])
    g.set_id(process.id)
    label = libsbgn.label()
    if hasattr(process, "label"):
        label.set_text(process.label)
    else:
        label.set_text("")
    g.set_label(label)
    bbox = libsbgn.bbox(0, 0, 0, 0)
    g.set_bbox(bbox)
    # port1 = libsbgn.port()
    # port1.set_id("{0}.1".format(p.get_id()))
    # port1.set_y(bbox.get_y() + bbox.get_h() / 2)
    # port1.set_x(bbox.get_x())
    # port2 = libsbgn.port()
    # port2.set_id("{0}.2".format(p.get_id()))
    # port2.set_y(bbox.get_y() + bbox.get_h() / 2)
    # port2.set_x(bbox.get_x() + bbox.get_w())
    # p.add_port(port1)
    # p.add_port(port2)
    return g

def _make_arcs_from_process(process, dids):
    arcs = []
    if hasattr(process, "reactants"):
        for reactant in process.reactants:
            arc = libsbgn.arc()
            start = libsbgn.startType(0, 0)
            end = libsbgn.endType(0, 0)
            arc.set_source(dids[reactant])
            # arc.set_target("{0}.1".format(process.getId()))
            arc.set_target(dids[process])
            arc.set_id("cons_{0}_{1}".format(dids[reactant], dids[process]))
            arc.set_start(start)
            arc.set_end(end)
            arc.set_class(libsbgn.ArcClass.CONSUMPTION)
            arcs.append(arc)
    if hasattr(process, "products"):
        for product in process.products:
            arc = libsbgn.arc()
            start = libsbgn.startType(0, 0)
            end = libsbgn.endType(0, 0)
            # arc.set_source("{0}.2".format(process.getId()))
            arc.set_source(dids[process])
            arc.set_target(dids[product])
            arc.set_id("prod_{0}_{1}".format(dids[process], dids[product]))
            arc.set_start(start)
            arc.set_end(end)
            arc.set_class(libsbgn.ArcClass.PRODUCTION)
            arcs.append(arc)
    return arcs

def _make_arc_from_modulation(modulation, dids):
    arc = libsbgn.arc()
    start = libsbgn.startType(0, 0)
    end = libsbgn.endType(0, 0)
    arc.set_source(dids[modulation.source])
    arc.set_target(dids[modulation.target])
    arc.set_id("mod_{0}_{1}".format(dids[modulation.source], dids[modulation.target]))
    arc.set_start(start)
    arc.set_end(end)
    arc.set_class(libsbgn.ArcClass[ModulationEnum(modulation.__class__).name])
    return arc

def _make_arcs_from_lo(op, dids):
    arcs = set()
    for child in op.children:
        arc = libsbgn.arc()
        start = libsbgn.startType(0, 0)
        end = libsbgn.endType(0, 0)
        arc.set_source(dids[child])
        arc.set_target(dids[op])
        arc.set_id("log_{0}_{1}".format(dids[child], dids[op]))
        arc.set_start(start)
        arc.set_end(end)
        arc.set_class(libsbgn.ArcClass["LOGIC_ARC"])
        arcs.add(arc)
    return arcs

def _renew_id_of_entity(entity, i):
        entity.id = "epn_{0}".format(i)
        if hasattr(entity, "conmponents"):
            for j, subentity in enumerate(entity.components): # should be made recursive
                _renew_id_of_subentity(subentity, entity, j)
        if hasattr(entity, "svs"):
            for k, sv in enumerate(entity.svs):
                _renew_id_of_sv(sv, entity, k)
        if hasattr(entity, "uis"):
            for l, ui in enumerate(entity.uis):
                _renew_id_of_ui(ui, entity, l)

def _renew_id_of_subentity(subentity, entity, j):
    subentity.id = "{0}_sub_{1}".format(entity.id, j)
    for h, subsubentity in enumerate(subentity.components): # should be made recursive
        _renew_id_of_subentity(subsubentity, entity, h)
    for k, sv in enumerate(entity.svs):
        _renew_id_of_sv(sv, entity, k)
    for l, ui in enumerate(entity.uis):
        _renew_id_of_ui(ui, entity, l)

def _renew_id_of_sv(sv, entity, k):
    sv.id = "{0}_sv_{1}".format(entity.id, k)

def _renew_id_of_ui(ui, entity, l):
    ui.id = "{0}_ui_{1}".format(entity.id, l)


def _renew_id_of_compartment(compartment, i):
    compartment.id = "comp_{0}".format(i)

def _renew_id_of_process(process, i):
    process.id = "proc_{0}".format(i)

def _renew_id_of_lo(op, i):
    op.id = "op_{0}".format(i)

def _renew_ids(net):
    for i, entity in enumerate(net.entities):
        _renew_id_of_entity(entity, i)
    for i, compartment in enumerate(net.compartments):
        _renew_id_of_compartment(compartment, i)
    for i, process in enumerate(net.processes):
        _renew_id_of_process(process, i)
    for i, op in enumerate(net.los):
        _renew_id_of_lo(op, i)

def write(net, filename, renew_ids = False):
    sbgn = libsbgn.sbgn()
    sbgnmap = libsbgn.map()
    language = libsbgn.Language.PD
    sbgnmap.set_language(language)
    sbgn.set_map(sbgnmap)
    dids = {}
    if renew_ids:
        _renew_ids(net)
    for comp in net.compartments:
        g = _make_glyph_from_compartment(comp)
        sbgnmap.add_glyph(g)
        dids[comp] = g.get_id()
    for entity in net.entities:
        g = _make_glyph_from_entity(entity, dids)
        sbgnmap.add_glyph(g)
        dids[entity] = g.get_id()
    for op in net.los:
        g = _make_glyph_from_lo(op)
        sbgnmap.add_glyph(g)
        dids[op] = g.get_id()
        arcs = _make_arcs_from_lo(op, dids)
        for arc in arcs:
            sbgnmap.add_arc(arc)
    for process in net.processes:
        p = _make_glyph_from_process(process)
        sbgnmap.add_glyph(p)
        dids[process] = p.get_id()
        arcs = _make_arcs_from_process(process, dids)
        for arc in arcs:
            sbgnmap.add_arc(arc)
    for modulation in net.modulations:
        arc = _make_arc_from_modulation(modulation, dids)
        sbgnmap.add_arc(arc)
    sbgn.write_file(filename)
    ifile = open(filename)
    s = ifile.read()
    ifile.close()
    s = s.replace("sbgn:","")
    s = s.replace(' xmlns:sbgn="http://sbgn.org/libsbgn/0.2"', "")
    s = s.replace('."', '.0"')
    ofile = open(filename, "w")
    ofile.write(s)
    ofile.close()


