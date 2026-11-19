# Revisão de código — R5 (18/11/2026)

**Escopo:** estado atual do checkout após a R5 (`feat/media-integrity-similarity`,
HEAD `e236962`), comparado ao pacote `HLSDownloaderPro-audit-2026-11-18-r5.zip`.
**Método:** leitura de código, rastreio de chamadas Python↔QML, execução da suíte
Qt offscreen e inspeção de capturas. Não houve teste em macOS/Linux, CI real,
leitor de tela nem hardware de GPU.

## Resumo

- **R5-01 (ordenação da Compressão)**: o pacote R5 empacotado ainda ordenava a
  lista compartilhada. O checkout atual já contém uma correção posterior:
  `_items` permanece na ordem de agendamento e `_display` guarda apenas a ordem
  visual. Revisei, executei os testes e considerei a correção adequada. O
  achado continua válido **para o ZIP R5**, não para o código atual.
- **Alinhamento dos tooltips**: corrigido nesta revisão. O conteúdo agora é
  centralizado horizontal e verticalmente; título, corpo e rodapé usam
  `Text.AlignHCenter`/`Text.AlignVCenter`, e o bloco é centralizado no popup.
- **Continuação R5.1**: varredura de pastas movida para thread auxiliar com
  contagens e cancelamento; ordenação por status ganhou rank de fluxo; CI de
  `qmllint` passou a distinguir avisos de erros; projeção da fila ganhou
  benchmark e throttle adaptativo.
- **Riscos abertos**: validação real do CI, stress de pastas gigantes/rede,
  medição formal de legibilidade/DPI e traduções longas em 940×620.

## Achados

| Prioridade | Arquivo/símbolo | Evidência | Impacto | Correção mínima | Teste/estado |
|---|---|---|---|---|---|
| **P1/P2** | `hlsdl/compress.py` — `CompressionModel._display` e `CompressionManager._next_waiting` | `_items` é a lista compartilhada; `sortBy()` reconstrói `_display`; `_next_waiting()` percorre `self.items` | Clicar no cabeçalho não muda mais a ordem real de processamento | Manter a separação; ações usam `sourceIndex` | `test_compression_model_sorting_is_display_only`, `test_compression_sort_does_not_change_scheduler_pick`; **resolvido no checkout atual** |
| **P2** | `hlsdl/ui/pages/CompressionPage.qml` — ações da linha | `cancelCompressionItem(model.sourceIndex)` etc. | Evita cancelar/remover a linha errada quando a tabela está ordenada | Usar sempre o papel `sourceIndex` | `test_compression_actions_reference_source_index`; `test_compression_row_actions_use_source_rows_after_sort` |
| **P2** | `hlsdl/ui/components/AppToolTip.qml` — conteúdo | Título/corpo/rodapé estavam alinhados à esquerda e ao topo | Texto visualmente desalinhado, principalmente com atalho e rodapé | `contentItem` com bloco centralizado + `AlignHCenter`/`AlignVCenter` | `test_rich_tooltips_open_inside_window_and_expose_shortcut`; capturas R5 atualizadas |
| **P2** | CI / `pyside6-qmllint` | 44 avisos no baseline R4; 48 no checkout atual; saída não-zero no Windows/PySide6 6.12 | CI pode falhar mesmo sem erro de sintaxe/tipo | Workflow agora bloqueia `[syntax]`/`is not a type`/`Could not find property`/`Expected token`/`^Error:` e só falha por rc se não houver Warning | **mitigado no workflow** — CI real ainda não executado |
| **P2** | `hlsdl/bridge_parts/compression.py` — `addCompressionFolder` | Varredura recursiva agora em `scan_media_paths` + thread auxiliar rastreada | UI não bloqueia; contagens e cancelamento disponíveis | Manter scan fora da GUI e `add_scanned` na GUI | **resolvido** — `test_scan_media_paths_counts_dedup_and_cancel`, `test_compression_folder_scan_reports_counts`; 10 mil arquivos ainda não stressados |
| **P3** | `hlsdl/model.py` — `DownloadModel.snapshot()` + `BatchPage.rebuildBatchRows()` | Benchmark: 1k 0,6 ms; 10k 6,4 ms; 50k 36,2 ms (snapshot) | Custo O(n) por atualização em filas muito grandes | Throttle 120/250/500 ms conforme tamanho; benchmark reproduzível | **mitigado** — `scripts/bench_queue_projection.py` |
| **P3** | `hlsdl/compress.py` — `CompressionModel._sort_value("status")` | Rank de fluxo substituiu a string alfabética | Ordenação previsível: analyzing → encoding → verifying → waiting → done → error → skipped → cancelled | Mapa `_COMPRESS_STATUS_RANK` | **resolvido** — `test_compression_status_sort_uses_workflow_rank` |
| **P3** | `hlsdl/ui/components/AppToolTip.qml` | Corpo 12 px, rodapé 11 px; atalho 11 px | Legibilidade em DPI alto/traduções longas não medida | Testar 100–200% e oito idiomas; ajustar tokens se necessário | **aberto** — capturas em 100% |
| **P3** | Layouts estreitos / traduções | “Ocultar ajustes” e filtros em 940×620 | Pode haver corte com strings longas (fr/it/ru) | Testar 940×620 em todos os idiomas e 125–200% | **parcial** — pt em 940×620 validado |

## O que foi alterado nesta revisão

- `hlsdl/ui/components/AppToolTip.qml`: conteúdo em `Item` com `ColumnLayout`
  centralizado; título, corpo e rodapé com alinhamento central nos dois eixos;
  `objectName` nos textos para teste.
- `tests/test_tooltips.py`: valida alinhamento horizontal/vertical e centro
  geométrico do bloco.
- `tests/test_table_tools.py`: guarda a ligação das ações ao `sourceIndex`.
- `tests/test_compress.py`: cobre cancelamento pelo índice de agendamento após
  ordenação visual, rank de status, varredura/deduplicação/cancelamento, teto
  de arquivos e erro de `os.walk`.
- `tests/test_table_tools.py`: cobre também a coalescência do timer sob
  progresso a ~100 Hz e o contrato `loadPlaylist(url, limit)` no root QML.
- `hlsdl/compress.py`: `scan_media_paths()` e `add_scanned()` separam a
  enumeração (thread auxiliar) da mutação do modelo (GUI).
- `hlsdl/bridge_parts/compression.py` + `signals.py`: `compressionScanBusy`,
  `compressionScanFinished`, cancelamento e resumo com contagens.
- `.github/workflows/ci.yml`: `qmllint` só falha por padrões bloqueantes/erros;
  avisos conhecidos não derrubam o job.
- `scripts/bench_queue_projection.py`: benchmark da projeção da fila.

## Adendo R7-L — falhas de execução e rate control

| ID | Estado | Evidência/teste |
|---|---|---|
| R7-L01 — clipboard sem import | **corrigido** | `downloads.py` usa `QApplication.clipboard()` com erro controlado; `test_copy_link_uses_the_imported_clipboard`, `test_copy_link_reports_unavailable_clipboard` |
| P1 anterior — `allow-unsafe-ext` | **já ausente no checkout** | `downloader.py` não monta retry inseguro; `test_ytdlp_never_retries_with_allow_unsafe_ext` |
| R7-L02 — Playlist com ids de outro QML | **corrigido** | `main.qml::loadPlaylist(url, limit)` recebe argumentos; `PlaylistPage.qml` passa `playlistUrl.text`/`playlistLimit.value`; `test_playlist_page_passes_url_and_limit_to_main` |
| R7-L03 — AV1 QSV falha com bitrate alvo | **hotfix** | `video_args("av1_qsv", ..., target_bitrate)` não emite `-b:v/-maxrate/-bufsize`; UI desabilita o alvo para AV1 QSV; teste de argumentos. Validação no hardware/driver real continua pendente |
| R7-L04 — “piso” não é piso | **corrigido no modelo/UI** | rótulo “Bitrate alvo”, tooltip explica VBR não garantido; backend ignora o alvo em AV1 QSV |
| R7-L05 — perfil por Playlist | **adiado** | evolução funcional (snapshot por item); fora desta rodada para não alterar o pipeline de fila sem contrato/teste dedicados |
| R7-L06 — SSIM/bitrate HEVC | **documentado** | SSIM amostral e bitrate de contêiner não são prova de qualidade integral; investigação A/B com VMAF fica pendente |
| R7-L07 — QUALITY_MAX AV1 QSV | **corrigido** | `quality_max_for_encoder`: AV1 QSV = 51, AV1 software = 63; UI e backend usam o limite efetivo |
| R7-01 — qmllint permissivo | **melhorado** | CI bloqueia padrões fatais e linhas não classificadas; ainda não executado no runner real |
| R7-02 — debounce adiado | **corrigido** | `batchSyncTimer.start()` coalescente (sem `restart()`), prazo máximo respeitado; teste estático |
| R7-03 — scan sem orçamento | **mitigado** | teto de 100 mil arquivos, resultado truncado sem adição parcial, métricas e cancelamento; I/O bloqueante de rede continua limitação |
| R7-04 — reset ao ordenar | **aceito** | tabela de Compressão não possui seleção persistente; reset não perde estado de seleção. Scroll não foi medido |
| R7-05 — DPI/idiomas/contraste | **parcial** | fr/it/ja/zh em 940×620 couberam; russo trunca estatísticas; sem WCAG/leitor de tela |

## R9/R10 — projeção Python e motion

- **Lote**: `DownloadFilterProxyModel` (`QSortFilterProxyModel`) substitui o
  `ListModel`/snapshot JS; filtro por tokens, ordenação por nome/status/progresso
  e `sourceIndex` estável. `BatchPage` não reconstrói mais a tabela em JS.
- **Barra de título**: tooltips compactos (96–150 px), animação de minimizar/
  restaurar com tokens de movimento e um único handler de `onVisibilityChanged`.
  Os controles usam `Qt.TabFocus`/`visualFocus`, então o clique do mouse não
  deixa anel de foco persistente; Tab continua acessível.
- **Motion tokens**: `hlsdl/ui/motion.js` para durações compartilhadas.
- **Testes**: proxy unitário, tabela, contrato de motion e smoke QML.

## Verificação

- `pytest -o addopts="" -q -ra`: **318 passed, 2 skipped** (320 coletados).
- `ruff check hlsdl tests main.py worker.py diagnostico.py exportar.py`:
  **All checks passed**.
- `compileall`: exit 0.
- `smoke_test.py`, `_i18n_test.py`: OK.
- `pyside6-qmllint`: 0 padrões bloqueantes; 44 avisos no baseline R4 e 48 no
  total atual, todos de `unqualified access`/`missing-property`. A saída é
  não-zero por causa dos avisos nesta versão do PySide6; o CI real precisa ser
  confirmado no runner Linux.
- Capturas: `scripts/ui_table_audit.py docs/ui-review/r5` (13/13, 0 falhas).
- Benchmark: 1k/10k/50k itens = 0,6/6,4/36,2 ms por snapshot; a projeção usa
  throttle de 120/250/500 ms conforme o tamanho.
- Varredura de 10 mil arquivos vazios em pasta plana: 0,568 s em thread
  auxiliar (não bloqueia a GUI; não mede rede/permissões).

## Limitações

- O pacote R5 histórico contém o bug R5-01; o checkout atual não. Não reescrevi
  a história do pacote: a correção está documentada aqui e no pacote R7.
- Não houve teste real de CI, macOS/Linux, leitor de tela, contraste WCAG ou
  GPU. A varredura assíncrona não foi stressada com 10 mil arquivos, permissões
  negadas ou symlink loops em volume; os casos vazios/cancelamento têm teste.
- Em 940×620, fr/it/ja/zh couberam no scan; com russo a linha de estatísticas
  foi truncada (botões continuaram acessíveis). `_languages_test.py` cobre os
  oito idiomas, mas não é um teste de layout.
