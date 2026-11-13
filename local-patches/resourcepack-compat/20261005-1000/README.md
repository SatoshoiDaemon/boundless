# Pacotes de recursos — Minecraft 1.20.1 / Forge 47.4.10

Os pacotes AL antigos estavam publicados para versões mais novas do Minecraft.
Além disso, Fresh Animations tinha prioridade maior que os modelos AL, e os
pacotes normais e suas variantes `+FA` estavam ativos ao mesmo tempo. Os `+FA`
já incluem os modelos e texturas necessários.

## Alterações

| Pacote | Instalação atual |
| --- | --- |
| Fresh Animations | 1.10.4, arquivo oficial já instalado e íntegro |
| AL's Skeletons Revamped x Fresh Animations | 1.3.1, publicado para 1.20.1 |
| AL's Zombies Revamped x Fresh Animations | 1.3, publicado para 1.20.1 |
| AL's Creepers Revamped | 1.3, publicado para 1.20.1, com ajuste local dos modelos de olhos |
| Artisan's Armory | 2.0, publicado para 1.20.1 |
| Alternative Rain Sounds | arquivo específico 1.20–1.20.1 |
| FA All Extensions | 1.8.1, disponível mas permanece desativado |
| Visual Traveler's Titles | Visual Titles 1.3 instalado e ativado |
| Human Era | 3.91.6 mantido; HEVI FreshAni Activator Fix 2 acrescentado |
| AL's Armor Stands | original mantido, com ajuste local das regras de equipamento |

Os pacotes Skeletons/Zombies normais e os arquivos substituídos foram retirados
da pasta ativa e guardados em `backups/resourcepacks`. Seus registros antigos no
launcher também foram substituídos; `.index` agora registra URLs e hashes dos
arquivos corretos. O complemento HEVI usa download direto sem atualização
automática de projeto, para evitar que o launcher o troque pelo arquivo principal.

`options.txt` mantém os outros pacotes ativos. Just Expressions agora fica abaixo
de Fresh Moves, para preservar as animações completas do jogador. Os nomes de
pacote e sua ordem exata estão em `active-pack-order.json`, da menor para a maior
prioridade. Na tela do Minecraft, a maior prioridade aparece no topo.

## Ajustes locais

`Local - AL Creepers 1.3 with Fresh Animations 1.10.4.zip` usa somente os três
modelos de creeper de Fresh Animations 1.9.2, compatíveis com o mapa das texturas
AL 1.3. Os demais mobs continuam usando FA 1.10.4. Foram removidas referências
opcionais a arquivos JPM ausentes, preservando os nós e as animações.
O manifesto registra o arquivo original, seu hash e cada mudança.

`AL-Armor-Stands-local-1.20.1.zip` substitui somente `armor_stand.properties`.
As regras recentes `equipment.*` não existem em 1.20.1. A condição `items.1=any`,
suportada pelo ETF 7.2.5 instalado, seleciona o modelo comum quando equipado;
as variantes nomeadas originais são preservadas. O ZIP oficial não foi alterado.

## Visual Titles

O arquivo oficial Visual Titles 1.3 tem prioridade acima dos demais pacotes.
As fontes, PNGs e caracteres usados nos títulos dimensionais foram conferidos.
A sombra foi desligada somente na seção `Dimension Titles` da configuração,
conforme orientação do autor. Biomas e waystones mantêm suas configurações.

Esse pacote estiliza títulos de dimensões. Os títulos de biomas permanecem em
texto comum. Com comandos habilitados, podem ser testados por:

```text
/dimensiontitle minecraft:overworld
/dimensiontitle minecraft:the_nether
/dimensiontitle minecraft:the_end
```

## Limites

- Fresh Skeleton Physics não possui versão oficial declarada para 1.20.1.
  O arquivo incompatível, que já estava desativado, foi arquivado.
- AL Armor Stands não tem release oficial para 1.20.1. O ajuste local cobre os
  modelos da entidade; ícones especiais de itens renomeados usam o formato novo
  de itens e não são disponibilizados por este ajuste.
- Alguns ZIPs oficiais publicados para 1.20.1 ainda usam um `pack_format`
  diferente de 15. Os arquivos originais foram preservados e seus avisos aceitos
  por `incompatibleResourcePacks`, sem falsificar a versão interna.
- Colourful Containers continua como estava. Seus recursos de GUI específicos
  de OptiGUI dependem desse mod, que é publicado para Fabric/Quilt, sem versão
  Forge. O port Forge encontrado tem outro estilo e não foi aplicado.

## Evidências e recuperação

`installed-manifest.json` contém os arquivos novos, URLs e hashes SHA512;
`static-validation.json` registra a integridade e o pacote vencedor de cada
modelo relevante. A conferência independente verificou fontes, prioridades,
índices do launcher e backups.

`backups/options.txt` e `backups/travelerstitles-forge-1_20.toml` preservam as
configurações anteriores. `backups/resourcepacks-index` preserva os metadados do
launcher. `before-pack-hashes.json` permite conferir os nove ZIPs arquivados.
`before-latest.log` preserva o registro anterior ao ajuste.

## Fontes

- [AL Skeletons +FA 1.3.1](https://www.curseforge.com/minecraft/texture-packs/als-skeletons-revamped-x-fresh-animations/files/5253518)
- [AL Zombies +FA 1.3](https://modrinth.com/resourcepack/als-zombies-revamped-x-fresh-animations/version/Qb0ailBs)
- [AL Creepers 1.3](https://modrinth.com/resourcepack/als-creepers-revamped/version/M9V8lKDB)
- [Fresh Animations e termos de uso](https://modrinth.com/resourcepack/fresh-animations)
- [Human Era e instalação do ativador](https://modrinth.com/resourcepack/human-era-villagers-illagers)
- [Visual Titles 1.3](https://modrinth.com/resourcepack/visual-travelers-titles/version/AwVu5ygs)
- [Visual Titles — recomendação de sombra](https://modrinth.com/resourcepack/visual-travelers-titles)
- [Just Expressions — ordem com outros modelos de jogador](https://modrinth.com/resourcepack/just-expressions)
- [Prioridade de diretórios no EMF](https://github.com/Traben-0/Entity_Model_Features/blob/master/src/main/java/traben/entity_model_features/utils/EMFDirectoryHandler.java)

## Verificação de inicialização

O teste abre somente o menu, sem entrar em mundos. Limita temporariamente os
FPS a 30 e restaura o arquivo `options.txt` completo ao terminar. O resultado
e os registros ficam em `validation`.

Na execução de 05/10/2026, o carregamento completo foi confirmado pelo registro
`Game took 84.456 seconds to start`. Não houve erros do EMF nem falhas dos
provedores de fonte. A execução foi encerrada depois de a CPU atingir 88 °C;
a identificação do processo precisou ser corrigida para usar seu diretório de
trabalho e a classe de entrada do launcher. O jogo e seu processo auxiliar foram
encerrados, e as opções completas foram restauradas, incluindo o limite de
260 FPS. Nenhum mundo foi aberto. Aparência e comportamento dentro de um mundo
ainda não foram testados.

O log continua contendo problemas já existentes em assets de mods, incluindo
modelos de folhas/slabs e texturas geradas de folhas/discos. Eles não são erros
dos modelos AL/Fresh nem do Visual Titles. O resumo exato dos registros fica em
`validation/resource-load-summary.json`.
