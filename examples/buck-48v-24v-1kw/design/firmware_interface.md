# Firmware interface contract - hardware V1

This is a required implementation contract, not working or tested firmware.
Hardware CAD completion does not establish stable closed-loop operation.

| Function | DSP / signal | Required interpretation |
|---|---|---|
| High / low PWM | GPIO0 / GPIO1, pins 5 / 6 | ePWM1A / ePWM1B; active high through enable logic |
| Arm | GPIO2, pin 7 | Rising edge latches enable only while FAULT_N is high |
| Hardware trip | GPIO12 / TZ1, pin 21 | FAULT_N low must asynchronously force both PWM outputs low |
| Vin | ADCINA0, pin 42 | Divider factor 4.99 / 125.99; 54 V -> 2.139 V |
| Vout | ADCINA1, pin 41 | Divider factor 1 / 11; 24 V -> 2.182 V |
| Current | ADCINA2, pin 40 | 0.002 ohm x gain 20 = 40 mV/A; positive current only |
| Temperature | ADCINA3, pin 39 | LM61 nominal 0.6 V + 10 mV/C; local PCB temperature |
| Clock | XCLKIN, pin 105 | External 30 MHz; configure PLL only after clock checks |
| Reset | XRS, pin 80 | External open-drain collection; do not drive push-pull high |
| UART | GPIO29 TX pin 2 / GPIO28 RX pin 141 | 3.3 V SCI-A; no RS232 voltage tolerance |

On reset, keep both PWM commands and ARM low, configure TZ1 as a one-shot
asynchronous trip, and leave gate enable cleared. Check rail stability,
reference calibration, plausible sensor values and acceptable input voltage
before arming. Set flash wait states and clock/PLL settings for the actual
silicon and 1.9 V core; use TI's device documentation.

For a 150 MHz time-base clock with no prescaler, center-aligned up/down counting
at 100 kHz uses TBPRD=750. An initial 200 ns dead-band is 30 TBCLK ticks. This is
only an initial timing choice: establish the real switching delays and avoid
cross-conduction across temperature, current and supply. Never rely on the
combinational XOR/AND network to generate deadtime.

Bootstrap supply requires low-side refresh; do not command 100% high-side duty.
Use a conservative duty ceiling (initial software proposal 0.80) and controlled
soft start. Enable synchronous low-side operation only under a reviewed
positive-current strategy; do not force reverse current into an unqualified
input supply. Prebiased-output startup is not supported by this V1 contract.

ADC sample timing should avoid switching edges. Set an acquisition window that
allows the 100 ohm / 1 nF front-end network and DSP sample capacitance to settle.
The ADC full-scale is 3 V. Calibrate offset/gain, especially shunt current and
temperature; rail clamps are not precision 3 V limiters. Implement lower
software current/temperature limits before the hardware fault thresholds.

A voltage-loop plant model, compensator, current limiting, anti-windup,
load-step behavior and stability margins remain to be developed and reviewed.
The approximately 796 Hz nominal LC resonance does not establish a valid
control bandwidth. No gains are invented in this package.

Any fault must keep PWM outputs low and latch a diagnostic. Do not repeatedly
auto-retry a short. Release requires an explicit reviewed restart sequence and
new ARM edge. Verify reset/enable behavior during brownout, loss of 5 V/12 V,
debugger attach, missing clock and firmware hang before any later power tests.

J8 1-2 sets GPIO84 low (SCI-A boot); J8 2-3 or no jumper selects Flash (1111).
Never connect a 5 V UART or a debugger's supply output to these rails. This task
does not authorize physical connection, fabrication or energization.
