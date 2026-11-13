# HUD Compatibility Fix 1.1.1

Patch local independente para Minecraft 1.20.1 / Forge 47.4.10, testado com
AutoHUD 8.6 e Combat Roll 1.2.1. Não incorpora nem altera o JAR desses mods.

O crash original aparecia no HUD do Combat Roll, mas a pilha gráfica já estava
vazia. Desativar esse HUD apenas deslocou a falha para o AutoHUD e a tela de
entrada do mundo. A execução de diagnóstico capturou a remoção da matriz base
em `AutoHudGui.cancelHudComponent` → `AutoHudRenderLayer$DoMove.doPostRender`.

O Mixin atual redireciona somente o `popPose` desse método. Se a pilha ainda tem
uma transformação adicional, executa o pop normal. Se resta somente a matriz
base, preserva essa matriz. O restante da limpeza, incluindo a lista de
componentes ativos e a transparência, continua a executar normalmente.

O HUD do Combat Roll e as animações do AutoHUD permanecem habilitados. O patch
não injeta código em PoseStack, GuiGraphics, renderização de entidades ou no
servidor. Uma linha de diagnóstico por execução informa quando a proteção atuou.

## Compilar

Execute `bash build.sh` nesta pasta. O script usa Java 17 e as bibliotecas já
instaladas no Freesm Launcher. O artefato fica em
`build/combatroll-hudfix-1.1.1.jar`. Os identificadores SRG de Minecraft 1.20.1
são intencionais, por isso o Mixin usa `remap=false` e não requer um refmap.

Instale apenas um JAR desse patch na pasta `mods`. Versões anteriores estão
guardadas em `backups/` e não devem ser ativadas simultaneamente.

## Evidências

- `validation/before-crash.txt`: crash de entrada antes da correção.
- `validation/before-latest.log`: log anterior à investigação.
- `validation/diagnostic-run-latest.log`: execução que identificou a chamada
  desequilibrada do AutoHUD.
- `validation/final-run-latest.log`: validação da versão final, quando concluída.
- [Relato oficial com a mesma sequência de reprodução](https://github.com/FiniteReality/embeddium/issues/480).
- [Discussão do AutoHUD](https://github.com/Crendgrim/AutoHUD/issues/157).

Os testes usam uma cópia de `Teste 13`, não o save original. Para desativar a
correção, mova `mods/combatroll-hudfix-1.1.1.jar` para fora de `mods`. Isso volta
ao comportamento dos mods originais e pode reproduzir o crash.

## Resultado da validação — 04/10/2026

A versão 1.1.1 carregou seu Mixin diretamente em
`AutoHudRenderLayer$DoMove`. A cópia do mundo entrou no End às 22:01:45;
a proteção atuou às 22:01:47 e o jogo continuou renderizando por mais de um
minuto, sem `NoSuchElementException`, falha de overlay ou novo crash report.
O teste foi encerrado por SIGTERM no processo iniciado para a validação, e
o servidor executou o salvamento normal. As cópias dos mundos de teste foram
arquivadas em `validation/`; o mundo original foi apenas lido e copiado.

A validação cobre o carregamento do mundo e da interface na configuração
atual. Não inclui teste completo de combate, rolamento ou troca de shaders.
