# Raspiberry PI Rower

## Description
I had purchased a rowing machine. Unfortunately, the machine did not calculate some values correctly, such as average Strokes Per Minute. Since I had a Raspberry PI and an ultrasonic sensor left, I thought I would try to build this myself. _The result is the RP Rower._

Of course, not all values can be calculated exactly, such as the distance per stroke, but the curiosity was aroused in me to try it out.

## Hardware
- Rowing machine
- Raspberry Pi 4
- Ultrasonic sensor HC-SR04 
- Resistors
- Breadboard
- Wires

## Set-up
- Set-up the Raspberry Pi with the sensor. You find enough tutorials in the internet to connect the sensor with the Raspberry Pi.
- The sensor measures the distance from the sensor to an object. In order to measure the distance, the sensor must be attached to the rowing machine. In my case I have attached the sensor under the hold for the feet. The object was placed under the seat.
- Clone the git project on your Raspberry Pi.
- Maybe you have to adapt the constant ```FACTOR_DISTANCE``` in the file ```rower.py```. This is used to convert the distance measured by the sensor to the distance of the stroke. As said, the distance value can only give a rough indication.

## Running
- Start the RP Rower with ```python3 rower.py```

## User Interface
- Connect with a device like a tablet to the rower, the server is running on port ```5000```.
- Click on Start button and start rowing :-) 