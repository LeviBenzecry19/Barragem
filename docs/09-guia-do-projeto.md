# 9. Guia do projeto: hardware, interpretação e referências

Visão geral do sistema em quatro partes: o hardware necessário, como interpretar
cada saída dos sensores, um guia das afirmações que precisam de referência e um
resumo do projeto. Cada afirmação técnica recebe um código (**A1**, **A2**, …),
que aparece na coluna **Ref.** das tabelas e entre colchetes no resumo. A seção 3
lista todos os códigos com a fonte onde conferir cada um.

Detalhes de ligação, calibração e custos estão em
[06 – Hardware](06-hardware.md) e [08 – Hardware necessário](08-hardware-necessario.md);
fórmulas e faixas, em [03 – Metodologia de análise](03-metodologia-analise.md).

## 1. Hardware

| Dispositivo | Grupo | Saída (variável) | Ligação | Funcionalidade | Prioridade | Ref. |
|---|---|---|---|---|---|---|
| **JSN-SR04T** (ultrassônico à prova d'água) | Sensor | `nivel_reservatorio` (m) | Digital: GPIO 5 (TRIG) e 18 (ECHO, com divisor) | Mede a distância até a água pelo tempo do eco; o firmware converte em nível (15,5 m − distância). | Obrigatório | A1 |
| **Transdutor de pressão 0,5–4,5 V** (0–100 kPa) em tubo piezométrico | Sensor | `pressao_poros` (kPa) | Analógico: GPIO 34 (ADC1), divisor 5 → 3,3 V | Mede a pressão da água nos poros do maciço, 5 m abaixo do talude de jusante (piezômetro de tubo aberto). | Obrigatório | A2 |
| **YF-S201** (fluxômetro de efeito Hall) | Sensor | `vazao_infiltracao` (L/min) | Pulsos: GPIO 27 | Mede a vazão que sai pelo dreno de pé contando os pulsos da turbina. | Obrigatório | A3 |
| **Potenciômetro linear 50 mm** (extensômetro de haste) | Sensor | `deslocamento_horizontal` (mm) | Analógico: GPIO 35 (ADC1) | Mede o movimento horizontal do talude em relação a uma haste fixa. | Obrigatório | — |
| **Potenciômetro linear 100 mm** + placa de recalque | Sensor | `recalque` (mm) | Analógico: GPIO 32 (ADC1) | Mede o afundamento da crista em relação a uma referência fixa. | Obrigatório | — |
| **Pluviômetro de báscula** (reed switch) | Sensor | `chuva_24h` (mm) | Pulsos: GPIO 26 | Conta as basculadas (0,2794 mm cada) e soma as últimas 24 h. | Obrigatório | A4 |
| **MPU-6050** (módulo GY-521) | Sensor | `inclinacao` (°) e `vibracao` (g) | I²C: GPIO 21 e 22, endereço 0x68 | Acelerômetro de 3 eixos: o ângulo dá a inclinação; o pico de aceleração do minuto (amostrado a ~100 Hz) dá a vibração. | Obrigatório | A5 |
| **DS18B20** à prova d'água | Sensor | `temperatura` (°C) | 1-Wire: GPIO 4, pull-up de 4,7 kΩ | Mede a temperatura do ar e dos sensores (contexto e correção). | Recomendado | A6 |
| **Turbidímetro TSD-10** | Sensor | `turbidez` (NTU) | Analógico: GPIO 33 (ADC1), com divisor | Mede as partículas em suspensão na água do dreno (solo sendo carreado). | Recomendado | A8 |
| **Anemômetro de conchas** (reed switch) | Sensor | `vento` (km/h) | Pulsos: GPIO 25 | Mede o vento sobre o reservatório, que gera ondas e sobrelevação. | Recomendado | A7 |
| **Estação fluviométrica** ou serviço de previsão (externo) | Fonte externa | `vazao_afluente` (m³/s) | Rede (4G/Internet) → `POST /api/leituras` | Informa a vazão do rio que chega ao reservatório; alimenta o balanço hídrico. Também pode ser digitada na página de sensores. | Recomendado | — |
| **ESP32 DevKit V1** | Aquisição | — | — | Lê os sensores, converte os sinais em grandezas, monta o JSON, envia por Wi-Fi a cada minuto e guarda até 20 pacotes para reenvio. | Obrigatório | A9, A10, A12 |
| **Divisores de tensão** (resistores 1%) ou conversor de nível lógico | Condicionamento | — | Entre sensor e ESP32 | Reduzem sinais de 5 V para ≤ 3,3 V, o limite das entradas do ESP32. | Obrigatório | A10 |
| **ADS1115** (ADC 16 bits) | Condicionamento | — | I²C | Faz a leitura analógica com mais precisão e linearidade que o ADC do ESP32 (exige adaptar o firmware). | Recomendado | A11 |
| **RTC DS3231** | Aquisição | — | I²C | Mantém o horário correto quando não há internet para o NTP. | Recomendado | — |
| **Módulo microSD** + cartão | Aquisição | — | SPI | Guarda as leituras quando a rede cai (a fila em memória só comporta 20 pacotes). | Recomendado | — |
| **Fonte 5 V / 2 A** (bancada) ou **kit solar** (painel 20 W, bateria 12 V 9 Ah, controlador de carga, step-down 12 → 5 V) | Energia | — | — | Alimenta o ESP32 e os sensores; o kit solar dá cerca de 3 dias de autonomia sem sol. | Obrigatório (um dos dois) | A13 |
| **Caixa IP65**, prensa-cabos, DPS com aterramento, fusíveis | Proteção | — | — | Protegem a eletrônica de água, poeira e surtos de descargas atmosféricas em campo. | Obrigatório (campo) | — |
| **Roteador Wi-Fi 2,4 GHz** (ou LoRa/4G em campo) | Comunicação | — | Wi-Fi | Liga a estação ao servidor. | Obrigatório | A12 |
| **Computador ou Raspberry Pi 4/5** + nobreak | Servidor | — | Ethernet ou Wi-Fi | Roda o `monitor.servidor` (Python): valida, grava no SQLite, avalia os modos de ruptura e gera os alertas. | Obrigatório | — |
| **Celular ou computador com navegador** | Visualização | — | HTTP | Acessa o dashboard e a página de sensores (topologia, explicações e entrada manual). | Obrigatório | — |
| **Ferramentas de calibração**: trena, régua linimétrica, coluna d'água graduada, proveta e cronômetro, paquímetro, padrões de formazina, nível de bolha | Calibração | — | — | Conferem cada sensor contra uma referência conhecida (por exemplo, 1 m de água = 9,81 kPa). | Obrigatório | A14 |

## 2. Interpretação

Galgamento e erosão interna respondem pela maioria das rupturas de barragens de
terra **[A15]**, por isso o sistema avalia cada leitura também por modo de
ruptura. Os limites de cada variável (atenção / alerta / crítico) e os pesos do
índice são valores experimentais do projeto **[A43]**.

### 2.1 Saída de cada sensor

| Saída | Sensor | O que indica | Leitura alta (ou mudança) significa | Correlações com outras saídas | Onde entra no cálculo | Ref. |
|---|---|---|---|---|---|---|
| `nivel_reservatorio` (m) · limites 12 / 13 / 14 | JSN-SR04T | Carga hidráulica sobre a barragem (P = ρ·g·h). | Mais empuxo e percolação, menos folga até a crista. Queda rápida (> 0,5 m/dia) deixa o talude de montante saturado sem o apoio da água. | Nível alto eleva a poropressão e a vazão esperadas (Darcy). Com recalque, vento e vazão afluente, define a borda livre. A taxa de queda dispara a verificação de rebaixamento rápido. | Índice (15%); galgamento; talude de montante; variável explicativa dos modelos de poropressão, vazão e deslocamento. | A14, A16, A23, A40 |
| `pressao_poros` (kPa) · 25 / 35 / 45 | Piezômetro | Água sob pressão no maciço; define a linha freática. | Menos tensão efetiva e menos resistência ao cisalhamento: o FS do talude cai e o gradiente de saída sobe. | Depende do nível e da chuva antecedente (modelo esperado): subir com o nível estável é anomalia. Com a vibração, entra no FS pseudoestático. | Índice (25%); talude de jusante (FS mínimo, β); erosão interna (FS contra piping); sismo. | A17, A18, A20, A21, A22 |
| `vazao_infiltracao` (L/min) · 35 / 50 / 70 | YF-S201 | Água que atravessa o maciço e chega ao dreno. | Mudança brusca indica caminho preferencial de fluxo (erosão interna). | Esperada proporcional ao nível (Darcy). Vazão subindo com nível estável é mais grave que vazão alta com o reservatório cheio. Com turbidez alta, indica piping. | Índice (20%); erosão interna (taxa, resíduo, combinação com turbidez). | A23, A24 |
| `deslocamento_horizontal` (mm) · 15 / 25 / 40 | Potenciômetro 50 mm | Movimento lateral do talude. | Deslizamento em curso. A velocidade importa tanto quanto o valor: deslocamento que acelera precede a ruptura. | Esperado em função de nível, temperatura e tempo (HST). A inclinação acompanha o deslocamento. | Índice (20%); deformações (velocidade, resíduo, Fukuzono). | A27, A28 |
| `recalque` (mm) · 25 / 40 / 60 | Potenciômetro 100 mm | Afundamento da crista. | Normal no início (adensamento); grande ou desigual abre trincas e reduz a borda livre. | Subtrai da cota da crista no cálculo da borda livre efetiva. | Índice (10%); galgamento. | A29 |
| `chuva_24h` (mm) · 50 / 80 / 120 | Pluviômetro | Chuva recente. | Eleva o reservatório e infiltra no talude. | Gera a chuva antecedente (API), que umedece o maciço (γ acima da linha freática) e explica a poropressão esperada com defasagem. | Índice (5%); talude de jusante (γ); modelo de poropressão. | A30 |
| `inclinacao` (°) · 0,5 / 1 / 2 | MPU-6050 | Rotação da estrutura em relação à leitura inicial. | Movimento desigual, por exemplo um bloco do talude começando a girar. | Acompanha o deslocamento horizontal. | Índice (5%). | A31 |
| `vibracao` (g) · 0,05 / 0,1 / 0,2 | MPU-6050 | Pico de aceleração do minuto (sismo, detonações, máquinas). | Acima de 0,05 g há um evento a verificar. | Junto com a poropressão, reduz o FS pelo método pseudoestático. Evolução: deslocamento de Newmark. | Alerta individual; modo sismo. | A32, A33 |
| `temperatura` (°C) · 40 / 50 / 60 | DS18B20 | Contexto ambiental. | Muda a velocidade do som (usada pelo ultrassônico) e causa deriva em sensores baratos. | Explica a parcela térmica do deslocamento esperado (HST). | Alerta individual; modelo de deslocamento. | A1, A28, A34 |
| `turbidez` (NTU) · 20 / 50 / 100 | TSD-10 | Partículas de solo na água do dreno. | Solo sendo carreado pela percolação: indício direto de piping. | Turbidez em Atenção com vazão alta ou crescente leva a erosão interna a Alerta; em Alerta ou Crítico, a Crítico. | Alerta individual; erosão interna. | A24 |
| `vento` (km/h) · 40 / 60 / 80 | Anemômetro | Vento sobre o reservatório. | Ondas que sobem o talude (espraiamento) e sobrelevação do nível. | Com o nível e o recalque, reduz a borda livre efetiva. | Alerta individual; galgamento. | A35, A36, A37 |
| `vazao_afluente` (m³/s) · 20 / 40 / 70 | Estação fluviométrica | Cheia chegando ao reservatório. | O nível vai subir: antecipa o galgamento. | Com o nível, o vertedouro e a tomada d'água, o balanço hídrico prevê o nível e a borda livre em 24 h. | Alerta individual; galgamento (previsão). | A38, A39 |

### 2.2 Leituras combinadas

| Combinação de saídas | Indicador calculado | Interpretação | Faixas (Atenção / Alerta / Crítico) | Ref. |
|---|---|---|---|---|
| Nível + recalque + vento | Borda livre efetiva | Folga real entre a água (com ondas) e a crista; abaixo de zero há galgamento. | < 2 m / < 1 m / < 0,5 m | A29, A35, A36, A37 |
| Nível + vazão afluente (+ vertedouro e tomada) | Borda livre prevista em 24 h | Galgamento previsto antes de o nível subir. | < 2 m / < 1 m / < 0,5 m | A38, A39 |
| Poropressão + chuva antecedente | FS mínimo do talude de jusante (varredura até 8 m) | Estabilidade do talude na superfície crítica, não só na ponta do piezômetro. | < 1,5 / < 1,3 / < 1,1 | A18, A19, A20, A21, A22 |
| Poropressão + incerteza de c' e φ' | Índice β e P(FS < 1) | Probabilidade de ruptura (informativo, não muda o nível). | — | A41, A42 |
| Poropressão + geometria até o dreno | FS contra piping (i_cr / i) | Risco de levantamento do solo na saída do fluxo. | < 3 / < 2 / < 1,5 | A25, A26 |
| Turbidez + vazão de infiltração | Água turva com vazão elevada | Carreamento de solo com percolação crescente. | Alerta ou Crítico | A24 |
| Vibração + poropressão | FS pseudoestático | Estabilidade durante o sismo. | < 1,1 / < 1,05 / < 1,0 | A32 |
| Taxa do nível (queda) | FS de montante no rebaixamento rápido | Talude de montante saturado sem o apoio da água. | < 1,3 / < 1,1 / < 1,0 | A40 |
| Histórico do deslocamento | Velocidade e método de Fukuzono | Aceleração pré-ruptura e tempo previsto até a ruptura. | 1 / 3 / 10 mm/dia; < 7 dias / < 72 h / < 24 h | A27 |
| Poropressão, vazão e deslocamento × modelos (nível, API, temperatura, tempo) | Resíduo em desvios-padrão | Comportamento fora do padrão do próprio histórico. | 2σ / 3σ / 4σ | A23, A28, A30 |
| Todas as variáveis com peso | Índice de risco I = Σ W·n | Visão geral ponderada. | 0,25 / 0,50 / 0,75 | A43 |

Uma tendência (taxa ou resíduo) sozinha leva o modo de ruptura no máximo a
Alerta; para Crítico, outro indicador do mesmo modo precisa confirmar.

## 3. Guia de referências

Foram feitas **45 afirmações** neste documento:

| Tipo | Quantidade |
|---|---:|
| Especificação de componente (datasheet) | 11 |
| Fórmula | 13 |
| Fato técnico | 7 |
| Método de análise | 5 |
| Critério de norma ou manual | 4 |
| Valor adotado pelo projeto | 4 |
| Legislação | 1 |
| **Total** | **45** |

| Situação | Significado | Quantidade |
|---|---|---:|
| Citada | A fonte já está na lista de fontes do README | 6 |
| Adicionar | Fonte clássica identificada; falta incluir na bibliografia | 32 |
| Conferir | Valor ou constante a confirmar na fonte antes de citar | 5 |
| Justificar | Escolha do projeto: precisa de justificativa, não de citação | 2 |

| Nº | Afirmação | Seção | Tipo | Onde buscar | Situação |
|---|---|---|---|---|---|
| A1 | Distância do ultrassônico = tempo do eco × velocidade do som (≈ 343 m/s a 20 °C) ÷ 2 | 1, 2.1 | Fórmula | Datasheet JSN-SR04T; Halliday & Resnick, *Fundamentos de Física*, v. 2 | Adicionar |
| A2 | O transdutor 0,5–4,5 V tem saída linear com a pressão (0 a 100 kPa) | 1 | Especificação | Datasheet do transdutor adquirido | Adicionar |
| A3 | YF-S201: f (Hz) = 7,5 × Q (L/min) | 1 | Especificação | Datasheet YF-S201 | Adicionar |
| A4 | Pluviômetro de báscula: 0,2794 mm por basculada | 1 | Especificação | Datasheet do pluviômetro (ex.: SparkFun Weather Meter Kit, SEN-15901) | Adicionar |
| A5 | MPU-6050: acelerômetro de 3 eixos, I²C no endereço 0x68, faixa de ±2 a ±16 g | 1 | Especificação | InvenSense, *MPU-6000/MPU-6050 Product Specification* | Adicionar |
| A6 | DS18B20: −55 a 125 °C, ±0,5 °C entre −10 e 85 °C, 1-Wire com pull-up de 4,7 kΩ | 1 | Especificação | Datasheet DS18B20 (Maxim Integrated / Analog Devices) | Adicionar |
| A7 | Anemômetro de conchas: 1 pulso por segundo = 2,4 km/h | 1 | Especificação | Datasheet SparkFun Weather Meter Kit (SEN-15901) | Adicionar |
| A8 | TSD-10: sensor óptico cuja tensão de saída cai com a turbidez | 1 | Especificação | Datasheet do TSD-10 (conferir a curva tensão × NTU) | Conferir |
| A9 | No ESP32 o ADC2 não funciona com o Wi-Fi ligado; usar o ADC1 (GPIO 32–39) | 1 | Especificação | Espressif, documentação ESP-IDF, seção ADC | Adicionar |
| A10 | As entradas do ESP32 aceitam no máximo 3,3 V | 1 | Especificação | Espressif, *ESP32 Series Datasheet* | Adicionar |
| A11 | O ADC do ESP32 é pouco linear; o ADS1115 (16 bits) mede com mais precisão | 1 | Especificação | Espressif, documentação ESP-IDF (ADC); Texas Instruments, datasheet ADS1115 | Adicionar |
| A12 | O ESP32 só conecta em redes Wi-Fi de 2,4 GHz | 1 | Especificação | Espressif, *ESP32 Series Datasheet* | Adicionar |
| A13 | Consumo ≈ 0,75 W; bateria 12 V 9 Ah dá ≈ 3 dias sem sol; painel de 20 W | 1 | Valor do projeto | Cálculo em `08-hardware-necessario.md`; consumo no datasheet do ESP32 | Justificar |
| A14 | 1 m de coluna d'água = 9,81 kPa (P = ρ·g·h) | 1, 2.1 | Fórmula | Fox & McDonald, *Introdução à Mecânica dos Fluidos* | Adicionar |
| A15 | Galgamento e erosão interna respondem pela maioria das rupturas de barragens de terra | 2, 4 | Fato técnico | Foster, Fell & Spannagle (2000), *Canadian Geotechnical Journal* 37(5); ICOLD, *Bulletin 99* (1995) | Adicionar |
| A16 | Nível alto aumenta a poropressão e a percolação e reduz a folga até a crista | 2.1 | Fato técnico | USBR, *Design Standards No. 13*; Fell et al. (2015), *Geotechnical Engineering of Dams* | Citada |
| A17 | Princípio da tensão efetiva: σ' = σ − u | 2.1 | Fórmula | Terzaghi (1943), *Theoretical Soil Mechanics* | Adicionar |
| A18 | FS do talude infinito com poropressão e sismo; simplificação dos métodos de Bishop, Spencer e Morgenstern-Price | 2.1, 2.2, 4 | Fórmula | Duncan, Wright & Brandon (2014), *Soil Strength and Slope Stability* | Adicionar |
| A19 | FS mínimo usual de 1,5 com percolação permanente | 2.2 | Critério | USACE, EM 1110-2-1902 (2003); USBR, *Design Standards No. 13*, cap. 4 | Citada |
| A20 | Com c' > 0, o FS do talude infinito diminui com a profundidade | 2.1, 2.2 | Fato técnico | Dedução da fórmula; Duncan, Wright & Brandon (2014) | Adicionar |
| A21 | Razão de poropressão rᵤ = u / σv | 2.1, 2.2 | Fórmula | Bishop & Morgenstern (1960), *Géotechnique* 10(4) | Adicionar |
| A22 | γd, γnat e γsat a partir de Gs, e e w | 2.1, 2.2 | Fórmula | Das, *Fundamentos de Engenharia Geotécnica*; Pinto, *Curso Básico de Mecânica dos Solos* | Adicionar |
| A23 | Em regime permanente a vazão de infiltração é proporcional ao nível (Darcy, Q = k·i·A) | 2.1, 2.2 | Fórmula | Darcy (1856); Cedergren (1989), *Seepage, Drainage, and Flow Nets* | Adicionar |
| A24 | Aumento brusco de vazão ou água turva no dreno indicam erosão interna | 2.1, 2.2 | Fato técnico | ICOLD, *Bulletin 164* (2017); USBR, *Embankment Dam Instrumentation Manual* | Citada |
| A25 | Gradiente crítico i_cr = (γsat − γw) / γw | 2.2, 4 | Fórmula | Terzaghi (1943); Das, *Fundamentos de Engenharia Geotécnica* | Adicionar |
| A26 | FS contra piping de referência entre 3 e 5 | 2.2 | Critério | USACE, EM 1110-2-1901 (*Seepage Analysis and Control for Dams*); Harr (1962), *Groundwater and Seepage* | Conferir |
| A27 | Deslocamento que acelera precede a ruptura; 1/v cai linearmente até zero (velocidade inversa) | 2.1, 2.2, 4 | Método | Fukuzono (1985), 4th International Conference and Field Workshop on Landslides, Tóquio | Adicionar |
| A28 | O deslocamento esperado se explica por nível, temperatura e tempo (modelo HST) | 2.1, 2.2 | Método | Willm & Beaujoint (1967), 9º Congresso da ICOLD, Istambul | Adicionar |
| A29 | O recalque da crista reduz a borda livre | 2.1, 2.2 | Fato técnico | USBR (1987), *Design of Small Dams* | Adicionar |
| A30 | A poropressão responde à chuva acumulada com defasagem; API_t = k·API_(t−1) + P_t, k ≈ 0,85–0,95 por dia | 2.1, 2.2 | Método | Kohler & Linsley (1951), *Research Paper 34*, U.S. Weather Bureau | Adicionar |
| A31 | Rotação (inclinação) indica movimento desigual da estrutura | 2.1 | Fato técnico | USBR, *Embankment Dam Instrumentation Manual* | Citada |
| A32 | Sismo: kₕ = 0,5·PGA/g com resistência reduzida a 80%; FS ≥ 1 aceitável | 2.1, 2.2, 4 | Critério | Hynes-Griffin & Franklin (1984), *Miscellaneous Paper GL-84-13*, USACE WES | Adicionar |
| A33 | O deslocamento permanente de Newmark é a evolução do método pseudoestático | 2.1 | Método | Newmark (1965), *Géotechnique* 15(2) | Adicionar |
| A34 | A velocidade do som no ar varia com a temperatura (≈ 331 + 0,6·T m/s) | 2.1 | Fórmula | Halliday & Resnick, *Fundamentos de Física*, v. 2 | Adicionar |
| A35 | Altura da onda de vento com pista limitada: H = 1,6×10⁻³ · U · √(F/g) | 2.1, 2.2 | Fórmula | USACE (1984), *Shore Protection Manual* | Adicionar |
| A36 | Sobrelevação pelo vento (Zuider Zee): S = V²·F / (62 000·D) em unidades SI | 2.1, 2.2 | Fórmula | USBR (1987), *Design of Small Dams* (em unidades inglesas: S = V²·F / (1400·D)) | Conferir |
| A37 | Espraiamento R ≈ 1,5 × altura da onda (rip-rap ≈ 1; face lisa até ≈ 2) | 2.1, 2.2 | Valor do projeto | USACE, EM 1110-2-1100 (*Coastal Engineering Manual*); USBR (1987) | Conferir |
| A38 | Vertedouro de soleira livre: Q = C·L·H^1,5 | 2.1, 2.2 | Fórmula | Chow (1959), *Open-Channel Hydraulics*; USBR (1987), *Design of Small Dams* | Adicionar |
| A39 | Balanço hídrico: dV/dt = Q_afl − Q_vert − Q_tomada − Q_infiltr − E·A | 2.1, 2.2, 4 | Fórmula | Chow, Maidment & Mays (1988), *Applied Hydrology* | Adicionar |
| A40 | No rebaixamento rápido a poropressão não dissipa e o FS de montante cai; FS mínimo usual 1,1–1,3 | 2.1, 2.2, 4 | Critério | USACE, EM 1110-2-1902 (2003); Duncan, Wright & Brandon (2014) | Adicionar |
| A41 | Confiabilidade por Monte Carlo: β = (μ_FS − 1) / σ_FS e P(FS < 1) | 2.2 | Método | Baecher & Christian (2003), *Reliability and Statistics in Geotechnical Engineering*; USACE, ETL 1110-2-547 (1995) | Adicionar |
| A42 | Coeficientes de variação típicos: c' ≈ 20%, φ' ≈ 10% | 2.2 | Valor do projeto | Phoon & Kulhawy (1999), *Canadian Geotechnical Journal* 36; Duncan (2000), *Journal of Geotechnical and Geoenvironmental Engineering* 126(4) | Conferir |
| A43 | Limites de controle, pesos e faixas são experimentais, definidos pelo grupo | 2, 2.2, 4 | Valor do projeto | `monitor/config.py` e `03-metodologia-analise.md` (validar com o orientador) | Justificar |
| A44 | O Plano de Segurança de Barragens é exigido por lei, e o sistema não o substitui | 4 | Legislação | Brasil, Lei nº 12.334/2010 | Citada |
| A45 | Barragens reais usam instrumentos profissionais (piezômetro de corda vibrante, inclinômetro, medidor triangular de vazão) | 4 | Fato técnico | USBR, *Embankment Dam Instrumentation Manual*; materiais da ANA | Citada |

## 4. Resumo do projeto

Protótipo acadêmico de monitoramento da estabilidade de uma barragem de terra
fictícia de 15 m. Sensores de baixo custo ligados a um ESP32 medem nível do
reservatório, pressão de poros, vazão e turbidez da drenagem, deslocamento,
recalque, inclinação, vibração, chuva, vento e temperatura; a vazão afluente
chega pela rede. A cada minuto o ESP32 envia um pacote JSON por Wi-Fi a um
servidor em Python, que valida, grava em SQLite e avalia a barragem em três camadas:

- **Índice de risco:** cada leitura vira uma nota de 0 a 1 pelos limites de
  controle, ponderada pelos pesos (pressão de poros 25%, vazão e deslocamento
  20%, nível 15%, recalque 10%, chuva e inclinação 5%) [A43].
- **Regras de sobreposição:** uma variável crítica leva a Alerta; duas, a Crítico.
- **Modos de ruptura:** galgamento, erosão interna, taludes de jusante e de
  montante, sismo e deformações, os mecanismos mais frequentes [A15]. Cada modo
  cruza sensores e histórico: borda livre com ondas e recalque, previsão por
  balanço hídrico, FS de talude infinito na profundidade crítica, gradiente de
  piping, FS pseudoestático, rebaixamento rápido e método de Fukuzono
  [A18, A25, A27, A32, A39, A40].

O nível global (Normal, Atenção, Alerta ou Crítico) é o mais severo das três
camadas, e cada subida gera um alerta que não se repete enquanto não for
reconhecido. O dashboard mostra valores, modos de ruptura, gráficos e alertas; a
página de sensores mostra a estação no estilo do Cisco Packet Tracer, explica
cada sensor e permite digitar leituras com prévia da classificação. Um simulador
com cinco cenários (normal, cheia, infiltração, sismo e rebaixamento) permite
testar sem hardware, e 61 testes automatizados cobrem fórmulas, modos e API.

Limites, pesos e faixas são experimentais [A43]. O sistema não substitui a
análise de um engenheiro habilitado nem o Plano de Segurança de Barragens
exigido pela Lei nº 12.334/2010 [A44]; numa barragem real, os sensores de baixo
custo seriam trocados por instrumentos profissionais [A45].
