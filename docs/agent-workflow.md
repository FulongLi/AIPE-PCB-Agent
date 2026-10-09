# Workflow and acceptance gates

## 0. Environment and smoke test

Inspect host and repository without overwriting collaborator work. Confirm
software and installation paths before installing. Discover and record the real
KiCad executables. Then generate a small, disposable, fully connected test
circuit and board using the automation layer.

Acceptance requires actual KiCad parsing, ERC, DRC (including unrouted items and
schematic parity), schematic PDF, board PDF, Gerber and drill exports. Record
commands, versions, exit codes and nonempty artifacts. Fix issues and rerun.
Library checks must use the installed or project-local symbol/footprint tables.
The converter work remains gated until this succeeds.

## 1. Requirements and engineering

Translate the task into explicit SI-unit inputs and a separate assumption
register. Unspecified limits must not masquerade as user requirements.
Resolve input range, operating temperature/cooling, ripple and transient targets,
mechanical constraints, manufacturing capabilities and control/firmware scope.
Use documented engineering judgement for routine decisions.

Produce reproducible calculations, component stress/loss estimates, protection
thresholds, thermal assumptions and manufacturer references. Document uncertainty
instead of substituting invented ratings or untested operating claims.

## 2. Schematic and board

Complete power, auxiliary supply, DSP, sensing, protection, clock, reset and
debug circuitry. Assign verified footprints, run ERC and correct violations.
Define a justified stack-up; place, route and inspect all intended connections.
Run DRC, schematic parity, footprint and connectivity checks. Treat CAD errors
as release blockers. Document any warning disposition individually.

## 3. Engineering review and release

Apply `pcb-design-rules.md` independently of CAD checks. Each rule needs evidence
and a truthful result: pass, fail, unverified or not applicable with justification.
Unverified engineering constraints must remain visible to the human reviewer.

Export the required manufacturing files and review package. Check the rendered
schematic and board views, reconcile BOM and placement files, then freeze V1
under `examples/buck-48v-24v-1kw/releases/v1/` with a file/hash manifest.
Never call a partial board a completed V1. Never rewrite a frozen V1 later.

Commit meaningful checkpoints and push to the existing remote when authorised
credentials permit. Open the requested PR only when its actual status can be
described accurately. No physical power-up and no V2 without human feedback.
