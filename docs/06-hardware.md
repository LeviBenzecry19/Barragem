# 6. Hardware do protótipo

## 6.1 Lista de componentes

| Qtde | Componente | Função |
|---:|---|---|
| 1 | ESP32 DevKit V1 | Microcontrolador com Wi-Fi |
| 1 | JSN-SR04T | Nível do reservatório (ultrassônico à prova d'água) |
| 1 | Transdutor de pressão 0,5–4,5 V (0–100 kPa ou 0–1,2 MPa) | Pressão de poros no tubo piezométrico |
| 1 | YF-S201 | Vazão de infiltração |
| 2 | Potenciômetro linear (50–100 mm) | Deslocamento horizontal e recalque |
| 1 | MPU-6050 | Inclinação e vibração |
| 1 | Pluviômetro de báscula (reed switch) | Chuva |
| 1 | DS18B20 (versão à prova d'água) | Temperatura |
| 1 | ADS1115 (opcional, recomendado) | ADC de 16 bits para as entradas analógicas |
| — | Resistores para divisores de tensão (ex.: 10 kΩ / 20 kΩ), 4,7 kΩ (pull-up do DS18B20) | Adequar sinais de 5 V a 3,3 V |
| 1 | Fonte 5 V (ou bateria + painel solar + controlador de carga) | Alimentação |
| 1 | Caixa IP65 | Proteção em campo |

## 6.2 Ligações (pinos padrão do firmware)

| Sensor | Pino ESP32 | Observação |
|---|---|---|
| JSN-SR04T TRIG / ECHO | GPIO 5 / GPIO 18 | ECHO em 5 V → usar divisor de tensão |
| Transdutor de pressão | GPIO 34 (ADC1) | Saída 0,5–4,5 V → divisor para ≤ 3,3 V |
| Potenciômetro deslocamento | GPIO 35 (ADC1) | Alimentar em 3,3 V |
| Potenciômetro recalque | GPIO 32 (ADC1) | Alimentar em 3,3 V |
| YF-S201 (sinal) | GPIO 27 | Interrupção; alimentar em 5 V, sinal com divisor |
| Pluviômetro | GPIO 26 | Interrupção com pull-up interno, debounce de 200 ms |
| DS18B20 | GPIO 4 | Pull-up de 4,7 kΩ para 3,3 V |
| MPU-6050 SDA / SCL | GPIO 21 / GPIO 22 | I2C, endereço 0x68 |

Usamos apenas pinos do ADC1 porque o ADC2 do ESP32 não funciona com o Wi-Fi ligado.

## 6.3 Conversões no firmware

| Sensor | Conversão |
|---|---|
| Ultrassônico | distância = tempo × 343 m/s ÷ 2; nível = altura do sensor − distância |
| Transdutor | u = (V − 0,5) / (4,5 − 0,5) × fundo de escala |
| YF-S201 | Q (L/min) = frequência (Hz) / 7,5 |
| Potenciômetro | mm = V × (curso / 3,3 V) − zero da instalação |
| Pluviômetro | chuva = basculadas × 0,2794 mm, soma móvel de 24 h |
| MPU-6050 | ângulo = atan2(aₓ, √(a_y² + a_z²)); vibração = pico de \|‖a‖ − 1 g\| no minuto |

## 6.4 Calibração

1. **Nível:** medir a distância real com trena em 3 ou mais níveis e ajustar `ALTURA_SENSOR_NIVEL_M`.
2. **Pressão:** comparar com colunas d'água conhecidas (1 m = 9,81 kPa) e ajustar `PIEZO_V_MIN`/`PIEZO_V_MAX`.
3. **Vazão:** cronometrar o enchimento de um recipiente de volume conhecido e ajustar `PULSOS_POR_LPM`.
4. **Pluviômetro:** despejar volume conhecido e contar basculadas (mm = volume ÷ área de captação).
5. **Deslocamentos e inclinação:** os "zeros" são lidos automaticamente na inicialização; verificar com paquímetro.

Registrar as calibrações (data, valores, responsável) na documentação.

## 6.5 Montagem do firmware

1. Instalar a Arduino IDE e o pacote de placas **esp32** (Espressif).
2. Instalar as bibliotecas **ArduinoJson** (v7), **OneWire** e **DallasTemperature**.
3. Copiar `credenciais.exemplo.h` para `credenciais.h` e preencher Wi-Fi, URL do servidor e chave.
4. Selecionar a placa *ESP32 Dev Module* e gravar.
5. Acompanhar o Monitor Serial (115200 baud): cada pacote enviado é impresso.

## 6.6 Modelo físico sugerido

Para testes em laboratório, pode-se construir uma barragem em escala dentro de
uma caixa de vidro/acrílico com solo compactado, um reservatório de um lado e
um dreno do outro: o ultrassônico mede o nível, um tubo com o transdutor
funciona como piezômetro, a água drenada passa pelo YF-S201, e os
potenciômetros/MPU-6050 são fixados em hastes cravadas no talude.
