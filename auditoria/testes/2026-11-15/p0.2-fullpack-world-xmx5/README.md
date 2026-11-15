# Full pack — novo mundo e capturas Xmx5

Clone offline, Minecraft 1.20.1 / Forge 47.4.28, Oracle JDK 17.0.12, 439 JARs diretos e 508 mods carregados. Xms 1 GiB / Xmx 5 GiB. Seed `20261115`, mundo clone `P02-Xmx5-20261115`, survival/normal. Nenhum save original foi aberto. O processo salvou o mundo e encerrou normalmente; não houve linha `[ERROR]` no log.

## Startup, memória e GC

- ModernFix registrou 328,172 s até o menu.
- 416 amostras de processo: Private Bytes p95/pico 9,83/10,29 GiB; working set 6,57/6,87 GiB; RAM física livre mínima 277 MiB (mediana 609 MiB).
- GC log durante aproximadamente 37 min: 1.510 registros de pausa, 54,06 s acumulados, p95 93,208 ms, p99 238,704 ms, pico 4.052,753 ms. Inclui o período de preparação do mundo e não é uma sessão GC estacionária.

## Simulação e carregamento

A amostra `/boundless perf` cobriu 523 ticks em 334,6 s durante a preparação do novo mundo: média MSPT 597,20, p50 230,98, p95 1.572,96, p99 4.916,34 e máximo 57.295,39; TPS equivalente médio 1,67. Os avisos de backlog variaram de 2,205 s até 172,371 s e continuaram em dezenas de segundos por vários minutos.

O `world-catchup-xmx5.jfr` cobre 240 s a partir de aproximadamente 16:42:57 local e contém 233 médias intervalares `minecraft.ServerTickTime`: média 143,74 ms, p95 281 ms, p99 395 ms e máximo 436 ms. Não há eventos `minecraft.ChunkGeneration`. Os valores são de catch-up/geração inicial, não de mundo estacionário. A sessão integrada durou menos de 30 min, então o critério de integração ainda está pendente.

## PresentMon exploratório

A captura de aproximadamente 120 s tem 4.268 intervalos: média 35,58 FPS, frametime p95/p99 36,89/124,64 ms, 1% low 1,26 FPS, 0,1% low 0,21 FPS e máximo 14,06 s; cinco intervalos passaram de 1 s. Cena, foco e estado dos shaders não foram anotados e houve interação com telas/backlog durante a captura. **Não use estes números como comparação shader on/off ou como benchmark visual válido.** O CSV preserva as linhas originais.

## Arquivos versionados nesta captura

- `latest.log`: saída completa do cliente/servidor integrado.
- `gc.log`: log de GC.
- `process-metrics.csv`: série de memória/processo.
- `frametime-world.csv`: CSV original do PresentMon.

JFRs grandes ficaram no diretório local ignorado `downloads/p0.2-fullpack-xmx6-20261115` para não acrescentar mais de 100 MiB de binários ao repositório. Os JFRs `startup-xmx5.jfr`, `world-entry-xmx5.jfr` e `world-catchup-xmx5.jfr` têm, respectivamente, 53.134.118, 33.306.412 e 29.378.207 bytes; SHA-256: `9acab352e53d38a640765d0ea537021edd6b72f51d5324b7e807757cd450677a`, `731f32a904d3e53796e5e637b208e9639cf98f1aba40c7278ba710fd7b791773` e `d48fea3f5c90467112e120f18a70e9291a1da8d051e36b38034528500e6a4a40`. O JFR de catch-up foi consultado para as métricas acima; os outros dois ficam preservados localmente, sem análise detalhada nesta rodada.

O CSV PresentMon tem SHA-256 `6da61c6332857477d324502efaa5457bb7a87c0f8d14e2250b38da46ec2c23da`; a série de memória, `acacf85c0639d64bb35a46f1fd02ef4a1c2dc9f8ab1077e042f9b382bf241d28`; GC log, `622bc28c0bad997e8502b959c7e9ca3a37d9a2c03bff3c898548cf5d67bb21a9`; log, `290c5bc568e93647fd896bdf64f5419de6b7fe280a2eb97f80dd47f9a82c9622`.
