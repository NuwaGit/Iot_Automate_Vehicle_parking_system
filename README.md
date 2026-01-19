# IoT and Cloud AI Based Smart Car Parking System

This project is a small **smart car park demo** built with **IoT devices** and **AI-based number plate recognition**.  
It was developed for the **COM6017M – The Internet of Things** module at **York St John University**.

The system:

- Detects vehicles at the **entry** and **exit** gates using a USB camera and virtual line detection.
- Reads the **vehicle number plate** using OCR.
- Checks **parking slot availability** using an ESP32 and sensors.
- Calculates **parking duration** and **fee**.
- Controls **entry/exit barriers** automatically using servo motors.
- Blocks entry when the car park is **full** and activates a **buzzer**.

There are **two main versions** of the system:

1. **Edge OCR version** – uses **PyTesseract** (Tesseract OCR) locally on the Raspberry Pi.  
2. **Cloud OCR version** – uses **Google Vision API** for number plate OCR.

---

## 1. System Overview

### 1.1 Hardware

- **Raspberry Pi 4**  
  Edge controller for image capture, pre-processing, serial communication, and system logic.

- **USB Web Camera**  
  Captures vehicle number plate images at entry and exit.

- **ESP32 Development Board**  
  Reads sensors, drives servo motors, and controls the buzzer. Communicates with the Raspberry Pi via UART.

- **2 x Servo Motors**  
  Used as **entry** and **exit** barriers.

- **IR Sensor(s)**  
  Used to detect vehicle presence and/or parking slot occupancy.

- **Small Buzzer**  
  Gives a beep when the car park is full or when an error occurs.

- **Power regulator + 5V, 3A USB-C supply**  
  Powers the Raspberry Pi and other components.

- **Breadboard, cables and wires**  
  For prototyping and connecting all modules.

---

## 2. Software Stack

### 2.1 Raspberry Pi (Python)

- **OpenCV (opencv-python)** – capture frames from the USB camera, run virtual line detection, crop plate areas.  
- **Pillow (PIL)** – resize and clean images before OCR.  
- **PySerial** – UART communication between Raspberry Pi and ESP32.  
- **Logging, datetime, threading** – for control logic and event handling.

#### OCR Options

1. **Edge OCR (PyTesseract)**  
   - Uses **Tesseract OCR** installed on the Pi.  
   - OCR runs fully on the Raspberry Pi (Edge AI style).

2. **Cloud OCR (Google Vision API)**  
   - Raspberry Pi sends the cropped plate image to **Google Vision API**.  
   - Cloud returns the recognised text (number plate).  
   - Requires a **Google Cloud project**, API key/service account, and network access.

### 2.2 ESP32 (Arduino)

- **ESP32 Arduino Core** – firmware platform.  
- **ESP32Servo** – drives the servo motors reliably on ESP32.  
- **Serial (UART)** – sends messages like `SLOT_OCCUPIED` / `SLOT_FREE` to the Pi and receives commands such as:

  - `OPEN_ENTRY`
  - `CLOSE_ENTRY`
  - `OPEN_EXIT`
  - `CLOSE_EXIT`
  - `BUZZER_ON` / `BUZZER_OFF`

---

## 3. Main Python Files

> ⚠️ Adjust filenames here if your repo uses different names.

- `main_tesseract.py`  
  Raspberry Pi controller using **PyTesseract** for local OCR.

- `main_google_vision.py`  
  Raspberry Pi controller using **Google Vision API** for cloud OCR.

Other important modules (example names):

- `serial_comm.py` – wraps serial communication with ESP32 and gate/buzzer commands.  
- `camera_handler.py` – camera initialisation, virtual line detection, plate extraction.  
- `data_manager.py` – stores active vehicles, history, and slot status (e.g., in memory / file / DB).  
- `fee_calculator.py` – calculates parking duration and fee.

---

## 4. How the System Works

### 4.1 Data Flow

1. A vehicle crosses the **entry** virtual line in the camera view.  
2. Raspberry Pi captures a frame, crops the entry zone, and sends the plate area to OCR  
   - locally (PyTesseract) **or**  
   - to Google Vision API (cloud OCR).
3. The Pi checks:
   - Is this vehicle already inside?  
   - Is there a free slot (`SLOT_FREE` / `SLOT_OCCUPIED` from ESP32)  
4. If there is space, the Pi:
   - logs vehicle number + entry time + slot,  
   - sends `OPEN_ENTRY` to ESP32,  
   - closes the gate after a short timeout.
5. On **exit**, the Pi:
   - reads the number plate again,  
   - finds the entry record,  
   - calculates duration and fee,  
   - adds a history record,  
   - sends `OPEN_EXIT` to ESP32.
6. If the car park is full, the Pi refuses entry and triggers the **buzzer**.

---

## 5. Setup and Running

### 5.1 Install Dependencies (Raspberry Pi)

```bash
sudo apt update
sudo apt install python3-pip

# If using PyTesseract version:
sudo apt install tesseract-ocr
pip3 install opencv-python pillow pytesseract pyserial

# If using Google Vision version:
pip3 install opencv-python pillow google-cloud-vision pyserial
