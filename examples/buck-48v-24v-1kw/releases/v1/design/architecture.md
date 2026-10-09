# V1 electrical architecture

The input feeds a 40 A / 70 V bolt-down fuse, local TVS, 14 bulk capacitors and
eight local high-frequency ceramics. Two 100 V MOSFETs form each half-bridge leg.
A 10 uH inductor and four-terminal 2 mohm shunt feed the output capacitor bank
and M5 output terminal. The return bus connects the output and input returns.

The UCC27211 gate driver has independent gate resistors for each MOSFET. Bootstrap
and VDD bypass parts are immediately adjacent to its pins. A latched enable and
logic gates inhibit both PWM paths on reset or fault. A combinational overlap
inhibit supplements, but does not replace, the DSP dead-band generator.

Auxiliary conversion is 48 V -> LM5164 12 V -> TPS54302 5 V -> TPS767D301
1.9 V and 3.3 V. A transistor enables the I/O rail only after core power-good.
Open-drain rail reset signals and a 5 V supervisor hold XRS low. The core output
uses substantial bulk capacitance; early power-down reset timing must be measured.
The LM5164 has its prescribed COT ripple-injection network, not merely an FB divider.

The TMS320F28335PGFA uses a 30 MHz 3.3 V oscillator on XCLKIN, X1 grounded, X2
unconnected, external JTAG pulldown/pullups, flash-boot straps, per-supply-pin
decoupling, ADC reference capacitors and a 22 kohm ADC bias resistor. TEST1 and
TEST2 remain unconnected. Unused analog inputs go to analog ground; unused
digital pins are explicitly marked unused. A 3.3 V UART header exposes SCI-A.

Vin and Vout are divided and buffered. INA240A1 measures inductor current after
the inductor using true Kelvin shunt terminals. LM61 measures power-area PCB
temperature, not MOSFET junction temperature. Separate comparators implement
overcurrent, output overvoltage, overtemperature, and input undervoltage. Faults
clear the hardware enable latch and reach the DSP trip-zone input. Recovery
requires an explicit arm edge after all faults clear.

The analog and digital grounds are one electrical net with placement-controlled
return paths over continuous planes. There is no split under ADC or PWM tracks.
Switch-node copper and plane exposure are restricted to the power area. Sensor
traces avoid the inductor, switching node and gate loops.

Sources, revisions and download hashes are in `../components/references.json`.
The DSP, driver, regulator and sensor implementations use their manufacturer
pin/function tables. Library symbols and custom pin mappings must be checked
against those tables before the schematic milestone is marked complete.
