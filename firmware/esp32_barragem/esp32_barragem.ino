/*
 * Estação de aquisição de dados — Monitoramento de Barragem (protótipo)
 * Placa: ESP32 DevKit (Arduino core para ESP32)
 *
 * Lê os sensores de baixo custo do protótipo e envia um pacote JSON ao
 * servidor (POST /api/leituras) a cada INTERVALO_ENVIO_MS:
 *
 *   {"estacao":"EST-01","instante":"2026-10-14T12:00:00Z",
 *    "leituras":{"nivel_reservatorio":10.2,"pressao_poros":16.1,...}}
 *
 * Sensores (ver docs/06-hardware.md para ligações e alternativas):
 *   - Nível do reservatório ... JSN-SR04T (ultrassônico à prova d'água)
 *   - Pressão de poros ........ transdutor de pressão 0,5–4,5 V (piezômetro de tubo aberto)
 *   - Vazão de infiltração .... YF-S201 (sensor de fluxo por efeito Hall)
 *   - Deslocamento horizontal . potenciômetro linear (extensômetro de haste)
 *   - Recalque ................ potenciômetro linear
 *   - Inclinação e vibração ... MPU-6050 (acelerômetro/giroscópio I2C)
 *   - Chuva ................... pluviômetro de báscula (reed switch)
 *   - Temperatura ............. DS18B20
 *
 * Bibliotecas: ArduinoJson (v7), OneWire, DallasTemperature.
 * Credenciais de Wi-Fi e endereço do servidor ficam em credenciais.h
 * (copie credenciais.exemplo.h). As constantes de calibração abaixo são
 * exemplos e DEVEM ser ajustadas na calibração de cada sensor.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <time.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#include "credenciais.h"  // WIFI_SSID, WIFI_SENHA, URL_SERVIDOR, CHAVE_API

// ---------------------------------------------------------------- pinos
const int PINO_US_TRIG    = 5;
const int PINO_US_ECHO    = 18;
const int PINO_PIEZO      = 34;   // ADC1 (entrada apenas)
const int PINO_DESLOC     = 35;   // ADC1
const int PINO_RECALQUE   = 32;   // ADC1
const int PINO_VAZAO      = 27;
const int PINO_CHUVA      = 26;
const int PINO_TEMP       = 4;
const int PINO_SDA        = 21;
const int PINO_SCL        = 22;

// --------------------------------------------------------- parâmetros
const char *ESTACAO = "EST-01";
const unsigned long INTERVALO_ENVIO_MS = 60000;   // 1 leitura por minuto
const unsigned long INTERVALO_AMOSTRA_MS = 10;    // amostragem do acelerômetro (~100 Hz)

// Calibração (valores de exemplo)
const float ALTURA_SENSOR_NIVEL_M = 15.5;   // cota do sensor ultrassônico em relação ao fundo
const float DIVISOR_TENSAO = 1.5;           // divisor resistivo 5 V -> 3,3 V nas entradas analógicas
const float PIEZO_V_MIN = 0.5, PIEZO_V_MAX = 4.5, PIEZO_KPA_MAX = 100.0;
const float DESLOC_MM_POR_V = 50.0 / 3.3;   // potenciômetro de 50 mm alimentado em 3,3 V
const float RECALQUE_MM_POR_V = 100.0 / 3.3;
const float PULSOS_POR_LPM = 7.5;           // YF-S201: f(Hz) = 7,5 × Q(L/min)
const float MM_POR_BASCULADA = 0.2794;      // pluviômetro de báscula típico
const float ACC_LSB_POR_G = 8192.0;         // MPU-6050 em ±4 g
const uint8_t MPU_ENDERECO = 0x68;

// Zeros obtidos na instalação (leitura inicial de referência)
float deslocZeroMm = 0, recalqueZeroMm = 0, anguloZeroGraus = 0;

// ------------------------------------------------------------ estado
volatile uint32_t pulsosVazao = 0;
volatile uint32_t basculadas = 0;
volatile unsigned long ultimaBasculada = 0;

uint16_t chuvaPorHora[24] = {0};  // basculadas em cada uma das últimas 24 horas
int horaAtual = 0;
unsigned long inicioHora = 0;

float picoVibracaoG = 0;
unsigned long ultimoEnvio = 0, ultimaAmostra = 0, ultimaContagemVazao = 0;

// Fila simples para reenviar pacotes quando o Wi-Fi/servidor estiver fora
const int TAM_FILA = 20;
String fila[TAM_FILA];
int filaInicio = 0, filaQtd = 0;

OneWire oneWire(PINO_TEMP);
DallasTemperature sensorTemp(&oneWire);

// ---------------------------------------------------------- interrupções
void IRAM_ATTR isrVazao() { pulsosVazao++; }

void IRAM_ATTR isrChuva() {
  unsigned long t = millis();
  if (t - ultimaBasculada > 200) {  // debounce do reed switch
    basculadas++;
    ultimaBasculada = t;
  }
}

// ------------------------------------------------------------- sensores
float lerTensao(int pino) {
  uint32_t soma = 0;
  for (int i = 0; i < 16; i++) soma += analogReadMilliVolts(pino);  // média de 16 amostras
  return (soma / 16.0f) / 1000.0f * DIVISOR_TENSAO;
}

float lerNivelM() {
  digitalWrite(PINO_US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PINO_US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PINO_US_TRIG, LOW);
  unsigned long us = pulseIn(PINO_US_ECHO, HIGH, 60000);
  if (us == 0) return NAN;
  float distanciaM = us * 343.0f / 2.0f / 1e6f;  // velocidade do som ≈ 343 m/s
  return ALTURA_SENSOR_NIVEL_M - distanciaM;
}

float lerPressaoPorosKpa() {
  float v = lerTensao(PINO_PIEZO);
  float kpa = (v - PIEZO_V_MIN) / (PIEZO_V_MAX - PIEZO_V_MIN) * PIEZO_KPA_MAX;
  return max(kpa, 0.0f);
}

float lerVazaoLpm() {
  noInterrupts();
  uint32_t pulsos = pulsosVazao;
  pulsosVazao = 0;
  interrupts();
  unsigned long agora = millis();
  float segundos = (agora - ultimaContagemVazao) / 1000.0f;
  ultimaContagemVazao = agora;
  if (segundos <= 0) return 0;
  return (pulsos / segundos) / PULSOS_POR_LPM;
}

bool lerAcelerometro(float &ax, float &ay, float &az) {
  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x3B);  // ACCEL_XOUT_H
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ENDERECO, (uint8_t)6) != 6) return false;
  int16_t x = (Wire.read() << 8) | Wire.read();
  int16_t y = (Wire.read() << 8) | Wire.read();
  int16_t z = (Wire.read() << 8) | Wire.read();
  ax = x / ACC_LSB_POR_G;
  ay = y / ACC_LSB_POR_G;
  az = z / ACC_LSB_POR_G;
  return true;
}

float anguloGraus(float ax, float ay, float az) {
  return atan2(ax, sqrt(ay * ay + az * az)) * 180.0 / PI;
}

void iniciarMPU() {
  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x6B); Wire.write(0x00);  // sai do modo sleep
  Wire.endTransmission();
  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x1C); Wire.write(0x08);  // fundo de escala ±4 g
  Wire.endTransmission();
}

// Amostra o acelerômetro continuamente e guarda o pico de vibração (|a| − 1 g)
void amostrarVibracao() {
  float ax, ay, az;
  if (!lerAcelerometro(ax, ay, az)) return;
  float pico = fabs(sqrt(ax * ax + ay * ay + az * az) - 1.0f);
  if (pico > picoVibracaoG) picoVibracaoG = pico;
}

// Mantém a soma móvel de chuva das últimas 24 h em "baldes" horários
void atualizarChuva() {
  noInterrupts();
  uint32_t n = basculadas;
  basculadas = 0;
  interrupts();
  chuvaPorHora[horaAtual] += n;
  if (millis() - inicioHora >= 3600000UL) {
    inicioHora += 3600000UL;
    horaAtual = (horaAtual + 1) % 24;
    chuvaPorHora[horaAtual] = 0;
  }
}

float chuva24hMm() {
  uint32_t total = 0;
  for (int i = 0; i < 24; i++) total += chuvaPorHora[i];
  return total * MM_POR_BASCULADA;
}

// ------------------------------------------------------------ rede
void conectarWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 15000) delay(250);
}

bool instanteIso(char *buf, size_t tam) {
  struct tm t;
  if (!getLocalTime(&t, 100)) return false;
  strftime(buf, tam, "%Y-%m-%dT%H:%M:%SZ", &t);
  return true;
}

bool enviarPacote(const String &corpo) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(URL_SERVIDOR);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Chave-API", CHAVE_API);
  int codigo = http.POST(corpo);
  if (codigo == 400) Serial.println("Pacote rejeitado: " + http.getString());
  http.end();
  // 400 = pacote inválido: descarta para não travar a fila.
  return (codigo >= 200 && codigo < 300) || codigo == 400;
}

void enfileirar(const String &corpo) {
  int pos = (filaInicio + filaQtd) % TAM_FILA;
  fila[pos] = corpo;
  if (filaQtd < TAM_FILA) filaQtd++;
  else filaInicio = (filaInicio + 1) % TAM_FILA;  // fila cheia: descarta o mais antigo
}

void esvaziarFila() {
  while (filaQtd > 0 && enviarPacote(fila[filaInicio])) {
    fila[filaInicio] = "";
    filaInicio = (filaInicio + 1) % TAM_FILA;
    filaQtd--;
  }
}

// ------------------------------------------------------------ ciclo
String montarPacote() {
  JsonDocument doc;
  doc["estacao"] = ESTACAO;
  char instante[25];
  if (instanteIso(instante, sizeof(instante))) doc["instante"] = instante;  // senão, o servidor usa a hora de chegada

  JsonObject l = doc["leituras"].to<JsonObject>();
  float nivel = lerNivelM();
  if (!isnan(nivel)) l["nivel_reservatorio"] = nivel;
  l["pressao_poros"] = lerPressaoPorosKpa();
  l["vazao_infiltracao"] = lerVazaoLpm();
  l["deslocamento_horizontal"] = lerTensao(PINO_DESLOC) * DESLOC_MM_POR_V - deslocZeroMm;
  l["recalque"] = lerTensao(PINO_RECALQUE) * RECALQUE_MM_POR_V - recalqueZeroMm;
  l["chuva_24h"] = chuva24hMm();

  float ax, ay, az;
  if (lerAcelerometro(ax, ay, az)) {
    l["inclinacao"] = fabs(anguloGraus(ax, ay, az) - anguloZeroGraus);
    l["vibracao"] = picoVibracaoG;
  }
  picoVibracaoG = 0;

  sensorTemp.requestTemperatures();
  float temp = sensorTemp.getTempCByIndex(0);
  if (temp != DEVICE_DISCONNECTED_C) l["temperatura"] = temp;

  String corpo;
  serializeJson(doc, corpo);
  return corpo;
}

void setup() {
  Serial.begin(115200);
  pinMode(PINO_US_TRIG, OUTPUT);
  pinMode(PINO_US_ECHO, INPUT);
  pinMode(PINO_VAZAO, INPUT_PULLUP);
  pinMode(PINO_CHUVA, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PINO_VAZAO), isrVazao, FALLING);
  attachInterrupt(digitalPinToInterrupt(PINO_CHUVA), isrChuva, FALLING);
  analogReadResolution(12);

  Wire.begin(PINO_SDA, PINO_SCL);
  iniciarMPU();
  sensorTemp.begin();

  // Leituras de referência ("zero") feitas na instalação
  deslocZeroMm = lerTensao(PINO_DESLOC) * DESLOC_MM_POR_V;
  recalqueZeroMm = lerTensao(PINO_RECALQUE) * RECALQUE_MM_POR_V;
  float ax, ay, az;
  if (lerAcelerometro(ax, ay, az)) anguloZeroGraus = anguloGraus(ax, ay, az);

  conectarWiFi();
  configTime(0, 0, "pool.ntp.org", "a.st1.ntp.br");  // horário em UTC
  inicioHora = ultimaContagemVazao = millis();
  Serial.println("Estação iniciada.");
}

void loop() {
  unsigned long agora = millis();

  if (agora - ultimaAmostra >= INTERVALO_AMOSTRA_MS) {
    ultimaAmostra = agora;
    amostrarVibracao();
  }

  if (agora - ultimoEnvio >= INTERVALO_ENVIO_MS) {
    ultimoEnvio = agora;
    atualizarChuva();
    String corpo = montarPacote();
    Serial.println(corpo);

    conectarWiFi();
    enfileirar(corpo);
    esvaziarFila();
    if (filaQtd > 0) Serial.printf("%d pacote(s) aguardando reenvio.\n", filaQtd);
  }
}
