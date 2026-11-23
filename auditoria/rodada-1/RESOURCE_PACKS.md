# Boundless v2 · Resource packs da Rodada 1

Perfil testado em Minecraft 1.21.1 com NeoForge 21.1.259. A configuração da instância ativa os 40 pacotes selecionados no CurseForge e o overlay local `Boundless R1 Resource Compatibility.zip`. Nenhum dos 40 foi removido. O conjunto de ZIPs no disco coincide com o inventário e com os 41 IDs `file/` da configuração. Os ZIPs passaram na leitura de todas as entradas com verificação de CRC e contêm `pack.mcmeta` na raiz.

## Prioridade e compatibilidade

- `resourcepacks-order.csv` lista todos os ZIPs da menor para a maior prioridade. `resourcepacks-inventory.csv` registra a finalidade, o formato e o conteúdo dos arquivos. As entradas integradas dos mods foram preservadas antes dos ZIPs.
- As bases de texturas vêm antes dos ajustes específicos, e Fresh Animations vem antes das extensões. Fresh Animations ganha nos modelos CEM compartilhados com Blue’s Better Zombies. Fresh Moves e JustExpressions ficam acima das extensões de entidades. A aparência das animações em jogo ainda precisa ser conferida.
- Os temas escuros ficam acima das bases visuais. Modded Containers Dark tem prioridade sobre temas amplos nas texturas que fornece, e Immersive Interfaces fica acima para o suporte à armadura cosmética. Darkmode Colourful Containers declara OptiGUI para as interfaces condicionais. Os ativos no namespace `optigui` estão no ZIP, mas o mod não consta na instância. Esse efeito permanece pendente, com o pacote preservado.
- O overlay local tem a prioridade mais alta entre os ZIPs. Seu `default.json` reúne 244 provedores de fonte de Icons e enchant icons. A conferência de exibição dos glifos ainda está pendente.
- Quatro pacotes têm avisos de formato aceitos na interface e registrados em `incompatibleResourcePacks`: Armors, Better End Portal Frame, Updated Aquaculture e Modded Containers Dark. Este último declara formato principal 15 fora da faixa declarada de 30 a 99. O cliente resolveu a divergência usando o formato principal e incluiu o ZIP no carregamento observado.
- A comparação por caminho encontrou 1.070 sobreposições dentro dos ZIPs, 750 com conteúdo diferente e 320 idênticas. Essa contagem inclui caminhos de overlays e metadados e não mede quantos recursos são substituídos em jogo. O cliente ignorou `.DS_Store` em Enchantment-Outlines e EnderEyes, como registrado no log.

## Evidência em execução

Em 22/11/2026, às 16:30:30, `ReloadableResourceManager` listou os 41 ZIPs numa recarga disparada pelo menu. Às 16:30:50, o KubeJS registrou `Client resource reload complete!`. Essa sessão usou a ordem de seleção da interface. Em 23/11, a ordem planejada foi persistida em `options.txt` e comparada com o CSV. A saída do reload completo e a renderização da ordem final precisam ser confirmadas em execução.
