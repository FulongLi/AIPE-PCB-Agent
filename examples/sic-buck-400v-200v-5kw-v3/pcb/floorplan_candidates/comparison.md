# V3 floorplan selection

Complete proposed multilayer centreline paths for floorplan selection; not routed measurements or extraction.

| Candidate | PCB area | External commutation copper proxy | Closed loop proxy | XY area proxy | H/L gate copper proxies |
|---|---:|---:|---:|---:|---:|
| A | 45000 mm² | 56.68 mm | 71.94 mm | 166.59 mm² | 19.97 / 21.94 mm |
| B | 45000 mm² | 58.34 mm | 73.60 mm | 137.94 mm² | 18.75 / 18.75 mm |

Selected **B**. Common planar thermal fixture and symmetric local gate cells, while retaining comparable commutation geometry. Candidate A needs two orthogonal contact planes and more complex accessible-control routing. Final choice remains subject to routed loop and native DRC gates.

Both are independent 202-part native four-layer floorplans. A uses opposed 90°/270° devices, drivers above/below, and a two-row HF bank beside the pair. B uses co-oriented devices along one edge, independent same-orientation gate cells and a back-side HF row. Bulk banks, separately supported magnetics and the four board supports are common system constraints.

Every capacitor is evaluated, including its return and layer transitions. Component-internal paths are straight terminal bridges, not package extraction. The proposed BUS path is B.Cu, SW F.Cu and PGND In1.Cu. Paths are preliminary corridors, not proof that the final track/zone avoids all pads. Values must be replaced by actual routed geometry in the final report; no nH is asserted. A low projected area alone does not prove low inductance or low EMI.

B separates the central control region from hazardous gate cells above and hazardous sensing cells below. Accessible control copper cannot underlie a hazardous island on any layer. Heavy film capacitors stay beside, rather than underneath, the thermal fixture. Quiet VEEA tie and divider placement is explicit; routing must prove that load return does not bypass the intended star.

The footprint-only native checks are retained separately from final routed DRC. Unconnected items are expected at this stage; a floorplan is not CAD-complete. Thermal fixtures, harness engagement, copper minimum widths and semiconductor timing remain independent gates.
