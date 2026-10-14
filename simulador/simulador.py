"""Simulador de sensores da barragem.

Gera leituras sintéticas e as envia ao servidor pela mesma API usada pelo
ESP32 (POST /api/leituras), permitindo validar o software sem hardware.

Exemplos:
    # Preenche as últimas 24 h com um cenário de infiltração crescente
    python -m simulador.simulador --cenario infiltracao --modo historico --horas 24

    # Envia uma leitura a cada 2 s, como uma estação real
    python -m simulador.simulador --cenario cheia --modo tempo-real --intervalo 2

Cenários:
    normal      operação estável, oscilações diárias e ruído
    cheia       chuva intensa eleva o reservatório; poropressão e vazão reagem com atraso
    infiltracao percolação crescente (ex.: início de erosão interna); deslocamentos aceleram
    sismo       operação normal com um evento de vibração e pequeno salto de deslocamento
"""

import argparse
import json
import math
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

CENARIOS = ("normal", "cheia", "infiltracao", "sismo")


def suave(p, inicio, fim):
    """Rampa suave de 0 a 1 entre as frações 'inicio' e 'fim' do cenário."""
    if p <= inicio:
        return 0.0
    if p >= fim:
        return 1.0
    x = (p - inicio) / (fim - inicio)
    return x * x * (3 - 2 * x)


def gerar_leitura(cenario, p, hora_do_dia, rng, acumulados):
    """Gera um pacote de leituras para a fração 'p' (0..1) do cenário."""
    ruido = lambda s: rng.gauss(0, s)  # noqa: E731
    ciclo = math.sin(2 * math.pi * (hora_do_dia - 9) / 24)  # máximo por volta das 15 h

    nivel = 10.0 + 0.15 * ciclo
    chuva = max(0.0, 3.0 + ruido(1.5))
    poros = 15.0 + 0.4 * ciclo
    vazao = 18.0 + 0.5 * ciclo
    desloc = 3.0
    recalque = 8.0
    vibracao = abs(ruido(0.003))

    if cenario == "cheia":
        chuva += 110 * math.exp(-((p - 0.35) / 0.12) ** 2)
        subida = suave(p, 0.25, 0.65)
        nivel += 3.6 * subida
        poros += 24 * suave(p, 0.35, 0.80)
        vazao += 34 * suave(p, 0.35, 0.80)
        desloc += 8 * suave(p, 0.45, 0.90)
        recalque += 6 * suave(p, 0.45, 0.90)
    elif cenario == "infiltracao":
        nivel += 1.0 * suave(p, 0.0, 0.3)
        poros += 34 * suave(p, 0.15, 0.95)
        vazao += 60 * suave(p, 0.10, 0.95) ** 1.5
        # Deslocamento cresce devagar e acelera no final (comportamento típico pré-ruptura).
        desloc += 2 + 45 * p ** 4
        recalque += 30 * p ** 3
    elif cenario == "sismo":
        if abs(p - 0.5) < 0.02:
            vibracao = 0.15 + abs(ruido(0.03))
        desloc += 6 * suave(p, 0.5, 0.52)
        recalque += 4 * suave(p, 0.5, 0.52)
        poros += 6 * math.exp(-max(0.0, p - 0.5) * 20) * (p >= 0.5)

    # Deslocamentos são acumulados: nunca diminuem (exceto ruído de leitura).
    acumulados["desloc"] = max(acumulados.get("desloc", 0.0), desloc)
    acumulados["recalque"] = max(acumulados.get("recalque", 0.0), recalque)
    desloc_acum = acumulados["desloc"]

    return {
        "nivel_reservatorio": round(nivel + ruido(0.02), 3),
        "pressao_poros": round(poros + ruido(0.3), 2),
        "vazao_infiltracao": round(max(0.0, vazao + ruido(0.6)), 2),
        "deslocamento_horizontal": round(desloc_acum + ruido(0.1), 2),
        "recalque": round(acumulados["recalque"] + ruido(0.1), 2),
        "chuva_24h": round(chuva, 1),
        # Inclinação aproximada a partir do deslocamento (tubo de inclinômetro de ~3 m).
        "inclinacao": round(math.degrees(math.atan(desloc_acum / 3000.0)) + abs(ruido(0.005)), 3),
        "vibracao": round(vibracao, 4),
        "temperatura": round(24 + 6 * ciclo + ruido(0.4), 1),
    }


def enviar(url, pacote, chave_api=None):
    dados = json.dumps(pacote).encode("utf-8")
    req = urllib.request.Request(url, data=dados, method="POST",
                                 headers={"Content-Type": "application/json"})
    if chave_api:
        req.add_header("X-Chave-API", chave_api)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def main(argv=None):
    ap = argparse.ArgumentParser(description="Simulador de sensores de barragem")
    ap.add_argument("--url", default="http://localhost:8000/api/leituras")
    ap.add_argument("--cenario", choices=CENARIOS, default="normal")
    ap.add_argument("--modo", choices=("historico", "tempo-real"), default="historico")
    ap.add_argument("--horas", type=float, default=24, help="duração simulada (modo histórico)")
    ap.add_argument("--passos", type=int, default=288, help="número de leituras")
    ap.add_argument("--intervalo", type=float, default=2.0, help="segundos entre envios (tempo real)")
    ap.add_argument("--estacao", default="SIM-01")
    ap.add_argument("--chave-api", default=None)
    ap.add_argument("--semente", type=int, default=42)
    args = ap.parse_args(argv)

    rng = random.Random(args.semente)
    acumulados = {}
    inicio = datetime.now(timezone.utc) - timedelta(hours=args.horas)
    ultimo_nivel = None

    for i in range(args.passos):
        p = i / max(args.passos - 1, 1)
        if args.modo == "historico":
            instante = inicio + timedelta(hours=args.horas * p)
        else:
            instante = datetime.now(timezone.utc)
        pacote = {
            "estacao": args.estacao,
            "instante": instante.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "leituras": gerar_leitura(args.cenario, p, instante.hour + instante.minute / 60, rng, acumulados),
        }
        try:
            resposta = enviar(args.url, pacote, args.chave_api)
        except urllib.error.URLError as e:
            print(f"Falha ao enviar para {args.url}: {e}. O servidor está rodando?", file=sys.stderr)
            return 1

        nivel = resposta["avaliacao"]["nivel"]
        if nivel != ultimo_nivel or args.modo == "tempo-real":
            print(f"[{i + 1:4d}/{args.passos}] {pacote['instante']}  índice={resposta['avaliacao']['indice']:.3f}"
                  f"  FS={resposta['avaliacao']['fator_seguranca']}  nível={nivel}")
            ultimo_nivel = nivel
        for alerta in resposta["alertas_gerados"]:
            print(f"      ALERTA [{alerta['nivel']}] {alerta['mensagem']}")
        if args.modo == "tempo-real":
            time.sleep(args.intervalo)

    print("Simulação concluída.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
