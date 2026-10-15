"""Optional engineering topology templates, independent of project references.

Templates place actual symbols and wires. The normal presentation connectivity
guard and native ERC still validate their output; a template never edits nets.
"""
from automation.kicad_tools.schematic_presentation import angle_for, snap, GRID


def apply_template(layout, config):
    if config.get('type') != 'buck_half_bridge':
        raise ValueError(f'Unknown schematic template {config!r}')
    buck_half_bridge(layout, config)


def buck_half_bridge(lay, cfg):
    parts = {p['ref']: p for p in lay.members}
    high, low, choke = (parts[cfg[key]] for key in ('high_side', 'low_side', 'inductor'))
    def role(part, name):
        found = [n for n, p in part['pins'].items() if p['name'].upper() == name]
        if len(found) != 1:
            raise ValueError(f'{part["ref"]}: template requires exactly one {name} pin')
        return found[0]
    hd, hs, ld, ls = role(high,'D'), role(high,'S'), role(low,'D'), role(low,'S')
    bus, sw, gnd = high['nets'][hd], high['nets'][hs], low['nets'][ls]
    if low['nets'][ld] != sw or set(choke['nets'].values()) != {sw, cfg['output_net']}:
        raise ValueError('Half-bridge/inductor connectivity does not match buck topology')
    out = cfg['output_net']
    cin, cout = [], []
    for p in parts.values():
        if p['ref'] in (high['ref'],low['ref'],choke['ref']):
            continue
        if p['kind'] != 'C' or len(p['nets']) != 2:
            raise ValueError(f'Unexpected part {p["ref"]} in buck topology group')
        ns = set(p['nets'].values())
        if ns == {bus,gnd}: cin.append(p)
        elif ns == {out,gnd}: cout.append(p)
        else: raise ValueError(f'Unexpected capacitor nets {p["ref"]}: {ns}')
    pitch = snap(max([25.4]+[lay.part_text_width(p)+10.16 for p in cin+cout]))
    xfet = snap(len(cin)*pitch+38.1)
    top, mid, bottom = 0., 38.1, 76.2
    def put(part, pad, direction, x, y):
        definition = lay.symbol(part)[1]
        return lay.place(part,1,x,y,angle_for(definition,1,pad,direction))
    qh = put(high,hd,(0,-1),xfet,19.05)
    ql = put(low,ld,(0,-1),xfet,57.15)
    # Drain and source share the vertical column for a conventional MOSFET glyph.
    col=qh.pins()[hd]['point'][0]
    if ql.pins()[ld]['point'][0] != col:
        raise ValueError('MOSFET symbol cannot form a vertical drain/source column')
    for q,d,s,a,b in [(qh,hd,hs,top,mid),(ql,ld,ls,mid,bottom)]:
        lay.wire(q.part['nets'][d],(col,a),q.pins()[d]['point'])
        lay.wire(q.part['nets'][s],q.pins()[s]['point'],(col,b))
        q.texts={'Reference':(xfet+12.7,q.y-2.54,'left'),'Value':(xfet+12.7,q.y+1.27,'left')}
        for pad, info in q.pins().items():
            if pad in (d,s):continue
            point=info['point'];ox,oy=info['outward']
            end=(snap(point[0]+ox*7.62),snap(point[1]+oy*7.62))
            lay.wire(q.part['nets'][pad],point,end)
            lay.end_marker(q.part['nets'][pad],end,-1,force=True)
    def bank(capacitors,xstart,uppernet,ytop):
        for i,p in enumerate(capacitors):
            pad=next(k for k,n in p['nets'].items() if n==uppernet)
            placed=put(p,pad,(0,-1),snap(xstart+i*pitch),snap((ytop+bottom)/2))
            lay.side_texts(placed)
            for n,info in placed.pins().items():
                net=p['nets'][n];yy=ytop if net==uppernet else bottom
                lay.wire(net,info['point'],(placed.x,yy))
    bank(cin,0,bus,top)
    lpad=next(k for k,n in choke['nets'].items() if n==sw)
    ll=put(choke,lpad,(-1,0),snap(col+50.8),mid)
    lay.inline_texts(ll)
    other=next(k for k,n in choke['nets'].items() if n==out)
    lay.wire(sw,(col,mid),ll.pins()[lpad]['point'])
    xout=snap(col+88.9)
    bank(cout,xout,out,mid)
    end=snap(xout+max(0,len(cout)-1)*pitch)
    lay.wire(bus,(0,top),(col,top))
    lay.wire(gnd,(0,bottom),(end,bottom))
    lay.wire(out,ll.pins()[other]['point'],(end,mid))
    for net,point,dx in [(bus,(0,top),-1),(gnd,(end,bottom),1),(sw,(col,mid),1),(out,(end,mid),1)]:
        lay.end_marker(net,point,dx,force=True,down=net==gnd)
    lay.finish()
