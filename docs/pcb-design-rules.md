# Initial PCB engineering review rules

These rules originate in the task. At bootstrap, **no geometry checker has been
implemented and no board has been reviewed**. The machine-readable register is
`automation/verification/pcb_rules.json`. Planned metrics do not constitute
validated electrical or thermal limits.

| ID | Requirement | Current review method | Required evidence |
| --- | --- | --- | --- |
| PE-PCB-001 | Minimise MOSFET gate loop | human-review | Gate and return path overlay; rationale for topology and geometry |
| PE-PCB-002 | Put high-frequency input capacitors close to half bridge | human-review | Pad-to-pad current path and capacitor placement |
| PE-PCB-003 | Minimise commutation loop | human-review | Complete loop overlay including layer transitions and return |
| PE-PCB-004 | Kelvin routing for current measurement | human-review | Sense pad takeoff and differential path inspection |
| PE-PCB-005 | Keep feedback away from switching node | human-review | All-layer coupling/return-path inspection |
| PE-PCB-006 | Size high-current copper and vias | human-review | Copper dimensions, via plating assumptions, current/loss and thermal rationale |
| PE-PCB-007 | Separate control from noisy power structures | human-review | Functional placement and ground-return review |
| PE-PCB-008 | Place decoupling next to the relevant IC pins | human-review | Per-supply pin map, capacitor location and return path |

Numeric thresholds will be established from the actual circuit, stack-up and
manufacturer evidence. Promote a rule to semi-automated or automated only when
its checker and limits have been implemented and verified. A short geometric
distance alone does not establish a suitable gate or commutation loop.
