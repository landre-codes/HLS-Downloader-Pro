# Revisão de UI — evidências reais

## Método

Capturas reais do `QQuickWindow` em modo offscreen, com fontes do sistema
(`QT_QPA_FONTDIR=C:\Windows\Fonts`), sem mockups:

- 5 abas, temas claro e escuro;
- resoluções 940×620, 1160×800, 1366×768 e 1920×1080;
- escalas 100%, 125%, 150% e 200% (amostras);
- toast longo e diálogo de erro.

As imagens selecionadas estão em `docs/ui-review/` (24 PNGs). O harness
reprodutível é `scripts/ui_snapshot.py` (offscreen, fontes do sistema). A
captura cobre apenas o Windows; Linux/macOS e leitor de tela continuam
pendentes.

## Defeitos encontrados e corrigidos nesta rodada

| ID | Evidência | Correção |
|---|---|---|
| Contraste | No tema claro, botões primários (`Baixar agora`, `Adicionar à Fila`, `Iniciar Fila`) ficavam brancos sobre fundo claro/transparente | `Material.background` da janela pintava o fundo dos botões; removido e substituído por `ApplicationWindow.background`. `AppButton` agora define fundo/texto explícitos para estados normal, hover, pressionado e desabilitado |
| Cabeçalho descritivo | Cada aba não tinha uma introdução visual; o DiskPilot usa cabeçalho + card com degradê | Novo `PageHero` com título, descrição, barra de acento e degradê sutil; em janelas pequenas fica compacto (40 px sem ações / 52 px com ações) em vez de sumir |
| Barra de título | Barra plana, versão misturada ao subtítulo e pouca resposta ao mouse | Gradiente sutil, divisor, versão em pill e espaçamento revisado; capturas `1160x800-light-titlebar-close-hover.png` e `...-pressed.png` |
| Hover/pressed | Botões tinham mudança discreta ou dependiam do Material | `AppButton`, `AppToolButton` e `TitleBarButton` com fundo de hover, mousedown, escala e transição de cor; `Baixar agora` e ações primárias usam azul mais claro no hover e mais escuro no pressed |
| UX-18-03 | Diálogo de erro mostrava texto técnico vermelho sem hierarquia | Resumo humano + “Detalhes técnicos” expansível, área rolável e copiar/fechar; `1160x800-light-error.png` e `...-error-details.png` |
| UX-19-01 | Botões secundários dependiam de hover para parecer clicáveis | `AppButton` ganhou variantes `primary/secondary/tertiary/danger` e `size`; `highlighted` continua compatível. Batch, Compressão, Playlist, erros e pasta usam secondary/tertiary de forma intencional |
| UX-19-02 | Pasta de saída era apenas um Label passivo | Novo `FolderPickerField` com caminho elidido, tooltip, Alterar, Abrir e Copiar; validação de escrita e feedback de erro; `1160x800-light-settings-folder.png` |
| UX-19-04 | Ações de fila sempre habilitadas | Iniciar/Cancelar/Limpar agora derivam de contadores reais; desabilitados quando não há operação aplicável |
| R4 — botões Material | Botões pareciam labels e eram pequenos | `AppButton` com 44 px (normal) / 36 px (compact), variantes com superfície/borda, ícones 18 px, hover/pressed e transição; capturas de Lote/Compressão/Configurações |
| R4 — filtro da compressão | Tabela só filtrava por texto livre e Status não alinhava com o badge | Status centralizado; seletor de campo (todos, nome/arquivo, status, progresso, tamanho, economia, erro) ao lado do filtro; `1160x800-light-settings-cookies.png` e `940x620-light-compression.png` |
| R4 — cookies/updates | Botão de cookies pouco visível e ações de atualização sem contraste | “Escolher…” com ícone/superfície e sempre visível; “Atualizar tudo”/“Verificar novamente” com ícones e borda; “Atualizar” por dependência idem |
| R4 — Lote/Individual | Label de formato desalinhada; download individual sem cancelar | Linha de formato em RowLayout centralizado; botão Cancelar na SinglePage e na lista de progresso |
| UI-01 | Em 940×620, o rodapé da aba Lote truncava os contadores (`0 aguardando · 0 baixando · 0 concluídos · 0…`) | Contadores com `wrapMode: Text.Wrap` (2 linhas) e barra de progresso oculta abaixo de 1050 px |
| UI-01/03 | Em 940×620, a aba Compressão empurrava o rodapé para fora da janela | Altura mínima do painel de ajustes (300), fila (100), rodapé fixo; scrollbars verticais sempre visíveis nos painéis de configuração |
| UI-06 | Toast de uma linha truncava mensagens longas | Até 3 linhas, largura maior, duração proporcional ao texto e dispensa por clique |
| Diálogos | Conteúdo do diálogo de erro tocava as bordas do surface | `AppDialogSurface` com margens de 16 px |
| UI-04 | Botões da barra de título e cabeçalhos de ordenação sem foco por teclado | Foco restaurado, contorno visível e `Button` semântico nos cabeçalhos |

As capturas `940x620-light-batch.png`, `940x620-light-compression.png`,
`1160x800-light-error.png` e `1160x800-light-toast.png` comprovam as correções
principais.

## Cabeçalho descritivo (inspirado no DiskPilot)

**Avaliação:** a ideia funciona, mas um bloco grande em todas as abas
prejudicaria a densidade em 940×620. A implementação adotada é uma faixa de
68 px, com degradê horizontal, barra de acento e brilho discreto, contendo:

- título da aba;
- uma frase curta explicando o fluxo;
- ações contextuais (em Compressão, “Adicionar arquivos/pasta”).

Em janelas menores a faixa continua presente em modo compacto: mostra o
título e o degradê, oculta a descrição e reduz a altura (40 px sem ações,
52 px com ações). Assim não há salto de hierarquia entre 940×620 e 1160×800.
Capturas: `1160x800-light-single.png`, `1160x800-light-batch-hero.png`,
`1160x800-dark-compression-hero.png`, `1366x768-light-settings-hero.png` e
`940x620-light-batch.png`.

O degradê usa tokens de tema (`heroFrom`, `heroTo`, `heroBorder`) e
`accentFill`, com contraste de texto vindo de `theme.text`/`textSecondary`.

## Pastas e ações (R3)

- `FolderPickerField` é somente leitura, elide o caminho no meio e expõe o
  caminho completo em tooltip; Alterar/Abrir/Copiar ficam visíveis em repouso.
- Cancelar o seletor preserva o destino anterior; pasta sem permissão de
  escrita não substitui a configuração.
- Abrir pasta usa um helper único; pasta removida ou gestor indisponível gera
  notificação em vez de erro silencioso.
- Adicionar pasta na compressão sem mídia elegível agora notifica o usuário.
- Ações de fila usam contadores reais para habilitar/desabilitar, reduzindo
  cliques sem efeito.

## O que permanece como ressalva

- Em 940×620, a seção “Geral” da compressão exige rolagem para ver todos os
  campos; o scrollbar está visível e o rodapé permanece acessível. O estado
  vazio da fila fica comprimido (cabeçalho e filtro visíveis, mensagem não).
- Em 1920×1080 a interface fica esparsa, sem corte; não foi feito redesign.
- A tipografia de 11–12 px foi mantida; a leitura nas capturas é aceitável,
  mas não houve teste com usuários ou medição formal de contraste WCAG.
- Não houve navegação com leitor de tela nem captura em Linux/macOS.
- Escalas 125/150/200% foram capturadas em todas as abas, mas a inspeção
  detalhada foi feita em amostras.
- Diálogos de qualidade, dependências, recuperação e similares não foram
  capturados individualmente nesta rodada.

## Próximo passo de UI

1. Revisar os diálogos restantes com o mesmo harness, especialmente
   `QualityConfirmDialog` e `DepsDialog`.
2. Medir contraste dos textos secundários e estados desabilitados.
3. Testar teclado completo (Tab/Shift+Tab/Enter/Espaço/Esc) em Windows e
   Linux.
4. Decidir se o painel de compressão em 940×620 deve virar uma página
   rolável única em vez de dois cards comprimidos.
