FROM ardupilot/ardupilot-dev-base:edge

# QGC connectivity: SITL exposes MAVLink on tcp 5760 (primary) and udp 14550
# (QGC default). The JSON bridge to the Gazebo ArduPilotPlugin is on
# 127.0.0.1:9002 (--model JSON:127.0.0.1). When run via docker-compose.yml the
# command is overridden to include --out=udp:0.0.0.0:14550 so QGC on the host
# (or any device on the same network) can connect without extra flags.
# See compose file for the full bringup command including --custom-location
# fix for the depth-hold baro/altitude bug.

# ARG COPTER_TAG=Copter-4.5.7

# install git
RUN apt-get update && apt-get install --no-install-recommends -y git; git config --global url."https://github.com/".insteadOf git://github.com/

# Now grab ArduPilot from GitHub
RUN git clone --depth=1 https://github.com/ArduPilot/ardupilot.git /ardupilot
WORKDIR /ardupilot

# Checkout the latest Copter...
# RUN git checkout master

# Now start build instructions from http://ardupilot.org/dev/docs/setting-up-sitl-on-linux.html
RUN git submodule update --init --recursive

# Trick to get apt-get to not prompt for timezone in tzdata
ENV DEBIAN_FRONTEND=noninteractive

# Need sudo and lsb-release for the installation prerequisites
RUN apt-get install -y --no-install-recommends sudo lsb-release tzdata

# Continue build instructions from https://github.com/ArduPilot/ardupilot/blob/master/BUILD.md
RUN ./waf distclean
RUN ./waf configure --board sitl
RUN ./waf build

# MAVLink for QGC / companion computer; JSON FDM bridge to Gazebo.
EXPOSE 5760/tcp
EXPOSE 5762/tcp
EXPOSE 14550/udp
EXPOSE 14555/udp
EXPOSE 9002/tcp
EXPOSE 9002/udp

RUN pip3 install --no-cache-dir --break-system-packages MAVProxy pymavlink 2>/dev/null \
  || pip3 install --no-cache-dir MAVProxy pymavlink # Install MAVProxy (Debian trixie needs --break-system-packages)

# Default command is overridden by docker-compose.yml (which adds --custom-location,
# --add-param-file and --out for QGC). This ENTRYPOINT remains usable for
# standalone `docker run`:
#   docker run --network host ghcr.io/davidnoronha1/mira_sim-ardupilot-sitl --out=udp:0.0.0.0:14550
ENTRYPOINT ["/ardupilot/Tools/autotest/sim_vehicle.py", "-N", "-f", "vectored_6dof", "-v", "ArduSub", "--console", "--model", "JSON:127.0.0.1"]