Introduction
============

.. image:: https://readthedocs.org/projects/adafruit-circuitpython-ssd1305/badge/?version=latest
    :target: https://docs.circuitpython.org/projects/ssd1305/en/latest/
    :alt: Documentation Status

.. image:: https://raw.githubusercontent.com/adafruit/Adafruit_CircuitPython_Bundle/main/badges/adafruit_discord.svg
    :target: https://adafru.it/discord
    :alt: Discord

.. image:: https://github.com/adafruit/Adafruit_CircuitPython_SSD1305/workflows/Build%20CI/badge.svg
    :target: https://github.com/adafruit/Adafruit_CircuitPython_SSD1305/actions/
    :alt: Build Status

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Code Style: Ruff

Framebuf (non-displayio) driver for SSD1305 displays


Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_
* `Bus Device <https://github.com/adafruit/Adafruit_CircuitPython_BusDevice>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://github.com/adafruit/Adafruit_CircuitPython_Bundle>`_.

Installing from PyPI
=====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/adafruit-circuitpython-ssd1305/>`_. To install for current user:

.. code-block:: shell

    pip3 install adafruit-circuitpython-ssd1305

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install adafruit-circuitpython-ssd1305

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install adafruit-circuitpython-ssd1305

Usage Example
=============

.. code-block:: python

    # Basic example of clearing and drawing pixels on a SSD1305 OLED display.
    # This example and library is meant to work with Adafruit CircuitPython API.
    # Author: Tony DiCola
    # License: Public Domain

    # Import all board pins.
    from board import SCL, SDA
    import busio

    # Import the SSD1305 module.
    import adafruit_ssd1305


    # Create the I2C interface.
    i2c = busio.I2C(SCL, SDA)

    # Create the SSD1305 OLED class.
    # The first two parameters are the pixel width and pixel height.  Change these
    # to the right size for your display!
    display = adafruit_ssd1305.SSD1305_I2C(128, 32, i2c)
    # Alternatively you can change the I2C address of the device with an addr parameter:
    #display = adafruit_ssd1305.SSD1305_I2C(128, 32, i2c, addr=0x31)

    # Clear the display.  Always call show after changing pixels to make the display
    # update visible!
    display.fill(0)

    display.show()

Documentation
=============

API documentation for this library can be found on `Read the Docs <https://docs.circuitpython.org/projects/ssd1305/en/latest/>`_.

For information on building library documentation, please check out `this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.

Web Simulator
=============

The library includes a high-performance web simulator for testing and development without physical hardware.

Features
--------

* **Real-time Display Simulation**: View SSD1305 display output in your browser
* **Hot-pluggable Sensors**: Automatic sensor detection with graceful fallback
* **Mock Mode**: Test without hardware using simulated sensor data
* **WebSocket Support**: Push updates for minimal latency (optional)
* **Dynamic Refresh Rate**: Automatically adjusts to match actual FPS
* **Performance Metrics**: Detailed timing breakdown for optimization
* **Static Benchmark**: Measure baseline server performance

Quick Start
-----------

.. code-block:: shell

    # Install optional dependencies
    pip install Pillow psutil
    
    # For WebSocket support (optional)
    pip install websockets
    
    # Run with mocked sensors
    python examples/ssd1305_web_simulator.py --use-mocks
    
    # Run with WebSocket push updates
    python examples/ssd1305_web_simulator.py --use-mocks --enable-websocket
    
    # Open browser to http://localhost:8000
    # Benchmark page at http://localhost:8000/benchmark

Performance
-----------

See `PERFORMANCE.md <PERFORMANCE.md>`_ for detailed performance information, benchmarking results, and optimization tips.

**Key Performance Features:**

* Client-side image scaling for 12x faster PNG delivery
* Background sensor data collection (non-blocking I/O)
* Cached sensor reads to minimize I2C overhead
* WebSocket push updates (~5ms latency vs 2000ms polling)
* Automatic refresh rate optimization based on actual FPS

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/adafruit/Adafruit_CircuitPython_SSD1305/blob/main/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.
