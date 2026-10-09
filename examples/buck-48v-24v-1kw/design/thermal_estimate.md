# V1 thermal estimate and limits

The reproducible loss budget is in calculations.json. It combines manufacturer
maximum DC resistance with clearly identified hot-resistance, switching-time,
reverse-recovery, core-loss and interconnect assumptions. It is not a thermal
simulation or measurement.

Use an external heatsink with total sink-to-air thermal resistance no greater
than 1.5 C/W under its specified forced airflow. Budget 0.5 C/W per isolated
TO-220 interface plus the CSD19536KCS maximum 0.4 C/W junction-to-case. Drain
tabs are electrically live: high-side tabs are VIN; low-side tabs are SW. A
common conductive heatsink requires verified insulating pads and shoulder
washers. Heatsink selection and its mechanical drawing remain review items.

With 25 W spread over the four MOSFETs at 50 C ambient, the sink rise would be
37.5 C and an 8 W hottest device would add about 7.2 C junction-to-sink. This
illustrative 95 C junction estimate excludes airflow obstruction and uneven
sharing; doubling the heat invalidates the assumed margin. Do not rate the
converter for continuous 1 kW from this arithmetic alone.

The inductor copper budget uses DCR at 100 C. The 4 W core-loss allocation needs
manufacturer loss data or measurement at the actual waveform. The shunt
dissipates about 3.5 W; its 6 W rating is conditional on terminal temperature.
Give its force terminals substantial copper without compromising Kelvin sense.

The dual LDO loses about 1.58 W for a 400 mA core / 200 mA I/O budget. Its exposed
pad needs a grounded thermal-via matrix and connected copper on multiple layers.
Actual DSP current depends on clocks and enabled peripherals. Confirm regulator
junction temperature and rail transients with the application firmware.

The input capacitor group has limited ripple-sharing margin. Review hot-spot
can temperature and life with the actual airflow. Copper and via resistance
calculations establish loss estimates only; temperature rise, plated slots,
connector joints, fuse studs and narrow necks require a fabricator/engineer review.
