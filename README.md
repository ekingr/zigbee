ZIGBEE controller
=================
Copyright (c) ekingr, Jul 2023



TODO
----

### Controller
- Add light devices

### Gateway
- Handle when running multiple rules at the same time (and avoid throttling).

### UI
- Only input rules time?
- Add input check before submit
- Improve display of messages & API status
- Improve graphics



Features & architecture
-----------------------

Allows to control Zigbee devices from a webapp.

### Features

Interact with Zigbee devices [CURRENTLY ONLY `on_off` TYPE OF DEVICES]:
- Read device state
- Send command to a device (eg. set on/off)
- Define rules to send commands in the future / periodically

### Architecture

*Controller* controls the Zigbee network
- _Python with zigpy & gRPC_
- Communicates with the Zigbee coordinator (adapter) via tty-serial
- Network coordinator state (incl. paired devices) is stored by zigpy in `zigpy.db` sqlite file
- Sends commands to devices: request state update, execute changes
- Handles network events (eg. when devices share their state changes)
- Caches the state of known devices internally to only poll the network periodically at low frequency (30s)
- Implements basic safety checks like commands throttling
- Advertizes API via gRPC to get/set devices state

*Gateway* offers a web API to interact with devices and additionnal intelligence (eg. rules)
- _Golang with gRPC_
- Communicates with the controller via gRPC (through VPN if relevant)
- Polls controller state at medium frequency (1s) and cahes the state internally
- Sends commands to the controller: execute changes
- Manages rules to send commands in the future / periodically
- Advertizes HTTP API that can be included in the `home` infrastructure, incl. requests authorization

*Frontend* web UI
- _Vanillia JS_



Installation
------------

### Installation for deployment (PROD & DEV)

All required steps are in the `deploy-ctrl` & `deploy-gway` scripts.
Those include few manual steps, listed in the comments at the top of the scripts.
To be run via `make`.

Configuration of network coordinator is saved in the `zigpy.db` sqlite file.
Configuration (eg. devices pairing) can be done manually first, and the db later copied over to the application.
Manual config for now can be done with `zigpy_app.py`. The relevant commands (pairing, viewing...) may be added to the main python scripts at some point.

### Installation for local dev, incl. building the source

Python virtual environment, incl. Zigbee & gRPC modules are installed by `make` in the `prep` step.

If needed to run zigpy, add current user to `dialout` group:
```bash
$ sudo usermod -g dialout ekingr
```

gRPC go software
```bash
$ # Installing protoc from bin release, to have the latest version
$ wget https://github.com/protocolbuffers/protobuf/releases/download/v24.0/protoc-24.0-linux-x86_64.zip
$ unzip protoc-24.0-linux-x86_64.zip -d ./protoc
$ sudo mv ./protoc/bin/protoc /usr/local/bin/
$ sudo mv ./protoc/include/google /usr/local/include/
$ rm -r ./protoc/

$ go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
$ go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
```

Frontend compilation requires a Babel toolchain (installed by `make`) and SASS.


Servers operations: start & stop
--------------------------------

To disable the services, so as they do not restart at next boot:
```bash
pi$ # For home_zbGateway @pi4:
pi$ sudo systemctl stop home_zbGateway
pi$ sudo systemctl disable home_zbGateway
pi$ sudo systemctl is-enabled home_zbGateway

pi4$ # For zbCtrl @pi4:
pi4$ sudo systemctl stop zbCtrl
pi4$ sudo systemctl disable zbCtrl
pi4$ sudo systemctl is-enabled zbCtrl
```

To re-enable them later-on:
```bash
pi$ # For home_zbGateway on pi:
pi$ sudo systemctl daemon-reload
pi$ sudo systemctl enable home_zbGateway
pi$ sudo systemctl is-enabled home_zbGateway
pi$ sudo systemctl start home_zbGateway
pi$ sudo service home_zbGateway status

pi4$ # For zbCtrl @pi4:
pi4$ sudo systemctl daemon-reload
pi4$ sudo systemctl enable zbCtrl
pi4$ sudo systemctl is-enabled zbCtrl
pi4$ sudo systemctl start zbCtrl
pi4$ sudo service zbCtrl status
```



Zigbee adapter [coordinator]
----------------------------

### Hardware

Bought from Aliexpress
- Designation: Wireless CC2652P CC2652 USB Dongle Zigbee Pack sniffer protocol analysis with antena
- Variant: CP2102N with cable
- Store: FDKJGECF Authorization Store
- Cost: $17.52 + shipping = $20.94

Hardware details
- `CC2652` main chip: TI SimpleLink(TM) ARM Cortex-M4F multiprotocol 2.4GHz wireless MCU with integrated power amplifier (Bluetooth 5.2 BLE, Tread, Zigbee 3.0)
- `CP2102N` interface: Silicon Labs USBXpress(TM) USB-to-UART bridge controller
- Comes flashed with Zigbee2mqtt

The corresponding radio module is `zigpy-znp`

### Find the mount point

Plug the adapter in and find its mount point (here `/dev/ttyUSB0`):

```bash
$ sudo dmesg
[  169.780545] usb 3-1: new full-speed USB device number 2 using xhci_hcd
[  169.930582] usb 3-1: New USB device found, idVendor=10c4, idProduct=ea60, bcdDevice= 1.00
[  169.930596] usb 3-1: New USB device strings: Mfr=1, Product=2, SerialNumber=3
[  169.930600] usb 3-1: Product: CP2102N USB to UART Bridge Controller
[  169.930603] usb 3-1: Manufacturer: Silicon Labs
[  169.930606] usb 3-1: SerialNumber: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
[  170.025161] usbcore: registered new interface driver usbserial_generic
[  170.025172] usbserial: USB Serial support registered for generic
[  170.030977] usbcore: registered new interface driver cp210x
[  170.030995] usbserial: USB Serial support registered for cp210x
[  170.031018] cp210x 3-1:1.0: cp210x converter detected
[  170.032820] usb 3-1: cp210x converter now attached to ttyUSB0

$ ls -l /dev/ttyUSB0
crw-rw---- 1 root dialout 188, 0 juil. 25 23:40 /dev/ttyUSB0
```

Add user `ekingr` to the `dialout` group so as to be able to talk to the controller without running as root:
```bash
$ sudo usermod -g dialout ekingr
```



RESEARCH
========

Zigbee network Setup
--------------------

Reset all devices:
- TRADFRI on/off switch: click the rest button 4 times quickly (red light should pulse afterwards)
- TRADFRI control outlet: hold the reset button for 10s (while light should pulse afterwards)

Put coordinator into paring mode (for 120s)
```zigpy_app.py
zigbee$ p 120
Allowing pairing for 120 seconds
```

Pair the TRADFRI on/off switch: hold the reset button for 10s (red light should pulse then blink)
```zigpy_app.py
device_joined <Device model=None manuf=None nwk=0x7D7F ieee=70:ac:08:ff:fe:90:0a:aa is_initialized=False>
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 0, cluster 19, src_ep 0, dst_ep 0,       message b'\x81\x7f}n\n\x90\xfe\xff\x08\xacp\x80'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 0, cluster 32770, src_ep 0, dst_ep 0,    message b'\x08\x00\x7f}\x02@\x80|\x11RR\x00\x00,R\x00\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 0, cluster 32773, src_ep 0, dst_ep 0,    message b'\t\x00\x7f}\x01\x01'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 0, cluster 32772, src_ep 0, dst_ep 0,    message b'\n\x00\x7f}$\x01\x04\x01 \x08\x01\x07\x00\x00\x01\x00\x03\x00\t\x00 \x00\x00\x10|\xfc\x07\x03\x00\x04\x00\x06\x00\x08\x00\x19\x00\x02\x01\x00\x10'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 0, src_ep 1, dst_ep 1,      message b'\x18\x0b\x01\x04\x00\x00B\x0eIKEA of Sweden\x05\x00\x00B\x15TRADFRI on/off switch'
Raw device init <Device model='TRADFRI on/off switch' manuf='IKEA of Sweden' nwk=0x7D7F ieee=70:ac:08:ff:fe:90:0a:aa is_initialized=True>
device_initialized <Device model='TRADFRI on/off switch' manuf='IKEA of Sweden' nwk=0x7D7F ieee=70:ac:08:ff:fe:90:0a:aa is_initialized=True>
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 49246, cluster 3, src_ep 1, dst_ep 2,    message b'\x01\x00\x01'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 3, src_ep 1, dst_ep 1,      message b'\x01\x00\x01'

zigbee$ ls
Found 2 devices...
0: 00:12:4b:00:24:cb:3e:00: 'Texas Instruments': 'CC1352/CC2652, Z-Stack 3.30+ (build 20221226)'
1: 70:ac:08:ff:fe:90:0a:aa: 'IKEA of Sweden': 'TRADFRI on/off switch'

zigbee$ d 1
====== 1: IKEA of Sweden TRADFRI on/off switch ======
IEEE Adress 70:ac:08:ff:fe:90:0a:aa
NWK 0x7D7F
Initialized True
rssi None
~~~ Endpoint #1 ~~~
  Input clusters:
        0       basic
        1       power
        3       identify
        9       alarms
        32      poll_control
        4096    lightlink
        64636   manufacturer_specific
  Output clusters:
        3       identify
        4       groups
        6       on_off
        8       level
        25      ota
        258     window_covering
        4096    lightlink
```

Pair the TRADFRI control outlet: hold the reset button for 10s (white light should pulse then blink)
```zigpy_app.py
device_joined <Device model=None manuf=None nwk=0x7A3D ieee=70:ac:08:ff:fe:7e:0b:xx is_initialized=False>
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 0, cluster 19, src_ep 0, dst_ep 0,       message b'\x81=z\xc8\x0b~\xfe\xff\x08\xacp\x8e'
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 0, cluster 32770, src_ep 0, dst_ep 0,    message b'\x10\x00=z\x01@\x8e|\x11RR\x00\x00,R\x00\x00'
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 0, cluster 32773, src_ep 0, dst_ep 0,    message b'\x11\x00=z\x02\x01\xf2'
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 0, cluster 32772, src_ep 0, dst_ep 0,    message b'\x12\x00=z\x1e\x01\x04\x01\n\x01\x01\x07\x00\x00\x03\x00\x04\x00\x05\x00\x06\x00\x08\x00\x00\x10\x04\x05\x00\x19\x00 \x00\x00\x10'
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 0, cluster 32772, src_ep 0, dst_ep 0,    message b'\x13\x00=z\x0c\xf2\xe0\xa1a\x00\x00\x01!\x00\x01!\x00'
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 0, src_ep 1, dst_ep 1,      message b'\x18\x14\x01\x04\x00\x00B\x0eIKEA of Sweden\x05\x00\x00B\x16TRADFRI control outlet'
Raw device init <Device model='TRADFRI control outlet' manuf='IKEA of Sweden' nwk=0x7A3D ieee=70:ac:08:ff:fe:7e:0b:xx is_initialized=True>
device_initialized <Device model='TRADFRI control outlet' manuf='IKEA of Sweden' nwk=0x7A3D ieee=70:ac:08:ff:fe:7e:0b:xx is_initialized=True>

zigbee$ ls
Found 3 devices...
0: 00:12:4b:00:24:cb:3e:00: 'Texas Instruments': 'CC1352/CC2652, Z-Stack 3.30+ (build 20221226)'
1: 70:ac:08:ff:fe:90:0a:aa: 'IKEA of Sweden': 'TRADFRI on/off switch'
2: 70:ac:08:ff:fe:7e:0b:xx: 'IKEA of Sweden': 'TRADFRI control outlet'

zigbee$ d 2
====== 2: IKEA of Sweden TRADFRI control outlet ======
IEEE Adress 70:ac:08:ff:fe:7e:0b:xx
NWK 0x7A3D
Initialized True
rssi None
~~~ Endpoint #1 ~~~
  Input clusters:
        0       basic
        3       identify
        4       groups
        5       scenes
        6       on_off
        8       level
        4096    lightlink
  Output clusters:
        5       scenes
        25      ota
        32      poll_control
        4096    lightlink
~~~ Endpoint #242 ~~~
  Input clusters:
        33      green_power
  Output clusters:
        33      green_power
```

Pair the TRADFRI on/off switch to the TRADFRI control outlet so that they can talk directly to each other:
press and hold the switch's reset button close to the outlet for 10s (LED should start pulsing).
Now the button will control the outlet even when the coordinator is not powered on.


Bind the TRADFRI control outlet to get command updates:
- `bind`
- `2` device: IKEA of Sweden TRADFRI control outlet (70:ac:08:ff:fe:7e:0b:xx)
- `1` endpoint
- `6` cluster: On/Off
- `in` in/out: input recieved by the outlet
And idem for the TRADFRI on/off switch.

```zigpy_app.py
zigbee$ bind 2 1 6 in
zigbee$ bind 1 1 6 out
```



Messages
--------

Message de status de la prise quand elle reçoit une commade de l'interrupteur appairé:
```
# Button only: simple on/off clicks
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x1b\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x1c\x01'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x1d\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x1e\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x1f\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01 \x01'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01!\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01"\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01#\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01$\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01%\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01&\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b"\x01'\x00"
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01(\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01)\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01+\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01*\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01,\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01-\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01.\x01'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01/\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x010\x01'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x011\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x012\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x013\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x014\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x015\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x016\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x017\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x018\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x019\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01:\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01;\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01<\x00'

# Button & outlet: simple on/off clicks
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01?\x00'
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 0, cluster 19, src_ep 0, dst_ep 0,       message b'\x81=z\xc8\x0b~\xfe\xff\x08\xacp\x8e'
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 4, src_ep 1, dst_ep 1,      message b'\x19\x07\x02\xff\x01\xa8\x06'
Error calling listener <bound method YourListenerClass.group_added of <__main__.YourListenerClass object at 0x7f00ee08f750>> with args (<Group group_id=0x06A8 name='No name group 0x06A8' members={}>,): TypeError("YourListenerClass.group_added() missing 1 required positional argument: 'ep'")
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01@\x01'                    #O  01 40 01                #Click ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x01\n\x00\x00\x10\x01'   #I  08 01 0a 00 00 10 01    #Switched to ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 25, src_ep 1, dst_ep 1,     message b'\x01\x02\x01\x01|\x11\x01\x11#F\x02 <\x00'
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01A\x00'                    #O  01 41 00                #Click OFF
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x03\n\x00\x00\x10\x00'   #I  08 03 0a 00 00 10 00    #Switched to OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01B\x01'                    #O  01 42 01                #Click ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x04\n\x00\x00\x10\x01'   #I  08 04 0a 00 00 10 01    #Switched to ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01C\x01'                    #I  01 43 01                #Click ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01D\x01'                    #I  01 44 01                #Click ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01E\x00'                    #I  01 45 00                #Click OFF
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x05\n\x00\x00\x10\x00'   #O  08 05 0a 00 00 10 00    #Switched to OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01F\x01'                    #I  01 46 01                #Click ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x06\n\x00\x00\x10\x01'   #O  08 06 0a 00 00 10 01    #Switched to ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01G\x01'                    #O  01 47 01                #Click ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01H\x01'                    #O  01 48 01                #Click ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01I\x00'                    #O  01 49 00                #Click OFF
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x07\n\x00\x00\x10\x00'   #I  08 07 0a 00 00 10 00    #Switched to OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01J\x00'                    #O  01 4a 00                #Click OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01K\x00'                    #O  01 4b 00                #Click OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01L\x01'                    #O  01 4c 01                #Click ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x08\n\x00\x00\x10\x01'   #I  08 08 0a 00 00 10 01    #Switched to ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01M\x01'                    #O  01 4d 01                #Click ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01N\x01'                    #O  01 4e 01                #Click ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01O\x00'                    #O  01 4f 00                #Click OFF
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\t\n\x00\x00\x10\x00'     #I  08 09 0a 00 00 10 00    #Switched to OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01P\x00'                    #O  01 50 00                #Click OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01Q\x01'                    #O  01 51 01                #Click ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\n\n\x00\x00\x10\x01'     #I  08 0a 0a 00 00 10 01    #Switched to ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01R\x00'                    #O  01 52 00                #Click OFF
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x0b\n\x00\x00\x10\x00'   #I  08 0b 0a 00 00 10 00    #Switched to OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01S\x01'                    #O  01 53 01                #Click ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x0c\n\x00\x00\x10\x01'   #I  08 0c 0a 00 00 10 01    #Switched to ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01T\x00'                    #O  01 54 00                #Click OFF
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\r\n\x00\x00\x10\x00'     #I  08 0d 0a 00 00 10 00    #Switched to OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01U\x01'                    #O  01 55 01                #Click ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x0e\n\x00\x00\x10\x01'   #I  08 0e 0a 00 00 10 01    #Switched to ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01V\x00'                    #O  01 56 00                #Click OFF
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x0f\n\x00\x00\x10\x00'   #I  08 0f 0a 00 00 10 00    #Switched to OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01W\x01'                    #O  01 57 01                #Click ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08\x10\n\x00\x00\x10\x01'   #I  08 10 0a 00 00 10 01    #Switched to ON


# Long press (first msg in the pair) then release (second one)
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01_\x05\x00S'               #O  01 5f 05 00 53          #Hold ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01`\x07'                    #O  01 60 07                #Release
# idem...
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01a\x05\x00S'               #O  01 61 05 00 53          #Hold ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01b\x07'                    #O  01 62 07                #Release
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01c\x05\x00S'               #O  01 63 05 00 53          #Hold ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01d\x07'                    #O  01 64 07                #Release
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01e\x05\x00S'               #O  01 65 05 00 53          #Hold ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01f\x07'                    #O  01 66 07                #Release


Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01}\x05\x00S'               #O  01 7d 05 00 53          #Hold ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01~\x07'                    #O  01 7e 07                #Release
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x7f\x01'                 #O  01 7f 01                #Click ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x00\x01'                 #O  01 00 01                #Click ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x01\x05\x00S'            #O  01 01 05 00 53          #Hold ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x02\x07'                 #O  01 02 07                #Release (ON)
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x03\x00'                 #O  01 03 00                #Click OFF
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08!\n\x00\x00\x10\x00'      #I  08 21 0a 00 00 10 00    #Switched to OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x04\x01\x01S\x00\x00'    #O  01 04 01 01 53 00 00    #Hold OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x05\x07'                 #O  01 05 07                #Release
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x06\x00'                 #O  01 06 00                #Click OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x07\x05\x00S'            #O  01 07 05 00 53          #Hold ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08"\n\x00\x00\x10\x01'      #I  08 22 0a 00 00 10 01    #Switched to ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x08\x07'                 #O  01 08 07                #Release
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\t\x01'                   #O  01 09 01                #Click ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\n\x01\x01S\x00\x00'      #O  01 0a 01 01 53 00 00    #Hold OFF [NO EFFECT]
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x0b\x07'                 #O  01 0b 07                #Release
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x0c\x01\x01S\x00\x00'    #O  01 0c 01 01 53 00 00    #Hold OFF [NO EFFECT]
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\r\x07'                   #O  01 0d 07                #Release
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x01\x0e\x00'                 #O  01 0e 00                #Click OFF
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08$\n\x00\x00\x10\x00'      #I  08 24 0a 00 00 10 00    #Switched to OFF
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x0f\x05\x00S'            #O  01 0f 05 00 53          #Hold ON
Handle_message 70:ac:08:ff:fe:7e:0b:xx profile 260, cluster 6, src_ep 1, dst_ep 1,      message b'\x08%\n\x00\x00\x10\x01'      #I  08 25 0a 00 00 10 01    #Switched to ON
Handle_message 70:ac:08:ff:fe:90:0a:aa profile 260, cluster 8, src_ep 1, dst_ep 1,      message b'\x01\x10\x07'                 #O  01 10 07                #Release
```

Format of on/off (`cluster 6`) output commands from the TRADFRI on/off switch (here `70:ac:08:ff:fe:90:0a:aa`)
1. Constant: `x01` (1B)
2. Incremental counter (1B)
3. State: `x00`=OFF | `x01`=ON | `x05`=HOLD | `x07`=RELEASE (1B)
4. Constant [only if in HOLD state]: `x00 x53` (2B)

Format of on/off (`cluster 6`) input commands from the TRADFRI control outlet (here `70:ac:08:ff:fe:7e:0b:xx`)
NB: only sends it when the state changes
1. Constant: `x08` (1B)
2. Incremental counter (1B)
3. Constant: `x0a x00 x00 x10` (4B)
5. State: `x00`=OFF | `x01`=ON


`cluster 8` = Level control

`LevelControl: move_with_on_off id=0x05`
`battery_2_quantity id=0x0053`
`BatterySize: CR2 = 0x07`



Bulb control
------------

Pairing: allow paring in the coordinator, then reset the bulb by switching it on/off 6 times:
```
Commands:
  LIST: list known devices
  INFO ID: detail all relevant information about device #ID
  STATUS ID: show status of device #ID
  SET ID STATUS: set status of device #ID to STATUS
  PAIR: allow pairing for 60s
  EXIT: exit program
command> pair
Allowing pairing for 60s
2023-10-01 20:28:00,816 INFO application/permit Permitting joins for 60 seconds
2023-10-01 20:28:18,257 INFO application/on_zdo_tc_device_join TC device join: ZDO.TCDevInd.Callback(SrcNwk=0x1F17, SrcIEEE=f4:b3:b1:ff:fe:9b:26:bb, ParentNwk=0x0000)
2023-10-01 20:28:18,361 INFO application/handle_join New device 0x1f17 (f4:b3:b1:ff:fe:9b:26:bb) joined the network
2023-10-01 20:28:18,361 INFO device/get_node_descriptor [0x1f17] Requesting 'Node Descriptor'
2023-10-01 20:28:18,453 INFO device/get_node_descriptor [0x1f17] Got Node Descriptor: NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered|RxOnWhenIdle|AllocateAddress: 142>, manufacturer_code=4476, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)
2023-10-01 20:28:18,453 INFO device/_initialize [0x1f17] Discovering endpoints
2023-10-01 20:28:18,543 INFO device/_initialize [0x1f17] Discovered endpoints: [1, 242]
2023-10-01 20:28:18,544 INFO device/_initialize [0x1f17] Initializing endpoints [<Endpoint id=1 in=[] out=[] status=<Status.NEW: 0>>, <Endpoint id=242 in=[] out=[] status=<Status.NEW: 0>>]
2023-10-01 20:28:18,544 INFO endpoint/initialize [0x1f17:1] Discovering endpoint information
2023-10-01 20:28:18,639 INFO endpoint/initialize [0x1f17:1] Discovered endpoint information: SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=268, device_version=1, input_clusters=[0, 3, 4, 5, 6, 8, 768, 4096, 64599], output_clusters=[25])
2023-10-01 20:28:18,639 INFO endpoint/initialize [0x1f17:242] Discovering endpoint information
2023-10-01 20:28:18,730 INFO endpoint/initialize [0x1f17:242] Discovered endpoint information: SizePrefixedSimpleDescriptor(endpoint=242, profile=41440, device_type=97, device_version=0, input_clusters=[33], output_clusters=[33])
2023-10-01 20:28:18,834 INFO device/_initialize [0x1f17] Read model 'TRADFRIbulbG125E27WSopal470lm' and manufacturer 'IKEA of Sweden' from <Endpoint id=1 in=[basic:0x0000, identify:0x0003, groups:0x0004, scenes:0x0005, on_off:0x0006, level:0x0008, light_color:0x0300, lightlink:0x1000, manufacturer_specific:0xFC57] out=[ota:0x0019] status=<Status.ZDO_INIT: 1>>
2023-10-01 20:28:18,834 INFO device/_initialize [0x1f17] Discovered basic device information for <Device model='TRADFRIbulbG125E27WSopal470lm' manuf='IKEA of Sweden' nwk=0x1F17 ieee=f4:b3:b1:ff:fe:9b:26:bb is_initialized=True>
Disabling pairing

Commands:
  LIST: list known devices
  INFO ID: detail all relevant information about device #ID
  STATUS ID: show status of device #ID
  SET ID STATUS: set status of device #ID to STATUS
  PAIR: allow pairing for 60s
  EXIT: exit program
command> list
Listing known devices:
  00:12:4b:00:24:cb:3e:00 0x0000 Texas Instruments CC1352/CC2652, Z-Stack 3.30+ (build 20221226) True
  70:ac:08:ff:fe:90:0a:aa 0x7D7F IKEA of Sweden TRADFRI on/off switch True
  70:ac:08:ff:fe:7e:0b:xx 0x7A3D IKEA of Sweden TRADFRI control outlet True
  34:25:b4:ff:fe:bd:7c:yy 0x2488 IKEA of Sweden TRADFRI control outlet True
  f4:b3:b1:ff:fe:9b:26:bb 0x1F17 IKEA of Sweden TRADFRIbulbG125E27WSopal470lm True
```

Device information:
```
Commands:
  LIST: list known devices
  INFO ID: detail all relevant information about device #ID
  STATUS ID: show status of device #ID
  SET ID STATUS: set status of device #ID to STATUS
  PAIR: allow pairing for 60s
  EXIT: exit program
command> info f4:b3:b1:ff:fe:9b:26:bb
Detailing information about device F4:B3:B1:FF:FE:9B:26:BB:
  DEVICE: ieee = f4:b3:b1:ff:fe:9b:26:bb
          nwk = 0x1F17
          manufacturer = IKEA of Sweden
          model = TRADFRIbulbG125E27WSopal470lm
          is initialised = True
  Endpoint #1 (status: 1)
  INPUT clusters:
       0 Basic <class 'zigpy.zcl.clusters.general.Basic'>
           0 reset_fact_default
       3 Identify <class 'zigpy.zcl.clusters.general.Identify'>
           0 identify
           1 identify_query
          64 trigger_effect
       4 Groups <class 'zigpy.zcl.clusters.general.Groups'>
           0 add
           1 view
           2 get_membership
           3 remove
           4 remove_all
           5 add_if_identifying
       5 Scenes <class 'zigpy.zcl.clusters.general.Scenes'>
           0 add
           1 view
           2 remove
           3 remove_all
           4 store
           5 recall
           6 get_scene_membership
          64 enhanced_add
          65 enhanced_view
          66 copy
       6 On/Off <class 'zigpy.zcl.clusters.general.OnOff'>
           0 off
           1 on
           2 toggle
          64 off_with_effect
          65 on_with_recall_global_scene
          66 on_with_timed_off
       8 Level control <class 'zigpy.zcl.clusters.general.LevelControl'>
           0 move_to_level
           1 move
           2 step
           3 stop
           4 move_to_level_with_on_off
           5 move_with_on_off
           6 step_with_on_off
           7 stop_with_on_off
           8 move_to_closest_frequency
     768 Color Control <class 'zigpy.zcl.clusters.lighting.Color'>
           0 move_to_hue
           1 move_hue
           2 step_hue
           3 move_to_saturation
           4 move_saturation
           5 step_saturation
           6 move_to_hue_and_saturation
           7 move_to_color
           8 move_color
           9 step_color
          10 move_to_color_temp
          64 enhanced_move_to_hue
          65 enhanced_move_hue
          66 enhanced_step_hue
          67 enhanced_move_to_hue_and_saturation
          68 color_loop_set
          71 stop_move_step
          75 move_color_temp
          76 step_color_temp
     4096 LightLink <class 'zigpy.zcl.clusters.lightlink.LightLink'>
           0 scan
           2 device_info
           6 identify
           7 reset_to_factory_new
          16 network_start
          18 network_join_router
          20 network_join_end_device
          22 network_update
          65 get_group_identifiers
          66 get_endpoint_list
     64599 Manufacturer Specific <class 'zigpy.zcl.clusters.manufacturer_specific.ManufacturerSpecificCluster'>
  OUTPUT clusters:
      25 Ota <class 'zigpy.zcl.clusters.general.Ota'>
           1 query_next_image
           3 image_block
           4 image_page
           6 upgrade_end
           8 query_specific_file
  Endpoint #242 (status: 1)
  INPUT clusters:
      33 GreenPowerProxy <class 'zigpy.zcl.clusters.general.GreenPowerProxy'>
  OUTPUT clusters:
      33 GreenPowerProxy <class 'zigpy.zcl.clusters.general.GreenPowerProxy'>
Requesting status info from device F4:B3:B1:FF:FE:9B:26:BB:
  OK: Properties with usable values:
  - manufacturer = IKEA of Sweden
  - model = TRADFRIbulbG125E27WSopal470lm
  - power_source = PowerSource.Mains_single_phase
  - generic_device_class = GenericDeviceClass.Lighting
  - generic_device_type = GenericLightingDeviceType.LED_bulb
  - on_off = Bool.true
  - global_scene_control = Bool.true
  - on_time = 0
  - off_wait_time = 0
  - start_up_on_off = StartUpOnOff.On
  - cluster_revision = 2
  KO: Properties with unusable values:
  - manufacturer_version_details = Status.UNSUPPORTED_ATTRIBUTE
  - serial_number = Status.UNSUPPORTED_ATTRIBUTE
  - product_label = Status.UNSUPPORTED_ATTRIBUTE
```

Basic on/off control works same as for the power outlets:
```
Commands:
  LIST: list known devices
  INFO ID: detail all relevant information about device #ID
  STATUS ID: show status of device #ID
  SET ID STATUS: set status of device #ID to STATUS
  PAIR: allow pairing for 60s
  EXIT: exit program
command> set f4:b3:b1:ff:fe:9b:26:bb off
Requesting status of device F4:B3:B1:FF:FE:9B:26:BB to be set to OFF
2023-10-01 20:30:23,212 INFO zigbee/setDeviceState Setting state of F4:B3:B1:FF:FE:9B:26:BB to 0
0

Commands:
  LIST: list known devices
  INFO ID: detail all relevant information about device #ID
  STATUS ID: show status of device #ID
  SET ID STATUS: set status of device #ID to STATUS
  PAIR: allow pairing for 60s
  EXIT: exit program
command> set f4:b3:b1:ff:fe:9b:26:bb on
Requesting status of device F4:B3:B1:FF:FE:9B:26:BB to be set to ON
2023-10-01 20:30:30,908 INFO zigbee/setDeviceState Setting state of F4:B3:B1:FF:FE:9B:26:BB to 1
1
```

Advanced control, to set intensity & temperature:
```python
>>> import asyncio
>>> import zigbee
>>> import logging
>>> logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s/%(funcName)s %(message)s', encoding='utf-8', level=logging.INFO)

>>> zbi = zigbee.ZBInterface()
>>> await zbi.start(lambda device, state: logging.info('State change: %s=%r' % (device, state)))

>>> zbi.listDevices()
dict_values([<ZNPCoordinator model='CC1352/CC2652, Z-Stack 3.30+ (build 20221226)' manuf='Texas Instruments' nwk=0x0000 ieee=00:12:4b:00:24:cb:3e:00 is_initialized=True>, <Device model='TRADFRI on/off switch' manuf='IKEA of Sweden' nwk=0x7D7F ieee=70:ac:08:ff:fe:90:0a:aa is_initialized=True>, <Device model='TRADFRI control outlet' manuf='IKEA of Sweden' nwk=0x7A3D ieee=70:ac:08:ff:fe:7e:0b:xx is_initialized=True>, <Device model='TRADFRI control outlet' manuf='IKEA of Sweden' nwk=0x2488 ieee=34:25:b4:ff:fe:bd:7c:yy is_initialized=True>, <Device model='TRADFRIbulbG125E27WSopal470lm' manuf='IKEA of Sweden' nwk=0x1F17 ieee=f4:b3:b1:ff:fe:9b:26:bb is_initialized=True>])

>>> id = 'f4:b3:b1:ff:fe:9b:26:bb'
>>> bulb, _, _ = zbi._getDevice(id)>>> bulb
<Device model='TRADFRIbulbG125E27WSopal470lm' manuf='IKEA of Sweden' nwk=0x1F17 ieee=f4:b3:b1:ff:fe:9b:26:bb is_initialized=True>
>>> onoff = bulb.endpoints[zigbee.DEVICE_ONOFF_ENDPOINT].in_clusters[6]
>>> lvl = bulb.endpoints[zigbee.DEVICE_ONOFF_ENDPOINT].in_clusters[8]
>>> color = bulb.endpoints[zigbee.DEVICE_ONOFF_ENDPOINT].in_clusters[768]

>>> # On/Off
>>> await onoff.command(1)
Default_Response(command_id=1, status=<Status.SUCCESS: 0>)
>>> await onoff.command(0)
Default_Response(command_id=0, status=<Status.SUCCESS: 0>)

>>> # Set intensity
>>> await lvl.command(0, level=254, transition_time=0)
Default_Response(command_id=0, status=<Status.SUCCESS: 0>)
>>> await lvl.command(0, level=0, transition_time=0)
Default_Response(command_id=0, status=<Status.SUCCESS: 0>)
>>> await lvl.command(0, level=254, transition_time=10)
Default_Response(command_id=0, status=<Status.SUCCESS: 0>)

>>> # Set intensity with on/off
>>> await lvl.command(4, level=0, transition_time=10)
Default_Response(command_id=4, status=<Status.SUCCESS: 0>)
>>> await lvl.command(4, level=254, transition_time=10)
Default_Response(command_id=4, status=<Status.SUCCESS: 0>)

>>> # Set color temperature
>>> await color.command(10, color_temp_mireds=250, transition_time=0)
Default_Response(command_id=10, status=<Status.SUCCESS: 0>)
>>> await color.command(10, color_temp_mireds=454, transition_time=0)
Default_Response(command_id=10, status=<Status.SUCCESS: 0>)
>>> await color.command(10, color_temp_mireds=454, transition_time=300)
Default_Response(command_id=10, status=<Status.SUCCESS: 0>)

>>> [attr.name for attr in sorted([attr for attr in color.AttributeDefs], key=lambda a: a.id)]
['current_hue', 'current_saturation', 'remaining_time', 'current_x', 'current_y', 'drift_compensation', 'compensation_text', 'color_temperature', 'color_mode', 'options', 'num_primaries', 'primary1_x', 'primary1_y', 'primary1_intensity', 'primary2_x', 'primary2_y', 'primary2_intensity', 'primary3_x', 'primary3_y', 'primary3_intensity', 'primary4_x', 'primary4_y', 'primary4_intensity', 'primary5_x', 'primary5_y', 'primary5_intensity', 'primary6_x', 'primary6_y', 'primary6_intensity', 'white_point_x', 'white_point_y', 'color_point_r_x', 'color_point_r_y', 'color_point_r_intensity', 'color_point_g_x', 'color_point_g_y', 'color_point_g_intensity', 'color_point_b_x', 'color_point_b_y', 'color_point_b_intensity', 'enhanced_current_hue', 'enhanced_color_mode', 'color_loop_active', 'color_loop_direction', 'color_loop_time', 'color_loop_start_enhanced_hue', 'color_loop_stored_enhanced_hue', 'color_capabilities', 'color_temp_physical_min', 'color_temp_physical_max', 'couple_color_temp_to_level_min', 'start_up_color_temperature', 'cluster_revision', 'reporting_status']
>>> attrs = ['remaining_time', 'current_x', 'current_y', 'color_temperature', 'color_mode', 'num_primaries', 'enhanced_color_mode', 'color_capabilities', 'color_temp_physical_min', 'color_temp_physical_max', 'couple_color_temp_to_level_min', 'start_up_color_temperature', 'cluster_revision']
>>> await color.read_attributes(attrs)
({'remaining_time': 0, 'current_x': 30138, 'current_y': 26909, 'color_temperature': 454, 'color_mode': <ColorMode.Color_temperature: 2>, 'num_primaries': 0, 'enhanced_color_mode': <EnhancedColorMode.Color_temperature: 2>, 'color_capabilities': <ColorCapabilities.Color_temperature: 16>, 'color_temp_physical_min': 250, 'color_temp_physical_max': 454, 'couple_color_temp_to_level_min': 370, 'start_up_color_temperature': 65535, 'cluster_revision': 2}, {})
```

Detection of bulb being powered-on:
```log
2023-10-02 01:25:44,990 DEBUG api/frame_received Received command: ZDO.EndDeviceAnnceInd.Callback(Src=0x1F17, NWK=0x1F17, IEEE=f4:b3:b1:ff:fe:9b:26:bb, Capabilities=<MACCapabilities.Router|MainsPowered|RXWhenIdle|AllocateShortAddrDuringAssocNeeded: 142>)
2023-10-02 01:25:44,990 DEBUG api/_unhandled_command Command was not handled
2023-10-02 01:25:44,990 DEBUG api/frame_received Received command: ZDO.MsgCbIncoming.Callback(Src=0x1F17, IsBroadcast=<Bool.true: 1>, ClusterId=19, SecurityUse=0, TSN=129, MacDst=0xFFFF, Data=b'\x17\x1F\xB6\x26\x9B\xFE\xFF\xB1\xB3\xF4\x8E')
2023-10-02 01:25:44,991 DEBUG application/packet_received Received a packet: ZigbeePacket(src=AddrModeAddress(addr_mode=<AddrMode.NWK: 2>, address=0x1F17), src_ep=0, dst=AddrModeAddress(addr_mode=<AddrMode.Broadcast: 15>, address=<BroadcastAddress.ALL_ROUTERS_AND_COORDINATOR: 65532>), dst_ep=0, source_route=None, extended_timeout=False, tsn=129, profile_id=0, cluster_id=19, data=Serialized[b'\x81\x17\x1f\xb6&\x9b\xfe\xff\xb1\xb3\xf4\x8e'], tx_options=<TransmitOptions.NONE: 0>, radius=0, non_member_radius=0, lqi=None, rssi=None)
2023-10-02 01:25:44,991 INFO application/handle_join Device 0x1f17 (f4:b3:b1:ff:fe:9b:26:bb) joined the network
2023-10-02 01:25:44,992 DEBUG listener/handle_message >handle_message f4:b3:b1:ff:fe:9b:26:bb profile:0 cluster:19 src_ep:0 dst_ep:0 message:b'\x81\x17\x1f\xb6&\x9b\xfe\xff\xb1\xb3\xf4\x8e'
2023-10-02 01:25:44,992 DEBUG __init__/handle_message [0x1f17:zdo] ZDO request ZDOCmd.Device_annce: [0x1F17, f4:b3:b1:ff:fe:9b:26:bb, 142]
2023-10-02 01:25:44,993 DEBUG __init__/request [0x1F17:1:0x0004] Sending request header: ZCLHeader(frame_control=FrameControl(frame_type=<FrameType.CLUSTER_COMMAND: 1>, is_manufacturer_specific=False, direction=<Direction.Server_to_Client: 0>, disable_default_response=0, reserved=0, *is_cluster=True, *is_general=False), tsn=7, command_id=2, *direction=<Direction.Server_to_Client: 0>)
2023-10-02 01:25:44,994 DEBUG __init__/request [0x1F17:1:0x0004] Sending request: get_membership(groups=[])
2023-10-02 01:25:44,994 DEBUG application/send_packet Sending packet ZigbeePacket(src=AddrModeAddress(addr_mode=<AddrMode.NWK: 2>, address=0x0000), src_ep=1, dst=AddrModeAddress(addr_mode=<AddrMode.NWK: 2>, address=0x1F17), dst_ep=1, source_route=None, extended_timeout=False, tsn=7, profile_id=260, cluster_id=4, data=Serialized[b'\x01\x07\x02\x00'], tx_options=<TransmitOptions.NONE: 0>, radius=0, non_member_radius=0, lqi=None, rssi=None)
2023-10-02 01:25:44,995 DEBUG api/request Sending request: AF.DataRequestExt.Req(DstAddrModeAddress=AddrModeAddress(mode=<AddrMode.NWK: 2>, address=0x1F17), DstEndpoint=1, DstPanId=0x0000, SrcEndpoint=1, ClusterId=4, TSN=7, Options=<TransmitOptions.SUPPRESS_ROUTE_DISC_NETWORK: 32>, Radius=0, Data=b'\x01\x07\x02\x00')
```
Need to handle message with the following characteristics:
```python
profile == zigpy.zdo.ZDO_ENDPOINT
cluster == zigpy.zdo.types.ZDOCmd.Device_annce
# header, data = device.endpoints[profile].deserialize(cluster, b'\x81\x17\x1f\xb6&\x9b\xfe\xff\xb1\xb3\xf4\x8e')
```


Sources
-------

Zigbee2MQTT
- <https://www.zigbee2mqtt.io/guide/getting-started/#installation>
- <https://www.zigbee2mqtt.io/supported-devices/>
- [TRADFRI ON/OFF switch](https://www.zigbee2mqtt.io/devices/E1743.html)
- [TRADFRI shortcut button](https://www.zigbee2mqtt.io/devices/E1812.html)
- [TRADFRI control outlet](https://www.zigbee2mqtt.io/devices/E1603_E1702_E1708.html)
- [TRADFRI LED globe-bulb](https://www.zigbee2mqtt.io/devices/LED1936G5.html)
- <https://github.com/Koenkk/zigbee2mqtt.io>
Zigpy
- <https://github.com/zigpy/zigpy>
- <https://github.com/zigpy/zigpy-znp>
- <https://github.com/zigpy/zigpy/wiki>
- <https://github.com/zigpy/zigpy/blob/dev/CONTRIBUTING.md>
Zigpy reference
- [Cluster base class](https://github.com/zigpy/zigpy/blob/dev/zigpy/zcl/__init__.py#L56)
- [Basic](https://github.com/zigpy/zigpy/blob/dev/zigpy/zcl/clusters/general.py#L204)
- [PowerConfiguration](https://github.com/zigpy/zigpy/blob/dev/zigpy/zcl/clusters/general.py#L301)
- [OnOff](https://github.com/zigpy/zigpy/blob/dev/zigpy/zcl/clusters/general.py#L862)
- [LevelControl](https://github.com/zigpy/zigpy/blob/dev/zigpy/zcl/clusters/general.py#L967)
- [Color](https://github.com/zigpy/zigpy/blob/dev/zigpy/zcl/clusters/lighting.py#L86)
Zigpy examples
- <https://github.com/MalteGruber/zigpy_standalone>
- <https://github.com/zigpy/zigpy-znp/blob/dev/TOOLS.md#tools>
- <https://github.com/zigpy/zigpy/issues/452>
- <https://github.com/zigpy/zigpy/issues/1087>
- <https://github.com/zigpy/zigpy-znp/issues/166>
Misc
- <https://www.youtube.com/watch?v=nAOIlTCQNnY&list=PL3XBzmAj53RllodTTGbJ-j8G066aczrj3&index=8>
- <https://www.aliexpress.com/item/1005004443820263.html>
- <https://www.home-assistant.io/integrations/zha/>
- <https://github.com/home-assistant/core/tree/dev/homeassistant/components/zha>
- <https://blog.jeedom.com/5183-tout-ce-quil-faut-savoir-sur-le-plugin-officiel-zigbee/>

