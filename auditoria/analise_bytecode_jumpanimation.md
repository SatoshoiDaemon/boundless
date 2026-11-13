# JumpAnimation 2.0.0 — análise do bytecode

## Escopo e método

Arquivo instalado: `mods/jumpanimation-2.0.0-1.20.1.jar`. O JAR não inclui código-fonte Java. Descompilei localmente as classes com CFR 0.152 e comparei o caminho com o stack trace do crash. A versão correspondente do código-fonte não foi encontrada nas páginas públicas do projeto consultadas; portanto, a conclusão de implementação vem do bytecode do JAR instalado, não de um checkout do repositório.

## Fluxo observado

| Etapa | Evidência no JAR | Consequência |
|---|---|---|
| Inicialização | O construtor da classe `Jumpanimation` verifica `Dist.CLIENT` e chama `JumpAnimationClient.registerClient()`. | O listener é criado apenas no cliente. |
| Registro | `registerClient()` registra um `JumpAnimationClient` em `MinecraftForge.EVENT_BUS`. | A instância recebe callbacks durante a execução do cliente. |
| Input | `onKeyInput(InputEvent.Key)` lê `Minecraft.getInstance().player` e retorna se `player == null`. Em seguida chama `isPlayerInSurvival(player)`. | A validação existente protege apenas `player`; não protege a transição em que o player ainda existe e o game mode já foi limpo. |
| Tick | `onPlayerTick(PlayerTickEvent)` aceita somente `LocalPlayer` no fim do tick e também chama `isPlayerInSurvival(player)`. | A mesma leitura insegura pode atingir o callback de tick, além do callback de tecla do crash. |
| Leitura insegura | `isPlayerInSurvival(LocalPlayer)` executa `Minecraft.getInstance().gameMode.getPlayerMode() == GameType.SURVIVAL` sem testar `gameMode`. | Se `gameMode == null`, a chamada a `getPlayerMode()` gera NPE. |

O bytecode descompilado coloca a leitura de `gameMode` dentro do helper compartilhado. Assim, proteger apenas `onKeyInput` por um evento externo deixaria o caminho `onPlayerTick` vulnerável.

## Crash e ciclo de vida

`crash-reports/crash-2026-11-13_09.58.24-client.txt` registra `Description: mouseClicked event handler`, com a mensagem de que `Minecraft.gameMode` está nulo. O stack passa por:

```text
JumpAnimationClient.isPlayerInSurvival
→ JumpAnimationClient.onKeyInput
→ Forge EventBus
→ ForgeHooksClient.onKeyInput
→ KeyboardHandler
```

O evento de input foi processado no loop de eventos do cliente durante uma transição de tela/menu. O campo `player` passou pelo guard; `gameMode`, que é estado independente, estava nulo. Isso confirma o defeito de null-check ausente. O arquivo não determina qual clique ou transição exata deixou o campo nesse estado; desconexão/retorno ao menu é uma hipótese de ciclo de vida compatível com o stack, ainda por reproduzir.

O método `InputEvent.Key` do Forge instalado não é cancelável. O Forge documenta que apenas eventos marcados como canceláveis aceitam cancelamento; tentar cancelar um evento não cancelável pode lançar exceção. Um listener adicional em `InputEvent.Key` não consegue impedir com segurança que o listener do JumpAnimation continue e dereferencie `gameMode`.

## Menor correção segura

Primeira escolha: atualização/correção upstream de `isPlayerInSurvival`. A mudança semântica mínima é retornar `false` quando a instância de `Minecraft.gameMode` for nula e manter a comparação atual nos demais casos:

```java
Minecraft mc = Minecraft.getInstance();
if (mc.gameMode == null) return false;
return mc.gameMode.getPlayerMode() == GameType.SURVIVAL;
```

Isso torna os dois callers seguros e apenas evita iniciar/analisar animações enquanto o cliente não tem `GameMode`; não altera física, input vanilla, estado do jogador nem efeitos durante jogo normal.

Se não houver atualização upstream utilizável, o fallback mínimo no mod exclusivo é um Mixin client-side no início de `JumpAnimationClient.isPlayerInSurvival(LocalPlayer)`: quando `Minecraft.getInstance().gameMode == null`, definir o retorno `false` e cancelar somente esse helper. A injeção deve ser opcional, limitada a `jumpanimation` 2.0.0 / assinatura verificada e não obrigatória para o restante do modpack. Não é necessário injetar em `KeyboardHandler`, cancelar eventos de input, substituir a classe toda ou modificar outros métodos.

## Classificação

- **Problema confirmado:** null-dereference em `gameMode` no helper compartilhado.
- **Ciclo de vida provável:** callback de tecla corre quando ainda há player, mas já não há sessão/game mode ativo.
- **Gatilho exato:** desconhecido; não atribuído a Oculus, Embeddium ou ao Mixin de VillagerTrades.
- **Impacto:** crash client-side quando a condição de transição ocorre.
- **Confiança:** alta para a causa técnica; média para o contexto preciso de menu/desconexão.
- **Risco do guard:** baixo; em `gameMode == null`, a função deixa de classificar como survival e o mod não avança a lógica de animação.
- **Risco do Mixin:** médio por depender de nome/mapeamento/assinatura privada; reduzido por alvo e versão estritos, `required=false` e ausência de hard dependency.
- **Eventos/API Forge:** não resolvem o callback existente, pois o evento usado pelo mod não é cancelável e o listener é registrado pelo próprio mod.
- **Mixin:** somente se o upstream não corrigir.

## Validação futura (não executada nesta auditoria)

1. Reproduzir input durante retorno ao menu, desconexão e entrada/saída de mundo enquanto `player` e `gameMode` assumem estados diferentes.
2. Confirmar que não há NPE e que o callback retorna sem iniciar animação quando `gameMode` está nulo.
3. Verificar que as animações de salto, mergulho/queda, água e aterrissagem continuam iguais em survival; confirmar que o mod mantém o comportamento esperado em creative/spectator.
4. Confirmar no log que a integração opcional não tenta aplicar o Mixin quando JumpAnimation não está instalado ou a versão/assinatura não corresponde.

## Referências

- Evidência principal: bytecode de `jumpanimation-2.0.0-1.20.1.jar` e stack do crash local acima.
- [Arquivos públicos do JumpAnimation para 1.20.1](https://www.curseforge.com/minecraft/mc-mods/jumpanimation/files/all?page=1&pageSize=20&showAlphaFiles=hide&version=1.20.1) e [página de versões no Modrinth](https://modrinth.com/mod/jumpanimation/versions). As páginas consultadas não expõem o código-fonte correspondente ao JAR instalado.
- [Forge 1.20.1 — eventos, cancelamento e `@Cancelable`](https://docs.minecraftforge.net/en/1.20.1/concepts/events/).
