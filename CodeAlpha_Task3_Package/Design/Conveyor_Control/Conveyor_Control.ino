/*
  CodeAlpha Task 3 - Sensor-based conveyor belt automation (Arduino Uno prototype)
  Author: Meet Agrawal

  Behaviour
    * Power-up: motor OFF (IDLE). Press START to begin.
    * RUN       : belt moves. Object sensor sees an object -> belt stops.
    * PROCESS   : belt held stopped for PROCESS_MS (count / inspect / sort station time).
    * CLEARING  : belt restarts; the object must leave the sensor beam within JAM_TIMEOUT_MS,
                  otherwise FAULT (jam or stuck sensor).
    * ESTOP     : E-stop contact opened (pressed OR wire broken) -> motor OFF in any state.
                  Needs the E-stop released AND a deliberate START press to resume.
                  If an already-counted object is still in the beam, the belt restarts in
                  CLEARING so that object is moved out without being counted again.
    * FAULT     : motor OFF, buzzer beeps; START press resets.
  The E-stop ALSO cuts motor power in hardware (see wiring diagram); this software
  input only tells the controller what happened. Software is never the only safety layer.

  Pins (Arduino Uno)
    D2  object sensor  (NPN-NO photoelectric, output LOW when object present)
    D3  E-stop monitor (2nd NC contact to GND: LOW = healthy, HIGH = pressed / open circuit)
    D4  exit sensor    (same type as D2)
    D5  START/RESET push button (to GND)
    D6  motor MOSFET gate (HIGH = run)
    D8  green LED   D9 red LED   D10 buzzer transistor base
*/
#include <Arduino.h>

const uint8_t PIN_OBJ = 2, PIN_ESTOP = 3, PIN_EXIT = 4, PIN_START = 5;
const uint8_t PIN_MOTOR = 6, PIN_GREEN = 8, PIN_RED = 9, PIN_BUZZ = 10;

const uint32_t DEBOUNCE_MS   = 30;     // input filter
const uint32_t PROCESS_MS    = 2000;   // station dwell time
const uint32_t CLEAR_MS      = 300;    // sensor must stay inactive this long to count as "clear"
const uint32_t JAM_TIMEOUT_MS = 5000;  // object must clear the beam within this time after restart

enum State : uint8_t { S_IDLE, S_RUN, S_PROCESS, S_CLEARING, S_FAULT, S_ESTOP };
State state = S_IDLE;
uint32_t stateSince = 0;
uint16_t objectCount = 0, exitCount = 0;
bool objectHeld = false;               // an already-counted object may still be in the beam

struct Input {                         // debounced digital input, active-LOW by default
  uint8_t pin; bool stable; bool raw; uint32_t since; bool rose;
};
Input inObj   = {PIN_OBJ,   false, false, 0, false};
Input inExit  = {PIN_EXIT,  false, false, 0, false};
Input inStart = {PIN_START, false, false, 0, false};
Input inEstop = {PIN_ESTOP, true,  true,  0, false};   // "active" = E-stop tripped; assume tripped until proven healthy

void updateInput(Input &in, bool activeNow, uint32_t now) {
  in.rose = false;
  if (activeNow != in.raw) { in.raw = activeNow; in.since = now; }
  if (in.raw != in.stable && now - in.since >= DEBOUNCE_MS) {
    in.stable = in.raw;
    if (in.stable) in.rose = true;
  }
}

void enter(State s, uint32_t now) { state = s; stateSince = now; }

void setup() {
  pinMode(PIN_OBJ, INPUT_PULLUP);  pinMode(PIN_EXIT, INPUT_PULLUP);
  pinMode(PIN_START, INPUT_PULLUP); pinMode(PIN_ESTOP, INPUT_PULLUP);
  pinMode(PIN_MOTOR, OUTPUT); pinMode(PIN_GREEN, OUTPUT);
  pinMode(PIN_RED, OUTPUT);   pinMode(PIN_BUZZ, OUTPUT);
  digitalWrite(PIN_MOTOR, LOW);          // motor OFF at power-up
  Serial.begin(9600);
  enter(S_IDLE, millis());
}

void loop() {
  uint32_t now = millis();
  updateInput(inObj,   digitalRead(PIN_OBJ)   == LOW,  now);
  updateInput(inExit,  digitalRead(PIN_EXIT)  == LOW,  now);
  updateInput(inStart, digitalRead(PIN_START) == LOW,  now);
  updateInput(inEstop, digitalRead(PIN_ESTOP) == HIGH, now);   // HIGH = tripped / wire broken
  if (inExit.rose) exitCount++;

  State prev = state;
  // E-stop has priority over everything (a raw tripped reading acts at once, no debounce delay)
  if (digitalRead(PIN_ESTOP) == HIGH && state != S_ESTOP) {
    digitalWrite(PIN_MOTOR, LOW);
    enter(S_ESTOP, now);
  }

  switch (state) {
    case S_IDLE:
      if (inStart.rose && !inEstop.stable) enter(S_RUN, now);
      break;
    case S_RUN:
      if (inObj.stable) { objectCount++; objectHeld = true; enter(S_PROCESS, now); }
      break;
    case S_PROCESS:
      if (now - stateSince >= PROCESS_MS) enter(S_CLEARING, now);
      break;
    case S_CLEARING: {
      static uint32_t clearSince = 0;
      if (stateSince == now) clearSince = 0;
      if (inObj.stable) clearSince = 0;
      else if (clearSince == 0) clearSince = now;
      if (clearSince != 0 && now - clearSince >= CLEAR_MS) { objectHeld = false; enter(S_RUN, now); }
      else if (now - stateSince >= JAM_TIMEOUT_MS) enter(S_FAULT, now);
      break; }
    case S_FAULT:
      if (inStart.rose && !inEstop.stable) enter(objectHeld ? S_CLEARING : S_RUN, now);
      break;
    case S_ESTOP:
      if (!inEstop.stable && inStart.rose) enter(objectHeld ? S_CLEARING : S_RUN, now);   // released AND deliberate START;
      // an object already counted is moved out of the beam first, so it is never counted twice
      break;
  }

  // ---- outputs (motor runs only in RUN and CLEARING) ----
  bool motorOn = (state == S_RUN || state == S_CLEARING);
  digitalWrite(PIN_MOTOR, motorOn ? HIGH : LOW);
  bool blink1 = (now / 500) % 2, blink4 = (now / 125) % 2;
  digitalWrite(PIN_GREEN, (state == S_RUN || state == S_CLEARING) ? HIGH : (state == S_PROCESS ? blink4 : LOW));
  digitalWrite(PIN_RED,   state == S_IDLE ? blink1 : (state == S_FAULT ? blink4 : (state == S_ESTOP ? HIGH : LOW)));
  digitalWrite(PIN_BUZZ,  state == S_FAULT ? blink4 : LOW);

  if (state != prev) {                       // log every state change
    Serial.print(now); Serial.print(" ms  state="); Serial.print((int)state);
    Serial.print("  objects="); Serial.print(objectCount);
    Serial.print("  exited=");  Serial.println(exitCount);
  }
}
