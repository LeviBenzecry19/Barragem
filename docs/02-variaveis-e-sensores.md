# 2. Variáveis monitoradas e sensores

As variáveis foram escolhidas a partir dos instrumentos citados pela ANA e pelo
*Embankment Dam Instrumentation Manual* (USBR) para barragens de terra e
enrocamento. Para cada uma, há o instrumento usado em barragens reais e um
equivalente de baixo custo para o protótipo.

| Variável (chave) | O que pode indicar | Instrumento profissional | Sensor do protótipo | Unidade |
|---|---|---|---|---|
| Nível do reservatório (`nivel_reservatorio`) | Carga hidráulica sobre a estrutura; aumenta poropressão e percolação | Régua linimétrica, transdutor de nível, radar | JSN-SR04T (ultrassônico à prova d'água) | m |
| Pressão de poros (`pressao_poros`) | Saturação do maciço e redução da tensão efetiva | Piezômetro Casagrande, piezômetro de corda vibrante, pneumático | Transdutor de pressão 0,5–4,5 V em tubo piezométrico | kPa |
| Vazão de infiltração (`vazao_infiltracao`) | Mudança na percolação; aumento brusco ou água turva pode indicar erosão interna (*piping*) | Medidor de vazão triangular (vertedouro), calha Parshall | YF-S201 (fluxo por efeito Hall) | L/min |
| Deslocamento horizontal (`deslocamento_horizontal`) | Movimentação do talude/fundação | Inclinômetro, marcos superficiais com topografia/GNSS | Potenciômetro linear em extensômetro de haste | mm |
| Recalque (`recalque`) | Movimentação vertical (adensamento, colapso) | Medidor de recalque magnético, placas de recalque, marcos | Potenciômetro linear | mm |
| Tensão total (*futuro*) | Estado de tensão no maciço | Célula de tensão total | Célula de carga (*load cell*) + HX711 | kPa |
| Chuva 24 h (`chuva_24h`) | Infiltração superficial e elevação do reservatório | Pluviômetro / pluviógrafo | Pluviômetro de báscula com reed switch | mm |
| Inclinação (`inclinacao`) | Rotação de estruturas e taludes | Tiltímetro, inclinômetro | MPU-6050 (acelerômetro) | ° |
| Vibração (`vibracao`) | Eventos sísmicos ou vibrações induzidas | Acelerógrafo / sismógrafo | MPU-6050 (pico de aceleração) | g |
| Temperatura (`temperatura`) | Contexto ambiental; correção térmica de sensores | Termistor, termopar | DS18B20 | °C |
| Turbidez (`turbidez`) | Solo carreado pela percolação: um dos melhores indicadores de erosão interna (piping) | Turbidímetro de processo, inspeção visual | TSD-10 (óptico, saída analógica) | NTU |
| Vento (`vento`) | Ondas e sobrelevação que reduzem a borda livre | Anemômetro de estação meteorológica | Anemômetro de conchas com reed switch | km/h |
| Vazão afluente (`vazao_afluente`) | Cheia chegando ao reservatório; antecipa o galgamento pelo balanço hídrico | Estação fluviométrica (régua e curva-chave), previsão hidrológica | Não vem do ESP32: enviada pela rede ou digitada na página de sensores | m³/s |

## Frequência de leitura

Em barragens reais, a frequência é definida no Plano de Segurança da Barragem e
costuma aumentar durante o primeiro enchimento, cheias ou após eventos
anômalos. No protótipo, a estação envia **uma leitura por minuto** e o
acelerômetro é amostrado a ~100 Hz, guardando o pico de cada minuto.

## Limitações dos sensores de baixo custo

- Precisão e estabilidade de longo prazo muito inferiores às dos instrumentos geotécnicos.
- O ADC do ESP32 é pouco linear: para medições analógicas mais precisas, recomenda-se um ADS1115 (16 bits).
- Sensores ultrassônicos sofrem influência de temperatura, espuma e ondas.
- O YF-S201 não mede vazões muito baixas, nem turbidez (que também é um indicador importante).
- O MPU-6050 tem deriva térmica; inclinações pequenas exigem média e compensação.

Por isso os dados do protótipo servem para **validar o software e a arquitetura**,
não para tirar conclusões sobre uma barragem real.
