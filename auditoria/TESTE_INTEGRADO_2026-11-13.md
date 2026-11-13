# Boundless — Teste integrado e benchmark real (13/11/2026)

## Resumo

A instância completa foi iniciada pelo perfil Boundless do CurseForge em três rodadas relevantes: uma com Boundless Compat habilitado, uma com o guard do JumpAnimation desabilitado e uma nova inicialização habilitada até o menu. Cada execução que chegou ao jogo carregou os **426 JARs** da pasta `mods/`; o Forge registrou **492 mods**.

O lado desabilitado reproduziu o crash original do JumpAnimation ao encerrar o mundo de teste: `Minecraft.gameMode` estava nulo dentro de `isPlayerInSurvival()`. O relatório registra o Mixin do Boundless Compat carregado, mas a configuração estava `false`, portanto o guard não retornou cedo. Na execução habilitada anterior, o jogo entrou no mundo, o comando de diagnóstico funcionou e as transições testadas terminaram sem esse crash. Essa execução, porém, não registrou `guard triggered=true`; assim, a evidência favorece a correção, mas não prova que o guard foi acionado naquele caso.

A nova execução habilitada também chegou ao menu. Não consegui entrar no mundo nessa tentativa porque a automação do Windows deixou de capturar a janela do Minecraft (`Accessibility state unavailable for window 4852028`). Os logs confirmam a inicialização completa. A janela ficou no menu ao encerrar a coleta.

## Ambiente e metodologia

- Minecraft 1.20.1, Forge 47.4.28, Microsoft OpenJDK 17.0.15.
- Heap do launcher: `-Xmx8192m` (8 GiB); RAM física: 11,91 GiB.
- Intel Core i5-6600, quatro núcleos; AMD Radeon RX 480, OpenGL 4.6.
- Resolução 1024×768, render distance 7, gráficos Fancy.
- Perfil e argumentos de execução do CurseForge foram reutilizados. Nenhum mod foi removido ou atualizado.
- Os testes usaram o mundo descartável `BC-Test-20261113-1526`; nenhum save pessoal foi aberto.
- Oculus mostrou `Shaderpack: (off) (fallback)`, apesar da configuração local indicar o shader MakeUp habilitado. A configuração não foi alterada e não há resultado de benchmark com shader.
- Os tempos abaixo são os informados pelo Minecraft/Forge. Eles variaram bastante entre execuções e não isolam a causa da diferença.

## Inicialização

| Rodada | Guard | Até o menu | Menu até o mundo | Total até o mundo | Resultado |
|---|---|---:|---:|---:|---|
| run3 — Compat corrigido | habilitado | 420,649 s | 229,196 s | 649,845 s | Entrou no mundo e executou diagnóstico |
| run4 — A/B | desabilitado | 675,652 s | 324,959 s | 1000,611 s | Entrou no mundo; NPE do JumpAnimation no encerramento |
| run5 — repetição habilitada | habilitado | 918,645 s | — | — | Chegou ao menu; controle da janela falhou antes de entrar no mundo |

A execução habilitada mais recente demorou mais que as anteriores, mas esse dado isolado não demonstra regressão do Boundless Compat. As rodadas não foram repetições controladas com cache, carga do sistema e estados internos idênticos.

## Boundless Compat e JumpAnimation

Em run3, o log detectou JumpAnimation 2.0.0 e selecionou o patch. `/boundless diagnose` confirmou Boundless Compat 0.1.0, Forge 47.4.28, Java 17.0.15, JumpAnimation 2.0.0, `config=true` e `version gate=SUPPORTED_VERSION`. O comando reportou `guard triggered=false`. O cliente sobreviveu às transições de pausa/retorno e ao retorno ao título registrados nessa rodada.

Em run4, o arquivo de configuração estava deliberadamente em `jumpAnimationNullGameModeGuard = false`. O comando confirmou `config=false`, JumpAnimation 2.0.0 e gate compatível. Depois de “Salvar e Sair”, a tela permaneceu em `Saving world`; o log parou em `Saving chunks` às 18:10:30. A janela ficou sem responder por cerca de 11 minutos e então o crash report de 18:21:59 registrou:

```text
NullPointerException: MultiPlayerGameMode ... is null
JumpAnimationClient.isPlayerInSurvival(JumpAnimationClient.java:432)
JumpAnimationClient.onKeyInput(JumpAnimationClient.java:243)
Description: mouseClicked event handler
```

O stack mostra `boundlesscompat.mixins.json:jumpanimation.JumpAnimationNullGameModeMixin` na classe transformada. Como o toggle estava falso, a injeção não interrompeu o helper e o defeito original ocorreu. Este é um controle negativo reproduzível para a configuração desligada. O relatório do Crash Assistant também identifica JumpAnimation 2.0.0 como mod suspeito; FPS Reducer aparece no caminho do evento de mouse, mas o dereference que lançou a exceção é do JumpAnimation.

Run5 iniciou novamente com o toggle em `true`; o log registrou “JumpAnimation 2.0.0 detected; enabling Boundless null-gameMode guard” e o menu carregou. A ferramenta não permitiu a segunda entrada no mundo. Portanto, o teste de execução habilitada que chegou ao mundo continua sendo run3, e o cenário exato do NPE só caiu com o guard desligado.

O erro anterior de inicialização `IllegalClassLoadError` do helper dentro do pacote Mixin não reapareceu depois da recompilação.

## FPS e frametime

As leituras do F3 são amostras pontuais em momentos distintos, não uma sessão padronizada. Não é possível inferir FPS médio estável, mínimo representativo, 1% low nem p95/p99 de frametime.

| Rodada / hora | FPS | Tick do servidor integrado | GPU no F3 | Heap usado |
|---|---:|---:|---:|---:|
| run3 16:33:21 | 17 | 110 ms | 3% | 4,85 GiB |
| run3 16:35:31 | 21 | 54 ms | 0% | 4,57 GiB |
| run3 16:35:56 | 38 | 41 ms | 3% | 6,79 GiB |
| run3 16:37:07 | 7 | 611 ms | 6% | 4,16 GiB |
| run3 16:41:55 | 46 | 126 ms | 2% | 5,73 GiB |
| run3 16:44:24 | 66 | 90 ms | 5% | 4,87 GiB |
| run4 17:37:14 | 20 | 655 ms | — | 4,38 GiB |
| run4 17:43:27 | 17 | 96 ms | 3% | 4,28 GiB |
| run4 17:44:25 | 10 | 86 ms | 1% | 7,20 GiB |
| run4 17:52:58 | 3 | 320 ms | 0% | 6,09 GiB |
| run4 18:09:36 | 56 | 49 ms | 4% | 6,77 GiB |

Nenhuma captura mediu VRAM. A utilização de GPU mostrada pelo F3 ficou baixa nas amostras, mas isso não identifica sozinha o limite de desempenho. Não foram coletados cenários comparáveis de combate, deslocamento por chunks novos ou renderização com shader. Não há evidência de 60–70 FPS estáveis.

## Servidor integrado e JFR

Os tempos de tick foram severos nas duas configurações, mas as janelas não são comparáveis o bastante para atribuir diferenças ao Compat:

| Captura | Janela e amostras | `ServerTickTime` |
|---|---|---|
| run3, parado, guard habilitado | 61 s; 51 amostras | média 598,5 ms; mediana 238,2 ms; p95 4,220 s; máximo 4,620 s |
| run4, parado, guard desabilitado | 73 s; 50 amostras | média 1.777,3 ms; mediana 736,9 ms; p95/máximo 6,234 s |
| run4, após stalls | 184 s; 41 amostras de execução do servidor; um evento `ServerTickTime` | evento com média de 14,184 s; sem eventos de GC ou geração de chunks nessa janela |

São amostras do JFR, não uma medição completa de cada tick. No JFR de run3, ocorreram cinco pausas de GC; a maior foi 2,18 s. Não houve evento de geração de chunks na janela estacionária.

Os stalls também aparecem no log:

- run3: watchdog ModernFix de 40,001 s; Forge reportou 250,015 s / 5.000 ticks de atraso.
- run4: watchdog ModernFix de 49,606 s e depois 69,065 s; Forge reportou 333,339 s / 6.666 ticks e 246,536 s / 4.930 ticks de atraso.

Capturas de threads encontraram stacks diferentes: run3 passou por `HashMap.resize → CompoundTag → ForgeRegistry$Snapshot.write` durante gravação de dados; run4 mostrou uma aranha em colisões de blocos via `ClimberComponent` e, em outra captura, um zumbi em `MoveControl`. As amostras apontam caminhos de salvamento e ticks de entidades para investigar. Como são stacks distintas e amostras isoladas, não confirmam um mod único como causa.

## Outros problemas observados

- A falha de transformação Forge `coremods/field_to_method.js function biome` reapareceu durante o carregamento.
- Persistiu a injeção de variável local incompatível em `fabric-object-builder-v1.mixins.json:TradeOffersTypeAwareBuyForOneEmeraldFactoryMixin`; o log também informou registro de trades. Não houve validação funcional de ofertas.
- Persistiu `NoSuchFieldException: byName` na tentativa de tratar receitas de scroll.
- O reload de recursos voltou a registrar índices de frame inválidos do Born in Chaos e um blockstate do Torchmaster sem modelo/variants.
- Esses avisos não impediram as execuções que chegaram ao menu; o impacto em conteúdo não foi medido.

## Cobertura e limites

- Foi possível executar o pack completo, carregar o mundo descartável, executar `/boundless diagnose` e registrar JFR, logs, crash reports e capturas de threads.
- O A/B observou o NPE somente com o guard desligado. A rodada habilitada completa não registrou `guard triggered=true`; por isso, o efeito do guard sob o estado nulo não foi diretamente confirmado pelo diagnóstico.
- Não foram obtidos TPS sustentados por Spark, MSPT p95/máximo de uma série completa, frametimes, 1% low ou VRAM.
- Não foram concluídos benchmarks controlados para exploração, chunks inéditos, combate ou shader ligado. O desempenho não permite prometer estabilidade em 60–70 FPS.
- O ambiente de automação não conseguiu capturar a janela do Minecraft depois de a nova rodada habilitada chegar ao menu. O log da rodada e as evidências anteriores foram preservados; o jogo ficou aberto no menu.

Os logs integrais, JFRs, crash report e dumps de threads permanecem localmente em `auditoria/testes/2026-11-13/`. O relatório versionado resume os resultados sem incluir esses artefatos brutos.

## Prioridades recomendadas

1. **Confirmar o guard habilitado no mesmo evento:** repetir entrada no mundo, diagnóstico antes e depois de “Salvar e Sair” e verificar se `guard triggered` muda para `true`.
2. **v0.2 — conteúdo:** corrigir os frames do Born in Chaos e investigar modelos de Grottol, blockstate do Torchmaster, receitas, trades/avanços, loot tables e tags. Usar datapacks/resourcepacks internos quando bastarem.
3. **v0.3 — diagnóstico de desempenho:** repetir JFR/Spark com coleta abrangendo o começo e o fim dos stalls; medir entidades, salvamento de dados e geração de chunks antes de atribuir causa.
4. **v0.4 — otimizações:** atuar nos gargalos demonstrados, preservando worldgen, entidades, efeitos visuais, animações e mecânicas do RPG.
