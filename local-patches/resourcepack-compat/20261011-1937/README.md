# Correção de resource packs — Minecraft 1.20.1 / Forge 47.4.10

## Estado corrigido

- Reativei no `options.txt` a seleção salva anteriormente para Fresh Animations, compatibilidades AL, Human Era e Visual Titles. O pacote de maior prioridade aparece por último na lista serializada; Visual Titles fica no topo da pilha.
- A ordem coloca Fresh Animations abaixo dos overlays AL +FA e do ajuste local de creepers. Just Expressions fica abaixo de Fresh Moves. Os packs AL normais que conflitam com as variantes +FA não estão ativos.
- Visual Titles 1.3 já estava instalado com o arquivo oficial compatível com 1.20.1; ele estava ausente da seleção ativa. A configuração de Traveler's Titles mantém títulos dimensionais ligados.
- Substituí `Default-Dark-Mode-26.3-2026.9.0.zip` (sem `pack.mcmeta`, gerava erro no log e não serve à instância 1.20.1) pelo release oficial `Default-Dark-Mode-1.20-2023.7.0.zip`, pack format 15.
- O `.index/default-dark-mode.pw.toml` agora aponta exatamente para o arquivo CurseForge 4633979, compatível com 1.20/1.20.1.

## Limites e compatibilidade

- Fresh Moves 3.1 declara compatibilidade com Minecraft 1.20.x, apesar do nome `1.21.2`; não é erro de versão para esta instância.
- AL Armor Stands Revamped não publica versão oficial para 1.20.1. Mantive o pacote instalado com o overlay local 1.20.1 acima dele, que substitui as regras novas de equipamento.
- Visual Titles estiliza títulos dimensionais. Os títulos de biomas e waystones seguem a configuração própria de Traveler's Titles.
- A instância não foi reiniciada nesta correção; a nova pilha foi verificada em `options.txt` e todos os ZIPs selecionados passaram na leitura de integridade. Aparência dentro do mundo continua sem validação visual.

## Arquivos de recuperação

`backups/` contém o `options.txt`, o resource pack 26.3 incorreto e o índice anteriores. `active-pack-order.json` e `installed-manifest.json` registram a pilha e hashes atuais.
