/*
 * Parking System - ESP32 Controller (Simplified)
 * Manages 1 IR sensor (parking slot), 2 servo motors (entry/exit gates), 
 * buzzer, and communicates with Raspberry Pi
 */

#include <ESP32Servo.h>

// Pin Definitions (NodeMCU ESP-32S)
// IR Sensor (Digital Input)
#define SLOT_IR_PIN 18      // Parking slot IR sensor (GPIO 18)

// Servo Motors (PWM Output)
#define ENTRY_SERVO_PIN 13  // Entry gate servo (GPIO 13)
#define EXIT_SERVO_PIN 14   // Exit gate servo (GPIO 14)

// Buzzer (Digital Output)
#define BUZZER_PIN 12       // Buzzer (GPIO 12)

// Servo Objects
Servo entryServo;
Servo exitServo;

// Servo Angles (adjust based on physical setup)
#define SERVO_CLOSED_ANGLE 0    // Gate closed position
#define SERVO_OPEN_ANGLE 90     // Gate open position

// Serial Communication
#define BAUD_RATE 115200

// Sensor States
bool slotIRState = false;
bool prevSlotIRState = false;

// Gate States
bool entryGateOpen = false;
bool exitGateOpen = false;

// Parking Slot State
bool slotOccupied = false;

// Debounce delay (milliseconds)
#define DEBOUNCE_DELAY 50
unsigned long lastSlotChange = 0;

void setup() {
  // Initialize Serial Communication
  Serial.begin(BAUD_RATE);
  while (!Serial) {
    delay(10); // Wait for serial port to connect
  }
  
  // Initialize IR Sensor Pin (Input with internal pull-up)
  pinMode(SLOT_IR_PIN, INPUT_PULLUP);
  
  // Initialize Servo Motors
  entryServo.attach(ENTRY_SERVO_PIN);
  exitServo.attach(EXIT_SERVO_PIN);
  
  // Initialize gates to closed position
  entryServo.write(SERVO_CLOSED_ANGLE);
  exitServo.write(SERVO_CLOSED_ANGLE);
  entryGateOpen = false;
  exitGateOpen = false;
  
  // Initialize Buzzer
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  
  // Read initial sensor state
  slotIRState = !digitalRead(SLOT_IR_PIN); // Invert because pull-up (LOW = detected)
  prevSlotIRState = slotIRState;
  
  // Determine initial parking slot occupancy
  slotOccupied = slotIRState;
  
  // Send initial parking slot status
  sendSlotStatus();
  
  delay(1000); // Allow system to stabilize
}

void loop() {
  // Read IR sensor with debouncing
  readIRSensor();
  
  // Check for sensor state changes and send messages
  checkParkingSlot();
  
  // Handle serial commands from Raspberry Pi
  handleSerialCommands();
  
  delay(10); // Small delay to prevent excessive CPU usage
}

void readIRSensor() {
  unsigned long currentTime = millis();
  
  // Parking Slot IR
  bool currentSlot = !digitalRead(SLOT_IR_PIN);
  if (currentSlot != slotIRState) {
    if (currentTime - lastSlotChange > DEBOUNCE_DELAY) {
      slotIRState = currentSlot;
      lastSlotChange = currentTime;
    }
  }
}

void checkParkingSlot() {
  // Check Parking Slot
  bool newSlotOccupied = slotIRState;
  if (newSlotOccupied != slotOccupied) {
    slotOccupied = newSlotOccupied;
    if (slotOccupied) {
      Serial.println("SLOT_OCCUPIED");
    } else {
      Serial.println("SLOT_FREE");
    }
  }
}

void sendSlotStatus() {
  // Send current parking slot status
  if (slotOccupied) {
    Serial.println("SLOT_OCCUPIED");
  } else {
    Serial.println("SLOT_FREE");
  }
}

void handleSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "OPEN_ENTRY_GATE") {
      openEntryGate();
    } else if (command == "CLOSE_ENTRY_GATE") {
      closeEntryGate();
    } else if (command == "OPEN_EXIT_GATE") {
      openExitGate();
    } else if (command == "CLOSE_EXIT_GATE") {
      closeExitGate();
    } else if (command == "BUZZER_ON") {
      digitalWrite(BUZZER_PIN, HIGH);
    } else if (command == "BUZZER_OFF") {
      digitalWrite(BUZZER_PIN, LOW);
    }
  }
}

void openEntryGate() {
  if (!entryGateOpen) {
    entryServo.write(SERVO_OPEN_ANGLE);
    entryGateOpen = true;
    delay(500); // Allow servo to move
  }
}

void closeEntryGate() {
  if (entryGateOpen) {
    entryServo.write(SERVO_CLOSED_ANGLE);
    entryGateOpen = false;
    delay(500); // Allow servo to move
  }
}

void openExitGate() {
  if (!exitGateOpen) {
    exitServo.write(SERVO_OPEN_ANGLE);
    exitGateOpen = true;
    delay(500); // Allow servo to move
  }
}

void closeExitGate() {
  if (exitGateOpen) {
    exitServo.write(SERVO_CLOSED_ANGLE);
    exitGateOpen = false;
    delay(500); // Allow servo to move
  }
}
