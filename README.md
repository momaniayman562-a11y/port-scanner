# Python Port Scanner

A multithreaded TCP port scanner with a GUI, built with Python and Tkinter.

## Features
- Scan any port range (1-65535) on a target IP
- Multithreaded scanning with adjustable threads and timeout
- Service detection and banner grabbing (including HTTP Server header)
- Live progress bar and Stop button
- Export results to CSV
- Input validation (invalid IP, empty fields, bad port ranges)

## Requirements
- Python 3 -
- No external libraries (standard library only)

## Usage
Run: `python port_scanner.py`

1. Enter the target IP and port range
2. Click **Start Scan**
3. Click **Stop** to cancel, or **Export CSV** to save results

## Disclaimer
For educational use. Only scan systems you own or have explicit permission to test.
