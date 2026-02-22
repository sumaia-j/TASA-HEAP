#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>


Adafruit_MPU6050 mpu;


// -------------------- CONFIG --------------------
const uint16_t SAMPLE_HZ = 100;          // 100 Hz sampling
const uint32_t SAMPLE_PERIOD_US = 1000000UL / SAMPLE_HZ;


enum Label : uint8_t {
  LABEL_NONE = 0,
  LABEL_REST,
  LABEL_UP,
  LABEL_DOWN,
  LABEL_FWD,
  LABEL_BWD,
  LABEL_LEFT,
  LABEL_RIGHT,
  LABEL_CIRCLE,
  LABEL_SCRATCH
};


Label currentLabel = LABEL_NONE;


// Gyro bias calibration (we'll estimate on boot while resting)
float gyroBiasX = 0.0f;
float gyroBiasY = 0.0f;


// Simple low-pass filter for gyro (helps a lot)
float gx_f = 0.0f, gy_f = 0.0f;
const float ALPHA = 0.2f; // 0..1 (higher = less smoothing)


// -------------------- HELPERS --------------------
const char* labelToStr(Label l) {
  switch (l) {
    case LABEL_REST:   return "REST";
    case LABEL_UP:     return "UP";
    case LABEL_DOWN:   return "DOWN";
    case LABEL_FWD:    return "FWD";
    case LABEL_BWD:    return "BWD";
    case LABEL_LEFT:   return "LEFT";
    case LABEL_RIGHT:  return "RIGHT";
    case LABEL_CIRCLE: return "CIRCLE";
    case LABEL_SCRATCH:return "SCRATCH";
    default:           return "NONE";
  }
}


void printControls() {
  Serial.println(F("\n--- Gesture Label Controls ---"));
  Serial.println(F("Send a character in Serial Monitor:"));
  Serial.println(F("  0 = NONE"));
  Serial.println(F("  r = REST"));
  Serial.println(F("  u = UP"));
  Serial.println(F("  d = DOWN"));
  Serial.println(F("  f = FWD"));
  Serial.println(F("  b = BWD"));
  Serial.println(F("  l = LEFT"));
  Serial.println(F("  ri = RIGHT"));
  Serial.println(F("  c = CIRCLE"));
  Serial.println(F("  s = SCRATCH"));
  Serial.println(F("--------------------------------\n"));
}


void handleSerialLabel() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r' || ch == ' ') continue;


    switch (ch) {
      case '0': currentLabel = LABEL_NONE; break;
      //case 'r': currentLabel = LABEL_REST; break;
      case 'u': currentLabel = LABEL_UP; break;
      case 'd': currentLabel = LABEL_DOWN; break;
      case 'f': currentLabel = LABEL_FWD; break;
      case 'b': currentLabel = LABEL_BWD; break;
      case 'l': currentLabel = LABEL_LEFT; break;
      case 'r': currentLabel = LABEL_RIGHT; break;
      case 'c': currentLabel = LABEL_CIRCLE; break;
      case 's': currentLabel = LABEL_SCRATCH; break;
      default: break;
    }


    Serial.print(F("# LABEL="));
    Serial.println(labelToStr(currentLabel));
  }
}


void calibrateGyroBias(uint16_t samples = 300) {
  Serial.println(F("# Calibrating gyro bias... keep device STILL (REST)."));
  float sumX = 0.0f, sumY = 0.0f;


  for (uint16_t i = 0; i < samples; i++) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);


    // g.gyro.x/y are in rad/s
    sumX += g.gyro.x;
    sumY += g.gyro.y;
    delay(5);
  }


  gyroBiasX = sumX / samples;
  gyroBiasY = sumY / samples;


  Serial.print(F("# Gyro bias X(rad/s)=")); Serial.println(gyroBiasX, 6);
  Serial.print(F("# Gyro bias Y(rad/s)=")); Serial.println(gyroBiasY, 6);
  Serial.println(F("# Done.\n"));
}


// -------------------- SETUP/LOOP --------------------
uint32_t nextSampleUs = 0;


void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }


  Wire.begin();


  if (!mpu.begin()) {
    Serial.println(F("MPU6050 not found. Check wiring + I2C address."));
    while (1) { delay(100); }
  }


  // Good defaults for gestures
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);


  printControls();
  calibrateGyroBias();


  // CSV header
  Serial.println(F("t_ms,label,ax_mps2,ay_mps2,az_mps2,gx_rads,gy_rads"));
  nextSampleUs = micros();
}


void loop() {
  handleSerialLabel();


  uint32_t now = micros();
  if ((int32_t)(now - nextSampleUs) < 0) return;
  nextSampleUs += SAMPLE_PERIOD_US;


  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);


  // Accel in m/s^2
  float ax = a.acceleration.x;
  float ay = a.acceleration.y;
  float az = a.acceleration.z;


  // Gyro in rad/s, bias corrected, ignoring GZ (broken)
  float gx = g.gyro.x - gyroBiasX;
  float gy = g.gyro.y - gyroBiasY;


  // Low-pass filter for stability
  gx_f = (1.0f - ALPHA) * gx_f + ALPHA * gx;
  gy_f = (1.0f - ALPHA) * gy_f + ALPHA * gy;


  // Print CSV line
  Serial.print(millis());
  Serial.print(',');
  Serial.print(labelToStr(currentLabel));
  Serial.print(',');
  Serial.print(ax, 4); Serial.print(',');
  Serial.print(ay, 4); Serial.print(',');
  Serial.print(az, 4); Serial.print(',');
  Serial.print(gx_f, 6); Serial.print(',');
  Serial.println(gy_f, 6);
}


