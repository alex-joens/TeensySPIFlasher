# Teensy 4.1 SPI Flasher by Jak Atackka
This is a basic utility for reading and writing to flash memory chips that use the SPI interface. This was originally written for flashing the NOR chip on a PS4, but it can be adapted to a variety of devices.

It is partially based on hjudge's [SPIway utility](https://github.com/hjudges/NORway/tree/master), which was originally written for the Teensy 2.0++.

# Disclaimer
**WARNING**: Use this software at your own risk. The author accepts no responsibility for any consequences of using this software.

# Supported Hardware
- Teensy 4.1
  - This should work on a Teensy 4.0 with some minor code changes
  - This can likely be adapted to other Arduino controllers as well
- Only the **Macronix MX25L25635F** is supported. Code changes are required to support the other chips.

This has been tested with the NOR chip still attached to the motherboard.

# Requirements
## Python Setup
Requirements:
- Python 2.7
- pyserial 2.5

## Teensy Software Setup
I am not distributing a `.hex` file because I haven't added a way to adjust the read/write clock speeds. You may need to adjust them to find values that are stable for your chip.

Follow [this guide](https://www.pjrc.com/teensy/td_download.html) to install the Arduino IDE and add the Teensy boards to the board manager.

To compile the code, simply open `TeensySPIFlasher/TeensySPIFlasher.ino` in the Arduino IDE and click "Verify". To deploy the code, you can click the "Upload" button from within the Arduino IDE, or you can open the build folder and deploy the `.hex` file manually.

## Teensy Hardware Setup
Follow the [MODDED WARFARE guide](https://www.youtube.com/watch?v=JxeSP1PJtEs) for installing a Teensy to quickly revert the PS4's hardware.

For the Teensy 4.1, use the following pins:
- **CS#**: Pin 10
- **SI/SIO0**: Pin 11
- **SO/SIO1**: Pin 12
- **SCLK**: Pin 13
- **WP#/SIO2**: Pin 14
- **HOLD#/RESET#**: Pin 15

# Usage
This is designed to work just like `SPIway` (see the [SPIway README](https://github.com/hjudges/NORway/blob/master/SPIway_README.txt)). After compiling and deploying the code to your Teensy, connect your PC to the Teensy over USB. You can check **Windows Device Manager > Ports (COM & LPT)* to find which COM port is assigned to the Teensy.

First, confirm that your Teensy can read from the NOR chip and recognizes it:

> `TeensySPIFlasher.py COMx info`

Dump the ROM contents (run this command multiple times and confirm the checksums match):

> `TeensySPIFlasher.py COMx dump filename`

Write a new ROM to the chip and verify the contents are correct:

> `TeensySPIFlasher.py COMx vwrite filename`

Erase the chip:

> `TeensySPIFlasher.py COMx erasechip`
