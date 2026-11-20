# Resposta à terceira reauditoria (R3) — 2026-11-18

Base: `HLSDownloaderPro-audit-2026-11-18-r2.zip` + alterações desta rodada.
Confirmado por código e testes locais; o que depende de CI/SO/hardware está
marcado como pendente.

## UX

| ID | Status | Evidência |
|---|---|---|
| UX-19-01 — hierarquia de botões | implementado | `AppButton` com `variant` (`primary`, `secondary`, `tertiary`, `danger`) e `size` (`normal`, `compact`); `highlighted` preservado como compatibilidade. Secundários têm superfície/borda em repouso |
| UX-19-02 — pasta de saída navegável | implementado | `FolderPickerField.qml` com caminho elidido/tooltip, Alterar, Abrir, Copiar, validação de escrita e feedback; integrado em Configurações; captura `1160x800-light-settings-folder.png` |
| UX-19-03 — adicionar pasta à compressão | parcial | pasta sem mídia elegível agora emite mensagem; ainda não há pré-varredura assíncrona, opção explícita de subpastas nem contagem de ignorados |
| UX-19-04 — ações de fila contextuais | implementado (estado) | Iniciar/Cancelar/Limpar derivam de `statWaiting`, `statDownloading`, `compWait`, `compWork`, `compDone`, `compErr`, `compSkip`; desabilitados sem operação aplicável |
| UX-19-05 — abrir pastas | implementado | helper único `_open_directory`; `openDownloadPath` e `openLogFolder` notificam pasta ausente/erro em vez de `pass`; `openOutputFolder` adicionado |
| UX-19-06 — tipografia/densidade | pendente | nenhuma alteração ampla de escala sem teste visual/usuário; compressão em 940×620 continua rolável |
| UX-19-07 — estados vazios | parcial | aba Lote mostra estado vazio completo em 940×620 e esconde filtro/hint quando não há itens; Compressão mostra estado vazio; CTAs adicionais ainda pendentes |

## Segurança e release

| ID | Status | Evidência |
|---|---|---|
| SEC-R2-A — sandbox de rede | documentado | `THREAT_MODEL.md`; nenhuma alegação de sandbox; yt-dlp/FFmpeg seguem com resolução/redirect próprios |
| SEC-R2-B — `allow-unsafe-ext` | removido na R8 | o fallback inseguro não existe mais; a URL é recusada e o fluxo seguro de raspagem/ffmpeg continua. `_looks_like_non_video` permanece como validação de mídia |
| REL-R2-A — update | implementado | hosts GitHub, tetos de API/manifesto/assinatura, tamanho durante streaming, redirect final e `version_key` |
| REL-R2-B — rastreabilidade | pendente | sem `.git` no ZIP; CI real e release assinada de teste ainda não executadas |
| QA-R2-A — cobertura por risco | pendente | gate global de 60%, cobertura 67,63%; sem branch coverage/mutation testing |
| COMP-R2-A — HDR | QSV validado | MKV/MP4 reais com QSV; NVENC/AMF e macOS/Linux pendentes |

## Testes adicionados nesta rodada

- `tests/test_ux19.py`: abertura de pasta, pasta ausente, destino sem escrita,
  pasta de compressão vazia.
- `tests/test_updater.py`: hosts confiáveis, limite de manifesto e ordem de
  prerelease/build metadata.
- `tests/test_p1_regressions.py`: validação de conteúdo disfarçado e garantia
  de que `_run_ytdlp` nunca reativa `allow-unsafe-ext`.

## Ajustes solicitados pelo mantenedor (R4)

- **Botões**: `AppButton` voltou a uma aparência Material mais clássica e maior
  (44 px normal, 36 px compact), com variantes primary/secondary/tertiary/danger,
  borda/superfície visível em repouso, ícones 18 px e estados hover/pressed.
- **Barra de título**: mantida a melhoria de gradiente/versão em pill; controles
  de janela continuam com hover/pressed próprios.
- **Tabela de compressão**: cabeçalho “Status” centralizado sobre o badge;
  coluna de filtro com seletor de campo (todos, nome/arquivo, status, progresso,
  tamanho, economia, erro) e campo de texto; colunas alinhadas com os delegates.
- **Cookies**: botão “Escolher…” agora tem superfície, ícone de arquivo e fica
  visível mesmo com cookies desativados; o toggle continua controlando o uso.
- **Dependências/atualizações**: “Atualizar tudo” e “Verificar novamente” têm
  ícones, borda e contraste; cada dependência tem botão “Atualizar” com ícone.
- **Lote**: linha “Formato da fila” usa RowLayout com alinhamento vertical
  central entre label, seletores, resumo e “Opções…”.
- **Download individual**: botão “Cancelar” aparece enquanto o item individual
  está ativo ou aguardando.
- **Encoding**: corrigidos `Â·`, `Ã©`, `Ã§` e similares em QML/Python que
  apareceram em uma edição intermediária; QML e bridge_parts voltaram a UTF-8
  sem BOM.

Evidências novas: `docs/ui-review/1160x800-light-settings-folder.png`,
`940x620-light-compression.png`, `1160x800-dark-compression-hero.png`,
`1160x800-light-batch-hero.png` e `940x620-light-batch.png`.

## Verificação local

- `295 passed` com `HLSDL_TEST_QSV=1`; sem a variável, `293 passed, 2 skipped`.
- Cobertura: `67,63%` (8638 statements, 2796 missed), gate de 60%.
- 5 execuções consecutivas da suíte completa sem crash.
- `ruff`, `mypy`, `compileall`, `pyside6-qmllint`: limpos.
- `smoke_test`, `_i18n_test` e `functional_test`: OK.

## Limitações

- A seleção de pasta da compressão ainda é síncrona; 10 mil arquivos e
  symlink loops não foram medidos.
- Não houve teste real em Linux/macOS, leitor de tela ou contraste WCAG.
- A matriz completa de estados idle/queued/running/paused/done/error foi
  verificada por código/capturas parciais, não por E2E de cada estado.
- CI, release assinada e stress de I/O continuam fora desta máquina.

---

## Rodada R5 — tooltips ricos, filtros e alinhamento de tabelas

Escopo desta rodada, sem alterar a semântica de downloads/compressão:

- **Tooltips ricos** (`components/AppToolTip.qml`): título, descrição longa,
  atalho em badge, ícone, rodapé contextual, abertura por hover ou foco de
  teclado, fechamento ao sair/pressionar, posicionamento no Overlay com flip
  acima/abaixo e limites da janela. Todos os `ToolTip` anexados das telas foram
  migrados; `AppButton`, `AppToolButton`, `AppComboBox`, `AppSpinBox`,
  `AppHintField`, abas e barra de título expõem `tipTitle`/`tipText`/
  `tipShortcut` e `Accessible.description` derivado. Na revisão R5.1 o bloco de
  conteúdo passou a ser centralizado horizontal e verticalmente; título, corpo e
  rodapé usam `AlignHCenter`/`AlignVCenter` e há teste geométrico para isso.
- **Filtro dinâmico** em Lote e Compressão: busca única em todas as colunas,
  sem combobox de campo, com normalização de acentos/caixa e prefixos
  (`status:`, `nome:`/`titulo:`, `erro:`, `tamanho:`, `economia:`) combináveis
  por E. `Ctrl+F` foca o filtro da aba ativa e `Esc` limpa.
- **Ordenação por cabeçalho**: Lote ordena por título, status e progresso;
  Compressão por arquivo, status, progresso e tamanho final. O indicador
  (▲/▼) fica junto ao rótulo, com foco por teclado e tooltip explicando a
  ordem. No Lote a ordenação é somente visual: `sourceIndex` preserva a ordem
  de agendamento da fila.
- **Tabela de Compressão**: larguras de coluna compartilhadas entre cabeçalho
  e delegate (`compColStatus`, `compColProgress`, `compColResult`,
  `compColActions`), cabeçalho de 36 px com todos os rótulos no mesmo Y,
  coluna “Ações” explícita e correção do “Arquivo” fora de posição. O teste
  compara a geometria real de cabeçalho × linha em 1160×800 e 940×620.
- **Densidade em 940×620**: botão “Ocultar ajustes”/“Mostrar ajustes” recolhe
  o painel de configuração da Compressão; a fila ocupa a altura liberada.
  Em 940×620 o painel expandido mantém rolagem interna.
- **Estados vazios**: Compressão distingue “nenhum vídeo” de “nenhum
  resultado”; Lote distingue fila vazia de filtro sem resultado, com texto de
  próximo passo.
- **i18n**: novas chaves de tabela/tooltips/ajustes nos oito idiomas; teste de
  paridade e de cobertura de chaves QML mantido.
- **Rastreabilidade**: `DownloadModel.snapshot()` é somente leitura e devolve
  `sourceIndex`; nenhum caminho de rede, subprocesso ou exclusão de arquivo foi
  alterado nesta rodada.

### Itens R3 afetados

| ID | Antes (R4) | Depois (R5) |
|---|---|---|
| UX-19-06 — densidade em telas pequenas | pendente/parcial | **melhorado**: ajustes recolhíveis na Compressão; fila utilizável em 940×620. Tipografia global não foi alterada |
| UX-19-07 — estados vazios | parcial | **melhorado**: vazio × sem resultado separados em Lote/Compressão, com microcopy de ação |
| UX-19-01 — hierarquia de botões | implementado | mantido; tooltips agora explicam comandos e atalhos |
| UX-19-04 — ações de fila | implementado (estado) | mantido; ações de linha continuam desabilitadas/ocultas por estado e recebem tooltip contextual |

### Evidências visuais

`docs/ui-review/r5/` contém 13 capturas produzidas por
`scripts/ui_table_audit.py` (dados sintéticos, Qt offscreen):

- Compressão: linhas, filtro `status:erro`, ordenação por arquivo, tema escuro,
  940×620 expandido e 940×620 com ajustes recolhidos.
- Lote: linhas, filtro `status:erro`, ordenação por título, tema escuro e
  940×620.
- Tooltips: ordenação (título + descrição + rodapé) e atalho `Ctrl+V`.

### Correção R5-01 — ordenação da Compressão

A ordenação da tabela de Compressão não reordena mais a lista compartilhada
com o `CompressionManager`. O modelo mantém duas ordens:

- `_items`: ordem de agendamento, intocada; é a lista consumida por
  `_pump()`/`_next_waiting()`.
- `_display`: ordem apenas visual, alterada por `sortBy()`.

Cada linha expõe o papel `sourceIndex`; as ações de cancelar, tentar de novo e
remover usam esse índice, não a posição exibida. `remove_rows()` continua
recebendo índices de agendamento e reconstrói a exibição. Regressões em
`tests/test_compress.py` cobrem ordenação, remoção/inserção e a escolha real
do próximo item pelo scheduler.

### Continuação R5.1 — itens restantes

- **Varredura de pastas assíncrona**: `scan_media_paths()` enumera em thread
  auxiliar rastreada; `add_scanned()` muta o modelo apenas na GUI. A UI mostra
  “Verificando pasta…”, permite cancelar e recebe um resumo com adicionados,
  ignorados, duplicados e erros. `os.walk` não segue symlinks de diretório e
  checa cancelamento periodicamente.
- **Ordenação por status previsível**: `_COMPRESS_STATUS_RANK` ordena por fluxo
  (analyzing → encoding → verifying → waiting → done → error → skipped →
  cancelled), não por string alfabética.
- **CI/qmllint**: o workflow agora bloqueia erros reais (`[syntax]`,
  `is not a type`, `Could not find property`, `Expected token`, `^Error:`) e só
  falha pelo código de saída quando não há qualquer `Warning`. A execução real
  do CI continua pendente.
- **Desempenho da fila**: `scripts/bench_queue_projection.py` mede 1k/10k/50k
  itens; a projeção do Lote usa throttle de 120/250/500 ms conforme o tamanho,
  reduzindo reconstruções desnecessárias. Varredura de 10 mil arquivos vazios
  em pasta plana levou 0,568 s em thread auxiliar; rede/permissões não medidos.
- **Testes**: 318 passed, 2 skipped (320 coletados); inclui varredura,
  cancelamento, deduplicação, rank de status, clipboard e Playlist.

### Adendo R7-L — correções de execução

- **Clipboard**: `copyLink` usa `QApplication.clipboard()` com tratamento de
  indisponibilidade; sem `NameError`; testes de sucesso e falha.
- **Playlist**: `loadPlaylist(url, limit)` recebe argumentos explícitos;
  `PlaylistPage` passa URL/limite no botão e no Enter; não há mais ids QML
  cruzados entre arquivos.
- **AV1 QSV**: o alvo VBR é ignorado no backend e desabilitado na UI para
  `av1_qsv`; qualidade limitada a 51 nesse encoder (software AV1 segue 63).
- **Bitrate alvo**: o rótulo/tooltip deixam claro que é alvo VBR aproximado,
  não piso garantido.
- **Timer da fila**: coalescência com `start()` em vez de `restart()`, sem
  adiar indefinidamente a atualização.
- **Scan**: teto de 100 mil arquivos; resultado truncado não adiciona itens
  parciais.
- **Pendências**: validação AV1/QSV em hardware real, perfil por item da
  Playlist (R7-L05) e investigação SSIM/VMAF (R7-L06).

### R9/R10 — projeção Python e motion

- A aba Downloads usa `DownloadFilterProxyModel` (`QSortFilterProxyModel`) com
  filtro por tokens, ordenação por nome/status/progresso e `sourceIndex`
  estável; a projeção em `ListModel`/JavaScript foi removida.
- A antiga aba Playlists foi absorvida: `Carregar playlist` abre um diálogo na
  aba Downloads, marca os itens por padrão, permite filtrar/desmarcar/limpar e
  envia os selecionados para a mesma fila.
- A barra de título ganhou tooltips compactos, animação de minimizar/restaurar
  e foco visual apenas por teclado (`Qt.TabFocus`/`visualFocus`); durações
  compartilhadas em `hlsdl/ui/motion.js`.

## Verificação local (R5)

- `python -m pytest -q`: **318 passed, 2 skipped** (320 coletados).
- `ruff check hlsdl tests main.py worker.py diagnostico.py exportar.py`:
  **All checks passed**.
- `compileall`: exit 0.
- `pyside6-qmllint` em main/pages/dialogs/components: sem
  `[syntax]`, `is not a type`, `Could not find property` ou `Expected token`;
  o baseline R4 tinha 44 avisos de `unqualified access`/`missing-property` e o
  total atual é 48, incluindo referências novas do atalho Ctrl+F. Nenhum é
  bloqueante para a regra da CI.
- `smoke_test.py` e `_i18n_test.py`: OK.
- Capturas: `scripts/ui_table_audit.py docs/ui-review/r5` (13/13, 0 falhas).

## Limitações (R5)

- A varredura de pasta da compressão agora é assíncrona e cancelável, mas ainda
  não foi stressada com 10 mil arquivos, permissões negadas ou symlink loops em
  volume; os casos vazios, contagem e cancelamento têm teste.
- Não houve leitor de tela, macOS/Linux real, medição formal de contraste WCAG
  nem captura de hover real: os tooltips foram verificados por abertura
  programática, geometria e conteúdo.
- A ordenação do Lote e da Compressão é de exibição; as ordens de agendamento
  do `QueueManager` e do `CompressionManager` permanecem as de inserção.
- Tooltips tiveram o corpo elevado para 12 px e o rodapé para 11 px; ainda
  faltam medição formal de legibilidade em DPI alto e teste com leitor de tela.
- Em 940×620, fr/it/ja/zh couberam durante o scan; com russo a linha de
  estatísticas foi truncada, mas as ações permaneceram acessíveis.
- A cobertura não foi remedida nesta rodada; o gate global de 60% permanece.
