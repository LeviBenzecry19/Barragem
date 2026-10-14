"""Parâmetros do sistema de monitoramento.

ATENÇÃO: todos os limites, pesos e parâmetros geotécnicos abaixo são
EXPERIMENTAIS e ILUSTRATIVOS, definidos para uma barragem de terra fictícia
de ~15 m de altura usada no protótipo. Eles fazem parte da metodologia do
projeto acadêmico e NÃO são valores normativos de engenharia. Em uma barragem
real, os limites de controle de cada instrumento são definidos pelo projetista
/ responsável técnico, a partir do projeto, do histórico de leituras e das
análises de estabilidade (ver docs/03-metodologia-analise.md).
"""

from dataclasses import dataclass

# Níveis de classificação, em ordem crescente de severidade.
NIVEIS = ["Normal", "Atenção", "Alerta", "Crítico"]


@dataclass(frozen=True)
class Variavel:
    chave: str
    nome: str
    unidade: str
    equipamento: str
    # Limites de controle (valores crescentes): referência, atenção, alerta, crítico.
    base: float
    atencao: float
    alerta: float
    critico: float
    # Peso no índice de risco (0 = variável monitorada, mas fora do índice).
    peso: float = 0.0
    descricao: str = ""


VARIAVEIS = {
    v.chave: v
    for v in [
        Variavel(
            "nivel_reservatorio", "Nível do reservatório", "m", "Sensor de nível",
            base=10.0, atencao=12.0, alerta=13.0, critico=14.0, peso=0.15,
            descricao="Carga hidráulica sobre a estrutura (crista a 15 m).",
        ),
        Variavel(
            "pressao_poros", "Pressão de poros", "kPa", "Piezômetro",
            base=15.0, atencao=25.0, alerta=35.0, critico=45.0, peso=0.25,
            descricao="Pressão da água nos poros do maciço, no talude de jusante.",
        ),
        Variavel(
            "vazao_infiltracao", "Vazão de infiltração", "L/min", "Medidor de vazão",
            base=20.0, atencao=35.0, alerta=50.0, critico=70.0, peso=0.20,
            descricao="Vazão de percolação coletada no dreno de pé.",
        ),
        Variavel(
            "deslocamento_horizontal", "Deslocamento horizontal", "mm", "Inclinômetro",
            base=5.0, atencao=15.0, alerta=25.0, critico=40.0, peso=0.20,
            descricao="Deslocamento horizontal acumulado do talude.",
        ),
        Variavel(
            "recalque", "Recalque", "mm", "Marco / medidor de recalque",
            base=10.0, atencao=25.0, alerta=40.0, critico=60.0, peso=0.10,
            descricao="Deslocamento vertical acumulado da crista.",
        ),
        Variavel(
            "chuva_24h", "Chuva acumulada (24 h)", "mm", "Pluviômetro",
            base=10.0, atencao=50.0, alerta=80.0, critico=120.0, peso=0.05,
            descricao="Precipitação acumulada nas últimas 24 horas.",
        ),
        Variavel(
            "inclinacao", "Variação de inclinação", "°", "Inclinômetro / tiltímetro",
            base=0.1, atencao=0.5, alerta=1.0, critico=2.0, peso=0.05,
            descricao="Variação angular em relação à leitura inicial.",
        ),
        Variavel(
            "vibracao", "Aceleração de pico", "g", "Acelerômetro",
            base=0.01, atencao=0.05, alerta=0.10, critico=0.20, peso=0.0,
            descricao="Evento sísmico/vibração. Fora do índice; gera alertas próprios.",
        ),
        Variavel(
            "temperatura", "Temperatura", "°C", "Termômetro",
            base=30.0, atencao=40.0, alerta=50.0, critico=60.0, peso=0.0,
            descricao="Temperatura ambiente/sensores. Usada para contexto e diagnóstico.",
        ),
    ]
}

# Faixas do índice de risco (0 a 1). Coincidem com a normalização das
# variáveis: atenção -> 0,25; alerta -> 0,50; crítico -> 0,75.
FAIXAS_INDICE = [(0.25, "Normal"), (0.50, "Atenção"), (0.75, "Alerta")]  # >= 0,75: Crítico

# Faixas do fator de segurança (FS). Abaixo de cada valor, o nível indicado.
# Referência: FS mínimo usual de 1,5 para percolação permanente.
FAIXAS_FS = [(1.1, "Crítico"), (1.3, "Alerta"), (1.5, "Atenção")]

# Parâmetros geotécnicos do talude de jusante (modelo de talude infinito).
GEOTECNIA = {
    "peso_especifico_solo": 19.0,      # γ  (kN/m³)
    "profundidade_ruptura": 5.0,       # z  (m) profundidade da superfície de ruptura / piezômetro
    "inclinacao_talude_graus": 21.8,   # β  (°) talude 1V:2,5H
    "coesao_efetiva": 15.0,            # c' (kPa)
    "angulo_atrito_graus": 32.0,       # φ' (°)
}

DENSIDADE_AGUA = 1000.0   # ρ (kg/m³)
GRAVIDADE = 9.81          # g (m/s²)
