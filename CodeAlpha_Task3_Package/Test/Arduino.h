// Minimal host-side Arduino shim so the real .ino can be compiled and tested on a PC.
#pragma once
#include <cstdint>
#include <cstdio>
#include <string>
enum { INPUT = 0, OUTPUT = 1, INPUT_PULLUP = 2 };
#define LOW 0
#define HIGH 1
extern uint8_t g_in[20], g_out[20]; extern uint32_t g_ms;
inline void pinMode(uint8_t, uint8_t) {}
inline int digitalRead(uint8_t p) { return g_in[p]; }
inline void digitalWrite(uint8_t p, uint8_t v) { g_out[p] = v; }
inline uint32_t millis() { return g_ms; }
struct SerialShim { void begin(int) {} template <class T> void print(T) {} template <class T> void println(T) {} } ;
extern SerialShim Serial;
