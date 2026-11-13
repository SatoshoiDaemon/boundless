# Validação dos fatores do Formations Nether — 04/10/2026

Alteração permanente autorizada: somente `formationsnether:common` e
`formationsnether:ore_shards`, de 0.5 para 1 em `config/sparsestructures.json5`.
O fator global, POIs, dungeons e todos os mods são preservados.

## Método

- Cópia de `saves/Teste 14`, com a mesma seed e os mesmos mods.
- O Nether copiado foi movido para esta pasta, para forçar geração nova
  **somente na cópia**. Nenhum arquivo do mundo original foi modificado.
- Datapack temporário somente na cópia: constrói um portal junto ao jogador,
  aguarda a transição normal e registra quando o servidor voltou a executar
  ticks no Nether. A meta seguinte é completar 1200 ticks (60 s a 20 TPS).
- Entrada automática pelo Freesm Launcher, offline, com o nome AxiomSealed.
- `pauseOnLostFocus=false` temporário, para não pausar o teste sem foco.
- Distância de renderização 16 e de simulação 18, sem mudanças.

Hash original de `Teste 14/level.dat` antes dos testes:
`70193071cf9d4660b2b156f10622d0b798c19bd325ba438a6db37c46c8202f6f`.
Mtime original: `2026-10-04 22:34:28.304883039 -0300`.

## Primeira execução

- Preparação do Overworld: 82093 ms.
- Portal iniciado às 22:47:14.325.
- Transição concluída às 22:47:41.140: aproximadamente 26.8 segundos.
- Sem aviso de tick acima de 40 s até a interrupção.
- O limite original era 260 FPS; a CPU atingiu 91 °C. SIGTERM foi enviado,
  mas o servidor ainda gerava chunks durante o encerramento. O processo
  de teste foi então interrompido à força, somente na cópia.
- Não completou os 1200 ticks de estabilidade. Não é validação completa.
- Logs: `first-run-latest.log`, `first-run-debug.log`; cópia: `first-test-save`.

## Segunda execução

Nova cópia do mesmo mundo, com Nether novamente sem chunks pré-gerados.
Limite de FPS temporário de 60, para reduzir carga gráfica durante a
validação; não constitui uma mudança permanente solicitada pelo usuário.
Esta repetição atingiu o corte automático de 88 °C ainda na inicialização
e foi interrompida antes de entrar no mundo. Portanto, não validou a
estabilidade do Nether a 60 FPS. Logs: `second-run-latest.log` e
`second-run-debug.log`; cópia: `second-test-save`.

## Resultado final

As duas alterações permanentes de fator foram aplicadas e a configuração
foi conferida. A primeira execução confirmou a transição normal pelo portal
em aproximadamente 26.8 s, sem aviso do watchdog. O teste de estabilidade
prolongada NÃO foi concluído devido à temperatura. Não é possível declarar
o problema de geração inteiramente resolvido nem o modpack estável.

FPS restaurado para 260 e `pauseOnLostFocus` restaurado para true. Todos os
mods foram mantidos. As cópias foram arquivadas nesta pasta, fora da lista de
mundos do launcher. O hash e o mtime de `Teste 14/level.dat` permaneceram
idênticos aos valores anteriores. Não houve alteração no patch de HUD.

## Limites

Este teste não cobre exploração contínua de grandes áreas ou todas as seeds.
Erros de colocação de `projectvibrantjourneys:charred_bones` continuam
aparecendo. Não foram suprimidos nem corrigidos neste ajuste.
