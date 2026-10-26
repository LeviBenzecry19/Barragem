// Página de sensores: topologia da estação (vistas lógica e física, no estilo
// do Cisco Packet Tracer), explicação de cada sensor e envio de leituras digitadas.
"use strict";

const ESTACAO = "MANUAL";
const ATRASO_PREVIA_MS = 150;
const ALTURA_SENSOR_NIVEL_M = 15.5;   // mesma constante do firmware
const NIVEIS = ["Normal", "Atenção", "Alerta", "Crítico"];

// Conteúdo didático de cada variável (docs/02-variaveis-e-sensores.md e docs/06-hardware.md).
const EXPLICACAO = {
  nivel_reservatorio: {
    curto: "Carga de água sobre a barragem",
    mede: "A altura da água no reservatório, contada a partir do fundo. A crista da barragem fica a 15 m.",
    importancia: "É a carga hidráulica sobre a estrutura. Quanto mais alto o nível, maior o empuxo da água, maior a percolação pelo maciço e menor a folga até a crista. Água passando por cima da crista (galgamento) costuma destruir barragens de terra.",
    real: "Régua linimétrica, transdutor de nível ou radar.",
    conversao: "distância = tempo do eco × 343 m/s ÷ 2; nível = 15,5 m − distância.",
  },
  pressao_poros: {
    curto: "Água sob pressão dentro do solo",
    mede: "A pressão da água nos poros do solo, 5 m abaixo da superfície do talude de jusante.",
    importancia: "Pelo princípio de Terzaghi (σ' = σ − u), a água nos poros empurra os grãos e reduz a tensão efetiva, que é o que dá resistência ao solo. Por isso é a variável de maior peso no índice e a base do cálculo do fator de segurança.",
    real: "Piezômetro Casagrande, de corda vibrante ou pneumático.",
    conversao: "u = (V − 0,5) ÷ (4,5 − 0,5) × 100 kPa. Cada 9,81 kPa equivalem a 1 m de coluna d'água.",
  },
  vazao_infiltracao: {
    curto: "Água que atravessa o maciço",
    mede: "A vazão da água que atravessa a barragem e é coletada no dreno de pé, do lado de jusante.",
    importancia: "Toda barragem de terra deixa passar um pouco de água; o perigo é a mudança. Um aumento brusco, ou água turva carregando solo, pode indicar erosão interna (piping), uma das principais causas de ruptura.",
    real: "Medidor de vazão triangular (vertedouro) ou calha Parshall.",
    conversao: "Q (L/min) = frequência dos pulsos (Hz) ÷ 7,5. Não mede turbidez nem vazões muito baixas.",
  },
  deslocamento_horizontal: {
    curto: "Movimento lateral do talude",
    mede: "O deslocamento horizontal acumulado do talude de jusante desde a instalação.",
    importancia: "Movimento lateral contínuo indica que o talude pode estar deslizando. A velocidade importa tanto quanto o valor: deslocamentos que aceleram costumam preceder rupturas.",
    real: "Inclinômetro em tubo-guia, marcos superficiais com topografia ou GNSS.",
    conversao: "mm = tensão × (50 mm ÷ 3,3 V) − zero da instalação.",
  },
  recalque: {
    curto: "Afundamento da crista",
    mede: "O deslocamento vertical (afundamento) acumulado da crista.",
    importancia: "Algum recalque é normal enquanto o solo se adensa depois da construção. Recalques grandes ou desiguais reduzem a folga entre a água e a crista e podem abrir trincas por onde a água passa.",
    real: "Medidor de recalque magnético, placas de recalque ou marcos topográficos.",
    conversao: "mm = tensão × (100 mm ÷ 3,3 V) − zero da instalação.",
  },
  chuva_24h: {
    curto: "Chuva das últimas 24 h",
    mede: "A chuva acumulada nas últimas 24 horas.",
    importancia: "Chuva forte eleva o reservatório e infiltra no talude, aumentando a pressão de poros. Ajuda a explicar a causa quando outras leituras sobem.",
    real: "Pluviômetro ou pluviógrafo.",
    conversao: "chuva = número de basculadas × 0,2794 mm, em soma móvel de 24 h.",
  },
  inclinacao: {
    curto: "Rotação da estrutura",
    mede: "A variação do ângulo da estrutura em relação à leitura inicial.",
    importancia: "Se uma parte da estrutura gira, ela está se movendo de forma desigual, por exemplo um bloco do talude começando a escorregar.",
    real: "Tiltímetro ou inclinômetro.",
    conversao: "ângulo = atan2(aₓ, √(a_y² + a_z²)) − ângulo inicial.",
  },
  vibracao: {
    curto: "Tremores e sismos",
    mede: "O pico de aceleração do último minuto, amostrado cerca de 100 vezes por segundo.",
    importancia: "Detecta sismos e vibrações fortes (explosões, máquinas pesadas). Não entra no índice, mas gera alerta próprio: depois de um evento forte, a barragem deve ser inspecionada.",
    real: "Acelerógrafo ou sismógrafo.",
    conversao: "vibração = maior valor de |‖a‖ − 1 g| no minuto.",
  },
  temperatura: {
    curto: "Contexto para as outras leituras",
    mede: "A temperatura do ar e dos sensores.",
    importancia: "Serve de contexto: a temperatura muda a velocidade do som (usada pelo sensor ultrassônico) e causa deriva em sensores baratos. Também é variável explicativa do modelo de deslocamento esperado. Não entra no índice, mas gera alerta próprio.",
    real: "Termistor ou termopar.",
    conversao: "Leitura digital direta, em °C.",
  },
  turbidez: {
    curto: "Solo sendo levado pela água",
    mede: "A turbidez (partículas em suspensão) da água que sai pelo dreno de pé.",
    importancia: "Água limpa no dreno é o esperado; água turva significa que a percolação está carregando solo do maciço, o sinal mais direto de erosão interna (piping). Junto com vazão alta ou crescente, eleva o modo de erosão interna a Alerta ou Crítico.",
    real: "Turbidímetro de processo na caixa de medição de vazão, além da inspeção visual.",
    conversao: "NTU a partir da tensão do sensor, por curva de calibração com padrões de formazina.",
  },
  vento: {
    curto: "Ondas que reduzem a borda livre",
    mede: "A velocidade do vento sobre o reservatório.",
    importancia: "Vento forte gera ondas que sobem o talude de montante (espraiamento) e empurra a água contra a barragem (sobrelevação). Os dois reduzem a borda livre efetiva e podem causar galgamento mesmo com o nível abaixo do limite.",
    real: "Anemômetro de conchas ou ultrassônico, com direção do vento, em estação meteorológica.",
    conversao: "velocidade = frequência dos pulsos × 2,4 km/h (um pulso por segundo a 2,4 km/h).",
  },
  vazao_afluente: {
    curto: "Água chegando ao reservatório",
    mede: "A vazão do rio que chega ao reservatório, medida a montante ou prevista.",
    importancia: "Antecipa o galgamento antes de o nível subir: o balanço hídrico (afluência − vertedouro − tomada d'água − infiltração − evaporação) prevê o nível das próximas 24 horas.",
    real: "Estação fluviométrica a montante (régua e curva-chave) ou previsão hidrológica.",
    conversao: "Não passa pelo ESP32: chega pela rede, em m³/s.",
  },
};

// Sensores físicos do protótipo, na ordem em que aparecem em volta do ESP32.
// "cabo" é a interface elétrica; quem tem "ligadoA" chega pela rede, com posição fixa.
const SENSORES = [
  {
    id: "ultrassom", nome: "Sensor de nível", curto: "Nível", modelo: "JSN-SR04T", icone: "nivel",
    variaveis: ["nivel_reservatorio"], cabo: "digital", porta: "GPIO 5 / 18",
    prototipo: "JSN-SR04T: ultrassônico à prova d'água, fixado 15,5 m acima do fundo e apontado para a água.",
    ligacao: "TRIG no GPIO 5 e ECHO no GPIO 18. O ECHO sai em 5 V e passa por um divisor de tensão.",
  },
  {
    id: "chuva", nome: "Pluviômetro", curto: "Pluviômetro", modelo: "Báscula com reed switch", icone: "chuva",
    variaveis: ["chuva_24h"], cabo: "digital", porta: "GPIO 26",
    prototipo: "Pluviômetro de báscula: cada basculada (0,2794 mm de chuva) fecha um reed switch.",
    ligacao: "GPIO 26 por interrupção, com pull-up interno e debounce de 200 ms.",
  },
  {
    id: "anemometro", nome: "Anemômetro", curto: "Vento", modelo: "Anemômetro de conchas", icone: "vento",
    variaveis: ["vento"], cabo: "digital", porta: "GPIO 25",
    prototipo: "Anemômetro de conchas com reed switch: um pulso por volta, no alto do mastro da estação.",
    ligacao: "GPIO 25 por interrupção, com pull-up interno.",
  },
  {
    id: "piezo", nome: "Piezômetro", curto: "Piezômetro", modelo: "Transdutor de pressão 0,5–4,5 V", icone: "pressao",
    variaveis: ["pressao_poros"], cabo: "analogico", porta: "GPIO 34",
    prototipo: "Transdutor de pressão 0,5–4,5 V (0 a 100 kPa) no fundo de um tubo piezométrico.",
    ligacao: "GPIO 34 (ADC1). A saída de até 4,5 V passa por um divisor para ficar abaixo de 3,3 V.",
  },
  {
    id: "vazao", nome: "Medidor de vazão", curto: "Vazão", modelo: "YF-S201", icone: "vazao",
    variaveis: ["vazao_infiltracao"], cabo: "digital", porta: "GPIO 27",
    prototipo: "YF-S201: turbina com sensor de efeito Hall que gera pulsos proporcionais à vazão.",
    ligacao: "GPIO 27 por interrupção. Alimentado em 5 V, com divisor no sinal.",
  },
  {
    id: "turbidez", nome: "Turbidímetro", curto: "Turbidez", modelo: "TSD-10", icone: "turbidez",
    variaveis: ["turbidez"], cabo: "analogico", porta: "GPIO 33",
    prototipo: "TSD-10: sensor óptico de turbidez com saída analógica, dentro da caixa do medidor de vazão.",
    ligacao: "GPIO 33 (ADC1), com divisor 5 V → 3,3 V.",
  },
  {
    id: "desloc", nome: "Extensômetro horizontal", curto: "Deslocamento", modelo: "Potenciômetro linear de 50 mm", icone: "desloc",
    variaveis: ["deslocamento_horizontal"], cabo: "analogico", porta: "GPIO 35",
    prototipo: "Potenciômetro linear com curso de 50 mm preso a uma haste (extensômetro).",
    ligacao: "GPIO 35 (ADC1), alimentado em 3,3 V. O zero é lido na inicialização.",
  },
  {
    id: "recalque", nome: "Medidor de recalque", curto: "Recalque", modelo: "Potenciômetro linear de 100 mm", icone: "recalque",
    variaveis: ["recalque"], cabo: "analogico", porta: "GPIO 32",
    prototipo: "Potenciômetro linear com curso de 100 mm, na vertical sobre a crista.",
    ligacao: "GPIO 32 (ADC1), alimentado em 3,3 V. O zero é lido na inicialização.",
  },
  {
    id: "temp", nome: "Termômetro", curto: "Temperatura", modelo: "DS18B20", icone: "temp",
    variaveis: ["temperatura"], cabo: "onewire", porta: "GPIO 4",
    prototipo: "DS18B20: sensor digital de temperatura em cápsula à prova d'água.",
    ligacao: "GPIO 4 (barramento 1-Wire) com resistor de pull-up de 4,7 kΩ para 3,3 V.",
  },
  {
    id: "mpu", nome: "Acelerômetro", curto: "Acelerômetro", modelo: "MPU-6050", icone: "mpu",
    variaveis: ["inclinacao", "vibracao"], cabo: "i2c", porta: "SDA 21 / SCL 22",
    prototipo: "MPU-6050: acelerômetro de 3 eixos. Um único chip fornece a inclinação e a vibração.",
    ligacao: "Barramento I²C: SDA no GPIO 21, SCL no GPIO 22, endereço 0x68.",
  },
  {
    id: "fluvio", nome: "Estação fluviométrica", curto: "Afluência", modelo: "Régua e curva-chave / previsão", icone: "fluvio",
    variaveis: ["vazao_afluente"], cabo: "internet", porta: "4G / Internet", ligadoA: "roteador", pos: [1060, 100], rotulo: "abaixo",
    prototipo: "Não faz parte da estação ESP32: a vazão vem de uma estação no rio, a montante, ou de um serviço de previsão hidrológica.",
    ligacao: "Envia ao mesmo POST /api/leituras, como outra estação (ex.: FLU-01). Também pode ser digitada nesta página.",
  },
];

// Demais dispositivos da cadeia de dados, com posição fixa na vista lógica.
const REDE = [
  {
    id: "esp32", nome: "ESP32", curto: "ESP32", sub: "Estação de aquisição", icone: "esp32", pos: [440, 400], rotulo: "direita",
    texto: "Microcontrolador com Wi-Fi instalado na barragem. Lê todos os sensores, converte os sinais elétricos em grandezas físicas e envia um pacote JSON ao servidor.",
    fatos: [
      ["Leituras", "Uma por minuto. O acelerômetro é amostrado cerca de 100 vezes por segundo e o pico do minuto é enviado."],
      ["Envio", "HTTP POST para /api/leituras, com o cabeçalho X-Chave-API."],
      ["Sem rede", "Guarda até 20 pacotes numa fila e reenvia quando a conexão volta."],
      ["Relógio", "Horário em UTC, sincronizado por NTP."],
      ["Entradas analógicas", "Só pinos do ADC1 (GPIO 32 a 39): o ADC2 não funciona com o Wi-Fi ligado."],
    ],
  },
  {
    id: "roteador", nome: "Roteador Wi-Fi", curto: "Roteador", sub: "Rede local", icone: "roteador", pos: [680, 400], rotulo: "acima",
    texto: "Liga a estação da barragem ao servidor e recebe, pela internet, a vazão afluente da estação fluviométrica. No protótipo é a rede Wi-Fi do laboratório.",
    fatos: [["Barragem real", "Rádio LoRa ou 4G para locais remotos, e MQTT no lugar de HTTP quando há muitas estações."]],
  },
  {
    id: "servidor", nome: "Servidor", curto: "Servidor", sub: "monitor.servidor", icone: "servidor", pos: [880, 400],
    texto: "Programa em Python (só biblioteca padrão) que recebe as leituras, valida, grava, avalia a barragem e gera os alertas.",
    fatos: [
      ["Avaliação", "Usa a última leitura de cada sensor e as médias horárias do histórico (taxas, chuva antecedente, modelos de valor esperado)."],
      ["Índice de risco", "Soma de peso × nota (0 a 1): < 0,25 Normal · < 0,50 Atenção · < 0,75 Alerta · ≥ 0,75 Crítico."],
      ["Modos de ruptura", "Galgamento, erosão interna, taludes de jusante e montante, sismo e deformações. Cada modo combina vários sensores; o nível global é o mais severo entre o índice, as regras e os modos."],
      ["Fator de segurança", "Menor FS de talude infinito até 8 m de profundidade: < 1,5 Atenção · < 1,3 Alerta · < 1,1 Crítico."],
      ["Regras extras", "Uma variável crítica eleva o nível global a pelo menos Alerta; duas ou mais, a Crítico."],
      ["Alertas", "Gerados quando uma variável, um modo ou o nível global sobe, sem repetir enquanto o anterior não for reconhecido."],
    ],
  },
  {
    id: "banco", nome: "Banco de dados", curto: "SQLite", sub: "barragem.db", icone: "banco", pos: [1080, 400],
    texto: "Arquivo SQLite com todo o histórico, criado automaticamente na primeira execução do servidor.",
    fatos: [
      ["Tabelas", "sensores (limites e pesos), leituras, avaliacoes e alertas."],
      ["Recomeçar do zero", "Pare o servidor e apague barragem.db."],
    ],
  },
  {
    id: "pc", nome: "Dashboard", curto: "Dashboard", sub: "Navegador", icone: "pc", pos: [680, 600],
    texto: "Mostra o estado atual, os modos de ruptura, os gráficos históricos e os alertas, atualizando a cada 5 segundos.",
    fatos: [["Abrir", '<a href="/">Dashboard</a>']],
  },
];

const LIGACOES_REDE = [
  ["esp32", "roteador", "wifi", "Wi-Fi · HTTP"],
  ["roteador", "servidor", "ethernet", "Ethernet · porta 8000"],
  ["roteador", "pc", "ethernet", "Ethernet · HTTP"],
  ["servidor", "banco", "arquivo", "arquivo local"],
];

const CABOS = {
  analogico: "Analógico (ADC)", digital: "Digital / pulsos", i2c: "I²C", onewire: "1-Wire",
  wifi: "Wi-Fi", ethernet: "Ethernet", internet: "4G / Internet", arquivo: "Arquivo local",
};

// Início da faixa do controle deslizante (as demais variáveis começam em zero).
const MINIMO = { temperatura: -10 };

// Ícones desenhados em uma área de 56 × 56 centrada em (0, 0).
const ICONES = {
  nivel: '<rect x="-9" y="-19" width="18" height="8" rx="2"/><path d="M-3 -11v4M3 -11v4"/><path d="M-18 6q4.5-4 9 0t9 0t9 0t9 0M-18 13q4.5-4 9 0t9 0t9 0t9 0"/>',
  pressao: '<circle cx="0" cy="-3" r="13"/><path d="M0 -3l7-7M-9 -3h2M9 -3h-2M0 -14v2"/><path d="M-4 10v8h8v-8"/>',
  vazao: '<path d="M-19 -7h38M-19 7h38"/><path d="M-11 0h18M3 -4l4 4l-4 4"/><path d="M14 11q-3 4 0 6q3-2 0-6z"/>',
  desloc: '<path d="M-17 -3h34M-12 -8l-5 5l5 5M12 -8l5 5l-5 5"/><path d="M-14 12h28M-14 12v-4M-7 12v-2M0 12v-4M7 12v-2M14 12v-4"/>',
  recalque: '<path d="M0 -19v20M-5 -4l5 5l5-5"/><path d="M-13 6h26v4h-26z"/><path d="M-18 16h36"/>',
  chuva: '<path d="M-12 2a7 7 0 0 1 1-14a9 9 0 0 1 17 2a6 6 0 0 1 1 12z"/><path d="M-8 7l-3 9M0 7l-3 9M8 7l-3 9"/>',
  mpu: '<rect x="-11" y="-11" width="22" height="22" rx="2"/><path d="M-6 -11v-5M0 -11v-5M6 -11v-5M-6 11v5M0 11v5M6 11v5M-11 -6h-5M-11 0h-5M-11 6h-5M11 -6h5M11 0h5M11 6h5"/><path d="M-6 3l3-6l3 6l3-6"/>',
  temp: '<path d="M-4 6v-19a4 4 0 0 1 8 0v19"/><circle cx="0" cy="11" r="6"/><path d="M0 7v-13M9 -12h4M9 -6h4M9 0h4"/>',
  turbidez: '<path d="M-7 -18v10l-9 24h32l-9-24v-10M-10 -18h20"/><circle cx="-4" cy="8" r="1.6"/><circle cx="4" cy="11" r="1.6"/><circle cx="1" cy="3" r="1.6"/><circle cx="-6" cy="13" r="1.6"/>',
  vento: '<path d="M-18 -6h20a5 5 0 1 0-5-5M-18 2h26a5 5 0 1 1-5 5M-18 10h12"/>',
  fluvio: '<path d="M-12 12v-30M-12 -18h14l-4 5 4 5h-14"/><path d="M-19 8q4.5-4 9 0t9 0t9 0t9 0M-19 15q4.5-4 9 0t9 0t9 0t9 0"/>',
  esp32: '<path d="M-12 -10v-7h5v5h5v-5h5v5h5v-5h4v7"/><rect x="-14" y="-6" width="28" height="20" rx="2"/><path d="M-14 -1h-4M-14 4h-4M-14 9h-4M14 -1h4M14 4h4M14 9h4"/>',
  roteador: '<ellipse cx="0" cy="-5" rx="19" ry="7"/><path d="M-19 -5v10a19 7 0 0 0 38 0v-10"/><path d="M-10 -8l6 2M10 -2l-6-2M10 -8l-6 2M-10 -2l6-2"/>',
  servidor: '<rect x="-11" y="-19" width="22" height="38" rx="2"/><path d="M-6 -12h12M-6 -6h12M-6 0h12"/><circle cx="0" cy="11" r="2"/>',
  banco: '<ellipse cx="0" cy="-12" rx="15" ry="5"/><path d="M-15 -12v24a15 5 0 0 0 30 0v-24M-15 0a15 5 0 0 0 30 0"/>',
  pc: '<rect x="-18" y="-16" width="36" height="24" rx="2"/><path d="M-6 16h12M0 8v8"/><path d="M-12 2l6-6l5 4l7-8l6 5"/>',
};

const ENVELOPE = '<g class="pdu"><rect x="-10" y="-7" width="20" height="14" rx="2"/><path d="M-10 -7l10 8l10-8"/></g>';

// ---------------------------------------------------------------------------

let sensores = [];      // definições vindas da API: limites, pesos, unidades
let porChave = {};
let ultimas = {};       // última leitura gravada de cada variável
let geotecnia = null;
let previa = null;      // resultado de /api/avaliar para os valores do formulário
let erroPrevia = "";
let servidorOk = true;
let selecionado = "piezo";
let vista = "logico";
let seqPrevia = 0;
let temporizador = null;

const TODOS = [...SENSORES, ...REDE];
const POS = posicoesLogicas();

const $ = (id) => document.getElementById(id);
const clamp = (v, a, b) => Math.min(Math.max(v, a), b);
const fmt = (v, casas = 2) =>
  v === null || v === undefined
    ? "—"
    : Number(v).toLocaleString("pt-BR", { maximumFractionDigits: Math.abs(v) < 1 && v !== 0 ? Math.max(casas, 3) : casas });
const hora = (iso) => new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "medium" });
const dispositivo = (id) => TODOS.find((d) => d.id === id);
const dispositivoDaVariavel = (k) => SENSORES.find((d) => d.variaveis.includes(k));
const movimentoReduzido = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function esc(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function selo(nivel) {
  return `<span class="selo n-${nivel}">${nivel}</span>`;
}

async function obter(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

// -- valores e níveis --------------------------------------------------------

function valoresDigitados() {
  const valores = {};
  for (const s of sensores) {
    const el = $(`in-${s.variavel}`);
    if (el && el.value !== "" && Number.isFinite(el.valueAsNumber)) valores[s.variavel] = el.valueAsNumber;
  }
  return valores;
}

// Valor que a avaliação vai usar: o digitado ou, se o campo estiver vazio, a última leitura.
function valorExibido(k, digitados) {
  if (k in digitados) return digitados[k];
  return ultimas[k] ? ultimas[k].valor : null;
}

function nivelDe(k) {
  return previa && previa.variaveis[k] ? previa.variaveis[k].nivel : null;
}

function nivelDispositivo(d) {
  const niveis = d.variaveis.map(nivelDe).filter(Boolean);
  return niveis.length ? niveis.reduce((a, b) => (NIVEIS.indexOf(b) > NIVEIS.indexOf(a) ? b : a)) : null;
}

function escala(s) {
  const min = MINIMO[s.variavel] ?? 0;
  const max = s.critico + (s.critico - s.alerta) * 1.5;
  const pct = (v) => clamp(((v - min) / (max - min)) * 100, 0, 100);
  const casas = Math.max(0, Math.ceil(-Math.log10((max - min) / 1000)));
  return { min, max, pct, casas, a: pct(s.atencao), al: pct(s.alerta), c: pct(s.critico) };
}

function gradiente(e) {
  return `linear-gradient(to right, var(--normal) 0 ${e.a}%, var(--atencao) ${e.a}% ${e.al}%, ` +
    `var(--alerta) ${e.al}% ${e.c}%, var(--critico) ${e.c}% 100%)`;
}

function rotulosLimites(s, e) {
  const marcas = [["atencao", e.a], ["alerta", e.al], ["critico", e.c]];
  return `<div class="trilho-rotulos">${marcas.map(([campo, p]) => `<span style="left:${p}%">${fmt(s[campo])}</span>`).join("")}</div>`;
}

// -- vista lógica ------------------------------------------------------------

// Sensores do ESP32 em arco à esquerda dele; os que chegam pela rede têm posição fixa.
function posicoesLogicas() {
  const pos = {};
  [...REDE, ...SENSORES.filter((d) => d.pos)].forEach((d) => (pos[d.id] = d.pos));
  const [cx, cy] = pos.esp32;
  const noArco = SENSORES.filter((d) => !d.pos);
  noArco.forEach((d, i) => {
    const ang = ((95 + (170 * i) / (noArco.length - 1)) * Math.PI) / 180;
    pos[d.id] = [cx + 300 * Math.cos(ang), cy - 320 * Math.sin(ang)];
  });
  return pos;
}

function pontoA(a, b, distancia) {
  const dx = b[0] - a[0], dy = b[1] - a[1], comp = Math.hypot(dx, dy);
  return [a[0] + (dx * distancia) / comp, a[1] + (dy * distancia) / comp];
}

function ladrilho(d) {
  return `<rect class="ladrilho ${d.variaveis ? "ladrilho-sensor" : "ladrilho-rede"}" x="-28" y="-28" width="56" height="56" rx="10"/>` +
    `<g class="icone">${ICONES[d.icone]}</g>`;
}

function no(d, digitados) {
  const [x, y] = POS[d.id];
  const sensor = Boolean(d.variaveis);
  const sub = sensor
    ? d.variaveis.map((k) => {
        const v = valorExibido(k, digitados);
        return v === null ? "—" : `${fmt(v)} ${porChave[k] ? porChave[k].unidade : ""}`;
      }).join(" · ")
    : d.sub;
  const nivel = sensor ? nivelDispositivo(d) : null;
  // Rótulo acima dos sensores do topo, para não ficar sob o cabo que desce até o ESP32.
  const posRotulo = d.rotulo || (sensor && POS.esp32[1] - y > 180 ? "acima" : "abaixo");
  const [y1, y2, ancora, tx] =
    posRotulo === "acima" ? [-52, -36, "middle", 0] : posRotulo === "direita" ? [28, 45, "start", 36] : [48, 65, "middle", 0];
  const aria = sensor ? `${d.nome}: ${sub}${nivel ? `, ${nivel}` : ""}` : `${d.nome} (${d.sub})`;
  return `<g class="no${d.id === selecionado ? " selecionado" : ""}" data-id="${d.id}" transform="translate(${x.toFixed(1)} ${y.toFixed(1)})"
             tabindex="0" role="button" aria-label="${esc(aria)}">
      <rect class="selecao" x="-35" y="-35" width="70" height="70" rx="13"/>
      ${ladrilho(d)}
      <text class="rotulo halo" x="${tx}" y="${y1}" text-anchor="${ancora}">${esc(d.curto)}</text>
      <text class="valor-no halo" x="${tx}" y="${y2}" text-anchor="${ancora}">${esc(sub)}</text>
    </g>`;
}

function cenaLogica() {
  const digitados = valoresDigitados();
  const luzRede = servidorOk ? "Normal" : "Crítico";
  const ligacoes = [
    ...SENSORES.map((d) => ({
      a: d.id, b: d.ligadoA || "esp32", cabo: d.cabo, rotulo: d.porta,
      luzA: nivelDispositivo(d) || "vazio",
      luzB: d.variaveis.some((k) => valorExibido(k, digitados) !== null) ? "Normal" : "vazio",
    })),
    ...LIGACOES_REDE.map(([a, b, cabo, rotulo]) => ({ a, b, cabo, rotulo, luzA: luzRede, luzB: luzRede })),
  ];

  let s = `<rect class="regiao" x="30" y="10" width="530" height="785" rx="16"/>
    <text class="regiao-rotulo" x="48" y="38">Barragem (campo)</text>
    <rect class="regiao" x="600" y="230" width="570" height="440" rx="16"/>
    <text class="regiao-rotulo" x="618" y="258">Sala de controle</text>
    <rect class="regiao" x="880" y="10" width="290" height="190" rx="16"/>
    <text class="regiao-rotulo" x="898" y="38">Rio a montante</text>`;

  for (const l of ligacoes) {
    const [pa, pb] = [POS[l.a], POS[l.b]];
    const ativa = l.a === selecionado || l.b === selecionado;
    s += `<line class="cabo cabo-${l.cabo}${ativa ? " ativo" : ""}" x1="${pa[0]}" y1="${pa[1]}" x2="${pb[0]}" y2="${pb[1]}"/>`;
  }
  for (const l of ligacoes) {
    const [pa, pb] = [POS[l.a], POS[l.b]];
    const [la, lb] = [pontoA(pa, pb, 40), pontoA(pb, pa, 40)];
    s += `<circle class="luz f-${l.luzA}" cx="${la[0]}" cy="${la[1]}" r="5"/>`;
    s += `<circle class="luz f-${l.luzB}" cx="${lb[0]}" cy="${lb[1]}" r="5"/>`;
    if (l.a === selecionado || l.b === selecionado) {
      s += `<text class="porta halo" x="${(pa[0] + pb[0]) / 2}" y="${(pa[1] + pb[1]) / 2 + 4}">${esc(l.rotulo)}</text>`;
    }
  }
  return s + TODOS.map((d) => no(d, digitados)).join("");
}

// -- vista física (corte da barragem) ----------------------------------------

function cenaFisica() {
  const digitados = valoresDigitados();
  const v = (k) => valorExibido(k, digitados);
  const F = { chao: 520, crista: 220, pxm: 20, peMont: 260, cristaMont: 600, cristaJus: 720, peJus: 1060 };
  const inc = (F.cristaMont - F.peMont) / (F.chao - F.crista);
  const xMont = (y) => F.peMont + (F.chao - y) * inc;
  const yMont = (x) => F.chao - (x - F.peMont) / inc;
  const yJus = (x) => F.chao - (F.peJus - x) / inc;
  const yCota = (m) => F.chao - m * F.pxm;
  const n = (x) => x.toFixed(1);
  const pt = (p) => `${n(p[0])} ${n(p[1])}`;
  let s = "";

  // Chuva: quantidade de gotas proporcional ao acumulado de 24 h.
  const chuva = v("chuva_24h");
  for (let i = 0; i < Math.min(Math.round((chuva || 0) / 3), 60); i++) {
    s += `<path class="gota" d="M${30 + ((i * 197) % 1000)} ${40 + ((i * 89) % 150)}l-4 10"/>`;
  }

  // Fundação, reservatório e limites de controle do nível.
  s += `<rect class="fundacao" x="0" y="${F.chao}" width="1200" height="100"/>`;
  const nivel = v("nivel_reservatorio");
  const yAguaRes = nivel === null ? null : yCota(clamp(nivel, 0, 15));
  if (yAguaRes !== null) {
    s += `<path class="agua" d="M0 ${n(yAguaRes)}H${n(xMont(yAguaRes))}L${F.peMont} ${F.chao}H0Z"/>
      <path class="agua-linha" d="M0 ${n(yAguaRes)}H${n(xMont(yAguaRes))}"/>`;
  }
  const sv = porChave.nivel_reservatorio;
  if (sv) {
    for (const [campo, nv] of [["atencao", "Atenção"], ["alerta", "Alerta"], ["critico", "Crítico"]]) {
      const y = yCota(sv[campo]);
      s += `<line class="limite s-${nv}" x1="0" y1="${y}" x2="${n(xMont(y))}" y2="${y}"/>
        <text class="texto-cena halo" x="8" y="${y - 4}">${fmt(sv[campo])} m · ${nv}</text>`;
    }
  }
  if (yAguaRes !== null) {
    s += `<text class="texto-cena halo" x="200" y="${n(yAguaRes - 6)}">nível ${fmt(nivel)} m</text>`;
  }

  // Maciço e dreno de pé.
  s += `<path class="macico" d="M${F.peMont} ${F.chao}L${F.cristaMont} ${F.crista}H${F.cristaJus}L${F.peJus} ${F.chao}Z"/>
    <path class="brita" d="M975 ${F.chao}H${F.peJus}L1036 498Z"/>`;

  // Piezômetro: a água sobe no tubo até a carga u / (ρ·g) acima da ponta.
  const xp = 900, ySupP = yJus(xp), yTopoTubo = ySupP - 14;
  const yPonta = ySupP + (geotecnia ? geotecnia.profundidade_ruptura : 5) * F.pxm;
  const u = v("pressao_poros");
  const yAguaP = u === null ? null : clamp(yPonta - (u / 9.81) * F.pxm, yTopoTubo, yPonta);

  // Linha freática: entra pelo talude de montante, passa pelo nível do
  // piezômetro e sai no dreno de pé (Catmull-Rom convertido em Bézier).
  if (yAguaRes !== null && yAguaP !== null) {
    const p0 = [xMont(yAguaRes), yAguaRes], m = [xp, yAguaP], p2 = [1030, 512];
    const c1 = [p0[0] + (m[0] - p0[0]) / 6, p0[1] + (m[1] - p0[1]) / 6];
    const c2 = [m[0] - (p2[0] - p0[0]) / 6, m[1] - (p2[1] - p0[1]) / 6];
    const c3 = [m[0] + (p2[0] - p0[0]) / 6, m[1] + (p2[1] - p0[1]) / 6];
    const c4 = [p2[0] - (p2[0] - m[0]) / 6, p2[1] - (p2[1] - m[1]) / 6];
    s += `<path class="freatica" d="M${pt(p0)}C${pt(c1)} ${pt(c2)} ${pt(m)}C${pt(c3)} ${pt(c4)} ${pt(p2)}"/>`;
  }
  if (yAguaP !== null) {
    s += `<rect class="agua" x="${xp - 3}" y="${n(yAguaP)}" width="6" height="${n(yPonta - yAguaP)}"/>
      <text class="texto-cena halo" x="${xp + 20}" y="${n(ySupP + 8)}">u = ${fmt(u, 1)} kPa ≈ ${fmt(u / 9.81)} m de água</text>`;
  }
  s += `<g data-id="piezo"><path class="equip-linha" d="M${xp - 4} ${n(yTopoTubo)}V${n(yPonta)}M${xp + 4} ${n(yTopoTubo)}V${n(yPonta)}"/>
    <rect class="equip" x="${xp - 6}" y="${n(yPonta)}" width="12" height="9" rx="2"/></g>`;

  // Tubo do inclinômetro, curvado pelo deslocamento horizontal (exagerado).
  const xi = 800, ySupI = yJus(xi), dx = clamp((v("deslocamento_horizontal") || 0) * 0.5, -20, 35);
  s += `<path class="referencia" d="M${xi} 575V${n(ySupI - 10)}"/>
    <g data-id="desloc"><path class="equip-linha tubo" d="M${xi} 575Q${xi} ${n(ySupI + 60)} ${n(xi + dx)} ${n(ySupI - 10)}"/></g>`;

  // Marco de recalque: a placa desce com o recalque (exagerado).
  const yPlaca = 196 + clamp((v("recalque") || 0) * 0.25, -5, 20);
  s += `<path class="referencia" d="M626 196H654"/>
    <g data-id="recalque"><path class="equip-linha" d="M640 ${F.crista}V${n(yPlaca)}"/>
    <rect class="equip" x="632" y="${n(yPlaca - 4)}" width="16" height="4" rx="1"/></g>`;

  // Sensor ultrassônico em um braço sobre o reservatório; o feixe mede a distância até a água.
  const yUs = yCota(ALTURA_SENSOR_NIVEL_M);
  const yAlvo = yAguaRes === null ? yMont(450) : Math.min(yAguaRes, yMont(450));
  s += `<g data-id="ultrassom"><path class="equip-linha" d="M606 ${F.crista}V${yUs - 7}H460"/>
    <rect class="equip" x="440" y="${yUs - 10}" width="20" height="10" rx="2"/></g>
    <path class="feixe" d="M450 ${yUs}V${n(yAlvo)}"/>`;
  if (nivel !== null) {
    s += `<text class="texto-cena halo" x="458" y="${n((yUs + yAlvo) / 2 + 4)}">d = ${fmt(ALTURA_SENSOR_NIVEL_M - nivel)} m</text>`;
  }

  // Mastro da estação na crista; inclina com a variação de inclinação (exagerada).
  const ang = clamp((v("inclinacao") || 0) * 4, -12, 12);
  s += `<g transform="rotate(${n(ang)} 690 ${F.crista})">
      <path class="equip-linha" d="M690 ${F.crista}V80"/>
      <g data-id="anemometro"><path class="equip-linha" d="M676 80H704"/>
        <circle class="equip" cx="676" cy="80" r="5"/><circle class="equip" cx="704" cy="80" r="5"/></g>
      <g data-id="chuva"><path class="equip" d="M676 96H704L696 110H684Z"/></g>
      <g data-id="esp32"><rect class="equip" x="674" y="138" width="32" height="26" rx="3"/>
        <text class="texto-equip" x="690" y="155">ESP32</text><path class="equip-linha" d="M702 138L708 122"/></g>
      <g data-id="temp"><path class="equip-linha" d="M680 164V178"/><rect class="equip" x="677" y="178" width="6" height="12" rx="3"/></g>
      <g data-id="mpu"><rect class="equip" x="697" y="210" width="14" height="10" rx="1.5"/></g>
    </g>`;

  // Vibração acima do normal: onda sísmica na fundação.
  const nvVib = nivelDe("vibracao");
  if (nvVib && nvVib !== "Normal") {
    let d = "M0 575";
    for (let x = 12; x <= 1200; x += 12) d += `L${x} ${x % 24 ? 567 : 583}`;
    s += `<path class="sismo s-${nvVib}" d="${d}"/>`;
  }

  // Wi-Fi até a sala de controle, medidor de vazão e textos do desenho.
  s += `<path class="cabo cabo-wifi" d="M712 124Q900 150 1062 90"/>
    <g class="no-fis${selecionado === "servidor" ? " selecionado" : ""}" data-id="servidor" tabindex="0" role="button" aria-label="Servidor (sala de controle)">
      <path class="equip" d="M1070 110V62H1160V110Z"/><path class="equip" d="M1062 64L1115 34L1168 64Z"/>
      <rect class="janela" x="1084" y="76" width="16" height="12"/><rect class="janela" x="1130" y="76" width="16" height="12"/>
      <text class="halo" x="1115" y="128" text-anchor="middle">Sala de controle</text>
    </g>
    <g data-id="vazao"><path class="cano" d="M1036 512H1095"/><rect class="equip" x="1095" y="494" width="55" height="26" rx="2"/>
      <path class="equip-linha" d="M1105 494L1122 510L1139 494"/></g>
    <g data-id="turbidez"><path class="equip-linha" d="M1141 486V508"/><rect class="equip" x="1137" y="506" width="8" height="10" rx="2"/></g>
    <g data-id="fluvio"><path class="cano" d="M14 196H74"/><path class="equip-linha" d="M64 189L76 196L64 203"/></g>
    <text class="texto-cena" x="16" y="28">Esquema fora de escala · deslocamento, recalque e inclinação exagerados</text>
    <text class="texto-cena" x="24" y="508">Reservatório</text>
    <text class="texto-cena halo" x="660" y="430" text-anchor="middle">Maciço de terra compactada</text>
    <text class="texto-cena" x="930" y="540">Dreno de pé</text>
    <text class="texto-cena" x="420" y="565">Fundação</text>
    <text class="texto-cena" x="16" y="606">← Montante</text>
    <text class="texto-cena" x="1184" y="606" text-anchor="end">Jusante →</text>`;

  const rotulo = (id, x, y, texto, ancora = "start") => {
    const d = dispositivo(id);
    const lado = ancora === "end" ? 8 : -8;
    const ponto = d.variaveis ? `<circle class="luz f-${nivelDispositivo(d) || "vazio"}" cx="${x + lado}" cy="${y - 4}" r="5"/>` : "";
    return `<g class="no-fis${selecionado === id ? " selecionado" : ""}" data-id="${id}" tabindex="0" role="button" aria-label="${esc(d.nome)}">
      ${ponto}<text class="halo" x="${x}" y="${y}" text-anchor="${ancora}">${texto}</text></g>`;
  };
  return s +
    rotulo("ultrassom", 424, 209, "Sensor de nível", "end") +
    rotulo("piezo", 920, 367, "Piezômetro") +
    rotulo("desloc", 810, 271, "Deslocamento horizontal") +
    rotulo("recalque", 622, 249, "Marco de recalque") +
    rotulo("anemometro", 722, 84, "Anemômetro") +
    rotulo("chuva", 722, 106, "Pluviômetro") +
    rotulo("turbidez", 1062, 548, "Turbidímetro") +
    rotulo("fluvio", 92, 201, "Vazão afluente (rio)") +
    rotulo("esp32", 722, 156, "Estação ESP32") +
    rotulo("temp", 658, 190, "Termômetro", "end") +
    rotulo("mpu", 734, 210, "Acelerômetro") +
    rotulo("vazao", 1050, 483, "Medidor de vazão");
}

// -- renderização ------------------------------------------------------------

function renderCena() {
  const svg = $("vista");
  const focado = svg.contains(document.activeElement) ? document.activeElement.dataset.id : null;
  svg.setAttribute("viewBox", vista === "logico" ? "0 0 1200 800" : "0 0 1200 620");
  $("camada-cena").innerHTML = vista === "logico" ? cenaLogica() : cenaFisica();
  if (focado) {
    const el = svg.querySelector(`[tabindex][data-id="${focado}"]`);
    if (el) el.focus();
  }
}

function renderLegenda() {
  const amostraCabo = (c) => `<svg width="36" height="12" aria-hidden="true"><line class="cabo cabo-${c}" x1="2" y1="6" x2="34" y2="6"/></svg>`;
  const amostraLuz = (n) => `<svg width="12" height="12" aria-hidden="true"><circle class="luz f-${n}" cx="6" cy="6" r="5"/></svg>`;
  const item = (amostra, texto) => `<span class="item">${amostra}${texto}</span>`;
  const luzes = `<div class="legenda-grupo"><span class="legenda-titulo">${vista === "logico" ? "Luz do lado do sensor" : "Ponto ao lado do sensor"}</span>
    ${[...NIVEIS, "vazio"].map((n) => item(amostraLuz(n), n === "vazio" ? "sem leitura" : n)).join("")}</div>`;
  if (vista === "logico") {
    $("legenda").innerHTML = `<div class="legenda-grupo"><span class="legenda-titulo">Cabos</span>
      ${Object.entries(CABOS).map(([c, nome]) => item(amostraCabo(c), nome)).join("")}</div>${luzes}`;
  } else {
    $("legenda").innerHTML = `<div class="legenda-grupo"><span class="legenda-titulo">Desenho</span>
      ${item('<svg width="16" height="12" aria-hidden="true"><rect class="agua" width="16" height="12"/></svg>', "Água (sobe com o nível e com a pressão de poros)")}
      ${item('<svg width="36" height="12" aria-hidden="true"><line class="freatica" x1="2" y1="6" x2="34" y2="6"/></svg>', "Linha freática estimada")}
      ${item('<svg width="36" height="12" aria-hidden="true"><line class="limite s-Crítico" x1="2" y1="6" x2="34" y2="6"/></svg>', "Limites do nível")}
      </div>${luzes}`;
  }
}

function trilhoPainel(s, valor) {
  const e = escala(s);
  const marca = valor === null ? "" : `<span class="trilho-marca" style="left:${e.pct(valor)}%"></span>`;
  return `<div class="trilho" style="--trilho:${gradiente(e)}">${marca}</div>${rotulosLimites(s, e)}`;
}

function renderPainel() {
  const d = dispositivo(selecionado);
  const topo = `<header class="painel-topo"><svg class="icone-mini" viewBox="-30 -30 60 60" aria-hidden="true">${ladrilho(d)}</svg>
    <div><h3>${esc(d.nome)}</h3><p class="detalhe">${esc(d.variaveis ? d.modelo : d.sub)}</p></div></header>`;

  if (!d.variaveis) {
    $("painel").innerHTML = `${topo}<p>${d.texto}</p>
      <dl class="ficha">${d.fatos.map(([t, txt]) => `<dt>${t}</dt><dd>${txt}</dd>`).join("")}</dl>`;
    return;
  }

  const digitados = valoresDigitados();
  const partes = d.variaveis.map((k) => {
    const s = porChave[k];
    const ex = EXPLICACAO[k];
    if (!s) return "";
    const valor = valorExibido(k, digitados);
    const nivel = nivelDe(k);
    const origem = k in digitados ? "no formulário" : ultimas[k] ? "última leitura gravada" : "";
    return `<section class="painel-var">
      <div class="painel-leitura"><h4>${esc(s.nome)}</h4>${nivel ? selo(nivel) : '<span class="selo">sem leitura</span>'}</div>
      <div class="painel-valor"><span class="valor">${fmt(valor)}</span> <span class="unidade">${esc(s.unidade)}</span>
        <span class="detalhe">${origem}</span></div>
      ${trilhoPainel(s, valor)}
      <dl class="ficha">
        <dt>O que mede</dt><dd>${ex.mede}</dd>
        <dt>Por que importa</dt><dd>${ex.importancia}</dd>
        <dt>Em uma barragem real</dt><dd>${ex.real}</dd>
        <dt>Conversão no firmware</dt><dd>${ex.conversao}</dd>
        <dt>No índice de risco</dt><dd>${s.peso > 0 ? `Peso ${fmt(s.peso * 100, 0)}%` : "Fora do índice; gera alerta próprio"}</dd>
      </dl>
      <button type="button" data-editar="${k}">Editar valor</button>
    </section>`;
  });
  $("painel").innerHTML = `${topo}${partes.join("")}
    <h4>No protótipo</h4>
    <dl class="ficha"><dt>Sensor</dt><dd>${d.prototipo}</dd><dt>Ligação ao ESP32</dt><dd>${d.ligacao}</dd></dl>`;
}

function renderCampos() {
  const d = dispositivo(selecionado);
  for (const s of sensores) {
    const k = s.variavel;
    const nivel = nivelDe(k);
    const vazio = $(`in-${k}`).value === "";
    const el = $(`nv-${k}`);
    el.textContent = nivel || "—";
    el.className = `selo${nivel ? ` n-${nivel}` : ""}`;
    el.title = vazio && nivel ? "Nível da última leitura gravada" : "";
    const cartao = el.closest(".campo-sensor");
    cartao.classList.toggle("vazio", vazio);
    cartao.classList.toggle("selecionado", Boolean(d.variaveis && d.variaveis.includes(k)));
  }
}

function renderPrevia() {
  const el = $("previa");
  if (erroPrevia) {
    el.innerHTML = `<p class="detalhe">${esc(erroPrevia)}</p>`;
  } else if (!previa) {
    el.innerHTML = '<p class="detalhe">Digite ao menos uma leitura para ver a prévia da classificação.</p>';
  } else {
    el.innerHTML = `<div class="previa-linha"><strong>Prévia</strong><span class="detalhe">nada é gravado até você enviar</span></div>
      <div class="previa-linha">${selo(previa.nivel)}
        <span>Índice <b>${fmt(previa.indice, 3)}</b></span>
        <span>FS <b>${fmt(previa.fator_seguranca)}</b></span>
        <span>Cobertura <b>${fmt(previa.cobertura * 100, 0)}%</b></span></div>
      <ul class="motivos">${previa.motivos.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>`;
  }
}

function renderTudo() {
  renderCampos();
  renderCena();
  renderPainel();
  renderPrevia();
}

function mostrarResultado(tipo, html) {
  $("resultado").className = `resultado ${tipo}`;
  $("resultado").innerHTML = html;
}

function selecionar(id) {
  selecionado = id;
  renderCena();
  renderPainel();
  if (sensores.length) renderCampos();
}

// -- formulário --------------------------------------------------------------

function montarCampos() {
  $("campos").innerHTML = sensores.map((s) => {
    const k = s.variavel;
    const e = escala(s);
    return `<div class="campo-sensor" data-variavel="${k}">
      <div class="campo-topo"><label for="in-${k}">${esc(s.nome)}</label><span id="nv-${k}" class="selo">—</span></div>
      <p class="curto">${EXPLICACAO[k] ? EXPLICACAO[k].curto : ""}</p>
      <div class="campo-entrada">
        <input id="in-${k}" type="number" step="any" inputmode="decimal" data-variavel="${k}">
        <span class="unidade">${esc(s.unidade)}</span>
      </div>
      <input id="sl-${k}" class="faixa" type="range" min="${e.min}" max="${e.max}" step="${10 ** -e.casas}"
             data-variavel="${k}" style="--trilho:${gradiente(e)}" aria-label="${esc(s.nome)} (controle deslizante)">
      ${rotulosLimites(s, e)}
    </div>`;
  }).join("");
}

function sincronizarFaixa(k) {
  const valor = $(`in-${k}`).valueAsNumber;
  const reserva = ultimas[k] ? ultimas[k].valor : escala(porChave[k]).min;
  $(`sl-${k}`).value = Number.isFinite(valor) ? valor : reserva;
}

function preencher(valorDe) {
  for (const s of sensores) {
    const valor = valorDe(s);
    const el = $(`in-${s.variavel}`);
    el.value = valor === null || valor === undefined ? "" : String(valor);
    el.placeholder = ultimas[s.variavel] ? `última: ${fmt(ultimas[s.variavel].valor)}` : "sem leitura";
    sincronizarFaixa(s.variavel);
  }
}

async function carregarEstado(preencherCampos) {
  try {
    const estado = await obter("/api/estado");
    servidorOk = true;
    ultimas = estado.leituras;
    geotecnia = estado.geotecnia;
    if (!sensores.length) {
      sensores = estado.sensores;
      porChave = Object.fromEntries(sensores.map((s) => [s.variavel, s]));
      montarCampos();
    }
    if (preencherCampos) preencher((s) => (ultimas[s.variavel] ? ultimas[s.variavel].valor : null));
    const global = $("nivel-global");
    global.textContent = estado.avaliacao ? estado.avaliacao.nivel : "Sem dados";
    global.className = `selo selo-grande${estado.avaliacao ? ` n-${estado.avaliacao.nivel}` : ""}`;
  } catch (e) {
    console.error(e);
    servidorOk = false;
    mostrarResultado("erro", "Sem conexão com o servidor. Ele está rodando (<code>python -m monitor.servidor</code>)?");
  }
}

async function atualizarPrevia() {
  const leituras = valoresDigitados();
  const seq = ++seqPrevia;
  erroPrevia = "";
  if (!Object.keys(leituras).length) {
    previa = null;
  } else {
    try {
      const r = await fetch("/api/avaliar", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ leituras }),
      });
      const corpo = await r.json();
      if (seq !== seqPrevia) return;
      servidorOk = true;
      if (r.ok) previa = corpo;
      else [previa, erroPrevia] = [null, corpo.erro || `Erro ${r.status}`];
    } catch (e) {
      if (seq !== seqPrevia) return;
      [previa, servidorOk, erroPrevia] = [null, false, "Sem conexão com o servidor: prévia indisponível."];
    }
  }
  renderTudo();
}

function agendarPrevia() {
  clearTimeout(temporizador);
  temporizador = setTimeout(atualizarPrevia, ATRASO_PREVIA_MS);
}

// -- envio e animação dos pacotes (PDUs) -------------------------------------

function pontoNaPoligonal(pontos, t) {
  const trechos = pontos.slice(1).map((p, i) => Math.hypot(p[0] - pontos[i][0], p[1] - pontos[i][1]));
  let resta = t * trechos.reduce((a, b) => a + b, 0);
  for (let i = 0; i < trechos.length; i++) {
    if (resta <= trechos[i] || i === trechos.length - 1) {
      const f = trechos[i] ? Math.min(resta / trechos[i], 1) : 1;
      const [a, b] = [pontos[i], pontos[i + 1]];
      return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
    }
    resta -= trechos[i];
  }
  return pontos[pontos.length - 1];
}

// Move um envelope por trajeto, todos ao mesmo tempo, como no modo simulação do Packet Tracer.
function animarPacotes(trajetos, duracaoMs) {
  if (vista !== "logico" || !trajetos.length) return Promise.resolve();
  const camada = $("camada-pdu");
  const envelopes = trajetos.map(() => {
    camada.insertAdjacentHTML("beforeend", ENVELOPE);
    return camada.lastElementChild;
  });
  return new Promise((resolve) => {
    const inicio = performance.now();
    function quadro(agora) {
      const t = Math.min((agora - inicio) / duracaoMs, 1);
      trajetos.forEach((pontos, i) => {
        const [x, y] = pontoNaPoligonal(pontos, t);
        envelopes[i].setAttribute("transform", `translate(${x.toFixed(1)} ${y.toFixed(1)})`);
      });
      if (t < 1) return requestAnimationFrame(quadro);
      envelopes.forEach((el) => el.remove());
      resolve();
    }
    requestAnimationFrame(quadro);
  });
}

function marcarServidor(ok) {
  const [x, y] = POS.servidor;
  $("camada-pdu").insertAdjacentHTML("beforeend",
    `<text class="marca ${ok ? "ok" : "falha"}" x="${x + 34}" y="${y - 30}">${ok ? "✓" : "✕"}</text>`);
  const marca = $("camada-pdu").lastElementChild;
  setTimeout(() => marca.remove(), 1900);
}

async function enviar(evento) {
  evento.preventDefault();
  const invalido = sensores.find((s) => $(`in-${s.variavel}`).validity.badInput);
  if (invalido) return mostrarResultado("erro", `Valor inválido em “${esc(invalido.nome)}”.`);
  const leituras = valoresDigitados();
  const chaves = Object.keys(leituras);
  if (!chaves.length) return mostrarResultado("erro", "Digite ao menos uma leitura.");

  const botao = $("btn-enviar");
  botao.disabled = true;
  mostrarResultado("", "Enviando…");
  const cabecalhos = { "Content-Type": "application/json" };
  const chave = $("chave-api").value.trim();
  if (chave) cabecalhos["X-Chave-API"] = chave;
  const pedido = fetch("/api/leituras", {
    method: "POST", headers: cabecalhos, body: JSON.stringify({ estacao: ESTACAO, leituras }),
  })
    .then(async (r) => ({ status: r.status, corpo: await r.json().catch(() => ({})) }))
    .catch(() => ({ status: 0, corpo: {} }));

  const animar = vista === "logico" && !movimentoReduzido();
  if (animar) {
    const origens = SENSORES.filter((d) => d.variaveis.some((k) => k in leituras));
    await animarPacotes(origens.map((d) => [POS[d.id], POS[d.ligadoA || "esp32"]]), 700);
    const trechos = [];
    if (origens.some((d) => !d.ligadoA)) trechos.push([POS.esp32, POS.roteador, POS.servidor]);
    if (origens.some((d) => d.ligadoA)) trechos.push([POS.roteador, POS.servidor]);
    await animarPacotes(trechos, 800);
  }
  const { status, corpo } = await pedido;
  const ok = status === 201;
  if (animar && vista === "logico") {
    marcarServidor(ok);
    if (ok) await animarPacotes([[POS.servidor, POS.banco], [POS.servidor, POS.roteador, POS.pc]], 700);
  }
  botao.disabled = false;

  if (ok) {
    const alertas = corpo.alertas_gerados || [];
    const qtd = `${chaves.length} ${chaves.length === 1 ? "variável" : "variáveis"}`;
    mostrarResultado("ok",
      `<p><strong>Leituras gravadas</strong> às ${hora(corpo.instante)} (estação ${ESTACAO}, ${qtd}). ` +
      `Nível global: ${selo(corpo.avaliacao.nivel)}</p>` +
      (alertas.length
        ? `<p>${alertas.length} ${alertas.length === 1 ? "alerta gerado" : "alertas gerados"}:</p>
           <ul class="motivos">${alertas.map((a) => `<li>${selo(a.nivel)} ${esc(a.mensagem)}</li>`).join("")}</ul>`
        : '<p class="detalhe">Nenhum alerta novo.</p>') +
      '<p><a href="/">Ver no dashboard →</a></p>');
    await carregarEstado(false);
    agendarPrevia();
  } else if (status === 401) {
    $("chave").open = true;
    mostrarResultado("erro", "Chave de API inválida ou ausente. O servidor foi iniciado com <code>BARRAGEM_CHAVE_API</code>: " +
      "informe a chave em “Chave de API” e envie de novo.");
  } else if (status === 0) {
    mostrarResultado("erro", "Sem conexão com o servidor. Ele está rodando (<code>python -m monitor.servidor</code>)?");
  } else {
    mostrarResultado("erro", `O servidor recusou o pacote (${status}): ${esc(corpo.erro || "erro desconhecido")}`);
  }
}

// -- eventos -----------------------------------------------------------------

$("vista").addEventListener("click", (e) => {
  const alvo = e.target.closest("[data-id]");
  if (alvo) selecionar(alvo.dataset.id);
});
$("vista").addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const alvo = e.target.closest("[data-id]");
  if (alvo) {
    e.preventDefault();
    selecionar(alvo.dataset.id);
  }
});

document.querySelectorAll("[data-vista]").forEach((aba) =>
  aba.addEventListener("click", () => {
    vista = aba.dataset.vista;
    document.querySelectorAll("[data-vista]").forEach((a) => a.setAttribute("aria-selected", String(a === aba)));
    $("vista").setAttribute("aria-label", vista === "logico" ? "Topologia da estação de monitoramento" : "Corte da barragem com a posição dos sensores");
    $("camada-pdu").innerHTML = "";
    renderLegenda();
    renderCena();
  })
);

$("painel").addEventListener("click", (e) => {
  const botao = e.target.closest("[data-editar]");
  if (!botao) return;
  const campo = $(`in-${botao.dataset.editar}`);
  campo.focus();
  campo.scrollIntoView({ block: "center", behavior: movimentoReduzido() ? "auto" : "smooth" });
});

$("campos").addEventListener("input", (e) => {
  const k = e.target.dataset.variavel;
  if (!k) return;
  if (e.target.type === "range") {
    $(`in-${k}`).value = String(Number(Number(e.target.value).toFixed(escala(porChave[k]).casas)));
  } else {
    sincronizarFaixa(k);
  }
  renderCena();
  agendarPrevia();
});
$("campos").addEventListener("focusin", (e) => {
  const d = dispositivoDaVariavel(e.target.dataset.variavel);
  if (d && d.id !== selecionado) selecionar(d.id);
});

$("btn-ultimas").addEventListener("click", async () => {
  await carregarEstado(true);
  atualizarPrevia();
});
$("btn-base").addEventListener("click", () => {
  preencher((s) => s.base);
  atualizarPrevia();
});
$("form-leituras").addEventListener("submit", enviar);

renderLegenda();
renderCena();
renderPainel();
carregarEstado(true).then(atualizarPrevia);
