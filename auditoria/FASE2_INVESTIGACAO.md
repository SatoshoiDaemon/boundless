# Fase 2 — investigação causal e plano técnico

**Instância examinada:** Boundless, Minecraft Forge 1.20.1 / Forge 47.4.28  
**Base local:** `logs/latest.log`, crash report de 13/11/2026, `/mods`, `/config`, recursos empacotados nos JARs e resource packs ativos.  
**Escopo desta fase:** investigação, pesquisa de compatibilidade e planejamento. Nenhum patch foi implementado; não foram executados build, teste ou benchmark.

## Síntese

1. **JumpAnimation:** causa técnica do crash confirmada por inspeção do JAR: um helper compartilhado testa o modo de jogo sem verificar `Minecraft.gameMode`. O callback recebeu um `player` não nulo enquanto `gameMode` já estava nulo. A menor correção é retornar `false` no helper nesse estado. O gatilho exato da transição de tela ainda precisa de reprodução. Ver [análise do bytecode](analise_bytecode_jumpanimation.md).
2. **Ticks:** atrasos confirmados, chegando a **111,641 s / 2.232 ticks**. A única captura do watchdog mostra um instante em `Villager.tick → Brain → HurtBySensor`; ela não mede contribuição por entidade nem por método e **não demonstra que o villager causou os atrasos**. A causa-raiz permanece desconhecida.
3. **Recursos:** o conjunto solicitado de 87 erros é exatamente 47 receitas, 18 avanços, 13 funções, 5 modelos e 4 animações. Há ainda **18 falhas secundárias** de loot tables/tags e **1.032 mensagens repetidas** sobre os projéteis Bone/Axe de Illage and Spillage; elas não entram na contagem 87 e são tratadas separadamente.
4. **Injeção:** o Mixin de Forgified Fabric API falha na transformação de `VillagerTrades` porque o tipo de variável local mudou de `ItemStack` para `Item`. A falha é compatível com issue upstream que registra a mesma incompatibilidade e correção em versão posterior da API.
5. **Correção simples:** `config/oculus.properties` aponta para `MakeUp-UltraFast-9.5g.zip`, mas o arquivo presente é `MakeUp-UltraFast-9.6.zip`; o log confirma que o shader não foi carregado. A sessão não mede renderização com shader ativo.

## 1. JumpAnimation — NPE e ciclo de vida do callback

### Evidências locais

- Crash `crash-reports/crash-2026-11-13_09.58.24-client.txt`: `Description: mouseClicked event handler`; `Minecraft.gameMode` está nulo; stack em `JumpAnimationClient.isPlayerInSurvival → onKeyInput → Forge EventBus → ForgeHooksClient.onKeyInput → KeyboardHandler`.
- JAR: `mods/jumpanimation-2.0.0-1.20.1.jar`. Não contém fonte Java; decompilei as classes instaladas para examinar apenas o fluxo e a leitura que falha.
- O construtor registra `JumpAnimationClient` no `MinecraftForge.EVENT_BUS` no cliente. `onKeyInput(InputEvent.Key)` retorna se `Minecraft.player` for nulo, mas passa ao helper quando o player ainda existe. O helper consulta `Minecraft.gameMode.getPlayerMode()` sem null guard.
- `onPlayerTick(PlayerTickEvent)` também chama o mesmo helper, portanto uma guarda apenas no handler de input não cobre todos os callers.
- O Forge 47.4.28 instalado define `InputEvent.Key` como não cancelável. O stack identifica a janela de tela/input, mas não o clique exato que esvaziou o `gameMode`.

### Conclusão e proposta mínima

**Causa confirmada:** dereference de `gameMode == null` no helper. **Ciclo de vida:** callback de input chega durante uma transição em que há `LocalPlayer`, mas não há `MultiPlayerGameMode`; menu/saída do mundo são cenários compatíveis, não reproduzidos. **Não há evidência** ligando este crash aos conflitos de renderer ou ao Mixin de trades.

Preferência: correção upstream no helper. Se não existir atualização utilizável, o último recurso é Mixin client-side no início de `isPlayerInSurvival(LocalPlayer)`, retornando `false` somente quando `Minecraft.gameMode` for nulo. A guarda compartilhada mantém seguros o tick e o input e só suprime a lógica de animação fora de uma sessão com modo de jogo. Não se deve tentar cancelar `InputEvent.Key`: além de não ser cancelável, isso não cobre o callback de tick.

**Rota:** API/evento Forge não intercepta com segurança esse listener privado; Mixin somente como último recurso, alvo e versão estritos, sem hard dependency.  
**Impacto/confiança:** alto/alta para crash e causa; média para o instante de ciclo de vida.  
**Risco:** baixo para o guard; médio para Mixin por depender de assinatura/mapeamento privado.  
**Validação futura:** reproduzir menu, disconnect e conexão; confirmar ausência de crash, retorno neutro sem `gameMode`, animações normais de salto/água/queda em survival e comportamento esperado em creative/spectator.

Detalhes método a método, limites da descompilação e fluxo de validação em [analise_bytecode_jumpanimation.md](analise_bytecode_jumpanimation.md). As páginas públicas consultadas do [JumpAnimation para 1.20.1](https://www.curseforge.com/minecraft/mc-mods/jumpanimation/files/all?page=1&pageSize=20&showAlphaFiles=hide&version=1.20.1) e do [Modrinth](https://modrinth.com/mod/jumpanimation/versions) não disponibilizam o código-fonte correspondente ao JAR instalado.

## 2. Atrasos extremos de ticks

### Linha do tempo

`logs/latest.log` mostra carga de datapack, preparação do spawn, entrada do jogador, um watchdog e nove avisos `Can't keep up`. A sequência, com timestamps, linha do log e leitura causal por evento, está em [linha_do_tempo_ticks.csv](linha_do_tempo_ticks.csv).

| Horário | Evidência | Leitura |
|---|---|---|
| 09:51:25 | Carga inicial de datapacks: 33,84 s (`latest.log:7996`). | Tempo alto de carga, mas não é um tick de jogo. |
| 09:51:32–09:51:38 | Preparação da região inicial do Overworld; spawn repetido em 0%; elapsed 5.786 ms (`8036–8049`). | Geração/carregamento coincide com a inicialização. Não explica sozinho os atrasos posteriores. |
| 09:51:42 | Jogador entra (`8124`). | Marca o começo da sessão jogável. |
| 09:51:45 | `Can't keep up`: 3.910 ms / 78 ticks (`8197`). | Pode ser custo de entrada, chunks ou outro trabalho; sem perfil para separar. |
| 09:52:34 | ModernFix registra um tick de 40.091 ms (`8281`). A captura inclui `HurtBySensor → Sensor → Brain → Villager.tick → ServerLevel`. | Uma amostra instantânea de stack. Não fornece contagem de villagers, tempo acumulado por entidade, nem atribuição de CPU. |
| 09:53:52 | Maior atraso: 111.641 ms / 2.232 ticks (`9016`). | Sem perfil e sem telemetria local de chunks/entidades junto ao warning. |
| 09:54:51–09:57:45 | Mais sete atrasos: 43.975; 7.352; 17.508; 6.734; 13.740; 6.097; 32.830 ms (`9019–9043`). | Causa desconhecida; sem série de métodos, movimento, chunks ou GC. |
| 09:58:02–09:58:16 | Salvamento de chunks em oito dimensões (`9048–9065`). | Ocorre depois dos warnings; não explica retroativamente os atrasos. |

### Causalidade e investigação proposta

- **Confirmado:** o servidor integrado ficou muito atrás de tempo real; há um tick isolado acima de 40 s e vários warnings longos.
- **Não confirmado:** villagers, IA, densidade de entidades, geração, salvamento, shader, partículas ou heap como causa-raiz. A sessão também não mostra qual entidade/chunk estava ativo nos avisos posteriores.
- A chamada no thread do Xaero World Map é worker assíncrono aguardando `CompletableFuture`; não há ligação demonstrada com o thread do servidor.
- A geração do spawn é observada uma vez. Não há logging de geração por chunk que permita relacioná-la às pausas de 09:53–09:57.
- Não há GC log, série de heap, OOM, JFR ou profiler nos arquivos. A configuração local usa `-Xmx4096m`, mas o crash é NPE e não há base para recomendar mais heap.

**Plano:** primeiro recolher perfil de um caso reproduzível com Spark/JFR, em cenários separados: mundo já gerado e imóvel; caminhada em chunks novos; região com entidades; e cena de combate/efeitos. Registrar duração de tick, contagem por tipo de entidade, contagem de chunks carregados/novos, dimensão, movimento e GC no mesmo relógio. Um `ServerTickEvent` opt-in pode medir duração agregada; `EntityJoinLevelEvent`/`EntityLeaveLevelEvent` e `ChunkEvent.Load/Unload` podem contar transições sem varrer o mundo. Esses eventos dão correlação, não atribuição por método; profiler continua necessário. Não implementar throttling, remoção de entidades, corte de partículas ou mudanças de worldgen sem esse perfil.

**Impacto/confiança:** impacto operacional alto; causa-raiz não atribuída. **Risco de instrumentação:** baixo se limitada a contadores/janelas e desligada por padrão. **Validação futura:** reproduzir cada cenário em mundo descartável/backup e comparar distribuição de tick time e amostras do profiler, sem alterar a qualidade visual.

## 3. Os 87 erros de recursos

Cada linha em [erros_carregamento_87.csv](erros_carregamento_87.csv) tem categoria, ID exato, linha/timestamp do log, origem/versão local, causa confirmada ou hipótese, impacto, correção sugerida, mecanismo, risco, confiança, validação futura e fonte externa. Os erros foram agrupados abaixo sem juntar os IDs individuais.

### Receitas — 47

| Grupo | Qtde | Evidência e causa | Impacto e caminho de correção |
|---|---:|---|---|
| EveryCompat dinâmico | 32 | `latest.log:7523–7686`. Erros dizem ingrediente sem `item`/`tag` ou campo `item` ausente. Every Compat local 2.9.26, Moonlight 2.16.35; geração está ativa, mas `save_debug_resources=false`, então o JSON dinâmico específico não foi salvo. É hipótese qual ramo do gerador produz cada JSON. | As recipes exatas de cutting/salvaging/furniture/chest boat não entram no RecipeManager. Primeiro comparar atualização suportada; depois habilitar debug só para capturar saída e corrigir IDs/ingredientes confirmados. Não desligar geração dinâmica inteira. Upstream/datapack; sem evento ou Mixin. A página oficial lista [Every Compat 2.9.29](https://www.curseforge.com/minecraft/mc-mods/every-compat/files/all?page=1&version=1.20.1) e [Moonlight 2.16.39](https://www.curseforge.com/minecraft/mc-mods/selene/files/all?page=1&version=1.20.1), mais novas que as instaladas; as páginas não provam que resolvem estes 32 erros. |
| Valhelsia Furniture | 7 | `latest.log:7603–7659`; parser diz que ingrediente custom não pode ser aninhado em ingredient-array. JAR local 1.1.3; usa estrutura cross-loader (`forge_value`/`fabric_value`). | Sete recipes específicas de mesa/cadeiras não entram. Preferir upstream; alternativa datapack Forge-native após revisar cada input para preservar as variantes. Sem Java/Event/Mixin. Risco baixo-médio se as alternativas forem mantidas. |
| VSlab/NetherExp | 3 | `latest.log:7530, 7568, 7638`; item `netherexp:yellow_nether_bricks`/`yellow_nether_brick_slab` não está no registry. Hipótese de integração para conteúdo opcional ou ID de versão incorreto. | Sem efeito demonstrado no conteúdo instalado; recipes de laje vertical opcionais ausentes. Corrigir condição/ID upstream após confirmar quem deveria registrar o item; não criar substituto. Datapack somente se um item válido for confirmado. |
| Exline/Warhammers | 3 | `latest.log:7572, 7611, 7634`; receitas de Exline v2.0.8 referem `warhammersmod:hammer_copper`, mas Warhammers não está instalado. | Só a integração opcional de martelo falha. Gatar com `forge:mod_loaded` em upstream/datapack; testar com addon ausente/presente. |
| NoCube/Galosphere | 1 | `latest.log:7511`; `galosphere:raw_silver_block` não existe no registry atual. A condição de mod carregado não implica que esse item exista. | Uma receita de integração de fundição não carrega. Confirmar ID/registro antes de qualquer troca; datapack se ID real existir, Java upstream se conteúdo deveria ser registrado. |
| Galosphere Block Comparator | 1 | `latest.log:7620`; `galosphere:block_comparator` desconhecido no registry apesar de arquivos de receita/modelo no JAR. O mesmo ID aparece em loot table/tag com falha (fora dos 87). | Sinal mais forte de divergência de recurso/registro ou de BlockItem ausente; não está provado que o bloco exista. Datapack não cria item. Investigar registry upstream; Java somente se houver falha de registro real. Issue [#253 do projeto](https://github.com/0rc1nus/Galosphere-Main/issues/253) trata de outro ID obsoleto na 1.5.2 e é apenas contexto, não prova sobre o comparator. |

**Confiança:** alta para mensagens e IDs ausentes; média para a causa geradora de EveryCompat/VSlab. **Validação:** recarregar dados, consultar todos os IDs em RecipeManager/JEI e testar craft/stonecutting/salvaging com ingredientes equivalentes.

### Avanços — 18

| Grupo | Qtde | Causa e impacto | Correção e validação |
|---|---:|---|---|
| Galosphere | 9 | `latest.log:7898, 7901–7903, 7905–7906, 7909, 7911–7912`. Oito ícones usam schema não suportado (parser pede chave `item`); um usa string onde espera array. O avanço falha, mas não remove item/mob/gameplay. | Datapack override dos 9 JSONs, mexendo somente no display icon/schema e preservando criteria, rewards e pais; conferir desbloqueio e árvore de avanços. |
| Spartan Shields | 4 | `latest.log:7899, 7904, 7910, 7913`. Ícones Mekanism/EnderIO ausentes na instância. | Usar ícone existente ou condição opcional de addon em datapack/upstream. Preservar criteria/rewards e conferir com addons ausentes/presentes. |
| Meteor Shower | 3 | `latest.log:7897, 7900, 7908`. Parser 1.20.1 rejeita o schema de ícone. | Datapack troca somente o ícone para forma 1.20.1; conferir evento, critérios e rewards. |
| Exline | 1 | `latest.log:7907`; avanço pede `minecraft:copper_pickaxe`, inexistente em 1.20.1, enquanto o JAR contém o asset no namespace `exlinecopperequipment`. | Corrigir só o icon ID via datapack e confirmar desbloqueio pela recipe. |
| Legendary Monsters | 1 | `latest.log:7914`; `legendary_monsters:ancient_dripstone_shard` não está no registry. | Verificar item pretendido e trocar somente o ícone via datapack/upstream, sem alterar trigger de Ambusher. |

As incompatibilidades de schema são confirmadas pelo parser; a escolha do ícone alternativo exige confirmar assets e não deve mexer na progressão.

### Funções — 13

- **Nove sondas `fokus:vd/cores/1.20.2` e `1.21+`:** comandos e IDs de versões posteriores falham no parse 1.20.1 (`latest.log:7721–7881`). O padrão parece parte de detecção de versão por funções; hipótese de que os ramos são inativos/esperados, ainda não confirmado por estado de scoreboard no mundo. Sem falha de inicialização observada. A correção menos arriscada é upstream separar probes por versão; só alterar se teste da rotina FokusAPI detectar falha.
- **Quatro funções restantes:** fallback `_ignored` de DoubleJump com sintaxe antiga de partícula; fallback FokusAPI com `replaceitem`; fallback de critério `play_one_minute`; e função com placeholder `$this.file` sem chamador encontrado (`latest.log:7689–7817`). Os logs confirmam parse inválido; call graph e flags locais indicam caminho provavelmente inativo. Não há base para remover/reescrever funções agora.

**Rota e risco:** datapack/upstream, sem Java/Event/Mixin. Baixo impacto presumido, mas confiança média; validação futura deve observar flags e acionar cada função compatível antes de eliminar fallback.

### Modelos — 5

- **Mowzie’s Mobs:** dois modelos de Grottol (`latest.log:2654–2676`) têm `textures.__comment` com frase que o loader tenta usar como resource location. Causa confirmada; falham somente os modelos afetados. Correção de baixo risco por resourcepack removendo essa chave e preservando as texturas. O [issue #9 upstream](https://github.com/BobMowzie/MowziesMobs-Public/issues/9) relata o mesmo erro.
- **Better Leaves/Twilight Forest:** `latest.log:2695`; `resourcepacks/Better-Leaves-9.6.zip` contém compat para `twilightforest:giant_block`, mas Twilight Forest não está em `/mods`. Não é conflito entre mods instalados e não afeta o pack atual. Condicionar/atualizar apenas o arquivo opcional.
- **VSlab Compat:** dois templates (`latest.log:2927, 3260`) com `$texture`/`$v_slab` são tentados como modelos finais. O erro é certo; o efeito visual ainda não foi observado, pois podem servir de template ao gerador. A correção preferida é upstream mover/filtrar templates, sem criar override que sombreie modelos dinâmicos.

### Animações GeckoLib — 4

`latest.log:2242, 2314, 2366, 2479–2480` e assets de `born_in_chaos_[Forge]1.20.1_1.7.5.jar` confirmam `-` em componente numérico de keyframe. Arquivos: `babyskeleton.animation.json#idle`, `babyskeletondeamon.animation.json#idle`, `boneimp.animation.json#idle` e `scarletpersecutor.animation.json#attack`. GeckoLib rejeita `-` como expressão Molang; a animação afetada pode não ser baked, sem remover a entidade. Preferir upstream; se for necessário, resourcepack override completo após interpretar o keyframe. Substituir hífen por zero sem revisar pose/timing pode achatar a animação. Não requer Java/Event/Mixin. Risco visual médio; validar transições idle/attack no jogo.

## 4. Falhas adicionais de loot tables, tags e atributos

As **16 loot tables e 2 tags** não fazem parte do conjunto de 87 acima, mas aparecem como `ERROR` durante o mesmo reload. Seus IDs, linha, parser, hipótese, impacto, rota e validação estão em [erros_secundarios_loot_tags.csv](erros_secundarios_loot_tags.csv).

- Sete loot tables de Armageddon, duas de DTBOP, uma de DTEcologics, uma de Galosphere, duas de Iron’s Spells ’n Spellbooks, duas de Strongholds e uma de Mansions falham por bloco/item ausente, função desconhecida ou campo `name` inválido. Resultado possível: drops ou pools de baús/estruturas faltando; confirmar no mundo antes de determinar impacto.
- A tabela `galosphere:blocks/block_comparator` e a tag `galosphere:experimental_blocks` repetem a referência inexistente `galosphere:block_comparator`, além da receita. São três recursos independentes corroborando o ID ausente. Se o block/item deveria existir, o reparo correto é upstream/registro Java; datapack não cria registry entry.
- `quark:wraith_spawnable` não carrega porque Bygone Nether referencia `quark:soul_stone`, ausente. Se opcional, corrigir tag condicional; se deveria ser item presente, primeiro confirmar versão/registro.
- Há **1.032 mensagens** `[ERROR] Entity illageandspillage:bone/axe has no attributes`, em duas rajadas por volta de 09:26:41 e 09:50:51. O mod instalado é Illage and Spillage: Respillaged 1.2.8 e esses IDs são projéteis. A repetição é conhecida em logs Forge; uma correção pública de terceiros menciona explicitamente a Axe/Bone de Illage and Spillage. O jogo não contém contagem/stack por mensagem que identifique o emissor local, então a hipótese é consulta de atributos sobre entidades não-living por algum consumidor. Não se deve adicionar atributos de mob aos projéteis nem silenciar globalmente sem identificar o caller. A menção externa em [Mystic’s Monstrosity Fixes](https://www.curseforge.com/minecraft/mc-mods/mystics-monstrosity-fixes/files/9341611/dependencies) confirma a classe de ruído e a entidade, mas não mostra que o mesmo mecanismo/versão se aplique à instância.

Esses erros adicionais ocorrem durante reload/registro, antes dos warnings mais longos de tick. A proximidade temporal **não estabelece causalidade** com o lag.

## 5. Injeções e conflitos conhecidos versus versões instaladas

### Forgified Fabric API — erro de injeção confirmado

`latest.log:7979–7981`: `TradeOffersTypeAwareBuyForOneEmeraldFactoryMixin` falha em `VillagerTrades$EmeraldsForVillagerTypeItem` no opcode 34. O Mixin esperava local `ItemStack`; bytecode local tinha `Item`. A versão empacotada dentro de TxniLib é Forgified Fabric API **0.92.2+1.11.12+1.20.1**; Forge local é **47.4.28**.

O [issue #224 do Forgified Fabric API](https://github.com/Sinytra/ForgifiedFabricAPI/issues/224) descreve o mesmo alvo e tipo de mismatch e informa que não ocorre com Forge 47.4.16 + FFAPI 0.92.6+1.11.14. O catálogo oficial hoje lista [0.92.6+1.11.15 para 1.20.1](https://www.curseforge.com/minecraft/mc-mods/forgified-fabric-api/files/all?page=1&version=1.20.1). As versões mais novas dão um caminho de atualização fundamentado, mas não provam quais trades são afetados neste pack.

**Plano:** atualizar a dependência Jar-in-Jar pelo pacote compatível de TxniLib, sem instalar uma segunda cópia standalone de FFAPI. **Não requer Mixin próprio, datapack ou Forge Event.** Risco baixo-médio. Validar load sem erro e ofertas de villager, incluindo pescador até nível mestre. As ofertas e o gameplay não foram auditados em runtime nesta fase.

### Forge `field_to_method.js` — falha de coremod, origem secundária desconhecida

`latest.log:1145–1147` e `1342–1344` registra duas falhas do coremod Forge: `Field f_47437_ is not private and an instance field` ao transformar função `biome`. O jogo continua. A falha do transform está confirmada; se o estado anterior veio de outro transformador ou de diferença interna de bytecode não foi estabelecido. Não há sintoma local de biome effect faltando e nenhum issue upstream exato foi identificado.

**Plano:** não remendar no mod exclusivo. Se houver bioma/modifier visual ou climático incorreto, capturar bytecode transformado e reportar ao Forge com repro. Validação posterior em biomas BOP/Terralith/dimensões. Mixin genérico aqui teria risco alto.

### Renderer: Oculus, Embeddium, Flywheel/Create e modificadores de internals

- Stack instalado: Create 6.0.8, Flywheel 1.0.5, Oculus 1.8.0, Embeddium 0.3.31 e Oculus-Flywheel-Compat 2.0.3. Flywheel recua de `irisflw:iris_instancing` para `flywheel:indirect` (`latest.log:8103`); o log também avisa que Oculus, Entity Texture Features 7.2.5, Sodium Dynamic Lights, CullLessLeaves Reforged 1.0.5, Supplementaries e BetterFPSDist 6.0 modificam classes internas do Embeddium. O JAR de Sodium Dynamic Lights chama-se `sodiumdynamiclights-forge-1.0.10-1.20.1.jar`, mas `mods.toml` e `logs/modlist.txt:438` reportam versão 1.0.9; uso 1.0.9 como versão carregada e registro essa divergência de nome. São warnings de acoplamento, não falhas de injeção demonstradas.
- O issue [Create #10327](https://github.com/Creators-of-Create/Create/issues/10327) discute combinação de versões semelhante e artefato de shader, mas em GPU/hardware diferente. O shader local nem carregou; portanto, não há sintoma local correlacionável.
- O issue [Oculus #631](https://github.com/Asek3/Oculus/issues/631) relata retenção de referências ao trocar dimensão em Oculus/Embeddium de versões anteriores e macOS ARM. A instância usa versões mais novas e RX 480; sem heap series não é diagnóstico local.
- [Sodium Dynamic Lights #46](https://github.com/txnimc/SodiumDynamicLights/issues/46) relata possível interação com `Animate Only Visible Textures` do Embeddium. A opção local está habilitada, mas nenhum defeito visual de luz dinâmica foi registrado. Só fazer A/B se houver sintoma de luz, preservando as luzes quando corretas.

**Plano:** corrigir caminho do shader e obter repro antes de mexer em renderer. Manter particulas, animações, shaders e efeitos; nada sustenta desabilitá-los agora. Mixin de renderer/leak apenas após perfil reproduzível e comparação de versões.

## 6. Configuração simples: referência de shader Oculus

- `config/oculus.properties:7`: `shaderPack=MakeUp-UltraFast-9.5g.zip`.
- Existe `shaderpacks/MakeUp-UltraFast-9.6.zip` e o log diz `Pack "MakeUp-UltraFast-9.5g.zip" is not valid! Can't load it` seguido de fallback sem shaders (`latest.log:1426–1428`).
- **Causa confirmada:** referência desatualizada; não é falha provada do Oculus nem do shader.
- **Correção proposta:** alterar somente o nome referenciado para `MakeUp-UltraFast-9.6.zip`, se essa for a seleção desejada. Não modifica JAR nem remove qualidade visual.
- **Rota/risco:** configuração simples, sem Java/Event/Mixin; risco baixo. Validar em reinício que o pack está ativo e conferir imagem/contraptions/partículas.

## 7. Oportunidades ainda não medidas

| Área | Evidência disponível | Classificação atual |
|---|---|---|
| Partículas | Opções de cliente permitem `ALL`; Particle Rain tem limite alto e há mods de partículas. Sem FPS, GPU frametime ou cena reproduzida. | Oportunidade de medir; gargalo não confirmado. Não reduzir efeitos. |
| Animações/modelos de entidades | Há falhas de recursos e muitos packs visuais de entidades. Sem captura de frame/render thread. | Corrigir recursos individuais; não há prova de custo de animação. |
| Entidades/IA | Uma amostra do watchdog em `Villager.tick`; sem contagens nem perfil. | Não atribuir ao villager/AI mods. Medir por método e tipo antes de otimizar. |
| Geração de chunks | Preparação de spawn registrada; pack tem várias camadas de worldgen e estruturas. Nenhum trace de chunks novos durante cada stall. | Hipótese fundamentada; usar perfil separado para chunks novos e já gerados. |
| Renderização | Configuração de culling, chunk updates e texturas animadas observada; shader desligado por caminho inválido. | Estado/config conhecido, custo e benefício reais não medidos. Corrigir o caminho antes de A/B. |
| Memória/GC | Heap máximo de 4 GiB; sem OOM, GC log ou retained heap. | Nenhum diagnóstico de pressão de memória. Não elevar Xmx nem adicionar leak Mixin sem dado. |

Tectonic declara suporte a BOP/Terralith por TerraBlender em sua [documentação do projeto](https://modrinth.com/datapack/tectonic?dep=1); portanto, a combinação não é classificada como conflito só por coexistir. Isso não garante custo de geração nem compatibilidade de toda estrutura presente.

## 8. Proposta arquitetural do mod exclusivo

### Módulos separados

1. **Núcleo e detecção:** mod Forge 1.20.1 sem dependências obrigatórias de mods opcionais. Consultar `ModList`/versões e ativar adaptadores quando o alvo estiver instalado; não fazer alteração automática no cliente.
2. **Pacote de dados de compatibilidade:** recipes, advancements, functions, loot tables e tags somente para recursos corrigidos e confirmados. Preferir arquivo declarativo completo que preserve triggers/inputs/outputs. Usar `forge:mod_loaded` para integração opcional.
3. **Pacote de assets cliente:** resourcepack próprio versionado com os dois modelos Mowzie, keyframes Born in Chaos e correções de modelos/templates quando forem validadas. Deve ser reversível e preservar a pilha de resource packs existente.
4. **Registro de packs:** avaliar `AddPackFindersEvent` do mod bus Forge 1.20.1 para expor um pack de dados e outro de recursos com posição explícita. Forge documenta recursos em `assets`/`data` e precedência por pilha; o evento adiciona fontes à criação do `PackRepository`. A prioridade, seleção em mundos existentes e persistência após reload precisam de validação antes de empacotar fixes ativos. Referências: [Forge resources 1.20.1](https://docs.minecraftforge.net/en/1.20.1/concepts/resources/) e [AddPackFindersEvent Forge 1.20.x](https://github.com/MinecraftForge/MinecraftForge/blob/1.20.x/src/main/java/net/minecraftforge/event/AddPackFindersEvent.java).
5. **Diagnóstico opt-in:** `ServerTickEvent` para duração agregada; eventos de entrada/saída de entidade e de chunk para contadores leves; dimensões e timestamps alinhados. Sem varredura completa por tick, sem guardar objetos de entidade, e desligado por padrão. Eventos correlacionam; Spark/JFR atribui hot methods.
6. **Adaptador JumpAnimation:** upstream primeiro. Um único Mixin de client-side no helper compartilhado fica isolado, condicional e versionado; não intercepta `KeyboardHandler` nem altera input vanilla.
7. **Config:** `ForgeConfigSpec` com módulos independentes. Defaults não mudam gameplay, simulação, partículas, shaders ou animações. Toda correção de dados deve ter versão/ID e opção de desativar ou pack reversível.

### Limite entre eventos e Mixins

Forge Events/APIs são adequados para registrar os próprios contadores e detectar transições de entidade/chunk. Datapack/resourcepack é a ferramenta apropriada para erros de JSON. Alterar registro de item/bloco exigiria corrigir o mod que possui o registro. O NPE é uma leitura privada dentro do callback alheio, e `InputEvent.Key` não é cancelável; por isso só esse defeito pode justificar o pequeno Mixin após tentar upstream. O Forge exige respeitar cancelabilidade e documenta que cancelamento indevido pode lançar exceção: [eventos Forge 1.20.1](https://docs.minecraftforge.net/en/1.20.1/concepts/events/).

## 9. Plano incremental proposto

| Ordem | Trabalho | Impacto / confiança | Complexidade e risco | Mecanismo | Validação |
|---:|---|---|---|---|---|
| 1 | Corrigir referência do shader para o arquivo realmente instalado, se MakeUp 9.6 é a seleção desejada. | Recupera visual pretendido; causa certa. | Muito baixa / baixo. | Config Oculus. | Reiniciar, confirmar shader ativo e conferir cena visual fixa. |
| 2 | Corrigir NPE do JumpAnimation via upstream; se indisponível, protótipo de guard no helper por Mixin condicionado a versão. | Crash alto / causa alta. | Média; risco baixo no guard, médio no Mixin. | Upstream, depois Mixin mínimo; sem cancelamento de evento. | Reproduzir entradas/saídas/menu; testar todas animações normais. |
| 3 | Medir atraso extremo sem mudar gameplay. Capturar JFR/Spark e telemetria de entidades/chunks em cenários controlados. | Impacto de lag alto / causa baixa. | Média / baixo se diagnóstico opt-in. | Forge Events leves + profiler. | Comparar tick p95/máximo e stacks em mundo gerado, geração nova e cena com entidades. |
| 4 | Corrigir injeção FFAPI por atualização suportada da dependência Jar-in-Jar em TxniLib. | Possível impacto em trades médio / correspondência local-upstream alta. | Baixa-média / baixo-médio. | Atualização de dependência; sem patch próprio. | Verificar load e ofertas de villager em níveis diferentes. |
| 5 | Recursos visuais localizados: Mowzie, quatro keyframes Born in Chaos, Better Leaves opcional, template VSlab. | Sem crash, preserva qualidade visual; confiança alta exceto impacto do template. | Baixa-média / baixo-médio. | Resourcepack/upstream. | Ver modelos/poses e todas as verticais de slabs; reload sem erros. |
| 6 | Receitas/avanços 1.20.1: schema Galosphere/Meteor, ícones ausentes, Exline/Warhammers, Valhelsia, EveryCompat e VSlab. | Impacto localizado; confiança por grupo na CSV. | Baixa-média; médio para preservar equivalência de receita. | Datapacks/condições/updates. | Consultar RecipeManager/advancements e testar crafting/triggers. |
| 7 | Auditar 18 erros secundários de loot tables/tags e verificar `block_comparator` no registro Galosphere. | Potencial impacto em drops/chests; confiança alta no parse, média no efeito. | Média / médio. | Datapack se recurso existe; upstream Java se registry ausente. | Testar loot no mundo descartável e inspecionar reports de registry/tag. |
| 8 | Só após diagnóstico, decidir ajustes de desempenho/renderização; verificar mensagens Bone/Axe e caller de atributos. | Impacto e causa ainda não estabelecidos. | Variável; Mixin de otimização teria risco alto. | Perfil primeiro; config/eventos próprios depois. | A/B com logs, tick/frame timings e as mesmas cenas, mantendo efeitos visuais. |

## Artefatos da fase 2

- [Investigação e plano](FASE2_INVESTIGACAO.md)
- [Análise do bytecode JumpAnimation](analise_bytecode_jumpanimation.md)
- [87 erros classificados por ID](erros_carregamento_87.csv)
- [18 erros secundários de loot tables/tags](erros_secundarios_loot_tags.csv)
- [Linha do tempo de ticks](linha_do_tempo_ticks.csv)
- [Matriz fase 2 de compatibilidade](matriz_fase2_compatibilidade.csv)
- [Auditoria inicial, inventário e dependências](AUDITORIA.md), [inventario_mods.csv](inventario_mods.csv), [dependencias_mods.csv](dependencias_mods.csv), [matriz_compatibilidade.csv](matriz_compatibilidade.csv)

## Limites e aprovação

Inspeção do bytecode não substitui o código-fonte correspondente do JumpAnimation; o gatilho exato do NPE e a causa dos atrasos ainda exigem reprodução/perfil. Updates externos são candidatos, não patches validados. Os erros JSON estão detalhados nas tabelas por ID; não foram alterados JARs/configs originais e nada foi implementado. O próximo passo é aguardar aprovação deste plano antes de iniciar patches.
