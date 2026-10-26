"""necpp compatibility wrapper backed by PyNEC (nec2++)."""
import PyNEC

_contexts = {}
_next_id = 1

def nec_create():
    global _next_id
    cid = _next_id
    _next_id += 1
    ctx = PyNEC.nec_context()
    ctx.get_geometry().set_intersection_check(False)
    _contexts[cid] = ctx
    return cid

def nec_delete(cid):
    if cid in _contexts:
        del _contexts[cid]

def nec_wire(cid, tag, nseg, x1, y1, z1, x2, y2, z2, rad, r1=1.0, r2=1.0):
    ctx = _contexts[cid]
    ctx.get_geometry().wire(tag, nseg, x1, y1, z1, x2, y2, z2, rad, r1, r2)

def nec_geometry_complete(cid, ground_flag=0):
    _contexts[cid].geometry_complete(ground_flag)

def nec_ld_card(cid, ld_type, tag, seg_start, seg_end, sigma, param1=0.0, param2=0.0):
    _contexts[cid].ld_card(ld_type, tag, seg_start, seg_end, sigma, param1, param2)

def nec_ex_card(cid, *args):
    _contexts[cid].ex_card(*args)

def nec_fr_card(cid, ifrq, nfrq, freq_mhz, del_freq=0.0):
    _contexts[cid].fr_card(ifrq, nfrq, freq_mhz, del_freq)

def nec_xq_card(cid, ipt=0):
    _contexts[cid].xq_card(ipt)

def nec_impedance_real(cid, index=0):
    return _contexts[cid].get_impedance_real(index)

def nec_impedance_imag(cid, index=0):
    return _contexts[cid].get_impedance_imag(index)
