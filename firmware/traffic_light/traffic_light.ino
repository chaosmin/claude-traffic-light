// ESP32-S3 Traffic Light Controller for Claude Code
// Commands via HTTP GET /cmd?state=THINKING (WiFi):
//   THINKING  - chase animation (R->Y->G cycling)
//   EXECUTING - yellow on (tool running)
//   DONE      - green on, auto-transitions to IDLE after DONE_HOLD_MS
//   ERROR     - red on
//   IDLE      - all off
//
// Also: GET /status  -> returns current state name
//
// WiFi config: hold BOOT button (GPIO0) on power-up to reset WiFi credentials.
// On first boot (or after reset), ESP32 opens hotspot "TrafficLight-Setup",
// connect with phone and visit 192.168.4.1 to configure WiFi.

#include <Adafruit_NeoPixel.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <WiFiManager.h>

// mDNS hostname: reachable at http://esp32-traffic-light.local/cmd?state=THINKING
#define HOSTNAME "esp32-traffic-light"

#define RESET_PIN 0  // BOOT button — hold on power-up to clear WiFi credentials

// === CONFIGURE YOUR GPIO PINS HERE ===
#define RED_PIN    4
#define YELLOW_PIN 5
#define GREEN_PIN  6
// =====================================

// YD-ESP32-S3 onboard WS2812 RGB LED
#define NEOPIXEL_PIN 48
#define NEOPIXEL_NUM 1

#define CHASE_INTERVAL_MS 300
#define DONE_HOLD_MS      60000

Adafruit_NeoPixel pixel(NEOPIXEL_NUM, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
WebServer server(80);

enum State { ST_IDLE, ST_THINKING, ST_EXECUTING, ST_DONE, ST_ERROR };

State     currentState = ST_IDLE;
int       chaseStep    = 0;
uint32_t  lastChase    = 0;
uint32_t  doneAt       = 0;

void blinkBuiltin(int times, uint32_t color) {
  for (int i = 0; i < times; i++) {
    pixel.setPixelColor(0, color);
    pixel.show();
    delay(80);
    pixel.setPixelColor(0, 0);
    pixel.show();
    delay(80);
  }
}

void allOff() {
  digitalWrite(RED_PIN,    LOW);
  digitalWrite(YELLOW_PIN, LOW);
  digitalWrite(GREEN_PIN,  LOW);
}

void applyIdle()      { allOff(); currentState = ST_IDLE; }
void applyThinking()  { allOff(); currentState = ST_THINKING; chaseStep = 0; lastChase = 0; }
void applyExecuting() { allOff(); digitalWrite(YELLOW_PIN, HIGH); currentState = ST_EXECUTING; }
void applyDone()      { allOff(); digitalWrite(GREEN_PIN,  HIGH); currentState = ST_DONE; doneAt = millis(); }
void applyError()     { allOff(); digitalWrite(RED_PIN,    HIGH); currentState = ST_ERROR; }

void handleCmd() {
  String state = server.arg("state");
  state.toUpperCase();
  state.trim();

  if      (state == "THINKING")  { blinkBuiltin(2, pixel.Color(0, 0, 255));   applyThinking(); }
  else if (state == "EXECUTING") { blinkBuiltin(1, pixel.Color(255, 255, 0)); applyExecuting(); }
  else if (state == "DONE")      { blinkBuiltin(3, pixel.Color(0, 255, 0));   applyDone(); }
  else if (state == "ERROR")     { blinkBuiltin(4, pixel.Color(255, 0, 0));   applyError(); }
  else if (state == "IDLE")      { applyIdle(); }
  else {
    server.send(400, "text/plain", "ERR:unknown state");
    return;
  }
  server.send(200, "text/plain", "OK:" + state);
  Serial.println("cmd: " + state);
}

void handleStatus() {
  const char* names[] = {"IDLE", "THINKING", "EXECUTING", "DONE", "ERROR"};
  server.send(200, "text/plain", names[currentState]);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pixel.begin();
  pixel.setBrightness(50);
  pixel.show();

  pinMode(RED_PIN,    OUTPUT);
  pinMode(YELLOW_PIN, OUTPUT);
  pinMode(GREEN_PIN,  OUTPUT);
  applyIdle();

  // Hold BOOT button on power-up = reset saved WiFi credentials
  pinMode(RESET_PIN, INPUT_PULLUP);
  if (digitalRead(RESET_PIN) == LOW) {
    Serial.println("BOOT held — clearing WiFi credentials");
    WiFiManager wm;
    wm.resetSettings();
    // Red blink to confirm reset
    for (int i = 0; i < 5; i++) {
      digitalWrite(RED_PIN, HIGH); delay(150);
      digitalWrite(RED_PIN, LOW);  delay(150);
    }
  }

  // WiFiManager: auto-connect or open config portal
  // Blink yellow while waiting
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);
  wm.setAPCallback([](WiFiManager*) {
    Serial.println("Config portal open: connect to 'TrafficLight-Setup'");
    // Yellow blink = config mode
    for (int i = 0; i < 3; i++) {
      digitalWrite(YELLOW_PIN, HIGH); delay(200);
      digitalWrite(YELLOW_PIN, LOW);  delay(200);
    }
    digitalWrite(YELLOW_PIN, HIGH);  // solid yellow during portal
  });

  if (!wm.autoConnect("TrafficLight-Setup")) {
    Serial.println("WiFi connect failed — restarting");
    ESP.restart();
  }
  WiFi.setSleep(false);  // disable modem sleep — eliminates ~5s wake latency
  allOff();

  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  // mDNS
  if (MDNS.begin(HOSTNAME)) {
    Serial.println("mDNS: http://" HOSTNAME ".local/cmd?state=THINKING");
  }

  // HTTP routes
  server.on("/cmd",    HTTP_GET, handleCmd);
  server.on("/status", HTTP_GET, handleStatus);
  server.begin();
  Serial.println("HTTP server started");

  // Green flash = WiFi ready
  blinkBuiltin(3, pixel.Color(0, 255, 0));
}

void loop() {
  server.handleClient();

  // Chase animation during THINKING
  if (currentState == ST_THINKING) {
    uint32_t now = millis();
    if (now - lastChase >= CHASE_INTERVAL_MS) {
      lastChase = now;
      allOff();
      switch (chaseStep % 3) {
        case 0: digitalWrite(RED_PIN,    HIGH); break;
        case 1: digitalWrite(YELLOW_PIN, HIGH); break;
        case 2: digitalWrite(GREEN_PIN,  HIGH); break;
      }
      chaseStep++;
    }
  }

  // Auto-transition: DONE -> IDLE after 3s
  if (currentState == ST_DONE && millis() - doneAt >= DONE_HOLD_MS) {
    applyIdle();
  }
}
