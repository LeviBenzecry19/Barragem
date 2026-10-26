# 3. Metodologia de análise e classificação

> **Aviso.** O modelo abaixo é **experimental e didático**. Limites, pesos e
> parâmetros do solo são valores ilustrativos de uma barragem fictícia e fazem
> parte da metodologia do trabalho, não são valores universais de engenharia.
> A classificação não substitui a análise de um engenheiro responsável.

Todos os valores citados estão em `monitor/config.py`, as fórmulas em
`monitor/analise.py` e os cálculos sobre o histórico em `monitor/tendencias.py`.

## 3.1 Barragem de referência (fictícia)

| Parâmetro | Valor |
|---|---|
| Tipo | Barragem de terra homogênea, com dreno de pé |
| Altura / cota da crista | 15 m |
| Nível normal do reservatório | 10 m |
| Soleira do vertedouro | cota 12 m, largura 8 m, C = 2,0 (Q = C·L·H^1,5) |
| Tomada d'água (descarga operacional) | 4 m³/s |
| Talude de jusante | 1V : 2,5H (β ≈ 21,8°) |
| Talude de montante | 1V : 3H (β ≈ 18,4°) |
| Densidade dos grãos (Gs) | 2,70 |
| Índice de vazios (e) / umidade (w) | 0,60 / 15% |
| Peso específico seco, natural e saturado | γd = 16,55 · γnat = 19,04 · γsat = 20,23 kN/m³ |
| Coesão efetiva (c') | 15 kPa |
| Ângulo de atrito efetivo (φ') | 32° |
| Piezômetro | ponta a 5 m de profundidade no talude de jusante (cota 3 m), 20 m antes do dreno de pé |
| Profundidade máxima da superfície de ruptura | 8 m (altura do talude no ponto do piezômetro) |
| Pista de vento sobre o reservatório (fetch) | 1,5 km |

Os pesos específicos não são mais um valor único: saem dos índices físicos,

$$\gamma_d = \frac{G_s\,\gamma_w}{1+e} \qquad \gamma_{nat} = \gamma_d\,(1+w) \qquad \gamma_{sat} = \frac{(G_s+e)\,\gamma_w}{1+e}$$

## 3.2 Modos de ruptura cobertos

Barragens de terra rompem principalmente por galgamento e por erosão interna,
que respondem pela grande maioria dos casos históricos. A avaliação é organizada
por modo de ruptura: cada modo combina leituras de vários sensores, e o
histórico, em indicadores próprios.

| Modo de ruptura | Situação | O que o app calcula |
|---|---|---|
| Galgamento | Coberto | Borda livre efetiva com recalque, onda e sobrelevação do vento; previsão do nível em 24 h pelo balanço hídrico |
| Erosão interna / piping | Coberto | FS contra piping pelo gradiente de saída; turbidez combinada com a vazão; taxa e resíduo da vazão |
| Instabilidade do talude de jusante | Coberto | Menor FS na varredura de profundidade, com γ variável; confiabilidade (Monte Carlo); taxa e resíduo da poropressão |
| Instabilidade do talude de montante (rebaixamento rápido) | Coberto | FS de montante quando o nível cai mais rápido que 0,5 m/dia |
| Instabilidade sísmica | Coberto (pseudoestático) | FS pseudoestático com kh = 0,5·PGA; liquefação não é avaliada |
| Trincas e deformações excessivas | Parcial | Velocidade do deslocamento, resíduo do modelo HST e método de Fukuzono; trincas dependem de inspeção |
| Ruptura pela fundação / subpressão | Não coberto | Exige piezômetros na fundação |
| Erosão superficial do talude | Não coberto | Exige inspeção visual (seção 3.12) |

## 3.3 Fórmulas utilizadas

**Pressão hidrostática** (carga do reservatório na base):

$$P = \rho \cdot g \cdot h$$

Ex.: h = 10 m → P = 1000 × 9,81 × 10 = 98,1 kPa.

**Carga piezométrica** (altura de água equivalente à pressão de poros medida):

$$h_p = \frac{u}{\rho \cdot g}$$

**Tensão vertical em camadas e tensão efetiva** (princípio de Terzaghi). A linha
freática fica à profundidade $z_w = z_{piezo} - u/\gamma_w$; acima dela o solo
pesa $\gamma_{acima}$ e abaixo, $\gamma_{sat}$:

$$\sigma_v(z) = \gamma_{acima}\,\min(z, z_w) + \gamma_{sat}\,\max(z - z_w, 0) \qquad \sigma' = \sigma - u$$

$\gamma_{acima}$ vai de $\gamma_{nat}$ a $\gamma_{sat}$ conforme a chuva
antecedente (API, seção 3.8): com API ≥ 150 mm a zona acima da linha freática é
tratada como saturada. Quanto maior a pressão de poros, menor a tensão efetiva
e, portanto, menor a resistência ao cisalhamento do solo.

**Razão de poropressão**:

$$r_u = \frac{u}{\sigma_v}$$

**Fator de segurança – talude infinito com poropressão e sismo** (critério de Mohr-Coulomb):

$$FS = \frac{c' + \left[\sigma_v(\cos^2\beta - k_h \sin\beta\cos\beta) - u\right]\tan\phi'}{\sigma_v(\sin\beta\cos\beta + k_h\cos^2\beta)}$$

Resistência ao cisalhamento disponível dividida pela tensão cisalhante atuante.
FS = 1 é a condição de ruptura iminente. Sem sismo ($k_h = 0$) e com
$\sigma_v = \gamma z$ é o talude infinito clássico.

**Varredura de profundidade.** Com c' > 0, o FS do talude infinito diminui com
a profundidade, e fixar z = 5 m (a ponta do piezômetro) pode não pegar a
superfície crítica. O FS é calculado de 0,25 m em 0,25 m até 8 m, com o rᵤ
medido no piezômetro aplicado a todas as profundidades, e o **menor** valor é o
FS do talude de jusante. Para a barragem de referência:

| u (kPa) | rᵤ | FS a 5 m | FS mínimo (z = 8 m) | Faixa | β | P(FS < 1) |
|---:|---:|---:|---:|---|---:|---:|
| 0 | 0,00 | 2,02 | 1,84 | Normal | 4,20 | 0,0% |
| 15 (base) | 0,15 | 1,73 | 1,56 | Normal | 3,34 | 0,0% |
| 25 (atenção) | 0,25 | 1,54 | 1,38 | Atenção | 2,58 | 0,4% |
| 35 (alerta) | 0,35 | 1,36 | 1,20 | Alerta | 1,58 | 5,2% |
| 45 (crítico) | 0,45 | 1,18 | 1,02 | Crítico | 0,24 | 40,8% |
| 52 | 0,51 | 1,06 | 0,90 | Crítico | −1,02 | 84,7% |

Com a varredura, os limites do piezômetro (25, 35 e 45 kPa) passam a coincidir
exatamente com as faixas de FS: cada limite de pressão de poros corresponde ao
mesmo nível no FS.

O modelo de talude infinito é uma simplificação, escolhida por ser adequada ao
nível acadêmico do projeto e calculável em tempo real. Barragens reais são
analisadas com métodos de equilíbrio limite em superfícies circulares ou não
circulares (Bishop simplificado, Spencer, Morgenstern-Price) em softwares
específicos, considerando a rede de fluxo completa.

**Faixas do FS** (ponto de partida: FS mínimo usual de 1,5 para
percolação permanente em normas e manuais de projeto):

| FS | Nível mínimo |
|---|---|
| ≥ 1,5 | Normal |
| 1,3 a 1,5 | Atenção |
| 1,1 a 1,3 | Alerta |
| < 1,1 | Crítico |

**(a) FS pseudoestático.** Quando a aceleração de pico medida pelo MPU-6050 passa
de 0,05 g, o FS é recalculado com coeficiente sísmico $k_h = 0{,}5 \cdot PGA/g$ e
com c' e tan φ' reduzidos a 80% (critério de Hynes-Griffin e Franklin). Assim o
sismo deixa de ser "diluído" no índice: ele reduz o FS diretamente.

| PGA (g) | kₕ | FS pseudoestático | Nível |
|---:|---:|---:|---|
| 0,05 | 0,025 | 1,16 | Normal |
| 0,10 | 0,050 | 1,09 | Atenção |
| 0,15 | 0,075 | 1,02 | Alerta |
| 0,20 | 0,100 | 0,96 | Crítico |

Faixas: < 1,1 Atenção · < 1,05 Alerta · < 1,0 Crítico. Um passo além seria o
deslocamento de Newmark.

**(h) Rebaixamento rápido.** Se o nível do reservatório cai mais rápido que
0,5 m/dia, o talude de montante é verificado logo após o rebaixamento: o maciço
continua saturado e a poropressão não dissipa (percolação paralela ao talude,
$u = \gamma_w z \cos^2\beta$), mas a água do reservatório já não o sustenta.
Para o talude de montante de referência, FS = 1,28 → Atenção. Faixas: < 1,3
Atenção · < 1,1 Alerta · < 1,0 Crítico.

**(d) Erosão interna: gradiente hidráulico.** Com o piezômetro e o ponto de saída
(dreno de pé, cota 0), o gradiente médio no trecho final do caminho de fluxo é

$$i = \frac{\Delta h}{L} = \frac{(z_{ponta} + u/\gamma_w) - z_{saída}}{L} \qquad i_{cr} = \frac{\gamma_{sat} - \gamma_w}{\gamma_w} \qquad FS_{piping} = \frac{i_{cr}}{i}$$

Para a barragem de referência $i_{cr}$ = 1,06; com u = 15 kPa, FS_piping = 4,7.
Valores de referência usuais ficam entre 3 e 5. Faixas: < 3 Atenção · < 2 Alerta
· < 1,5 Crítico. O gradiente médio subestima o gradiente na saída; um segundo
piezômetro perto do dreno melhoraria a estimativa.

**Turbidez combinada com a vazão.** Água turva no dreno com vazão de infiltração
elevada (acima do limite de atenção, crescendo ou acima do esperado pelo modelo)
indica carreamento de solo: turbidez em Atenção leva o modo a **Alerta**, e em
Alerta ou Crítico leva a **Crítico**. Vazão alta com o reservatório cheio e água
limpa não dispara essa regra.

**(e) Borda livre efetiva** (liga nível, recalque e vento):

$$BL_{ef} = (Z_{crista} - \text{recalque}) - h_{reservatório} - (R_{onda} + S_{vento})$$

- Onda (SPM, 1984, pista limitada): $H = 1{,}6\times10^{-3}\cdot U\cdot\sqrt{F/g}$, com U em m/s e F em m.
- Espraiamento no talude: $R = 1{,}5\cdot H$ (rip-rap ≈ 1; face lisa até ≈ 2).
- Sobrelevação (Zuider Zee): $S = V^2 F / (62\,000\,D)$, com V em km/h, F em km e D (profundidade média) em m.

| Vento (km/h) | H (m) | R (m) | S (m), nível 12 m |
|---:|---:|---:|---:|
| 20 | 0,11 | 0,16 | 0,002 |
| 40 | 0,22 | 0,33 | 0,006 |
| 60 | 0,33 | 0,49 | 0,015 |
| 80 | 0,44 | 0,66 | 0,026 |

Faixas: < 2 m Atenção · < 1 m Alerta · < 0,5 m Crítico (abaixo de zero há galgamento).

**(j) Balanço hídrico do reservatório** (previsão de galgamento):

$$\frac{dV}{dt} = A(h)\frac{dh}{dt} = Q_{afl} - Q_{vert}(h) - Q_{tomada} - Q_{infiltr} - E\cdot A(h)$$

A área A(h) vem da curva cota-área; a integração usa passos de 5 minutos por
24 h, mantendo a vazão afluente atual. Partindo de 12 m:

| Q afluente (m³/s) | Nível máximo em 24 h | Galgamento |
|---:|---:|---|
| 20 | 12,98 m | não |
| 40 | 13,70 m | não |
| 60 | 14,29 m | não |
| 100 | 15,29 m | em 9,6 h |

A borda livre prevista (crista − recalque − nível máximo previsto − onda) usa as
mesmas faixas da borda livre atual.

**(k) Incerteza dos parâmetros.** c' e φ' são tratados como variáveis normais
(coeficientes de variação de 20% e 10%) e o FS da superfície crítica é calculado
para 2000 amostras (Monte Carlo, semente fixa). O resultado é a probabilidade de
FS < 1 e o índice de confiabilidade $\beta = (\mu_{FS} - 1)/\sigma_{FS}$. Ele é
mostrado ao lado do FS, mas **não altera o nível**: os coeficientes de variação
ainda não vêm de ensaios.

## 3.4 Limites de controle por variável

Cada variável tem quatro valores crescentes: **base** (comportamento normal
esperado), **atenção**, **alerta** e **crítico**. Na prática, esses limites
viriam do projeto e das leituras históricas de cada instrumento (por exemplo,
média ± *k* desvios-padrão, ou valores de projeto com margem).

| Variável | Base | Atenção | Alerta | Crítico | Peso |
|---|---:|---:|---:|---:|---:|
| Nível do reservatório (m) | 10 | 12 | 13 | 14 | 15% |
| Pressão de poros (kPa) | 15 | 25 | 35 | 45 | 25% |
| Vazão de infiltração (L/min) | 20 | 35 | 50 | 70 | 20% |
| Deslocamento horizontal (mm) | 5 | 15 | 25 | 40 | 20% |
| Recalque (mm) | 10 | 25 | 40 | 60 | 10% |
| Chuva 24 h (mm) | 10 | 50 | 80 | 120 | 5% |
| Inclinação (°) | 0,1 | 0,5 | 1,0 | 2,0 | 5% |
| Vibração (g) | 0,01 | 0,05 | 0,10 | 0,20 | — |
| Temperatura (°C) | 30 | 40 | 50 | 60 | — |
| Turbidez da drenagem (NTU) | 5 | 20 | 50 | 100 | — |
| Vento (km/h) | 15 | 40 | 60 | 80 | — |
| Vazão afluente (m³/s) | 5 | 20 | 40 | 70 | — |

As três variáveis novas têm peso 0: entram nos modos de ruptura (erosão interna
e galgamento) e geram alertas individuais, sem mudar o índice.

## 3.5 Normalização

Cada leitura é convertida em uma nota *n* entre 0 e 1, linear por trechos:

| Valor | Nota |
|---|---|
| ≤ base | 0,00 |
| = atenção | 0,25 |
| = alerta | 0,50 |
| = crítico | 0,75 |
| acima do crítico | continua com a inclinação do último trecho, até 1,00 |

Assim, a escala é comparável entre variáveis de unidades diferentes e as faixas
do índice têm o mesmo significado que as faixas de cada variável.

## 3.6 Índice experimental de risco

$$I = \sum_i W_i \cdot n_i \qquad \sum_i W_i = 1$$

| Índice | Nível |
|---|---|
| < 0,25 | Normal |
| 0,25 a 0,50 | Atenção |
| 0,50 a 0,75 | Alerta |
| ≥ 0,75 | Crítico |

**Critério usado para os pesos.** As variáveis foram agrupadas em:

1. **Resposta da estrutura** – indicam diretamente mudança de comportamento do
   maciço: pressão de poros (25%), deslocamento horizontal (20%), vazão de
   infiltração (20%) e recalque (10%). Somam 75%.
2. **Solicitação / carregamento** – causas externas que só se tornam
   preocupantes se a estrutura responder: nível do reservatório (15%) e chuva (5%).
3. **Indicadores complementares** – inclinação (5%), sensível mas sujeita a
   ruído no protótipo.

Vibração, temperatura, turbidez, vento e vazão afluente têm peso 0. Em vez de
entrar na média, cada uma atua no modo de ruptura em que tem significado físico:
a vibração no FS pseudoestático, a turbidez na erosão interna, o vento e a
vazão afluente na borda livre. A temperatura é usada no modelo de deslocamento
esperado. Todas continuam gerando alertas individuais.

Os pesos podem ser revistos pelo grupo junto ao orientador (por exemplo, via
método AHP – *Analytic Hierarchy Process* – com comparação par a par feita por
especialistas) sem alterar o código: basta editar `monitor/config.py`.

## 3.7 Modos de ruptura: indicadores e faixas

Cada modo recebe o nível mais severo entre os seus indicadores. Indicadores
marcados como informativos aparecem no dashboard, mas não definem o nível.
Como na regra das variáveis críticas (seção 3.9), uma **tendência** (taxa ou
resíduo, que são estimativas estatísticas sujeitas a ruído) sozinha leva o modo
no máximo a Alerta: para Crítico, outro indicador do mesmo modo precisa estar
acima de Normal.

| Modo | Indicadores que definem o nível | Informativos |
|---|---|---|
| Galgamento | Borda livre efetiva; borda livre prevista (24 h) | — |
| Erosão interna | FS contra piping; taxa e resíduo da vazão; turbidez × vazão | Turbidez |
| Talude de jusante | FS mínimo da varredura; taxa e resíduo da poropressão | FS a 5 m; β e P(FS < 1) |
| Talude de montante | FS de montante no rebaixamento rápido | Variação do nível (m/dia) |
| Sismo | FS pseudoestático (PGA ≥ 0,05 g) | Aceleração de pico |
| Deformações | Velocidade do deslocamento; resíduo do deslocamento; Fukuzono | — |

## 3.8 Indicadores que usam o histórico

São calculados sobre as **médias horárias** do banco (`monitor/tendencias.py`).
Sem histórico suficiente o indicador não aparece, em vez de dar um valor ruim.

**(i) Taxas de variação.** Inclinação da regressão linear nas últimas 24 h
(mínimo de 6 h de dados), em unidades por dia. Só aumentos contam:

| Variável | Atenção | Alerta | Crítico |
|---|---:|---:|---:|
| Deslocamento horizontal (mm/dia) | 1 | 3 | 10 |
| Pressão de poros (kPa/dia) | 3 | 6 | 10 |
| Vazão de infiltração ((L/min)/dia) | 5 | 10 | 20 |

A taxa do nível do reservatório não tem faixa própria: ela dispara a
verificação de rebaixamento rápido.

**Método da velocidade inversa (Fukuzono).** A velocidade do deslocamento é
calculada em blocos de 6 h nas últimas 72 h. Se as últimas quatro ou mais
velocidades acima de 0,5 mm/dia mostram 1/v caindo, a reta de 1/v contra o tempo
é extrapolada até 1/v = 0, que é o instante previsto da ruptura. Faixas pelo
tempo restante: < 7 dias Atenção · < 72 h Alerta · < 24 h Crítico.

**(g) Índice de precipitação antecedente**, que modela a defasagem da chuva:

$$API_t = k \cdot API_{t-1} + P_t \qquad k = 0{,}9 \text{ por dia, 30 dias}$$

P é a chuva de 24 h registrada em cada dia. O API umedece o maciço (γ acima da
linha freática, seção 3.3) e é variável explicativa da poropressão esperada.

**(f) Modelos de valor esperado (resíduos).** Uma regressão linear treinada com
até 30 dias de histórico, sem as últimas 6 h (para não aprender a anomalia
recente) e com pelo menos 48 h de dados, prevê o valor de cada grandeza:

| Grandeza | Variáveis explicativas | Desvio mínimo |
|---|---|---:|
| Pressão de poros | nível do reservatório, API | 1 kPa |
| Vazão de infiltração | nível do reservatório (Darcy: Q ∝ k·i·A) | 2 L/min |
| Deslocamento horizontal | nível, temperatura, tempo (modelo HST simplificado) | 0,5 mm |

O alerta é pelo resíduo em desvios-padrão, $z = (\text{medido} - \text{esperado}) / \sigma$:
2σ Atenção · 3σ Alerta · 4σ Crítico (só resíduos positivos). Assim, vazão
subindo com o nível estável é muito mais grave que vazão alta com o reservatório
cheio, e os limites fixos sozinhos não distinguem os dois casos.

## 3.9 Regras de sobreposição (nível global)

Uma média ponderada pode esconder um problema isolado grave (por exemplo, vazão
crítica com as demais variáveis normais resulta em índice de apenas 0,15).
Por isso o nível global é o **mais severo** entre:

1. a faixa do índice;
2. **Alerta**, se uma variável estiver crítica; **Crítico**, se duas ou mais estiverem;
3. o nível de cada modo de ruptura (seção 3.7), que inclui o fator de segurança.

Os motivos que determinaram o nível são registrados e mostrados no dashboard.

## 3.10 Exemplo de cálculo

Leituras: nível 12,5 m; poros 30 kPa; vazão 40 L/min; deslocamento 10 mm;
recalque 15 mm; chuva 60 mm; inclinação 0,3°.

| Variável | Nota | Peso | W·n |
|---|---:|---:|---:|
| Nível | 0,375 | 0,15 | 0,056 |
| Pressão de poros | 0,375 | 0,25 | 0,094 |
| Vazão | 0,333 | 0,20 | 0,067 |
| Deslocamento | 0,125 | 0,20 | 0,025 |
| Recalque | 0,083 | 0,10 | 0,008 |
| Chuva | 0,333 | 0,05 | 0,017 |
| Inclinação | 0,125 | 0,05 | 0,006 |
| **Índice** | | | **0,273 → Atenção** |

Modos de ruptura:

- **Talude de jusante:** FS a 5 m = 1,45, mas o FS mínimo da varredura
  (z = 8 m) é **1,28 → Alerta**; β = 2,1.
- **Galgamento:** borda livre efetiva = 15 − 0,015 − 12,5 = 2,49 m → Normal.
- **Erosão interna:** FS_piping = 3,5 → Normal.

Nenhuma variável crítica. **Nível global: Alerta** (o modelo antigo, só com
z = 5 m, dava Atenção: a superfície mais profunda é a crítica).

Se além disso houver vento de 50 km/h e vazão afluente de 45 m³/s, a borda livre
atual cai para 2,06 m (onda de 0,41 m), e o balanço hídrico prevê o nível chegando
a 13,86 m em 24 h: borda livre prevista de **0,70 m → Alerta** no modo galgamento.

## 3.11 Geração de alertas

- Um alerta é gerado quando uma variável, um modo de ruptura (origem
  `modo:<nome>`) ou o nível global **sobe** de nível.
- Para evitar repetição quando a leitura oscila sobre um limite, não se gera
  novo alerta da mesma origem enquanto houver um alerta pendente (não
  reconhecido) de nível igual ou superior.
- O operador reconhece o alerta no dashboard. No protótipo os alertas são
  exibidos e registrados no log do servidor; a integração com e-mail, SMS ou
  Telegram fica como trabalho futuro.

## 3.12 Parâmetros que ainda faltam

Estes parâmetros não são sensores: vêm de ensaios de laboratório, do projeto e
de inspeções, idealmente por zona da barragem (núcleo, espaldares, filtros,
fundação). Ficam registrados aqui como próximos passos.

**Material do maciço**

| Parâmetro | Por que importa |
|---|---|
| Grau de compactação | Barragem mal compactada tem menor resistência e maior permeabilidade |
| Permeabilidade (kh, kv) e anisotropia | Controla a rede de fluxo, a poropressão e a vazão esperada (Darcy) |
| c', φ' de pico e residuais | Após grande deformação, a resistência cai para a residual |
| Resistência não drenada (Su) | Carregamentos rápidos: sismo, rebaixamento, primeiro enchimento |
| Granulometria e limites de Atterberg (LL, LP, IP) | Suscetibilidade a erosão interna e a liquefação |
| Compressibilidade (Cc, cv), módulo E, Poisson | Previsão de recalque e adensamento |
| Sucção mátrica / curva de retenção | Na zona não saturada a sucção aumenta a resistência; a chuva a destrói |

**Composição química**

| Parâmetro | Efeito |
|---|---|
| Dispersividade (ensaio pinhole, crumb test) | Argilas dispersivas se desagregam em água e são a principal causa química de piping |
| Teor de sódio (ESP, SAR), sais solúveis totais | Indicadores químicos de dispersividade |
| Argilominerais expansivos (montmorilonita) | Variação de volume com a umidade e trincas |
| Matéria orgânica | Reduz a resistência e aumenta a compressibilidade |
| Carbonatos, sulfatos, gipsita | Podem dissolver com a percolação e abrir caminhos preferenciais |
| pH e química da água percolada | Mudança na água que sai pode indicar dissolução ou carreamento |
| Reação álcali-agregado, carbonatação | Só nas estruturas de concreto (vertedouro, tomada d'água) |

**Geometria, drenagem e fundação:** largura da crista, filtro chaminé e tapete
drenante (e a perda de eficiência quando colmatam), tipo de solo ou rocha da
fundação, camadas moles, falhas, carste e cortina de injeção.

**Superfície do talude (inspeção visual):** tipo de proteção (rip-rap, grama,
sem proteção), trincas de ressecamento ou de tração na crista, ravinas,
surgências e "pontos molhados", tocas de animais e árvores (raízes que apodrecem
viram caminhos de percolação). Um formulário de inspeção que pontue o índice é
uma extensão natural do app.

**Outras variáveis externas:** intensidade da chuva (mm/h), capacidade e estado
das comportas do vertedouro, direção do vento, duração e magnitude do sismo,
detonações e tráfego pesado, evaporação e ciclos de molhagem e secagem, e
escavações ou cortes no pé do talude.

## 3.13 Limitações e melhorias futuras

- O talude infinito com rᵤ constante é uma simplificação; não há rede de fluxo.
  No talude infinito o peso aparece dos dois lados (força que desliza e atrito),
  então o umedecimento pela chuva muda pouco o FS: a chuva age sobretudo pela
  poropressão medida e pela perda de sucção, que não é modelada.
- O gradiente de piping é o médio entre o piezômetro e o dreno, não o gradiente
  na saída; não há piezômetros na fundação (subpressão).
- A verificação sísmica é pseudoestática; não avalia liquefação nem o
  deslocamento permanente (Newmark).
- O rebaixamento rápido assume o caso extremo (poropressão que não dissipa).
- O balanço hídrico mantém a afluência atual constante; uma previsão
  hidrológica de verdade traria o hidrograma das próximas horas.
- Os modelos de valor esperado são regressões lineares simples; com anos de
  dados, o modelo HST completo (termos sazonais) e métodos estatísticos mais
  robustos seriam preferíveis.
- Os limites deveriam ser derivados do histórico de cada instrumento, e os
  coeficientes de variação do Monte Carlo, de ensaios.

## 3.14 Pontos para orientação

1. Os pesos e o critério de agrupamento (resposta × solicitação) são adequados?
2. O modelo de talude infinito com varredura de profundidade é suficiente, ou
   seria melhor implementar o método de Bishop simplificado?
3. As faixas experimentais dos novos indicadores (FS_piping, borda livre,
   resíduos, Fukuzono) fazem sentido para a barragem de referência?
4. A confiabilidade (β) deve passar a definir o nível depois que houver
   coeficientes de variação de ensaio?
5. Como apresentar os limites de alerta deixando claro que não se trata de uma
   avaliação profissional de segurança?
