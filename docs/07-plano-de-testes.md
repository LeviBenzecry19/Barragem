# 7. Plano de testes e indicadores

## 7.1 Testes automatizados

```bash
python -m unittest discover -s tests -t .
```

| Arquivo | O que verifica |
|---|---|
| `tests/test_analise.py` | Fórmulas (pressão hidrostática, tensão efetiva, FS), normalização, classificação, pesos, regras de sobreposição. |
| `tests/test_sistema.py` | Gravação no banco, avaliação com última leitura de cada sensor, geração e deduplicação de alertas, validação de dados, API HTTP, cenários simulados. |

## 7.2 Indicadores da proposta × como medir

| Indicador | Como é avaliado |
|---|---|
| Comunicação entre sensores e software | Simulador e ESP32 enviam pacotes; o servidor responde `201`. Teste `TestAPI.test_fluxo_completo`. |
| Registro correto dos dados | Leituras gravadas e recuperadas pelo histórico (`test_registra_e_avalia`). |
| Visualização em gráficos | Dashboard com gráfico por variável (com limites) e do índice. Verificação manual. |
| Geração de alertas | `test_alerta_ao_subir_de_nivel`, `test_sem_alerta_repetido_enquanto_pendente`, `test_novo_alerta_apos_reconhecer`. |
| Detecção de alterações simuladas | `TestCenariosSimulados`: normal permanece Normal; cheia chega a Alerta; infiltração chega a Crítico; sismo gera alerta. |
| Tempo de resposta | Medir o tempo de `POST /api/leituras` (ver 7.3) e o intervalo de atualização do dashboard (5 s). |

## 7.3 Medindo o tempo de resposta

Com o servidor rodando:

```bash
python - <<'EOF'
import json, time, urllib.request
corpo = json.dumps({"leituras": {"pressao_poros": 20, "nivel_reservatorio": 10}}).encode()
tempos = []
for _ in range(100):
    r = urllib.request.Request("http://localhost:8000/api/leituras", data=corpo,
                               headers={"Content-Type": "application/json"})
    t0 = time.perf_counter(); urllib.request.urlopen(r).read(); tempos.append(time.perf_counter() - t0)
tempos.sort()
print(f"mediana {tempos[50]*1000:.1f} ms  ·  p95 {tempos[95]*1000:.1f} ms")
EOF
```

## 7.4 Roteiro de teste manual com hardware

1. Ligar a estação e confirmar no Monitor Serial que os pacotes são enviados.
2. Encher o reservatório do modelo físico e verificar o aumento do nível no dashboard.
3. Elevar a coluna d'água do piezômetro e observar a queda do FS.
4. Aumentar a vazão no dreno e verificar o alerta da vazão.
5. Deslocar manualmente a haste do potenciômetro e verificar deslocamento/alertas.
6. Bater levemente na base do MPU-6050 e verificar o alerta de vibração.
7. Desligar o Wi-Fi por alguns minutos e confirmar o reenvio dos pacotes da fila.
