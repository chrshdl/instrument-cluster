## Instrument Cluster

This instrument cluster is purpose-built for racing: fully digital, highly configurable, and offering real-time insights on critical vehicle dynamics, performance, and strategy. Drivers can tailor the display to their immediate needs, shifting from a broad overview of systems and resources (Page 1) to a performance-centered focus (Page 2) as the situation demands.

## Features

| Feature                          | Function & Benefit                                              |
| -------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Dual Dash Pages**    | Enables quick switching based on driving context—strategy vs. attack mode. |
| **Tyre, Oil, and Temp Readouts** | Facilitates real-time monitoring of mechanical health and tire performance.|
| **DSC/TC/ABS Status** | Allows instant feedback on stability systems—critical for safety and handling in varied conditions. |
| **Gear, Speed, Fuel Usage**   | Essential metrics for race strategy and real-time decision-making. |
| **RPM & Shift Lights**   | Help drivers optimize gear shifts and engine performance, maximizing speed and efficiency.|


### 1. Selectable Dash Pages
The instrument cluster allows the driver to switch between two customizable pages, each displaying a different set of data to suit the driver's needs.

####  Page 1 (Comprehensive Monitoring)
This primary layout presents vital vehicle and system information at a glance:

- Tyre Pressures (in bar or PSI) – displayed in the upper-left cluster.
- DSC (Dynamic Stability Control) Settings – current mode visible below tire pressure.
- Traction Control (TC) Status – shows if TC is active or disabled, especially when DSC is off, highlighted in red when TC is off.
- ABS Status – indicates if the Anti-lock Braking System is on or off based on DSC/TC mode.
- Throttle Setting – shows the current throttle mapping in use.
- Temperature Readouts:
  - Engine coolant (TMOT)
  - Engine oil (TOIL)
  - Gearbox oil (TGEAR)
  - Differential oil (TDIFF)
- Gear Indicator – center top, too important to miss.
- Speed – current speed (kph or mph) clearly displayed.
- Fuel Used – tracks how much fuel has been consumed since last pit stop, helping with strategic planning.

####  Page 2 (Performance-Focused)

This view zeroes in on performance metrics:
- RPM / Tachometer – crucial for managing engine rev limits and shift points.
- Shift Lights – alerts driver when it’s optimal to shift gears for maximum performance.

### 2. LED Shift Lights
The shift lights aren’t just a set of pretty LEDs— they’re a tuned, real-time performance guide for the driver. Here's how they work and how they decide when and how to alert you.

In a real race car, the ECU knows the engine torque curve (torque vs RPM).
From that, and the gear ratios, you can figure out in which gear the car accelerates harder, and when to shift. In GT7 telemetry we don’t get engine torque.
So we need a proxy (an indirect measurement).

From the telemetry we get:
- Engine RPM
- Gear number
- Car speed
- Wheel speeds
- Acceleration (derived from speed change)

The trick is: _Wheel torque proxy_

Physics says force at the wheels is car mass × acceleration.

$$
F=m \cdot a
$$

If we don’t know the mass, we just say “Acceleration itself is a proxy for force.”

If we add wheel radius:

$$
T_{wheel} \approx a \cdot r
$$

That’s our wheel torque proxy (up to a scaling factor we don’t need).
So: _"How hard the car pushes you back in the seat = how much torque it’s really making at the wheels."_

That’s all we care about for shift lights.

#### Building the per-gear curves
We watch telemetry over time and collect samples:

- Gear = 3, RPM = 5000 -> Proxy torque = 420
- Gear = 3, RPM = 6000 -> Proxy torque = 410
- Gear = 3, RPM = 7000 -> Proxy torque = 370
- ... and the same for gear 4, gear 5, etc.

Then we put them into bins (say every 100 RPM) and keep the 95th percentile (so noise or bad samples don’t ruin it).

This gives us a smooth curve: _"What the car really delivers at the wheels in this gear."_

#### Implementation
Pass thresholds into the constructor:

```python
from shift_lights import ShiftLights

# Light outer pair at 62% of target, next at 78%, next at 92%, center pair at 98%
custom_steps = [0.62, 0.78, 0.92, 0.98]   # fractions of target RPM

# Pairs become yellow after halfway in, red after 80% of the pairs
color_breaks = (0.5, 0.8)  # (green_to, yellow_to), both in 0..1 by pair index

widget = ShiftLights(anchor, step_thresholds=custom_steps, color_thresholds=color_breaks)
```

Or tweak at runtime:

```python
widget.step_thresholds = [0.65, 0.80, 0.93, 0.985]
widget.color_thresholds = (0.45, 0.78)
```
#### What is “clean coast data”?
A sample (speed $v$, measured longitudinal acceleration $a$) is considered clean if
 - Throttle ~ 0: throttle < 0.05
   
   (no engine tractive force; we’re measuring resistances only)

- Brake ~ 0: brake < 0.05
  
  (no additional decel from brakes)

- Straight-ish: small steering input (the demo uses a modest limit internally; in your GT7 pipeline you’d use your steer signal and drop turns)

- Above a minimum speed: we ignore very low speeds where sensors are noisy and the v² term is meaningless (demo uses a small floor implicitly).

- No rev-limiter events: limiter oscillation can glitch the accel; those samples are ignored.

These filters make sure the acceleration we record during coast is dominated by rolling resistance $(C_0)$ speed-proportional losses $(C_1v)$, and aero drag $(C_2v^2)$. That’s exactly what we need to model and later subtract during WOT pulls.

**Tip to warm it up quickly in Sim**

Lift completely (throttle 0, brake 0) on a straight for a few seconds.
You’ll see N rise; once it crosses ~200, the button flips to WARM and your console prints the coefficients.

**Behavior summary**

LEDs light in pairs from the outside in, based on the step_thresholds (fractions of the target RPM).

For 8 LEDs (4 pairs), provide 4 thresholds: one per pair.

Pair colors use color_thresholds by pair index:

index fraction < green_to -> green
< yellow_to -> yellow
otherwise -> red

At/over the target RPM: all LEDs flash red (on/off).

### Torque calculations

Acceleration

$$
a = \frac{dV}{dt}
$$

Velocity 

$$
V=r\omega
$$

where $r$ is the radius of wheel (`packet.wheels.front_left.radius`) and $\omega$ the angular speed of wheel (`packet.angular_velocity` or `packet.wheels.front_left.rps`) in radians/sec or
$\omega=2\pi\ \cdot \text{RPM} / 60$

Torque

$$
T=rMa
$$

where $M$ the mass of the car.


## License
All of my code is MIT licensed. Libraries follow their respective licenses.
