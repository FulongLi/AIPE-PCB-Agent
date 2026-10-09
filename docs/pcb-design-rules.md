# Initial PCB engineering review rules

These rules originate in the task. The V1 checker
`automation/verification/check_power_layout.py` now measures the actual routed
board, checks pad/net mapping and power topology, and guards the intended
ground-plane extent. The machine-readable register is
`automation/verification/pcb_rules.json`. Measurements do not constitute
validated electrical or thermal limits. See the example's
`verification/pcb_rule_review.md` for the separate final review and open issues.

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

The table describes the electrical acceptance evidence, which remains a human
responsibility. The register marks geometric support as semi-automated for
rules 001, 002, 004-008. Only exact pad/net equality, explicit critical topology,
layer count and the ground-plane extent guard are automatic invariants. A short
distance alone does not establish a suitable gate or commutation loop.
