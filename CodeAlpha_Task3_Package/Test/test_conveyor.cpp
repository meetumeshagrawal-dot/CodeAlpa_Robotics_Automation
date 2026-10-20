// Host test: compiles the real Conveyor_Control.ino against a fake Arduino + simple belt model.
#include "Arduino.h"
uint8_t g_in[20], g_out[20]; uint32_t g_ms = 0; SerialShim Serial;
#include "../Design/Conveyor_Control/Conveyor_Control.ino"
#include <vector>
#include <cmath>

static FILE* csv = nullptr; static int fails = 0, checks = 0;
#define CHECK(name, cond) do { checks++; bool ok = (cond); printf("  [%s] %s\n", ok ? "PASS" : "FAIL", name); if (!ok) fails++; } while (0)

struct Plant {                      // belt model: 100 mm/s while motor pin HIGH
  std::vector<double> x;            // leading-edge position of each object (mm), -1 = not yet on belt
  double len = 60, v = 100; double sensor0 = 500, sensor1 = 540, exit0 = 900, exit1 = 940;
  bool stuck = false;               // force object sensor active (jam / failed sensor)
  bool objActive() const { if (stuck) return true; for (double p : x) if (p >= sensor0 && p - len <= sensor1) return true; return false; }
  bool exitActive() const { for (double p : x) if (p >= exit0 && p - len <= exit1) return true; return false; }
};

struct Sim {
  Plant pl; bool estop = false, start = false; bool noise = false; double pos_when_stopped = -1;
  void reset() {                  // emulate a power cycle: all sketch globals back to their power-up values
    for (auto& v : g_in) v = HIGH; for (auto& v : g_out) v = LOW; g_ms = 0; g_in[PIN_ESTOP] = LOW;
    objectCount = 0; exitCount = 0; objectHeld = false; state = S_IDLE; stateSince = 0;
    inObj = {PIN_OBJ, false, false, 0, false}; inExit = {PIN_EXIT, false, false, 0, false};
    inStart = {PIN_START, false, false, 0, false}; inEstop = {PIN_ESTOP, true, true, 0, false};
    pl = Plant(); noise = false; estop = false; start = false; setup(); }
  void tick() {
    // plant motion
    if (g_out[PIN_MOTOR]) for (auto& p : pl.x) if (p >= 0) p += pl.v * 0.001;
    g_in[PIN_OBJ]   = (pl.objActive() || noise) ? LOW : HIGH;
    g_in[PIN_EXIT]  = pl.exitActive() ? LOW : HIGH;
    g_in[PIN_ESTOP] = estop ? HIGH : LOW;
    g_in[PIN_START] = start ? LOW : HIGH;
    loop(); g_ms++;
    if (csv && g_ms % 10 == 0)
      fprintf(csv, "%u,%d,%d,%d,%d,%d,%d,%d,%d\n", g_ms, state, g_out[PIN_MOTOR], !g_in[PIN_OBJ], !g_in[PIN_EXIT],
              g_in[PIN_ESTOP], !g_in[PIN_START], g_out[PIN_RED], g_out[PIN_BUZZ]);
  }
  void run(uint32_t ms) { while (ms--) tick(); }
  void press() { start = true; run(60); start = false; run(60); }
};

int main() {
  Sim s;
  printf("Scenario 1: power-up, START, three objects, normal operation\n");
  csv = fopen("scenario1.csv", "w"); fprintf(csv, "t_ms,state,motor,object_sensor,exit_sensor,estop_open,start_btn,red,buzzer\n");
  s.reset(); s.pl.x = {-1, -1, -1};
  s.run(1000);
  CHECK("motor OFF and state IDLE after power-up (no auto-start)", state == S_IDLE && g_out[PIN_MOTOR] == LOW);
  s.press();
  CHECK("START press -> RUN, motor ON", state == S_RUN && g_out[PIN_MOTOR] == HIGH);
  s.pl.x[0] = 0; double stopPos = -1; uint32_t stopT = 0, resumeT = 0; bool seenStop = false;
  for (uint32_t k = 0; k < 40000; k++) {
    if (k == 9000) s.pl.x[1] = 0;      // second object enters 9 s later
    if (k == 18000) s.pl.x[2] = 0;
    State pv = state; s.tick();
    if (pv != state && state == S_PROCESS && !seenStop) { stopPos = s.pl.x[0]; stopT = g_ms; seenStop = true; }
    if (pv == S_PROCESS && state == S_CLEARING && !resumeT) resumeT = g_ms;
  }
  fclose(csv); csv = nullptr;
  CHECK("belt stopped with object 1 at the sensor (leading edge 500-510 mm)", stopPos >= 500 && stopPos <= 510);
  CHECK("dwell time was 2.00 s", resumeT - stopT >= 1999 && resumeT - stopT <= 2002);
  CHECK("3 objects counted at the station", objectCount == 3);
  CHECK("3 objects counted at the exit sensor", exitCount == 3);
  CHECK("ends in RUN, no fault", state == S_RUN);

  printf("Scenario 2: sensor noise (10 ms glitches) while belt is empty\n");
  s.reset(); s.pl.x.clear(); s.run(100); s.press(); uint16_t c0 = objectCount; bool changed = false;
  for (int k = 0; k < 50; k++) { s.noise = true; s.run(10); s.noise = false; s.run(190); if (state != S_RUN) changed = true; }
  CHECK("no false detection from 10 ms glitches", !changed && objectCount == c0);
  s.noise = true; s.run(60); s.noise = false;
  CHECK("a sustained signal (60 ms) IS accepted as an object", state == S_PROCESS);

  printf("Scenario 3: emergency stop (a broken E-stop wire reads the same as a pressed button)\n");
  s.reset(); s.pl.x = {0}; s.run(100); s.press(); s.run(2000);
  s.estop = true; s.tick();
  CHECK("motor OFF within 1 ms of E-stop (no debounce delay)", g_out[PIN_MOTOR] == LOW && state == S_ESTOP);
  s.estop = false; s.run(500);
  CHECK("releasing E-stop alone does NOT restart", state == S_ESTOP && g_out[PIN_MOTOR] == LOW);
  s.press();
  CHECK("START after release restarts", state == S_RUN && g_out[PIN_MOTOR] == HIGH);
  s.estop = true; s.start = true; s.run(300); s.start = false; s.run(100);
  CHECK("START pressed while E-stop is held is ignored", state == S_ESTOP && g_out[PIN_MOTOR] == LOW);
  s.estop = false; s.run(100); s.press();
  s.reset(); s.pl.x = {0}; s.run(100); s.press(); while (state != S_PROCESS) s.tick();
  s.estop = true; s.tick(); CHECK("E-stop during PROCESS -> ESTOP", state == S_ESTOP && g_out[PIN_MOTOR] == LOW);
  s.estop = false; s.run(300);
  CHECK("releasing E-stop in PROCESS does not restart by itself", state == S_ESTOP && g_out[PIN_MOTOR] == LOW);
  s.press(); CHECK("START restarts into CLEARING (object still in beam)", state == S_CLEARING && g_out[PIN_MOTOR] == HIGH);
  s.run(2000); CHECK("object moved out, back to RUN, and NOT counted twice", state == S_RUN && objectCount == 1);

  printf("Scenario 4: jam / stuck sensor\n");
  s.reset(); s.pl.x = {-1}; s.run(100); s.press(); s.pl.stuck = true; s.run(100);
  CHECK("stuck-active sensor is treated as an object", state == S_PROCESS);
  s.run(2000 + 5000 + 100);
  CHECK("jam detected: FAULT after dwell + 5 s timeout, motor OFF", state == S_FAULT && g_out[PIN_MOTOR] == LOW);
  { bool hi = false, lo = false; for (int k = 0; k < 1000; k++) { s.tick(); (g_out[PIN_BUZZ] ? hi : lo) = true; }
    CHECK("buzzer pulses (both on and off) while in FAULT", hi && lo); }
  s.pl.stuck = false; s.press();
  CHECK("after the jam is removed, START resets (CLEARING)", state == S_CLEARING);
  s.run(500); CHECK("then RUN, object count still 1", state == S_RUN && objectCount == 1);

  printf("\n%d/%d checks passed\n", checks - fails, checks);
  return fails ? 1 : 0;
}
