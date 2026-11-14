# Boundless Compat — resolução P0 e P1 — 2026-11-13

## Resultado

- **P0 — aplicação do Mixin comprovada; cenário Save and Quit e acionamento do guard ainda não comprovados.** A build 0.1.1 confirmou no log que o Mixin foi aplicado ao método esperado. Não há registro de `Intercepted ... gameMode was null`, portanto não afirmo que a condição foi interceptada nem que o NPE foi evitado no cenário original.
- **P1 — diagnóstico multicausal, sem correção de desempenho segura comprovada.** As capturas mostram trabalho ativo na thread do servidor em subsistemas diferentes, sem um método ou mod dominante. Não foi aplicado patch de TPS e não há ganho antes/depois a declarar.
- A versão 0.1.1 foi compilada, passou nos quatro testes unitários e foi instalada em `mods`. A versão anterior foi preservada em `run6-live-v010-in-world`.

## P0 — JumpAnimation 2.0.0

### Código e comportamento

O Mixin em [`JumpAnimationNullGameModeMixin.java`](../development/boundless-compat/src/main/java/com/satoshoidaemon/boundlesscompat/compat/jumpanimation/JumpAnimationNullGameModeMixin.java) injeta no início de `com.saltywater.jumpanimation.JumpAnimationClient.isPlayerInSurvival(LocalPlayer)`, é cancelável e selecionado apenas para `jumpanimation` versão `2.0.0`. Lê `Minecraft.getInstance().gameMode` antes do método original. Quando a opção está ativa e o campo é nulo, registra o acionamento e retorna `false`; nos outros casos não cancela a chamada. Assim, com `gameMode` válido, a execução original de JumpAnimation permanece intacta.

O predicado isolado está em [`JumpAnimationGuard.java`](../development/boundless-compat/src/main/java/com/satoshoidaemon/boundlesscompat/runtime/JumpAnimationGuard.java). A 0.1.1 acrescenta contagem/log de acionamentos, registro em `postApply` e detalhes em `/boundless diagnose`; não altera a condição nem o caminho normal da animação. A opção `jumpAnimationNullGameModeGuard` estava `true`.

### Evidência disponível e limite

No boot da 0.1.1, o log registra:

- `20:47:42`: `JumpAnimation 2.0.0 detected; enabling Boundless null-gameMode guard.`
- `20:48:23`: `Applied Boundless null-gameMode guard to com.saltywater.jumpanimation.JumpAnimationClient.isPlayerInSurvival(LocalPlayer).`

Essas linhas comprovam seleção e aplicação no runtime. A captura [`latest-v0.1.1-startup.log`](testes/2026-11-13/run7-p0-v011-startup/latest-v0.1.1-startup.log) não contém a linha de interceptação, e o mundo não chegou a ser aberto nesta tentativa.

A execução anterior com o guard desativado reproduziu o NPE em `Minecraft.gameMode` nulo dentro de `JumpAnimationClient.onKeyInput`; o stack contém o Mixin do Boundless Compat. Consulte [`crash-2026-11-13_18.21.48-client.txt`](../crash-reports/crash-2026-11-13_18.21.48-client.txt) e os logs das execuções anteriores. Isso confirma o caso original com o guard desativado, mas não é evidência de interceptação com ele ativado.

Após o boot da 0.1.1, a automação de interface expirou: primeiro `js execution timed out; kernel reset`; a única renovação de estado falhou com `Native apps: Error: computer-use request timed out: list_apps`. A instrução do skill `computer-use` exige parar a automação após essa segunda falha. Por isso não executei Esc → Save and Quit, não consultei `/boundless diagnose` dentro do mundo e não classifico a ausência do NPE como validada. O cliente foi deixado aberto no menu principal.

### Testes e artefato

`gradlew --no-daemon -Dorg.gradle.jvmargs=-Xmx1G build` concluiu com `BUILD SUCCESSFUL`; a suíte contém quatro casos, todos aprovados (0 falhas, 0 erros), cobrindo nulo com guard ligado, estado normal com guard ligado e os dois estados com guard desligado. Relatório JUnit: [`TEST-com.satoshoidaemon.boundlesscompat.runtime.JumpAnimationGuardTest.xml`](../development/boundless-compat/build/test-results/test/TEST-com.satoshoidaemon.boundlesscompat.runtime.JumpAnimationGuardTest.xml).

JAR instalado: [`boundlesscompat-0.1.1.jar`](../mods/boundlesscompat-0.1.1.jar), SHA-256 `61950F6FEC62D81E0F73D5DCB0E83705DF9DF8086985BFD714EE018CDC0595F4`. O JAR 0.1.0 removido da pasta de carregamento foi preservado como [`boundlesscompat-0.1.0-installed-original.jar`](testes/2026-11-13/run6-live-v010-in-world/boundlesscompat-0.1.0-installed-original.jar).

## P1 — stalls do servidor integrado

### Métricas observadas

| Captura | `ServerTickTime` | Média | Mediana | p95 | Máximo |
|---|---:|---:|---:|---:|---:|
| `run3-compat-fixed/stationary.jfr` (61 s) | 51 | 598,5 ms | 238,2 ms | 4,22 s | 4,62 s |
| `run4-compat-disabled/stationary.jfr` (73 s) | 50 | 1,777 s | 736,9 ms | 6,23 s | 6,23 s |
| `run4-compat-disabled/after-stall.jfr` (184 s) | 1 | — | — | — | 14,2 s |
| `run6-live-v010-in-world/live-180s.jfr` (213 s) | 146 | 4,798 s | 1,010 s | 28,2 s | 33,3 s |

A última linha resume o campo `averageTickDuration` dos 146 eventos amostrados pelo JFR; não é uma distribuição completa de todos os ticks individuais. Nessa captura, 142/146 amostras excedem 50 ms, 75 excedem 1 s e 22 excedem 10 s. Os logs anteriores ainda registram atrasos acumulados de até 333,339 s e, em `20:19:54`, o ModernFix integrated server watchdog relatou um tick de `204284 ms`. As advertências `Can't keep up` variam de cerca de 11 s a 94 s nesse trecho.

### CPU, espera, GC e subsistemas

- A captura ao vivo contém 2.865 `ExecutionSample`, dos quais 1.356 são da `Server thread`. Entre as pilhas mais frequentes estão leitura de `PalettedContainer`/`LevelChunk` (50 amostras), consulta de entidades em `EntitySectionStorage` (17), atualização de `ChunkHolder`/`ServerChunkCache` (15), `DistanceManager` (12), mapas de entidades/chunks, tags e colisões multipart (cerca de 10 cada). Cada grupo é uma fração pequena da amostra da thread; não aponta um culpado único.
- O thread dump de run6 encontra a `Server thread` em estado `RUNNABLE`, executando `EntitySelector`/`EntityLookup` a partir de `FunctionCallback → TimerQueue`. É uma consulta de entidade disparada por uma função agendada, mas o dump não identifica o autor nem a função. A busca nos datapacks e scripts do diretório da instância não encontrou função `@e` correspondente. Uma stack isolada não justifica atribuir culpa ou adicionar patch.
- O JFR não registrou eventos `minecraft.ChunkGeneration` nessa captura. Ainda há amostras de manutenção/obtenção de chunks; não há evidência suficiente para atribuir os stalls a geração inicial, e o evento ausente não prova que nunca haja geração fora da janela.
- Há apenas 17 amostras `ThreadCPULoad` da thread do servidor (média `user=1,88%`, máximo `7,77%`), insuficientes para uma estimativa robusta de ocupação. Em contraste, a thread aparece em 1.356 pilhas executáveis. Entre 10.168 `ThreadPark` e 2.009 `JavaMonitorWait` do processo inteiro, só um park pertence à `Server thread` (10,6 ms), sem espera longa registrada nela. A evidência favorece trabalho ativo do tick a bloqueio prolongado, com a ressalva da amostragem esparsa de CPU.
- Foram registrados três ciclos principais de GC: duas pausas G1 Young de 72 e 144 ms e um ciclo G1 Old com duração total de 67 s. Para esse ciclo antigo, `sumOfPauses=38,4 ms` e a maior pausa foi 37,6 ms; portanto os 67 s não são 67 s de stop-the-world. As pausas somadas são aproximadamente 254 ms durante os 213 s de captura. GC pode competir por CPU, mas as pausas observadas não explicam stalls de dezenas ou centenas de segundos.
- Os 4.849 `ObjectAllocationSample` são amostras ponderadas, não uma contagem exata de bytes. Há alocações amostradas em file watchers e na thread watchdog do ModernFix ao montar dumps; isso pode refletir diagnósticos disparados pelos stalls e não estabelece causa raiz.
- No boot da 0.1.1, que levou 665,204 s até o menu, o working set do cliente chegou a cerca de 7,1 GiB num sistema com 11,9 GiB de RAM; a memória livre chegou a 0,12 GiB. Interrompi processos secundários de CurseForge, mantendo o Java do jogo e o Minecraft Launcher ativos; depois disso a memória livre ficou entre 0,62 e 1,12 GiB. É pressão durante carregamento inicial, não uma medição de tick estável. Não alterei Xmx. O boot também marcou `disableWarnings=true`; restaurei `config/memorysettings.json` para o valor anterior (`false`) e restaurei os arquivos que só tinham timestamps ou uma quebra de linha adicionada. O `minecraftinstance.json` foi mantido com a referência ao JAR instalado 0.1.1.
- Os dumps antigos também divergem entre serialização de `ForgeRegistry$Snapshot`/`CompoundTag`, colisão em `CubeVoxelShape` com `ClimberComponent.updateWalkingSide` e lógica vanilla `MoveControl` de zumbi. São caminhos distintos, coerentes com gargalos múltiplos.

### Decisão de intervenção

Não alterei spawn, quantidade de mobs, distância de visão, shaders, geração de estruturas ou conteúdo. Também não acrescentei cache ou patch genérico para consultas de chunks/entidades: as amostras são distribuídas entre caminhos diferentes e não sustentam uma otimização segura específica. Assim, P1 fica **inconclusivo quanto à correção**, sem medição antes/depois e sem ganho inventado. O perfil/JFR e os dumps originais foram preservados em `testes/2026-11-13`; a captura de 213 s é [`live-180s.jfr`](testes/2026-11-13/run6-live-v010-in-world/live-180s.jfr) e o dump correspondente é [`thread-dump-before-jfr.txt`](testes/2026-11-13/run6-live-v010-in-world/thread-dump-before-jfr.txt).

## Estado do workspace

Não houve commit nem push. As alterações de `config/cinematic_respawn.properties` e `minecraftinstance.json` foram preservadas sem edição nesta resolução. O servidor integrado ainda precisa de um teste interativo reproduzível com 0.1.1 para completar o critério P0; a tela de Save and Quit e a confirmação visual das animações normais não foram alcançadas nesta sessão.
