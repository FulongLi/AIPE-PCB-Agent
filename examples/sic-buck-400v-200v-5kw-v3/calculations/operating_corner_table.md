# V3 reproducible electrical sizing

Run `python -m automation.sic_v3.calculations`. Full numeric precision and assumptions: `results.json`. These are analytical estimates, not measurements or guaranteed efficiency.

| Vin | Iout | AL factor | L at peak | ripple | peak | loss | efficiency | HS Tj |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 360 V | 25 A | 0.92 | 350.3 uH | 5.08 A | 27.54 A | 105.7 W | 97.93% | 102.0 C |
| 360 V | 25 A | 1.00 | 381.5 uH | 4.66 A | 27.33 A | 105.6 W | 97.93% | 101.9 C |
| 360 V | 25 A | 1.08 | 412.8 uH | 4.31 A | 27.15 A | 105.5 W | 97.93% | 101.9 C |
| 360 V | 30 A | 0.92 | 331.1 uH | 5.37 A | 32.68 A | 138.7 W | 97.74% | 123.1 C |
| 360 V | 30 A | 1.00 | 360.9 uH | 4.93 A | 32.46 A | 138.7 W | 97.74% | 123.1 C |
| 360 V | 30 A | 1.08 | 390.6 uH | 4.55 A | 32.28 A | 138.6 W | 97.74% | 123.1 C |
| 400 V | 25 A | 0.92 | 349.1 uH | 5.73 A | 27.86 A | 109.1 W | 97.87% | 102.5 C |
| 400 V | 25 A | 1.00 | 380.4 uH | 5.26 A | 27.63 A | 109.0 W | 97.87% | 102.5 C |
| 400 V | 25 A | 1.08 | 411.6 uH | 4.86 A | 27.43 A | 108.9 W | 97.87% | 102.5 C |
| 400 V | 30 A | 0.92 | 329.8 uH | 6.06 A | 33.03 A | 142.6 W | 97.68% | 123.2 C |
| 400 V | 30 A | 1.00 | 359.5 uH | 5.56 A | 32.78 A | 142.5 W | 97.68% | 123.2 C |
| 400 V | 30 A | 1.08 | 389.3 uH | 5.14 A | 32.57 A | 142.4 W | 97.68% | 123.2 C |
| 440 V | 25 A | 0.92 | 348.2 uH | 6.27 A | 28.13 A | 112.4 W | 97.80% | 103.5 C |
| 440 V | 25 A | 1.00 | 379.4 uH | 5.75 A | 27.88 A | 112.3 W | 97.80% | 103.4 C |
| 440 V | 25 A | 1.08 | 410.7 uH | 5.31 A | 27.66 A | 112.2 W | 97.81% | 103.4 C |
| 440 V | 30 A | 0.92 | 328.6 uH | 6.64 A | 33.32 A | 146.3 W | 97.62% | 123.9 C |
| 440 V | 30 A | 1.00 | 358.4 uH | 6.09 A | 33.04 A | 146.2 W | 97.62% | 123.9 C |
| 440 V | 30 A | 1.08 | 388.1 uH | 5.62 A | 32.81 A | 146.1 W | 97.62% | 123.9 C |

The ripple iteration evaluates inductance at the current peak, rather than using only its DC operating value. Load current, AL tolerance and all three input corners are independent sweep axes.
