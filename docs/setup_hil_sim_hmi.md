# Setup HIL, Simulation, and HMI

## Communication

## Network Configuration

Ensure that all three machines (HIL, Simulation, and HMI) are on the same network and can communicate with each other. You may need to configure firewall settings to allow necessary ports for ROS 2 communication.
We propose the following IP configuration:
| Machine | IP Address | Hostname |
|------------|----------------|------------|
| Simulation | 192.168.1.1 | sim |
| HIL | 192.168.1.2 | hil |
| HMI | 192.168.1.4 | hmi |

Make sure that all machines are reachable by their ip addresses and hostnames. You can test this by pinging each machine from the others.

Verify bandwidth and latency between machines to ensure they meet the requirements for real-time communication.
This demo requires at least 60 Mbps bandwidth.
Perform a simple bandwidth test using `iperf3`:

1. On the Simulation machine (server):
2. ```bash
   iperf3 -s
   ```
3. On the HIL machine (client):
4. ````bash
       iperf3 -c 192.168.1.1
       ```
   You should see a bandwidth of at least 900 Mbps for 1 GBps transfer. If not, check your network configuration (cables, switches, etc.).
   ````

## DDS Configuration

ROS 2 uses DDS (Data Distribution Service) for communication. To optimize performance, you may need to configure the DDS settings.
Add this to your `.bashrc` or `.zshrc` file on all three machines:

```bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=~/cyclonedds.xml
```

Create a `cyclonedds.xml` file in the specified location with the following content:

```xml
<?xml version="1.0" encoding="utf-8"?>
<CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="https://cdds.io/config https://raw.githubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">

  <Domain Id="any">
    <General>
      <!-- Force no multicast on all interfaces -->
      <Interfaces>
        <NetworkInterface name="<PUT_YOUR_INTERFACE_NAME>" multicast="false" priority="default" />
        <!-- Add more interfaces as needed -->
      </Interfaces>
      <AllowMulticast>false</AllowMulticast>

      <!-- Increase message size if needed to avoid fragmentation -->
      <MaxMessageSize>65536B</MaxMessageSize>  <!-- adjust based on MTU etc. -->
    </General>

    <Discovery>
      <!-- No multicast SPDP, specify peers explicitly -->
      <Peers>
        <Peer address="192.168.1.2"/>  <!-- peer A -->
        <Peer address="192.168.1.3"/>  <!-- peer B -->
	<Peer address="192.168.1.4"/>  <!-- peer C -->
</Peers>

      <!-- Optionally fix participant index for port calculation -->
      <ParticipantIndex>auto</ParticipantIndex>

      <!-- SPDP interval tuning -->
      <SPDPInterval>1s</SPDPInterval>  <!-- more frequent to reduce join latency -->
    </Discovery>

    <Internal>
      <!-- Larger socket buffers for heavy throughput -->
      <SocketReceiveBufferSize min="1 MiB" max="16 MiB" />
      <SocketSendBufferSize min="1 MiB" max="16 MiB" />

      <!-- Possibly multiple receive threads if needed -->
      <MultipleReceiveThreads>true</MultipleReceiveThreads>

      <!-- Adjust heartbeat‐interval for reliable performance -->
      <HeartbeatInterval min="5 ms" max="100 ms" />
    </Internal>
  </Domain>
</CycloneDDS>
```

**IMPORTANT: Replace `<PUT_YOUR_INTERFACE_NAME>` with the actual network interface name (e.g., `eth0`).
You can find your interface name using the `ip a` command.**

## Setup HIL

HIL (Hardware in the Loop) is the machine that runs the ROS 2 Stack and GenAI inference.

Setup instructions: [HiL setup](./setup_hil.md)

## Setup Simulation

Simulation is the machine that runs the O3DE simulation environment.

Setup instructions: [Simulation setup](./setup_sim.md)

## Setup HMI

HMI (Human–Machine Interface) is the machine that runs the GUI.

Setup instructions: [HMI setup](./setup_hmi.md)

# Next Steps

- [Running the demo](./running_hil_sim_hmi.md)
