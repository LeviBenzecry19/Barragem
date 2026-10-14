# 3. Metodologia de análise e classificação

> **Aviso.** O modelo abaixo é **experimental e didático**. Limites, pesos e
> parâmetros do solo são valores ilustrativos de uma barragem fictícia e fazem
> parte da metodologia do trabalho, não são valores universais de engenharia.
> A classificação não substitui a análise de um engenheiro responsável.

Todos os valores citados estão em `monitor/config.py` e as fórmulas em
`monitor/analise.py`.

## 3.1 Barragem de referência (fictícia)

| Parâmetro | Valor |
|---|---|
| Tipo | Barragem de terra homogênea |
| Altura / cota da crista | 15 m |
| Nível normal do reservatório | 10 m |
| Talude de jusante | 1V : 2,5H (β ≈ 21,8°) |
| Peso específico do solo (γ) | 19 kN/m³ |
| Coesão efetiva (c') | 15 kPa |
| Ângulo de atrito efetivo (φ') | 32° |
| Profundidade do piezômetro / superfície de ruptura (z) | 5 m |

## 3.2 Fórmulas utilizadas

**Pressão hidrostática** (carga do reservatório na base):

$$P = \rho \cdot g \cdot h$$

Ex.: h = 10 m → P = 1000 × 9,81 × 10 = 98,1 kPa.

**Carga piezométrica** (altura de água equivalente à pressão de poros medida):

$$h_p = \frac{u}{\rho \cdot g}$$

**Tensão total e tensão efetiva** (princípio de Terzaghi):

$$\sigma = \gamma \cdot z \qquad \sigma' = \sigma - u$$

Ex.: z = 5 m → σ = 95 kPa; com u = 25 kPa, σ' = 70 kPa. Quanto maior a pressão
de poros, menor a tensão efetiva e, portanto, menor a resistência ao
cisalhamento do solo.

**Razão de poropressão**:

$$r_u = \frac{u}{\gamma \cdot z}$$

**Fator de segurança – talude infinito com poropressão** (critério de Mohr-Coulomb):

$$FS = \frac{c' + (\gamma z \cos^2\beta - u)\tan\phi'}{\gamma z \sin\beta \cos\beta}$$

Resistência ao cisalhamento disponível dividida pela tensão cisalhante atuante.
FS = 1 é a condição de ruptura iminente. Para os parâmetros da barragem de
referência:

| u (kPa) | rᵤ | FS | Faixa |
|---:|---:|---:|---|
| 0 | 0,00 | 2,02 | Normal |
| 15 (base) | 0,16 | 1,73 | Normal |
| 25 (atenção) | 0,26 | 1,54 | Normal |
| 35 (alerta) | 0,37 | 1,35 | Atenção |
| 45 (crítico) | 0,47 | 1,16 | Alerta |
| 52 | 0,55 | 1,03 | Crítico |

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

## 3.3 Limites de controle por variável

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

Os limites da pressão de poros foram escolhidos de forma coerente com o FS:
ao atingir o limite crítico (45 kPa), o FS cai para 1,16.

## 3.4 Normalização

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

## 3.5 Índice experimental de risco

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

Vibração e temperatura têm peso 0: um sismo é um evento pontual (não deve ser
"diluído" em uma média) e a temperatura é usada para contexto e correção de
sensores. Ambas continuam gerando alertas individuais.

Os pesos podem ser revistos pelo grupo junto ao orientador (por exemplo, via
método AHP – *Analytic Hierarchy Process* – com comparação par a par feita por
especialistas) sem alterar o código: basta editar `monitor/config.py`.

## 3.6 Regras de sobreposição (nível global)

Uma média ponderada pode esconder um problema isolado grave (por exemplo, vazão
crítica com as demais variáveis normais resulta em índice de apenas 0,15).
Por isso o nível global é o **mais severo** entre:

1. a faixa do índice;
2. **Alerta**, se uma variável estiver crítica; **Crítico**, se duas ou mais estiverem;
3. a faixa do fator de segurança.

Os motivos que determinaram o nível são registrados e mostrados no dashboard.

## 3.7 Exemplo de cálculo

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

FS com u = 30 kPa: 1,45 → Atenção. Nenhuma variável crítica.
**Nível global: Atenção.**

## 3.8 Geração de alertas

- Um alerta é gerado quando uma variável ou o nível global **sobe** de nível.
- Para evitar repetição quando a leitura oscila sobre um limite, não se gera
  novo alerta da mesma origem enquanto houver um alerta pendente (não
  reconhecido) de nível igual ou superior.
- O operador reconhece o alerta no dashboard. No protótipo os alertas são
  exibidos e registrados no log do servidor; a integração com e-mail, SMS ou
  Telegram fica como trabalho futuro.

## 3.9 Limitações e melhorias futuras

- Limites fixos não consideram a **taxa de variação** (ex.: deslocamento em
  mm/dia), muito usada em barragens; pode ser adicionada como nova regra.
- Não há correlação entre variáveis (ex.: poropressão esperada para um dado
  nível do reservatório). Modelos estatísticos (regressão, HST) ou de
  aprendizado de máquina poderiam prever o valor esperado e alertar sobre desvios.
- O FS usa um único piezômetro e um modelo simplificado.
- Os limites deveriam ser derivados do histórico de cada instrumento.

## 3.10 Pontos para orientação

1. Os pesos e o critério de agrupamento (resposta × solicitação) são adequados?
2. O modelo de talude infinito é suficiente para o nível do projeto, ou seria
   melhor implementar o método de Bishop simplificado?
3. Como apresentar os limites de alerta deixando claro que não se trata de uma
   avaliação profissional de segurança?
