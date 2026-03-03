### AS1100™ Accurate Distance Sensor

# User’s Manual

```
For use with AS1100™ Accurate Distance Sensor
```
```
June 14, 2024
```
### Acuity

A product line of Schmitt Measurement Systems, Inc.
8000 NE 14th Place
Portland, OR 97211
[http://www.acuitylaser.com](http://www.acuitylaser.com)


AS1100 Manual i

```
Limited Use License Agreement
```
##### CAREFULLY READ THE FOLLOWING TERMS AND CONDITIONS BEFORE OPENING THE

##### PACKAGE CONTAINING THE PRODUCT AND THE COMPUTER SOFTWARE LICENSED

##### HEREUNDER. CONNECTING POWER TO THE MICROPROCESSOR CONTROL UNIT

##### INDICATES YOUR ACCEPTANCE OF THESE TERMS AND CONDITIONS. IF YOU DO NOT

##### AGREE WITH THE TERMS AND CONDITIONS, PROMPTLY RETURN THE UNIT WITH

##### POWER SEAL INTACT TO THE DEALER FROM WHOM YOU PURCHASED THE PRODUCT

##### WITHIN FIFTEEN DAYS FROM DATE OF PURCHASE AND YOUR PURCHASE PRICE WILL

##### BE REFUNDED BY THE DEALER. IF THE DEALER FAILS TO REFUND YOUR PURCHASE

##### PRICE, CONTACT SCHMITT MEASUREMENT SYSTEMS, INC. IMMEDIATELY AT THE

##### ADDRESS SET OUT BELOW CONCERNING RETURN ARRANGEMENTS.

Schmitt Measurement Systems, Inc. provides the hardware and computer software program
contained in the microprocessor control unit. Schmitt Measurement Systems, Inc. has a
valuable proprietary interest in such software and related documentation ("Software), and
licenses the use of the Software to you pursuant to the following terms and conditions. You
assume responsibility for the selection of the product suited to achieve your intended results,
and for the installation, use and results obtained.

```
License Terms And Conditions
```
a. You are granted a non-exclusive, perpetual license to use the Software solely on and in
conjunction with the product. You agree that the Software title remains with Schmitt
Measurement Systems, Inc. at all times.

b. You and your employees and agents agree to protect the confidentiality of the Software.
You may not distribute, disclose, or otherwise make the Software available to any third
party, except for a transferee who agrees to be bound by these license terms and
conditions. In the event of termination or expiration of this license for any reason
whatsoever, the obligation of confidentiality shall survive.

c. You may not disassemble, decode, translate, copy, reproduce, or modify the Software,
except only that a copy may be made for archival or back-up purposes as necessary for
use with the product.

d. You agree to maintain all proprietary notices and marks on the Software.

e. You may transfer this license if also transferring the product, provided the transferee agrees
to comply with all terms and conditions of this license. Upon such transfer, your license will
terminate and you agree to destroy all copies of the Software in your possession.


AS1100 Manual ii

## Procedures for Obtaining Warranty Service

1. Contact your Acuity distributor or call Schmitt Measurement Systems, Inc. to obtain a
return merchandise authorization (RMA) number within the applicable warranty period.
Schmitt Measurement Systems will not accept any returned product without an RMA
number.
2. Ship the product to Schmitt Measurement Systems, postage prepaid, together with
your bill of sale or other proof of purchase. your name, address, description of the
problem(s). Print the RMA number you have obtained on the outside of the package.

```
This device has been tested for electromagnetic emissions and immunity and has been
found to be in compliance with the following directives for class A equipment:
```
```
EN 60825-1:
```
```
This device complies with part 15 of the FCC Rules. Operation is subject to the
following two conditions:
```
```
(1) This device may not cause harmful interference, and (2) this device must accept
any interference received, including interference that may cause undesired operation.
```
```
Note: This equipment has been tested and found to comply with the limits for a Class A
digital device, pursuant to part 15 of the FCC rules. These limits are designed to provide
reasonable protection against harmful interference when the equipment is operated in a
commercial environment. This equipment generates, uses, and can radiate radio
frequency energy and, if not installed and used in accordance with the instruction manual,
may cause harmful interference to radio communications. Operation of this device in a
residential area is likely to cause harmful interference in which case the user will be
required to correct the interference at his or her own expense.
```
```
This manual copyright © 2024, Schmitt Measurement Systems, Inc.
```

## AS1100 Manual iii



- 1 Introduction Table of Contents
   - 1.1 General Overview
   - 1.2 Component Diagram
   - 1.3 Technical Specs
- 2 Sensor Description
   - 2.1 Principle of Operation
   - 2.2 Prohibited Use/Limits to Use
      - 2.2.1 Prohibited Actions
      - 2.2.2 Environmental Limits
      - 2.2.3 Application Limits
   - 2.3 Laser Dimensions
   - 2.4 Laser Safety Label...........................................................................................................................................
   - 2.5 Identification Label
   - 2.6 Label Location
   - 2.7 Sensor Maintenance
   - 2.8 Sensor Service
- 3 Signal and Power Interface
   - 3.1 Cable Description
   - 3.2 Connector Pinout/Cable Color Codes
   - 3.3 Screw Terminals
   - 3.4 USB Mini Jack
   - 3. 5 Reset Button...................................................................................................................................................
   - 3.6 Power Supply (Red, Black wires)....................................................................................................................
   - 3.7 Serial Communications
      - 3.7.1 RS232 Serial Communication (Orange, Gray-Pink)
      - 3.7.2 RS422/RS485 Serial Communication (Blue, Green, Violet, Yellow)
   - 3.8 Analog Output (Brown)
      - 3.8.1 Minimum Analog Output Measurement Value
      - 3.8.2 Analog Error Value
   - 3.9 Digital Signal Outputs (White, Pink, Gray)
   - 3.10 Digital Trigger Input (Pink)
   - 3.11 Status LEDs...............................................................................................................................................
- 4 Commands AS1100 Manual iv
   - 4.1 Syntax
      - 4.1.1 Command termination - <CrLf>
      - 4.1.2 Sensor Identification - #......................................................................................................................
      - 4.1.3 Parameter Separator - +/ -
      - 4.1.4 “Set” and “Read” Commands
      - 4.1.5 Startup String
      - 4.1.6 Errors
      - 4.1.7 DO1/DI (Pink Wire)..............................................................................................................................
   - 4.2 Operation Commands
      - 4.2.1 Stop/Clear – [s#c]
      - 4.2.2 Single Distance Measurement – [s#g]
      - 4.2.3 Single Sensor Tracking – [s#h].............................................................................................................
      - 4.2.4 Timed Sensor Tracking – [s#h+aaaaaaaa]
      - 4.2.5 Buffered Sensor Tracking – [s#f]
      - 4.2.6 Read Tracking Buffer – [s#q]
      - 4.2.7 Signal Strength Measurement – [s#m]
      - 4.2.8 Temperature Measurement – [s#t]
      - 4.2.9 Read/Clear Error Stack – [s#re]/[s#ce]
      - 4.2.10 Laser On – [s#o]
   - 4.3 Configuration Commands
      - 4.3.1 Save Configuration – [s#s]...................................................................................................................
      - 4.3.2 Reset to Factory Default – [s#d]
      - 4.3.3 Set Serial Interface Parameters – [s#br]
      - 4.3.4 Set Sensor ID – [s#id]
      - 4.3.5 Analog Output Minimum Current – [s#vm]
      - 4.3.6 Analog Output Error Value – [s#ve]
      - 4.3.7 Analog Output Distance Range – [s#v]
      - 4.3.8 Digital Signal Output Type – [s#ot]
      - 4.3.9 Digital Signal Output Thresholds – [s#1], [s#2]...................................................................................
      - 4.3.10 Digital Trigger Input Function – [s#DI1]
      - 4.3.11 Read Digital Trigger Input Status – [s#RI]
      - 4.3.12 Measuring Mode – [s#mc]
      - 4.3.13 Measurement Filter Configuration – [s#fi]
      - 4.3.14 Auto Start Configuration – [s#A]
   - 4.4 Advanced Configuration Commands AS1100 Manual v
      - 4.4.1 User Output Format – [s#uo]
      - 4.4.2 User Distance Offset – [s#uof]
      - 4.4.3 User Distance Gain Factor – [s#uga]
   - 4.5 Informational Commands
      - 4.5.1 Firmware Version [s#sv]
      - 4.5.2 Serial Number [s#sn]
- 5 Quick Reference Tables
   - 5.1 Command Reference.
   - 5.2 Error Codes


## 1 Introduction

### 1.1 General Overview

```
The AS1100 is a long-distance sensor can measure targets with an accuracy of ± 3mm
(0.12 in) up to 100m (328 ft) away on natural targets and up to 150m (492 ft) away with
the aid of an Acuity reflective target. The AS1100 is a rugged laser sensor that can
accurately measure on difficult targets, including dark surfaces, surfaces in sunlight, and
glowing targets up to 1400°C. The maximum measurement frequency of the AS1100 is
100Hz in optimal conditions.
```
```
The AS1100 can communicate using RS-232, RS-422, or RS-485 serial protocols by
adjusting a single parameter. There is also a mini-USB connection under the back cover
that can be connected to a PC for easy configuration and troubleshooting. The AS
also comes with a current loop analog output with a user-configurable measurement
span that can output at a 4-20 mA or 0-20 mA current range.
```
### 1.2 Component Diagram

```
Figure 1: Diagram of AS1100 Components
1) Reset Button
2) Screw terminal block and plug. Accommodates
up to 16 AWG (0.05” dia.) wire.
3) Tab to connect wire shielding.
4) Slot holes for installation.
5) Socket set screw for sensor alignment.
6) Sensor front.
7) Product label.
```
```
8) Status LEDs.
9) Communications port (not currently used)
10) USB 2.0 socket (mini-B).
11) User removable back cover.
12) Valve diaphragm.
13) Cable connector.
14) Screws (recommended torque: 1.6 Ncm)
```

### 1.3 Technical Specs

**_Table 1: AS1100 Specifications_**
**English Units Metric Units**
Range ~2 in. min. to 328 ft. max (natural targets)
~131 ft. min. to 492 ft. max (reflective foil*)

```
0.05...~100 m (natural targets)
~ 40 ... 150 m max (reflective foil*)
Accuracy @ 2σ ± 0. 119 in. ± 3 mm
Repeatability @ 2σ 0.0 28 in. 0. 7 mm
Resolution 0.0 04 in. 0. 1 mm
Laser spot diameter
@ 10, 50, 100 m
```
```
0.28 x 0.12 in.; 1.10 x 0.51 in.; 2.16 x 1.81 in. 7 x 3 mm; 28 x 13 mm; 55 x 30 mm
```
```
Dimensions (l x w x h) 5.51 x 3.07 x 1.89 in. 140 x 78 x 48 mm
Weight (less cable) 0.77 lbs. 350 grams
Laser class Class 2, Complies with 21 CFR 1040.10 and with Laser Notice 50, IEC/EN60825-1:
Laser type Typical 650 nm (620 – 690 nm), <1 mW visible RED
Power 12 - 30 Volts DC; Max. Current: 0.2A
Sample rates 100 Hz
Operating temp 14 to 122 °F - 10 to 50 °C
Environmental IP
Material Sensor body: Aluminum Alloy EN-AW 6060 (Anodized 20μm)
Front and back cover: Mineral reinforced nylon resin
Shock & Vibration IEC 60068- 2 - 27 (Shock); IEC 60068- 2 - 6 (Vibration)
Outputs: Serial RS232, RS422, RS485, (USB connection only for configuration)
Analog output,
programmable
```
```
4 - 20 mA/0-20mA software configurable
```
```
Measuring accuracy
of analog output
```
```
± 0.1 % of the programmed AO range or ± 3 .0 mm
(Whichever is greater)
*Contact Acuity for these targets. Other reflectivity targets can damage the sensor. Contact a sales rep for pricing.
```

## 2 Sensor Description

### 2.1 Principle of Operation

```
The AS1100 measures distance using a direct time-of-flight measurement of the laser
beam and a measurement of the phase shift between the beam as it exits and reenters
the sensor. In combination, this allows for precise measurements with targets at long
distances.
```
```
The laser beam leaves the sensor front through a small lens that is adjacent to the larger
main lens. The light reflects off the target then is collected through the main lens. The
light is then both measured to determine its time of flight and is compared to the
outgoing beam to determine the phase shift. This information is processed by the
sensor and the information communicated through serial and analog outputs accessed
through the cable connector, the screw terminals, or the mini-USB port.
```
### 2.2 Prohibited Use/Limits to Use

```
The AS1100 may not be used in any way contrary to this manual, in any way that may
jeopardize the safety of the user or others, or in any way contrary to local laws and
regulations.
```
#### 2.2.1 Prohibited Actions

```
Prohibited actions include, but are not limited to:
```
```
 Using the sensor without proper safety training.
 Using outside of stated limits.
 Deactivating of safety systems or removal of hazard labels.
 Opening the sensor (Except the user removable back cover. See section
1.2)
 Modifying the sensor internals or the main body of the sensor.
 Aiming sensor directly into the sun.
 Pointing the laser beam directly at 3rd parties or in areas where others
may be affected by the beam.
```
#### 2.2.2 Environmental Limits

```
Do not use the AS1100 in the following environmental conditions:
```
```
 Volatile or corrosive vapor or liquids (Salt, acid, poison, etc.)
 Snow or rain (without an appropriate protective casing)
 Radiation
 Explosive environments
 High-gloss (mirror-like) targets.
```
#### 2.2.3 Application Limits

```
The AS1100 cannot be used in the following applications:
```
```
 Aerospace (Aviation and Space Flight)
 Nuclear technology
```

### 2.3 Laser Dimensions

```
The diagram below is measured in mm [in.]. The red line is the path of the laser beam.
```
**_Figure 2: AS1100 Dimensions_**

### 2.4 Laser Safety Label...........................................................................................................................................

```
The AS1100 uses a Class 2 laser with a continuous output of < 1mW. The following
warning label is placed on the sensor body.
```
```
Figure 3: Laser Safety Label
```

### 2.5 Identification Label

```
Figure 4: AS1100 ID Label
```
### 2.6 Label Location

```
Figure 5: Laser Safety Label Location Figure 6: ID Label Location
```
### 2.7 Sensor Maintenance

```
The AS1100 sensor requires little maintenance from the user. The sensor lens should be
kept clean of dust buildup as a part of regular preventative maintenance. Use
compressed air to blow dirt off the windows or use delicate tissue wipes. Do not use any
organic cleaning solvents on the sensor. If your sensor does not function according to
specifications, contact Schmitt Measurement Systems, Inc.
```
```
Except for the removable back cover, do not attempt to loosen any screws or open the
sensor housing.
```
### 2.8 Sensor Service

```
The AS1100 sensor is not user-serviceable. Refer all service questions to Schmitt
Measurement Systems, Inc.
```
```
Except for the removable back cover, do not attempt to loosen any screws or open the
sensor housing.
```

## 3 Signal and Power Interface

### 3.1 Cable Description

```
The AS1100 comes with an M12, 1.25 mm thread, 12 pin male connector attached
(similar to a Binder 713 series connector). A connecting cable that terminates in flying
leads can be ordered from an Acuity salesperson at lengths of up to 35 meters (
feet).
```
### 3.2 Connector Pinout/Cable Color Codes

```
Table 2: Cable Pinout
Pin # Wire Color Function
1 Brown Analog Out (AO)
2 Orange RS232 RX Data (RXD)
3 Black Ground (GD)
4 White Digital Error Output (DOE)
5 Gray-Pink RS232 TX Data (TXD)
6 Pink Digital Signal Output #1 (DO1)/
Digital Trigger Input (DI1)*
7 Gray Digital Signal Output #2 (DO2)
8 Red Power 12-30 VDC (V+)
9 Blue RS422 T+ /485 D+ (T+)
10 Green RS422 T- /485 D- (T-)
11 Violet RS422 R+ /485 D+ (R+)
12 Yellow RS422 R- /485 D- (R-)
* “DO1” is the label used on the AS1100 screw terminals. In this manual this
connection will be referred to as “DI1” when it is used as a trigger input
(See sections 3.9 and 3.10)
```
### 3.3 Screw Terminals

```
Removing the back cover of the AS1100 will reveal screw terminals that connect to the
connector on the back cover. The wires can be removed from the screw terminals by the
user so that other wires or a cable can be attached.
```
```
Note: The labels on the terminals correspond to the wire functions in section 4.2. The
terminals use the abbreviations listed in parentheses.
```
```
Caution: Wires connected to the terminals incorrectly can damage the AS1100. Take
steps to verify the correct wiring before attempting to apply voltage.
```
```
Figure 7 : AS1100 Male Connector
```

### 3.4 USB Mini Jack

```
Also found inside the back cover of the AS1100 is a USB Mini-B jack. Connecting a
standard USB 2.0 A male to Mini-B male cable will allow the sensor to act as its own
RS232 serial to USB adapter to a PC. This can aid in quick testing and troubleshooting of
the sensor.
```
```
Note: Connecting the AS1100 to a PC using the USB Mini jack is not recommended for
long term use. Exposing the rear circuit board increases the risk of damage to
the board. The IP65 rating only applies when the rear cover is securely attached
and operated through the rear connector.
```
### 3. 5 Reset Button...................................................................................................................................................

```
The reset button is also found inside the AS1100 back cover. To reset the AS1100 to
factory settings please use the following procedure:
```
1. Remove power from the AS1100 if it is currently powered on.
2. Press the reset button and hold while applying power.
3. Continue holding the reset button with the power on until the status LEDs all
    flash for a half second.
4. Release the reset button and power off.
Upon restoring power, the AS1100 will be configured to factory settings.

### 3.6 Power Supply (Red, Black wires)....................................................................................................................

```
The Black wire is the Power Supply Common return, also named Ground. It carries the
return current for the power supply and the analog signals.
```
```
The Red wire is the Power Supply Input to the sensor. The sensor requires 12 - 30 VDC
power and consumes 2 – 4 Watts of power (< 0.2A draw) depending on the sensor’s
configuration.
```
```
Power supplies from 12 – 30 VDC may be used, but 15 – 24 VDC power supplies are
recommended to protect against any excursions. Higher voltages will result in excessive
current drawn by the over-voltage protection circuitry and may cause permanent
damage. Voltages less than 10 VDC may result in inaccurate measurement readings.
```
### 3.7 Serial Communications

```
The AS1100 uses a serial connection for sensor configuration and issuing commands. It
can also be used to collect data. Commands and replies are all ASCII based. Please refer
to Section 5.1 for a comprehensive list of commands and detailed descriptions of each
command’s function and parameters.
```

The AS1100 supports RS232, RS422, and RS485 serial protocols. The default
communication rate is 19,200 baud, but 9,600 baud and 115,200 baud are also
supported for all serial protocols. For the measurement speeds of 100Hz, a 115,
baud connection is required.

(See section 4.3.3: Set Serial Interface Parameters)

The AS1100 cable has dedicated wires for the RS232 and RS422/485 connections.

**Note:** For PCs without dedicated serial ports, Acuity recommends serial to USB
converters that use FTDI chips.

#### 3.7.1 RS232 Serial Communication (Orange, Gray-Pink)

```
The RS232 Serial Communication Standard is normally used for shorter
distances of communications (max. cable length: 15 meters). Only one
transmitter and one receiver are allowed per network. A standard DB9 RS
serial female connector can be built to interface with an RS232 serial port or a
serial to USB converter using the pins below.
```
```
Table 3: RS232 Cable Wires and Functions
Wire Color DB9 Pin Function
Gray-Pink 2 Transmit data from sensor (TXD)
Orange 3 Receive data from sensor (RXD)
Black 5 Ground (GD)
```
#### 3.7.2 RS422/RS485 Serial Communication (Blue, Green, Violet, Yellow)

```
RS422 and RS485 serial connections can be used to connect multiple AS
units to your PC or PLC. Up to 100 AS1100s can be connected on the same
network in this fashion. RS422 and RS485 connections also support much longer
cables. A 115,200 baud connection can be transmitted over cables up to 500
meters long.
```
```
When wiring a RS422 or RS485 connection to a PC using a serial to USB
connector or a PLC, follow the pinout for the connecting hardware. There is no
standard pinout for wiring an RS422 or RS485 connection to a DB9 connection,
so the correct pin configuration will vary. The table below shows the
appropriate wires from our cable, the abbreviations used on the screw
terminals, and their functions.
```
```
Table 4: RS422/RS485 Cable Wires and Functions
Wire Color Term. Abbr. RS422 RS
Blue T+ Transmit + Data +
Green T- Transmit - Data -
Violet R+ Receive +
Yellow R- Receive -
Black GD Ground Ground
```

```
Note: When connecting multiple AS1100s to an RS422 or RS485 connection,
termination resistors should be used that are equal to the cable
impedance.
```
```
Caution: When connecting more than one AS1100s on the same RS422 or
RS485 connection, do not issue commands with continuous answers
(ex. Single Sensor Tracking). The constant responses will prevent
issuance of additional commands. If tracking is needed, use
Buffered Sensor Tracking (Section 4.2.5) and issue commands to
read each sensor’s buffer as needed.
```
### 3.8 Analog Output (Brown)

```
The analog output for the AS1100 is a current loop transmitted through the brown (AO)
wire that can be set to 4-20 mA or 0-20 mA (See section 4.3.5). The return signal should
be routed through the black (ground, GD) wire.
```
```
The AO wire delivers a current proportional to the measured distance over a user-set
distance range. The command to set this range can be found in section 4.3.7. This range
The AO wire is supplied by a 12-bit digital to analog converter. This gives the analog
output a resolution of 0.025% of the user-set distance range. Therefore, if the +/- 3 mm
accuracy must be kept while using the analog signal, the AO measurement range should
be set to no more than twelve meters.
```
#### 3.8.1 Minimum Analog Output Measurement Value

```
The minimum analog output measurement value can be set to either 0 or 4 mA
(see section 4.3.5). The AO resolution is the same regardless of the value
selected.
```
#### 3.8.2 Analog Error Value

```
When the AS1100 is in an error state, the analog output will transmit a value
that can be defined by the user (see section 4.3.6). This value can be anywhere
between 0 and 20 mA regardless of the minimum AO measurement value
selected. For example, if the minimum AO value is set at 4 mA, the error value
could be set and displayed at 3 mA.
```

### 3.9 Digital Signal Outputs (White, Pink, Gray)

```
The AS1100 contains two digital outputs (DO1 and DO2) for limit monitoring and one
digital output (DOE) that signals when the sensor is in an error state. These outputs can
be configured as NPN, PNP or Push-Pull outputs. The digital outputs are able to transmit
up to 150 mA and are specified for a voltage of up to 30 VDC. All 3 outputs can be
configured by the user (see sections 4.3.8 and 4.3.9).
```
```
Below are the digital signal output cable wires, their functions, and the associated
abbreviations on the AS1100 screw terminals:
```
```
Table 5: Digital Output Wires and Functions
Wire Color Function Term. Abbr.
White Digital Error Output DOE
Pink Digital Signal Output #1 DO
Gray Digital Signal Output #2 DO
```
```
Note: If any of the digital signal outputs are to be connected to a digital input of a
control device such as a PLC, either the Push-Pull output should be selected, or
an additional pull-up/pull-down resistor should be used along with an NPN or
PNP output.
```
```
Note: If the AS1100 is configured to use a digital trigger input (see section 4.3.10), DO
cannot be used as an output.
```
### 3.10 Digital Trigger Input (Pink)

```
If the AS1100 is configured to accept a digital trigger input (see section 4.3.10), the pink
wire (DO1) no longer outputs current, but it is instead used as the digital input (DI).
```
```
The DI can be used for single measurement triggering or to start/stop tracking
measurements.
```
```
DI Signal Specification:
```
- Low: Less than 2 VDC
- High: Between 9 and 30 VDC

```
Caution: To protect against damage from a short circuit, always use a 1 kΩ resistor
between the input voltage source and the DI.
```

### 3.11 Status LEDs...............................................................................................................................................

```
The AS1100 has 4 LEDs on the top of the sensor. They show the operating status of the
sensor and the digital outputs (DO1, DO2). See the table below for more detail:
```
```
Table 6: Status LED Indicators and Corresponding Sensor Status
Power Error DO1 DO2 Sensor Status
ON OFF OFF OFF Power ed and ready for operation.
```
```
ON ON OFF OFF Normal sensor error. The error code is transmitted over serial
connec tions. (see sec tion _____ for error codes)
```
```
ON OFF ON/OFF ON/OFF Normal operation with digital signal outputs. DO1 and DO2 will be
ON or OFF when their signals are ON or OFF.
```
```
ON ON ON ON (Flashing for 0.5s) Sensor resetting to factory default.
```
```
OFF ON ON ON Voltage supplied to sensor is too low or high. If the voltage is
correct and this continues to occur after a power cycle, contact
Acuity technical support.
OFF OFF OFF ON Ready for firmware download.
```

## 4 Commands

### 4.1 Syntax

#### 4.1.1 Command termination - <CrLf>

```
All commands for the AS1100 are ASCII-based and are terminated with a
Carriage Return and Line Feed (<CrLf>) at the end of each command. All replies
from the AS1100 terminate the same way.
```
```
Note 1: When commands or replies are written in this manual, the terminating
<CrLf> should be assumed unless stated otherwise.
```
```
Note 2: If you are attempting to communicate with the AS1100 using a
terminal emulator, and you find the sensor unresponsive, check that it
is terminating each command correctly.
```
#### 4.1.2 Sensor Identification - #......................................................................................................................

```
Each AS1100 has an ID number that can be assigned by the user. The character
‘#’ will represent this ID number in any command in this manual. Please
substitute the target AS1100’s ID number when entering the command.
```
#### 4.1.3 Parameter Separator - +/ -

```
Commands and replies will often use a plus (+) or minus (-) between the
command or reply and a parameter. If both plus (+) and minus (-) can be used,
the command will be written with ‘(+/-)’, but only one will be used in the actual
command.
```
#### 4.1.4 “Set” and “Read” Commands

```
Commands that are saved with parameters will have different syntax to “Set” a
parameter or “Read” a saved parameter to the user. These terms will be used to
make this distinction throughout this manual.
```
#### 4.1.5 Startup String

```
When an AS1100 is powered on, it will transmit the following string after
initialization:
```
```
g#?
```
```
Once this string is received, the sensor is ready for operation. (Remember: ‘#’ is
the sensor’s ID number)
```
#### 4.1.6 Errors

```
When the sensor sends an error in response to a command, it will take the
following form:
```
```
g#@Ezzz
```
```
Where “zzz” is the error code. (See section 5.2 for a list of error codes)
```

#### 4.1.7 DO1/DI (Pink Wire)..............................................................................................................................

```
When the digital trigger input function is enabled (See section 4.3.10), The
digital output function of DO1 (pink wire) is disabled, and it is used for the
digital input. When DO1 is used for digital input, it is referred to as DI to
eliminate confusion.
```
### 4.2 Operation Commands

#### 4.2.1 Stop/Clear – [s#c]

```
Stops any commands currently executing and resets the digital outputs and
status LEDs
```
```
Command s#c
Response g#?
Key # Sensor ID
```
#### 4.2.2 Single Distance Measurement – [s#g]

```
Takes a single distance measurement and cancels any previous measurement
command.
```
```
Command s#g
Response g#g+aaaaaaaa
Key # Sensor ID
aaaaaaaa Distance (unit: 0.1 mm)
```
#### 4.2.3 Single Sensor Tracking – [s#h].............................................................................................................

```
Starts output of continuous measurements for a single sensor. The
measurements will be made as quickly as possible dependent on target
conditions (Max. 100 Hz) and will continue until the Stop/Clear command [s#c]
is given.
```
```
Note on RS422: When using this command with multiple sensors over an
RS422 connection, stop sensor tracking before attempting
to communicate with another sensor.
```
```
Note on RS485: Sensor tracking can’t be stopped with a command over an
RS485 connection. If tracking is started over an RS-
connection it can only be stopped by cycling the sensors
power or by issuing the Stop/Clear command over an RS
or RS422 connection.
```
```
Command s#h
Response g#h+aaaaaaaa (continuously updated)
Key # Sensor ID
aaaaaaaa Distance (unit: 0.1 mm)
```

#### 4.2.4 Timed Sensor Tracking – [s#h+aaaaaaaa]

```
Starts continuous distance measurements of a single sensor at a rate defined by
the user. These measurements will continue until the Stop/Clear command
[s#c] is given.
```
```
See the RS422 and RS485 notes in section 8.2.3.
```
```
Command s#h+aaaaaaaa
Response g#h+bbbbbbbb (continuously updated)
Key # Sensor ID
aaaaaaaa Sampling Time (unit: 1 ms)
[Range: 0-86400000 (0 = max possible rate)]
bbbbbbbb Distance (unit: 0.1 mm)
```
#### 4.2.5 Buffered Sensor Tracking – [s#f]

```
Starts continuous distance measurements of a single sensor to its measurement
buffer at a rate defined by the user. The buffer holds one distance measurement
at a time. When a new measurement is taken the previous measurement is
overwritten. At any time the measurement in the buffer can be retrieved with
the [s#q] command (See section 4.2.6). These measurements will continue until
the Stop/Clear command [s#c] is given.
```
```
Set Command Read Command
Command s#f+aaaaaaaa s#f
Response g#f? g#f+aaaaaaaa
Key # Sensor ID
aaaaaaaa Sampling Time (unit: 1 ms)
[Range: 0-86400000 (0 = max possible rate)]
```
#### 4.2.6 Read Tracking Buffer – [s#q]

```
Reads distance measurement tracking buffer after the [s#f] command is given
(see section 4.2.5). This command returns the current distance measurement in
the buffer and a value that signals if the buffer has updated since the previous
[s#q] command and if the buffer has been updated more than once.
```
```
If distance tracking into the buffer has not been started [s#f], this command
will not work.
```
```
Command s#q
Response g#h+aaaaaaaa+b
Key # Sensor ID
aaaaaaaa Distance (unit: 0.1 mm)
b 0 – Not updated since last request
1 – Updated once since last request
2 – Updated more than once since last request
```

#### 4.2.7 Signal Strength Measurement – [s#m]

```
Triggers a single signal measurement or continuous signal measurements. The
signal strength is returned as a relative number in the range of 0 to ~25,000. The
signal strength value is approximate. It can differ from sensor to sensor and can
depend on environmental conditions.
```
```
If continuous measurements are requested, they will continue until the
Stop/Clear command is given. Continuous signal measurements are subject to
the same RS422/RS485 notes as in section 4.2.3.
```
```
Command s#m+a
Response g#h+bbbbb
Key # Sensor ID
a 0 – Single measurement
1 – Continuous measurements
bbbbb Approximate signal strength (0 - ~25,000)
```
#### 4.2.8 Temperature Measurement – [s#t]

```
Triggers a single internal sensor temperature measurement.
```
```
Command s#t
Response g#h+aaaaa
Key # Sensor ID
aaaaa Temperature (unit: 0.1°C)
```
#### 4.2.9 Read/Clear Error Stack – [s#re]/[s#ce]

```
These two commands allow the user to read and clear the error stack. Errors are
stored in the error stack until the error stack clear command is issued.
```
```
Read Command Clear Command
Command s#re s#ce
Response g#re+aaa+aaa+... g#ce?
Key # Sensor ID
aaa+aaa+... List of error codes in the error stack. The first
code is the most recent. (0 = no errors in stack)
```
#### 4.2.10 Laser On – [s#o]

```
Turns laser on to aid in sensor adjustment. The laser remains on until the
Stop/Clear command is issued [s#c]. This command does not trigger
measurements.
```
```
Command s#o
Response g#?
Key # Sensor ID
```

### 4.3 Configuration Commands

#### 4.3.1 Save Configuration – [s#s]...................................................................................................................

```
Saves current configuration commands to flash (non-volatile) memory.
```
```
For the configuration commands in sections 4.3 and 4.4, issuing these
commands alone updates the sensor configuration in the volatile memory only,
and a power cycle will reset the configuration to the previous values. The save
configuration command [s#s] writes all current configuration parameter to the
flash memory so that they will be retained after a power cycle.
```
```
Note: The reset to factory default command [s#d] (See section 4.3.2) and the
auto start configuration (See section 4.3.14) automatically save their
settings to the flash memory.
```
```
Command s#s
Response g#?
Key # Sensor ID
```
#### 4.3.2 Reset to Factory Default – [s#d]

```
Resets all configuration parameters to factory default and saves them to the
flash memory.
```
```
Note: This also returns communication settings to factory default. If the
communication settings have been changed you may have to
reconfigure your communication device to continue issuing commands.
```
```
Command s#d
Response g#?
Key # Sensor ID
```
#### 4.3.3 Set Serial Interface Parameters – [s#br]

```
Sets the communication parameters (baud rate, data bits, parity, stop bits) for
the serial interface.
```
```
Command s#br+aa
Response g#?
Key # Sensor ID
aa Sets the communication parameters per the
following chart:
aa Baud Rate Data Bits Parity Stop Bits
1 9600 8 none 1
2 19200 8 none 1
6 9600 7 even 1
7 19200 7 even 1
10 115200 8 none 1
11 115200 7 even^1
Default 7
```

#### 4.3.4 Set Sensor ID – [s#id]

```
Sets the sensor ID number (#). After this command is issued, future commands
to the target sensor will need to use the new ID.
```
```
Command s#id+aa
Response g#?
Key # Sensor ID
aa New sensor ID (0-99)
Default 0
```
#### 4.3.5 Analog Output Minimum Current – [s#vm]

```
Sets/reads the analog output minimum current to 0 or 4 mA.
```
```
Set Command Read Command
Command s#vm+a s#vm
Response g#vm? g#vm+a
Key # Sensor ID
a Minimum current for analog output
0 – Minimum current = 0 mA
1 – Minimum current = 4 mA
Default 1 – Minimum current = 4 mA
```
#### 4.3.6 Analog Output Error Value – [s#ve]

```
Sets/reads the analog output current value transmitted in the case of an error. If
the minimum current is set to 4 mA, the error current can be less than the
minimum.
```
```
Set Command Read Command
Command s#ve+aaa s#ve
Response g#ve? g#vm+aaa
Key # Sensor ID
aaa Error current output (unit: 0.1 mA)
If set to 999, the output will transmit the last valid
distance.
Default 0 mA
```

#### 4.3.7 Analog Output Distance Range – [s#v]

```
Sets/reads the current distance measurements that will result in the minimum
analog output (0 or 4 mA) and the maximum analog output (20 mA)
```
```
Set Command Read Command
Command s#v+aaaaaaaa+bbbbbbbb s#ve
Response g#v? g#v+aaaaaaaa+bbbbbbbb
Key # Sensor ID
aaaaaaaa Distance (unit: 0.1 mm) set to minimum analog
output (0 or 4 mA)
bbbbbbbb Distance (unit: 0.1 mm) set to maximum analog
output (20 mA)
Default Minimum: 0 mm
Maximum: 10,000 mm
```
#### 4.3.8 Digital Signal Output Type – [s#ot]

```
Sets/reads the output type for all digital signal outputs (DO1, DO2, and DOE).
The options are NPN, PNP, Push-Pull.
```
```
Set Command Read Command
Command s#ot+a s#ot
Response g#ot? g#ot+a
Key # Sensor ID
a Output type for all digital signal outputs:
0 = NPN
1 = PNP
2 = Push-Pull
Default 0 = NPN
```
#### 4.3.9 Digital Signal Output Thresholds – [s#1], [s#2]...................................................................................

```
Sets/reads the distance thresholds that will trigger and turn off digital signal
outputs DO1 and DO2.
```
```
Set Command Read Command
Command s#a+bbbbbbbb+cccccccc s#a
Response g#a? g# a+bbbbbbbb+cccccccc
Key # Sensor ID
a 1 or 2 for DO1 and DO2, respectively
bbbbbbbb ON value for output
(unit depends on data source)
cccccccc OFF value for output
(unit depends on data source)
Default DO1: ON value – 2005 mm; OFF value – 1995 mm
DO2: ON value – 995 mm; OFF value – 1005 mm
```

#### 4.3.10 Digital Trigger Input Function – [s#DI1]

```
Enables digital input control and sets/reads the current function/event that the
digital trigger inputs control.
```
```
Note: When the digital trigger inputs are activated DO1 is automatically set to
be a trigger input, and the signal output capability of DO1 is
automatically deactivated.
```
```
Set Command Read Command
Command s#DI1+a s#DI1
Response g#DI1? g#DI1+a
Key # Sensor ID
a Trigger input function:
0 = Trigger inputs disabled
2 = Trigger single distance measurement
3 = Start/stop single sensor tracking
4 = Start/stop buffered sensor tracking
8 = Start/stop timed sensor tracking
Default 0 = Trigger inputs disabled
```
#### 4.3.11 Read Digital Trigger Input Status – [s#RI]

```
Reads out the digital trigger input status as either active or inactive. An active
status will occur when the trigger input wire detects a high enough current to
activate the trigger input function.
```
```
Command s#RI
Response g#RI+a
Key # Sensor ID
a 0 = Input inactive
1 = Input active
```

#### 4.3.12 Measuring Mode – [s#mc]

```
Sets/reads the current measuring mode. Measuring modes help optimize
measurements for speed and/or accuracy depending on the application.
```
```
The AS1100 has 5 measuring modes:
```
- **Normal**
     Max. Measuring Rate: 20 Hz
     Typical Accuracy: +/- 3 mm
     Normal mode is a multi-purpose measurement mode that can be
       used in a wide variety of applications.
- **Fast**
     Max. Measuring Rate: 100 Hz
     Typical Accuracy: +/- 4.5 mm
     Fast mode allows the measurement rate to be increased to the
       sensor’s maximum with a slight cost in accuracy.
- **Precise**
     Max. Measuring Rate: 10 Hz
     Typical Accuracy: +/- 2.4 mm
     Precise mode improves the measurement accuracy by lowering the
       measurement rate and increasing integration time.
- **Timed**
     Max. Measuring Rate: User programmed (up to 100 Hz)
     Typical Accuracy: Dependent on measuring rate and conditions.
     Timed mode lets the user set the measurement speed that best fits
       the application. The typical accuracy will fall between Precise and
       Fast modes for a given target.
- **Moving Target**
     Max. Measuring Rate: 100 Hz
     Typical Accuracy: +/- 3 mm
     Moving target mode optimizes the sensor to measure fast moving
       targets. This mode requires the best measurement signal of all the
       measurement modes.

```
Set Command Read Command
Command s#mc+a s#mc
Response g#mc? g#mc+a
Key # Sensor ID
a Measuring mode:
0 = Normal
1 = Fast
2 = Precise
3 = Timed
4 = Moving target
Default 0 = Normal
```

#### 4.3.13 Measurement Filter Configuration – [s#fi]

```
Sets/reads the parameters of the measurement filter.
```
```
In the simplest configuration, the measurement filter takes the previous 2 to 32
measurements as directed by this command and calculates a moving average.
```
```
However, in addition to averaging, the filter can be set up to omit a set number
of min/max pairs of measurements or a set number of errors from the average.
Omitting min/max pairs reduces the effect of measurement spikes on the
average. Omitting errors allows the sensor to calculate the average as long as
there are no more error values than the programmed amount. Both of these
options can be useful when target quality changes over time or are otherwise
less cooperative than optimal.
```
```
Set Command Read Command
Command s#fi+aa+bb+cc s#fi
Response g#fi? g#fi+aa+bb+cc
Key # Sensor ID
aa Filter Length:
0 = Filter Off
2- 32 = Filter length (32 measurements max.)
bb Pairs of min/max values to suppress.
(1 = suppresses the highest and lowest value,
2 = suppressed the 2 highest and 2 lowest values,
etc.)
cc Maximum number of errors to suppress.
```
```
Note Values must adhere to this formula:
(2 * bb) + cc ≤ (0.4 * aa)
Default Filter Off
```

#### 4.3.14 Auto Start Configuration – [s#A]

```
Sets/reads the auto start configuration parameter.
```
```
Setting this parameter does the following:
```
```
 Starts distance tracking into the measurement buffer immediately.
(same as [s#f], see section 4.2.5)
 Writes this command to the flash (non-volatile) memory.
 Restarts the tracking immediately upon power on.
```
```
To stop this command, the Stop/Clear command [s#c] must be given. To keep
this command from reactivating after a power cycle, the Save command [s#s]
must be given after the Stop/Clear command.
```
```
Except for the above, [s#A] operates just like [s#f], and measurement values can
be read from the buffer in the same manner. (See section 4.2.6)
```
```
Set Command Read Command
Command s#A+aaaaaaaa s#A
Response g#A? g#A+aaaaaaaa
Key # Sensor ID
aaaaaaaa Sampling Time (unit: 1 ms)
[Range: 0-86400000 (0 = max possible rate)]
```

### 4.4 Advanced Configuration Commands

#### 4.4.1 User Output Format – [s#uo]

```
This command allows the configuration of a user specific output format. The
configuration only affects the serial interface. A parameter value of 0 is the
default. (ex. g0g+00001234)
```
```
The user output format can be configured to fit the requirement of an external
ASCII display. A parameter values between 101 and 199 define the format for an
external display. (See command key below)
```
```
The command parameter value of 200 allows the user to set a distance offset
and gain factor (See sections 4.4.2 and 4.4.3) and outputs the distance in the
default format. (ex. g0g-00000234)
```
```
The command parameter values of 300 and 301 allows the user to select
extended output formats. 300 outputs distance (unit: 0.1mm), signal, and
temperature (unit: 0.1°C) in that order (ex. g0g+00000234+008384+254). 301
outputs distance (unit: 0.1mm), signal, temperature (unit: 0.1°C), and speed
(unit: mm/s) in that order (ex. g0g+00000234+008384+254+000500). Like with
parameter value 200, 300 and 301 allow user defined distance offset and gain
factor.
```
```
Set Command Read Command
Command s#uo+aaa s#uo
Response g#uo? g#uo+aaa
Key # Sensor ID
aaa Output format:
0 = Default format (ex. g0g+00001234)
1xy = External display output format
x – Digits after decimal point
y – Total digits in output
y must be ≥ 1, and x must be ≤ y
(ex. an output of 1.234 could be given by
1xy = 134)
200 = Default format with gain/offset active
300 = Extended format with distance, signal, and
temperature (distance gain/offset active)
301 = Extended format with distance, signal,
Temperature, and speed
(distance gain/offset active)
```
```
Default 0 = Default format
```

#### 4.4.2 User Distance Offset – [s#uof]

```
Sets/reads the user defined distance offset. This affects all distance
measurement commands if and only if a user output format (see section 4.4.1)
is set that allows for it. This command does not affect the analog output signal.
```
```
Set Command Read Command
Command s#uof(+/-)aaaaaaaa s#uof
Response g#uof? g#uof(+/-)aaaaaaaa
Key # Sensor ID
aaaaaaaa Distance offset (units: 0.1 mm)
Both positive (+) and negative (-) offsets can be
Entered.
Default 0 mm
```
#### 4.4.3 User Distance Gain Factor – [s#uga]

```
Sets/reads the user defined distance gain factor. The gain factor is a fraction
that is entered as 2 parameters, a numerator and denominator. The gain factor
will be used by the sensor to multiply the distance value +/- any set offset. This
affects all distance measurement commands if and only if a user output format
(see section 4.4.1) is set that allows for it. This command does not affect the
analog output signal.
```
```
Set Command Read Command
Command s#uga+aaaaaaaa+bbbbbbbb s#uga
Response g#uga? g#uga+aaaaaaaa+bbbbbbbb
Key # Sensor ID
aaaaaaaa Gain factor numerator.
bbbbbbbb Gain factor denominator. (Cannot be 0)
Default Gain factor = 1
```

### 4.5 Informational Commands

#### 4.5.1 Firmware Version [s#sv]

```
Reads the firmware version of the sensor.
```
```
Command s#sv
Response g#sv+aaaabbbb
Key # Sensor ID
aaaa Measuring module firmware version
bbbb Interface firmware version
```
#### 4.5.2 Serial Number [s#sn]

```
Reads the serial number of the sensor.
```
```
Command s#sn
Response g#sn+aaaaaaaa
Key # Sensor ID
aaaaaaaa Sensor serial number
```

## 5 Quick Reference Tables

### 5.1 Command Reference.

```
Below is a table of all the commands listed in this manual. Please refer to the section
listed for a detailed explanation.
```
**_Table 7: Command Reference_**
Function Description Section Command

```
Operation
```
```
Stop/Cl ear Stops commands and resets digital outputs. 4.2.1 s#c
Single Distanc e Measur ement Takes a single distance measurement 4.2.2 s#g
Single Sensor Tracking Starts output of continuous measurements. 4.2.3 s#h
Timed Sensor Tracking Starts output of continuous measurements at
specified rate.
```
```
4.2.4 s#h+aaaaaaaa
```
```
Buffered Sensor Tracking Starts output of continuous measurements to
buffer.
```
```
4.2.5 s#f
```
```
Read Tracking Buffer Reads measurement buffer. 4.2.6 s#q
Signal Strength Measurement Starts measurements of signal strength. 4.2.7 s#m
Temperatur e Measur ement Takes a single sensor temperature measur ement. 4.2.8 s#t
Read/Clear Error Stack Read or clear saved error stack. 4.2.9 s#re, s#ce
Laser On Turns laser beam on for alignment or adjustment. 4.2.10 s#o
```
```
Configuration
```
```
Save Configuration Saves current configuration to flash. 4.3.1 s#s
Reset to Factor y Default Reset configuration to factory defaults 4.3.2 s#d
Set Serial Interface Parameters Sets serial communication parameters. 4.3.3 s#br
Set Sensor ID Sets sensor ID number. 4.3.4 s#id
Analog Output Minimum Current Sets the minimum analog output value. 4.3.5 s#vm
Analog Output Error Value Sets the analog output value for errors. 4.3.6 s#ve
Analog Output Distance Range Sets the distance measur ements that will
correspond to min. and max. analog output
values.
```
```
4.3.7 s#v
```
```
Digital Signal Output Type Sets the output type for DO1, DO2, and DOE. 4.3.8 s#ot
Digital Signal Output Thresholds Sets distance thresholds for DO1 and DO2 4.3.9 s#1, s#2
Digital Trigger Input Function Enables digital input and sets what it will control. 4.3.10 s#DI1
Read Digital Trigger Input Status Returns the digital input status. 4.3.11 s#RI
Measuring Mode Sets current sensor measuring mode 4.3.12 s#mc
Measurement Filter Configuration Enables and configures the measurement filter. 4.3.13 s#fi
Auto Start Configuration Enables and configures the auto start function. 4.3.14 s#A
```
```
Advanced
```
(^) User Output Format Configur es measurement output format. 4.4.1 s#uo
User Distance Offset Configures distance offset. 4.4.2 s#uof
User Distance Gain Factor Configures measurement gain factor/multiplier. 4.4.3 s#uga
Info
Firmware Version^ Returns current firmware version^ 4.5.1^ s#sv^
Serial Number Returns sensor serial number. 4.5.2 s#sn


### 5.2 Error Codes

```
Below is a table of error codes and suggestions for troubleshooting each error. If the
troubleshooting suggestions do not resolve the error, please contact Acuity Technical
Support.
```
**_Table 8: Error Code Reference_**
Code Description Troubleshooting
200 This code denotes a sensor boot in the error
stack. Not an error itself.

```
None
```
```
203 Wrong command or syntax. Check command is entered correctly. Check
communication settings
210 Sensor not in tracking mode. Start tracking measurement first.
211 Tracking measurement time too short for
measurement conditions.
```
```
Increase measurement time or improve
measurement conditions.
212 Command can’t be executed while tracking
measurement is active.
```
```
Stop tracking before issuing command.
```
```
220 Serial communication error. Check communication settings.
230 Distance value overflow. Check user offset/gain configuration.
233 Number can’t be displayed. Check output format.
234 Distance not in measurement range. Check measurement setup.
236 Conflict in digital input/output DI1/DO1
configuration.
```
```
Check DI1/DO1 config. If digital input is activated
both DI1 and DO1 can be used for input only.
252 Temperature too high. Reduce ambient temperature. Should not occur at
room temperature
253 Temperature too low. Increase ambient temperature. Should not occur at
room temperature.
255 Signal too low. If target is in range, use a more reflective target
surface.
256 Signal too high. Use a less reflective target surface.
257 Signal to noise ratio is too low. Reduce sources of background light. Try using a
more reflective target surface.
258 Power supply voltage is too high. Check supplied voltage is within specifications.
259 Power supply voltage is too low. Check supplied voltage is within specifications.
260 Signal unstable. Stabilize target surface. (Decrease variations in
reflectivity or angle.)
261 Distance measurement spike greater than set
limit.
```
```
Check target for unexpected movements.
Reconfigure sensor limits. Restarting measurement
clears error condition.
284 Signal disturbance in laser output. Clean window. Be sure to use optically safe cloths
or wipes.
290 Signal disturbance in sensor optics. Clean window. Be sure to use optically safe cloths
or wipes.
402 Firmware installation error. Check power and connection. Power cycle the
sensor before reattempting.
```

