# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o versionamento segue [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Compressão em hardware (R12u)

- **Fallback automático**: quando o encoder de hardware falha na abertura
  (QSV/NVENC/AMF), o job tenta o mesmo QSV com `-low_power 0` e, se ainda
  falhar, refaz com o encoder de software do codec. O original só é mantido
  se todas as tentativas falharem.
- **Diagnóstico reproduzível**: cada falha registra resolução, codec,
  `pix_fmt`, HDR, contagem de áudio/legendas, encoder, tentativa e comando do
  FFmpeg com os caminhos locais redigidos.
- **Formato de hardware explícito**: encoders QSV/NVENC/AMF recebem
  `-pix_fmt nv12` ou `p010le`, evitando que fontes 4:2:2/4:4:4 cheguem ao
  driver num layout recusado.
- **Linha da fila atualizada**: ao cair para software, o item mostra o encoder
  realmente usado.

## [1.5.0] - 2026-11-21 — padrão-ouro: catálogo, SSIM, HDR, fila e CLI

### Janela e foco (R12t)

- **Minimizar preserva a maximização**: o estado maximizado passou a ser
  rastreado em `isMaximized`, separado da visibilidade Qt; ao restaurar, a
  janela volta maximizada (ou normal, se era normal) em vez de cair para o
  modo janela e exibir o botão "restaurar".
- **Foco não fica na barra de título**: ao minimizar, o item focado é
  memorizado e restaurado ao voltar, ignorando controles da barra de título.
  Os controles da barra não recebem foco por clique e não mostram tooltip
  apenas por foco, evitando a bolha imediata no toggle de tema.

### Correções finais (R12q)

- **Logs de dependências no idioma da UI**: o terminal de instalação e
  atualização de yt-dlp/ffmpeg agora usa o idioma selecionado, inclusive nos
  estados de download, checksum, sucesso, falha, cancelamento e fallback.
  Mensagens internas do `pip`/gerenciador de pacotes continuam sendo a saída
  nativa da ferramenta.
- **Ícones de navegadores em alta resolução**: os logotipos passaram a ser
  exibidos em 20 px, rasterizados a 32 px e com mipmap, mantendo nitidez em
  telas HiDPI e no popup do seletor.

### Identidade Cobalt Slate (R12p)

- **Acento de execução**: o azul-cobalto `#2563EB` passa a identificar
  iniciar/baixar/confirmar, com hover `#1D4ED8` e pressed `#1E40AF`.
- **Verde semântico**: os botões de início deixaram de usar `success`; o verde
  fica reservado a conclusão, integridade validada e confirmações de sucesso.
- **Superfícies azul-acinzentadas**: janela `#F3F6FB`, cards brancos e tema
  escuro `#111923`/`#1B2633`, com bordas, inputs, tabelas e hovers ajustados.
- **Hierarquia de ações**: preenchido para executar/confirmar; tonal
  azul-acinzentado para importar, colar, adicionar e analisar; contorno para
  configurações, seleção de pasta, opções e ações auxiliares; transparente para
  baixa prioridade.
- **Geometria**: raio dos botões em 8 px e espaço ícone-texto em 8 px,
  preservando alturas de 44/36 px, hover e escala de pressão.
- **Contraste**: testes cobrem texto do tema e os estados base, hover, pressed
  e disabled dos botões preenchidos e tonais.

### Licença GPLv3 (R12s)

- **Licença do projeto**: o código passou de MIT para **GPL-3.0-only**, em
  alinhamento com o uso de PySide6/Qt (LGPLv3/GPLv3) e com os demais
  componentes. Os avisos de terceiros continuam em `THIRD_PARTY_NOTICES.md`.
- **Instalador**: o texto completo da GPLv3 é exibido/licenciado pelo Inno
  Setup e incluído no pacote.

### Idiomas, RTL e dependências (R12q)

- **Novos idiomas**: alemão, árabe, hebraico, coreano e português de Portugal
  entram no seletor, no catálogo da UI, nas mensagens do backend e nos testes
  de paridade.
- **Português de Portugal**: variante `pt_pt` com «ficheiro», «transferência»,
  «definições», «utilizador», «ligação» e «gestor», bandeira própria e opção
  separada no instalador.
- **RTL**: árabe e hebraico ativam `LayoutMirroring`, direção RTL do Qt e
  espelhamento de navegação, tabelas e alinhamento de texto.
- **Aba Sobre**: página dedicada com identidade, versão, licença GPLv3,
  atualizações, repositório, issues, dependências, logs e pasta de saída; o
  card de atualizações saiu de Configurações.
- **Saída localizada**: o terminal de dependências segue o idioma selecionado,
  inclusive em `dep_log_downloading`, checksums e erros de instalação.
- **Glossário técnico**: codec, bitrate, container, preset, stream, playlist,
  checksum, encoder, GPU, HDR, SSIM, NVENC/QSV/AMF permanecem em inglês ou
  entre parênteses, evitando traduções literais que dificultam a leitura.
- **Ícones de navegador**: placas de 32 px, ícones de 24 px e rasterização
  em 48 px para telas HiDPI; o popup de idiomas ganhou superfície opaca e
  altura limitada com rolagem.

### Polimento de diálogos e edição (R12)

- **Diálogos expressivos**: `AppDialogSurface` ganhou cabeçalho em degradê com
  ícone, título/subtítulo, botão de fechar, arrastar pelo cabeçalho,
  redimensionamento pelo canto e expandir/restaurar. Os mini-formulários de
  Playlist e Opções usam a mesma superfície; títulos longos são elididos e a
  largura respeita a janela.
- **Botões da Playlist**: ações de selecionar/limpar/fechar deixaram o estilo
  de texto e passaram a usar as variantes com borda/ícone dos demais botões.
- **Títulos de aba maiores**: o `PageHero` aumentou o título e mantém elide/clip
  para não vazar do degradê em larguras menores.
- **Scrollbar da Compressão**: as grades reservam uma calha à direita para a
  barra vertical não cobrir o último controle.
- **Edição da fila**: o campo inline ganhou um “x” para cancelar sem Esc e a
  coluna Ações ganhou lixeira para remover o item diretamente.
- **Menu de contexto i18n**: `AppHintArea`/`AppHintField` substituem o menu
  nativo do Qt por Desfazer/Refazer/Recortar/Copiar/Colar/Excluir/Selecionar
  tudo traduzidos nos treze idiomas.
- **Hover destrutivo**: fechar, remover, excluir e limpar usam fundo/texto
  avermelhados no hover, com `hoverEnabled` ativo nos botões.
- **Cantos do título**: o cabeçalho em degradê usa raios independentes nos
  cantos superiores, acompanhando o raio da janela e sem vazar do diálogo.
- **Grip de redimensionamento**: três traços diagonais no canto, em vez de um
  único traço que se confundia com scrollbar.
- **Limpeza de inputs**: campos de texto ganharam botão “×” com tooltip e
  `Esc` para limpar; os campos com botão externo mantêm o botão existente.
- **Scrollbars sem sobreposição**: gutters reservados em configurações, filas,
  playlist, terminal, detalhes de erro e similaridade.
- **Contraste de inputs/tabelas**: novos tokens `inputBg`/`inputBorder`/
  `tableBg` deixam campos e tabelas um tom abaixo dos cards. O seletor de
  pasta também usa essa superfície.
- **Configurações mais expressivas**: cada card ganhou ícone no título e os
  botões Alterar/Abrir da pasta usam ícones e o mesmo estilo das demais abas.
- **Títulos maiores**: PageHero e cabeçalhos de diálogo aumentaram título e
  descrição para leitura mais confortável.
- **Ícones em botões primários**: novos SVGs `*_accent.svg` garantem contraste
  branco em “Adicionar à Fila”, “Baixar agora”, “Iniciar Fila” e afins.
- **Labels de controles maiores**: títulos de campos em Configurações, Compressão,
  Download Individual, Playlist e Opções subiram para 13–14 px.
- **Fila de compressão completa**: checkbox por item, selecionar tudo,
  remoção múltipla e menu de contexto com remover em qualquer status, inclusive
  aguardando. A lixeira da linha também aparece em todos os estados.
- **Progresso e tamanho**: ícones de status (aguardando, analisando, baixando,
  concluído, erro etc.) ao lado da barra de progresso nas duas tabelas e coluna
  “Tamanho” na compressão (visível em larguras maiores).
- **Opções compacta**: diferente da Playlist, o diálogo de Opções ficou fixo em
  560×380, sem maximizar, redimensionar ou arrastar, para preservar a dinâmica
  dos controles internos.
- **Configurações cobalt**: ícones azuis sobre placas azul-escuras, alinhados
  ao acento principal.
- **Paleta de ações**: cobalto para executar/confirmar, tonal para
  importar/colar/adicionar, contorno para auxiliares e cores semânticas para
  sucesso, alerta e perigo.
- **Multilinha com viewport**: o campo de vários links usa um `Flickable`
  interno com scrollbar e acompanha o cursor; ao digitar muitas linhas, o
  conteúdo rola dentro do campo em vez de invadir a interface.
- **Remover sidecars**: ação promovida de label para botão secundário com
  ícone de lixeira e hover avermelhado.
- **Navegação lateral adaptativa**: `AppSidebar` substitui a barra horizontal.
  Em telas largas usa 220 px com ícone + texto; entre 1120 e 1279 px usa 64 px
  só com ícones; abaixo de 1120 px vira drawer sobreposto. Configurações fica
  separada no rodapé, com badges discretos para downloads/compressões ativos.
  `Ctrl+1`…`Ctrl+4` trocam de seção e o `SwipeView` preserva formulários,
  seleção, foco e rolagem.
- **Hambúrguer global**: o botão da barra de título alterna a rail em todos os
  tamanhos, com animação suave; em janelas estreitas abre o drawer.
- **Transição de páginas**: o carrossel foi substituído por `StackLayout` com
  `PageFrame`, que desliza/surge como um card sem manter resíduos da aba
  anterior. A troca de largura da rail não altera o índice ativo.
- **Barra de título funcional**: botão de tema claro/escuro ao lado dos
  controles da janela e menu hambúrguer em todos os tamanhos. O tema saiu de
  Configurações e passa a ser uma preferência de acesso rápido.
- **Seletor de idioma**: bandeiras locais simplificadas + nome nativo do idioma.
- **Cookies de navegador**: o combobox voltou a exibir logotipos locais de
  Chrome, Chromium, Edge, Firefox, Opera, Vivaldi e Brave, cada um com fundo
  próprio claro/escuro e sem download em runtime. O contêiner aceita novos
  assets em `icons/browsers/`.
- **Compressão mais larga**: o preset passou a 320 px e os grids de ajustes
  usam 2 colunas em larguras comuns, deixando os comboboxes mais largos.
- **Rolagem da aba Individual**: o conteúdo usa `ScrollView` com barra vertical
  sempre visível, evitando corte do card de progresso em janelas baixas.
- **Warnings do Qt**: removidos `Accessible` inválido no diálogo de opções,
  acesso a tema nulo no diálogo de substituição, fundo nulo nos diálogos
  Material e injeção implícita de parâmetro no handler da navegação.
- **Seletor de navegador**: voltou ao `AppComboBox` padrão. Badges com
  iniciais foram descartados por não representarem os logotipos oficiais.
- **Placeholders e filtros**: o hint usa a mesma linha de base do cursor;
  o campo multilinha mantém o hint no canto superior esquerdo. Filtros de
  Downloads/Compressão passaram a 56 px, com botão de limpar dentro do campo
  e ícone de busca alinhado ao placeholder.
- **Contadores da Compressão**: todos os `AppSpinBox` passaram a 200 px para
  exibir valores de quatro ou mais dígitos sem corte.
- **Filtro por tamanho**: usa o valor exibido na coluna Tamanho (saída, com
  fallback para a origem) e aceita bytes, valor formatado com/sem espaço
  (`9.5 MB`, `9.5MB`), decimal com vírgula (`9,5`) e `tamanho 9.5`.
- **Sort por tamanho**: ordena pela mesma regra da coluna (saída quando
  existe, origem enquanto não houver arquivo gerado), sem jogar pendentes
  para o fim por `size_after` zerado.
- **Remover selecionados**: botão de 200×56 px, centralizado verticalmente
  com o campo de filtro ao lado.
- **Selecionar tudo**: fica desabilitado quando a fila de compressão está vazia.
- **Selecionar tudo (Compressão)**: o primeiro clique marca todos os itens
  diretamente, sem exibir o estado intermediário “-”. O botão de remoção tem
  largura fixa para não deslocar o seletor e impedir o segundo clique.
- **Playlist sem URL**: Enter/clique sem link são bloqueados pelo validador;
  respostas JSON nulas e miniaturas nulas do yt-dlp não derrubam mais o app.
- **Botões ciano**: a variante violeta (rosa/lavanda no estado desabilitado)
  deu lugar ao ciano em “Carregar itens”, “Iniciar Fila” e “Retomar”.
- **Confirmações**: os diálogos usam o layout centrado do anexo, com ícone
  circular suave, título/mensagem centralizados, botões largos lado a lado,
  ação destrutiva vermelha e fechar no canto. Sem cabeçalho em degradê,
  arraste ou expansão de janela. O componente `ConfirmSurface` cobre
  “Apagar original após sucesso”, queda de qualidade, dependências e futuros
  popups de confirmação.
- **Resultado x Tamanho**: as colunas “Antes → depois” e “Tamanho” têm sort
  independente (`saving`/`size`) e filtros `resultado:`, `antes:`, `depois:` e
  `tamanho:` separados; a tabela de Compressão voltou a filtrar corretamente.

### Interface e tabelas (R5)

- **Tooltips ricos e acessíveis**: novo `AppToolTip` com título, descrição,
  atalho, ícone e rodapé; abre por hover ou foco de teclado, reposiciona dentro
  da janela e fecha ao sair/pressionar. Botões, combos, spins, campos, abas e
  barra de título expõem `tipTitle`/`tipText`/`tipShortcut`; o texto também
  alimenta `Accessible.description`. O bloco de conteúdo é centralizado
  horizontal e verticalmente, com teste de geometria dedicado.
- **Filtro dinâmico nas tabelas**: Lote e Compressão buscam em todas as colunas
  enquanto se digita, com normalização de acentos e prefixos (`status:`,
  `nome:`/`titulo:`, `erro:`, `tamanho:`, `economia:`). O combobox de campo foi
  removido; `Ctrl+F` foca o filtro da aba ativa e `Esc` limpa.
- **Ordenação por cabeçalho**: Lote ordena por título, status e progresso;
  Compressão por arquivo, status, progresso e tamanho final. Cabeçalhos são
  focáveis, respondem a Enter/Espaço e exibem ▲/▼ junto ao rótulo.
- **Varredura de pastas assíncrona**: `scan_media_paths()` roda em thread
  auxiliar; a UI mostra progresso, permite cancelar e resume adicionados,
  ignorados, duplicados e erros. Symlinks de diretório não são seguidos.
- **Ordenação por status previsível**: rank de fluxo em vez de ordem
  alfabética; a fila do Lote usa throttle adaptativo (120/250/500 ms) para
  projeções grandes.
- **CI/qmllint**: o workflow bloqueia erros reais e tolera avisos conhecidos de
  `unqualified access`/`missing-property`.
- **Tabela de Compressão alinhada**: larguras compartilhadas entre cabeçalho e
  delegate, todos os títulos no mesmo Y, coluna “Ações” explícita e correção do
  “Arquivo” fora de posição. Teste compara a geometria real em 1160×800 e
  940×620.
- **Compressão em 940×620**: “Ocultar ajustes”/“Mostrar ajustes” recolhe o
  painel de configuração e devolve a altura para a fila; estados vazios e de
  filtro sem resultado são distintos.
- **Rastreabilidade da fila**: `DownloadModel.snapshot()` é somente leitura e
  inclui `sourceIndex`; as ordenações do Lote e da Compressão são visuais e
  não alteram a ordem de agendamento dos managers.
- **Fallback inseguro removido (R8)**: o downloader não usa mais
  `--compat-options allow-unsafe-ext`; extensões incomuns são recusadas e o
  fluxo seguro de raspagem/ffmpeg é preservado, com teste de regressão.
- **Clipboard e Playlist (R7-L)**: `copyLink` usa o clipboard importado e
  informa indisponibilidade; `loadPlaylist(url, limit)` elimina a dependência de
  ids internos entre `main.qml` e `PlaylistPage.qml`.
- **AV1 QSV e rate control (R7-L)**: alvo VBR desabilitado/ignorado no
  `av1_qsv`; qualidade limitada a 51 nesse encoder (63 no AV1 software);
  “bitrate alvo” substitui a nomenclatura enganosa de “piso”.
- **Fila**: sincronização com coalescência (`start()` sem `restart()`), teto de
  100 mil arquivos na varredura (sem adição parcial ao truncar) e benchmark
  reproduzível da projeção.
- **Playlist unificada à aba Downloads**: o separador Playlists foi removido;
  `Carregar playlist` abre um diálogo na própria aba Downloads. Os itens já
  entram marcados por padrão, podem ser filtrados/desmarcados e há
  **Limpar lista**; os selecionados vão para a mesma fila.
- **Modelo da aba Downloads**: `DownloadFilterProxyModel` em Python substitui a
  projeção em `ListModel`/JavaScript; filtro, ordenação e `sourceIndex` estável
  no mesmo ambiente do backend.
- **Motion/título**: tooltips compactos na barra de título, animação de
  minimizar/restaurar e tokens de duração em `hlsdl/ui/motion.js`. Os controles
  de janela usam `Qt.TabFocus` e anel de foco apenas com `visualFocus`, sem
  ficarem “selecionados” após o clique do mouse.
- **Testes**: `tests/test_table_tools.py` (filtro/ordenação/geometria),
  `tests/test_tooltips.py` (abertura, limites e atalhos) e regressões de
  clipboard/Playlist/AV1; capturas em `docs/ui-review/r5/`.

### Adicionado
- **Catálogo SQLite** (`catalog.sqlite3`) indexando source key, SHA-256/BLAKE3, probe/validação, arquivos e jobs; consulta por identidade/hash e `prune_missing`.
- **BLAKE3 opcional** ao lado do SHA-256 obrigatório, no sidecar e na verificação.
- **SSIM amostral** source × output em trechos (10%/50%/90%) para reencodes sem filtros que mudam pixels.
- **HDR10 estático**: extração de mastering display/content light do `ffprobe` e emissão de `master-display`/`max-cll`/`hdr10-opt` no x265.
- **Decodificação por hardware** (`-hwaccel auto`) como opção na UI.
- **Geometria**: crop (`w:h:x:y`), escala (largura/altura), rotação 0/90/180/270 e FPS, com validação das dimensões esperadas.
- **Status `verifying`** para hash/validação, no download e na compressão.
- **Fila persistente** (`queue.json`): restaura downloads e compressão ao abrir, omitindo concluídos.
- **CLI `hlsdl`** com `probe`, `verify`, `similar`, `compress` e `download`.
- **Arquitetura modular**: `bridge.py` dividido em mixins (`hlsdl/bridge_parts/`), páginas QML em `hlsdl/ui/pages/`, componentes compartilhados em `hlsdl/ui/components/` e todos os diálogos globais (erro, confirmações, dependências, lote, sugestões, similaridade e recuperação) em `hlsdl/ui/dialogs/`; `main.qml` ficou só com o shell da janela.
- **Atualizações assinadas**: os manifestos `SHA256SUMS-windows.txt` e `SHA256SUMS-linux.txt` são assinados com Ed25519; o app valida a assinatura do Windows com a chave pública embutida antes de aceitar o instalador, e o pacote Linux publica o `.sig` para verificação manual. Inclui `scripts/gen_update_key.py` e `scripts/sign_release.py`.
- **Manifesto de release canônico** (`release-manifest-*.json`): assinatura Ed25519 cobre `schema_version`, `version`, `tag` e assets (nome, tamanho e SHA-256). O app verifica a assinatura antes do parsing e exige igualdade estrita com a API do GitHub; replay de manifesto antigo e downgrade são rejeitados. Gerado por `scripts/gen_release_manifest.py`.
- **Política de rede única** (`hlsdl/netpolicy.py`): somente HTTP/HTTPS, `Referer` same-origin sem query/fragmento/credenciais, redirects manuais revalidados e bloqueio de salto público → loopback/rede privada.
- **Limite de resposta do scraper**: leitura em streaming com teto de 4 MiB descompactados e validação de `Content-Type`.
- **Proveniência do FFmpeg**: macOS exige pin de SHA-256 ou consentimento explícito (`HLSDL_ALLOW_UNVERIFIED_FFMPEG=1`); Linux registra o fingerprint e alerta que o fornecedor só publica MD5; gerenciador de pacotes do sistema continua preferido.
- **Paridade integral de i18n** no backend e nos 15 catálogos JS da UI, com teste que também verifica chaves referenciadas no QML.
- **Migrações versionadas do catálogo SQLite** (`PRAGMA user_version`) e `foreign_keys=ON` por conexão.
- **SBOM do bundle**: `scripts/gen_sbom.py --bundle` inclui cada arquivo do PyInstaller com SHA-256 e tamanho, além do inventário do ambiente.
- **Teste HDR10 real com QSV**: fixture sintético com mastering display/max-cll gera saída HEVC QSV em MKV/MP4 e valida a preservação dos metadados; roda no workflow de hardware com `HLSDL_TEST_QSV=1` e é skipado fora dele.
- **Cabeçalho descritivo por aba** (`PageHero`): título, frase de contexto e degradê sutil; ações contextuais na Compressão. Em janelas menores que 1050×650, mantém o título simples para preservar a densidade.
- **Harness de screenshots** (`scripts/ui_snapshot.py`): captura as 5 abas em temas/resoluções/escalas, além de toast e diálogo de erro; evidências em `docs/ui-review/`.
- **Toast persistente para mensagens longas**: até 3 linhas, duração proporcional ao texto e dispensa por clique.
- **Build fixado**: `constraints.txt` pina PySide6, yt-dlp, requests, cryptography, PyInstaller e ferramentas de teste; Actions e o fallback do Inno Setup foram fixados/detectados.
- **Teste de hardware**: workflow semanal/manual roda encode QSV real em runner self-hosted; CI Linux instala ffmpeg para executar os testes reais de software.
- **QML no CI**: `pyside6-qmllint` bloqueia erros de sintaxe/tipo em todas as telas.
- **Teste Windows no CI** e testes de catálogo/CLI/persistência/SSIM/HDR.
- **SBOM CycloneDX em todas as plataformas** (`*-sbom.json`), com hash incluído nos `SHA256SUMS` de Windows e Linux.
- **CI valida o wheel** instalável: `bridge_parts/` e as subpastas QML (`pages/`, `components/`, `dialogs/`) precisam estar presentes.

### Alterado
- Ciclo de vida de QThreads centralizado em `hlsdl/jobs.py`.
- `detect_encoders` passou a considerar apenas encoders de vídeo.
- Presets agora resetam filtros/políticas e permanecem selecionados; alterações individuais marcam “Personalizado”.
- **Presets e RF mais conservadores**: os presets prontos usam RF menor (Equilibrado HEVC 22, Qualidade HEVC 18, Arquivo 16, Rápido H.264 21, AV1 27) e o reencode automático do download usa H.264 18/21/24 e H.265 20/24/27 por nível. O objetivo é reduzir a perda de bitrate sem sacrificar a qualidade percebida.
- **Bitrate mínimo opcional**: o ajuste (padrão **0**, desativado) aplica um piso VBR (`-b:v`/`-maxrate`/`-bufsize`) em QSV/NVENC/AMF para quem quiser limitar a redução. O padrão volta a ser qualidade constante: CRF/ICQ controlam a qualidade e o bitrate é consequência. O aviso de queda só aparece quando o SSIM também está abaixo de 0,95.
- **Sem referências externas na UI**: textos e documentação falam apenas em presets prontos, sem comparação com outros aplicativos.
- Atualização de dependências bloqueada com jobs ativos e PySide6 não é mais atualizado in-process.
- Extração de ffmpeg/ffprobe e downloads de ferramentas agora são atômicas.
- **Metadados de cor inválidos**: tags `reserved`/`unknown`/`unspecified` deixam de ser repassadas como `-color_primaries`/`-color_trc`/`-colorspace`/`-color_range`; isso corrige a falha do `hevc_qsv` (`Unable to parse "color_primaries" option value "reserved"`).
- **Barra de título**: botões de minimizar/maximizar/restaurar/fechar redesenhados com ícones vetoriais consistentes, estado de restaurar correto ao maximizar, cursor de mão, **foco visível e navegável por teclado** e tooltips traduzidos em todos os botões.
- **Aba Compressão redesenhada**: opções divididas em **Geral**, **Vídeo**, **Áudio e legendas** e **Avançado**, com grid responsivo (2–4 colunas), presets sempre visíveis, altura adaptativa ao conteúdo da seção e mais espaço para a fila. As abas internas usam o mesmo `TabBar`/`AppTabButton` das abas superiores.
- `pyproject.toml` inclui `hlsdl.bridge_parts` e todo o QML modular no pacote instalável.

### Corrigido
- **P1-01 — vazamento de `Referer`**: o cabeçalho não é mais montado com a URL crua. Scraper, yt-dlp e FFmpeg recebem apenas `Referer` da mesma origem, sem query string, fragmento ou userinfo; redirecionamentos cross-origin não o encaminham.
- **P2-01 — esquemas perigosos**: `file://`, `ftp://`, `data:` e URLs sem host válido são recusados antes da fila e novamente antes de yt-dlp/ffmpeg.
- **P2-02 — SSRF/HTML ilimitado**: redirects do scraper são revalidados a cada salto; destino privado a partir de página pública é bloqueado; corpo tem limite de bytes.
- **P2-03/P2-04 — verificação de release e HDR**: manifesto assinado vincula versão/tag/asset; HDR10 compara mastering display e content-light na saída para todos os encoders que prometem preservação. Metadados HDR10 reais são lidos também do primeiro frame (SEI), não apenas de `stream.side_data_list`; QSV foi validado em MKV e MP4 com fixture HDR10.
- **P3-01 — colisão de caminhos**: `install_output()` rejeita `final == source` (também symlink/hardlink) antes de criar backup ou remover arquivos.
- **P2-06 — gates da CI**: `qmllint` e smoke tests deixam de usar `|| true`; exit code, encerramento prematuro e marcador de inicialização são verificados em Linux e Windows.
- **P2-07 — shutdown**: updater, dependências, scanner de similaridade e detecção QSV do compressor têm cancelamento cooperativo, `join` com timeout e supressão de callbacks após o teardown; threads auxiliares do Bridge são rastreadas.
- **Reauditoria 18/11 — update**: download limitado aos hosts do GitHub, manifesto/assinatura com tetos de bytes, instalador conferido pelo tamanho durante o streaming e redirect final revalidado; comparador de versão semântico com prerelease/build metadata.
- **Reauditoria 18/11 — `allow-unsafe-ext`**: retry só publica arquivo que passe por `ffprobe` com vídeo/áudio ou assinatura de contêiner conhecida; HTML, playlist crua e binário desconhecido são descartados.
- **Reauditoria 18/11 — barra de título e botões**: gradiente sutil, versão em pill, divisor; hover, mousedown, escala e transição de cor em `TitleBarButton`, `AppButton` e `AppToolButton`.
- **Reauditoria 18/11 — diálogo de erro**: resumo humano, detalhes técnicos expansíveis, área rolável e copiar/fechar.
- **Reauditoria 18/11 — PageHero compacto**: o cabeçalho degradê permanece em 940×620 em versão compacta (40/52 px), em vez de desaparecer.
- **Reauditoria R3 — botões semânticos**: `AppButton` com variantes primary/secondary/tertiary/danger e tamanho compact/normal; `highlighted` continua compatível. Ações secundárias de Lote, Compressão, Playlist, erros e pasta ganharam superfície/borda em repouso.
- **Reauditoria R3 — pasta de saída**: novo `FolderPickerField` com caminho elidido/tooltip, Alterar/Abrir/Copiar, validação de escrita e feedback; abrir pasta usa helper único com notificação de erro.
- **Reauditoria R3 — fila e feedback**: Iniciar/Cancelar/Limpar desabilitam sem operação aplicável; adicionar pasta de compressão sem mídia elegível informa o usuário.
- **Revisão R4 — acabamento Material**: botões maiores (44 px normal/36 compact), variantes semânticas com superfície/borda visível, ícones 18 px e estados hover/pressed; “Atualizar tudo”, “Verificar novamente”, “Verificar atualizações” e “Escolher…” deixam de parecer labels.
- **Revisão R4 — compressão**: cabeçalho Status centralizado sobre o badge e filtro por campo (todos, nome/arquivo, status, progresso, tamanho, economia, erro).
- **Revisão R4 — Lote**: linha de formato com RowLayout alinhado verticalmente entre label, seletores, resumo e “Opções…”.
- **Revisão R4 — Download individual**: botão Cancelar visível enquanto o download individual está ativo ou aguardando.
- **Revisão R4 — cookies/pastas**: botão de arquivo de cookies sempre visível com ícone; cada dependência tem botão Atualizar com ícone; correção de encoding em QML/bridge_parts.
- **Reauditoria R3 — estado vazio do Lote**: em 940×620 o hint/filtro são ocultados quando não há itens, preservando a mensagem “Nenhum link na fila” e o rodapé.
- **Acessibilidade**: botões da barra de título voltam a receber foco por teclado e cabeçalhos ordenáveis da compressão são `Button` com foco, Enter/Espaço e nome acessível.
- **Tema claro**: botões primários deixavam de exibir texto/fundo legível porque `Material.background` da janela pintava os botões `highlighted`; fundo da janela separado e `AppButton` com cores explícitas para normal, hover, pressionado e desabilitado.
- **Responsividade 940×620**: contadores do Lote quebram em duas linhas e a barra de progresso some em larguras menores; painel de Compressão mantém o rodapé visível, com scrollbars explícitos.
- **Diálogos**: `AppDialogSurface` ganhou margens internas de 16 px, corrigindo conteúdo colado às bordas.
- **BOM UTF-8** removido de `hlsdl/bridge_parts/*.py`; documentação alinhada sobre `requests`/`beautifulsoup4` e sidecars POSIX.
- **Sidecars POSIX**: novos sidecars usam ponto inicial (`.video.mp4.hlsdl.json`) no Linux/macOS; sidecars antigos continuam legíveis e são limpos normalmente.
- **Ícones após a extração QML**: `iconPath()` agora devolve URL absoluta; páginas e componentes não procuram mais `pages/icons` ou `components/icons`.
- **Estilo Material na GUI extraída**: páginas, diálogos e componentes agora importam `QtQuick.Controls.Material`; ComboBox/SpinBox/Switch/CheckBox deixam de aparecer como barras pretas e voltam ao tema claro/escuro correto.
- **Probes QSV concorrentes**: a detecção de dispositivos QSV usa cache global e lock, evitando vários `ffmpeg` simultâneos ao criar múltiplos managers; `refresh_encoders` invalida o cache.
- **Mapeamento QSV**: o regex aceita o BDF completo (`0000:00:02.0`), então GPUs Intel Arc/UHD voltam a ser associadas ao índice `-qsv_device` correto.
- **Economia estimada**: a estimativa agora cresce com o RF/quantização (arquivo menor); antes estava invertida e reduzia a economia ao aumentar o RF.
- **Download de atualização atômico**: o instalador é gravado em `.part`, verificado por SHA-256 e só então movido para o nome final; falhas removem o parcial.
- **Qualidade mensurável**: bitrate/resolução/SSIM de origem e saída ficam no log, na linha da fila e no tooltip; o gate SSIM subiu para 0,90 e quedas extremas de bitrate com resolução/FPS iguais geram aviso e confirmação antes de instalar. No CLI, o padrão é recusar; `--allow-quality-drop` aceita explicitamente.
- **Bitrate não é métrica de qualidade**: a compressão automática do download aceita quedas grandes quando o SSIM permanece alto; o corte artificial de 90% foi removido. O SSIM mínimo de 0,90 continua valendo.
- **JSONs de integridade opcionais**: sidecars `.hlsdl.json` passam a ser gerados somente com a opção ativa (padrão desligado). O catálogo SQLite continua centralizando os metadados, e Configurações → Integridade tem um botão para remover sidecars antigos da pasta de saída.
- **Tabela de compressão ordenável**: cabeçalhos de nome, status, progresso e resultado alternam ordem crescente/decrescente, com indicador visual. Os separadores da linha de qualidade passaram de `?` para `·`.
- **Filtro na fila de compressão**: busca por nome, caminho, encoder, saída, erro e status traduzido, com limpar e mensagem de “nenhum resultado”.
- **Sidecars JSON ocultos**: os `.hlsdl.json` de integridade continuam ao lado da mídia para portabilidade, mas recebem atributo oculto no Windows.

## [Não lançado] — integridade, similares e recuperação

### Adicionado
- **Identidade de mídia** por ID de extractor, hash de manifesto HLS ou URL canônica sem tokens, com sidecar `.hlsdl.json` contendo `ffprobe` + SHA-256.
- **Validação profunda de saída**: resolução, bit depth, cor/HDR, áudio (contagem/canais/duração), legendas e frames; arquivos inválidos não substituem o original.
- **Pipeline transacional de compressão**: `.part` único, journal, backup do original por hard link/cópia, rollback em hash/tamanho inválido e recuperação na inicialização.
- **Busca de mídias similares (VDF/Czkawka-inspired)**: dHash multi-frame + aHash + envelope RMS, com fallbacks por hash amostral, metadados e nome.
- **Extração de cookies escopada** por domínio/path/secure, incluindo `#HttpOnly_`.
- **Importação de .txt** UTF-8/UTF-16/ANSI e validação do arquivo de cookies.
- **Retry de compressão** e bloqueio de retry enquanto a thread anterior ainda está viva.

### Corrigido
- **Fallback ffmpeg**: `-loglevel info` elimina o falso “travamento” de 180 s e volta a mostrar progresso/velocidade.
- **Vazamento de QThread**: threads concluídas e os itens capturados pelas closures são liberados.
- **Corrida de detecção**: iniciar compressão antes da detecção de encoders não marca mais todos os itens como erro.
- **Duplicata entre Download Individual e Lote**: o lote ignora URLs ativas na fila individual.
- **Perda de texto no lote**: campo só é limpo quando algo foi realmente adicionado.
- **Atalhos**: focar um botão não desabilita mais Ctrl+V/Delete.
- **Pasta de logs** correta em modo portátil/dev.
- **`single_busy`** traduzido nos 8 idiomas.

## [Não lançado] — compressor com presets, filtros, HDR e validação

### Adicionado
- **Presets de compressão** (Rápido H.264, Equilibrado HEVC, Qualidade HEVC,
  Arquivo HEVC 10-bit e AV1 equilibrado).
- **RF por codec**: faixa 1–51 para H.264/HEVC e 1–63 para AV1.
- **Filtros**: desentrelaçamento automático/forçado (`yadif`) e redução de
  ruído (`hqdn3d` leve/média/forte).
- **Política de HDR**: pular, preservar 10-bit ou converter para SDR com
  tone mapping (`zscale`/`tonemap`) e metadados bt709 corretos.
- **Áudio**: automático, cópia quando o contêiner permite ou conversão
  consistente (AAC/Opus/MP3), com bitrate maior para multichannel.
- **Legendas**: automático, todas ou nenhuma; MKV preserva PGS/bitmap e
  fontes/anexos, MP4/MOV usam `mov_text` e WebM usa `webvtt`.

### Corrigido
- **Pipeline único**: a compressão durante o download agora usa o mesmo
  planejador da aba Compressão, grava em `.part`, valida com `ffprobe` e só
  troca o arquivo atomicamente; arquivos parciais/stale não são reaproveitados.
- **Encoder por job**: mudar o codec com a fila ativa não usa mais o encoder
  antigo para os próximos itens.
- **Validação de saída**: confere duração (tolerância de 2%/2 s), presença de
  vídeo e quantidade de faixas de áudio antes do `os.replace`.
- **Logs do ffmpeg** limitados em memória; MKV deixa de recodificar áudio
  DTS/TrueHD/FLAC desnecessariamente.

## [1.4.0] — 2026-11-09

### Corrigido
- **Threading**: sinais de download/compressão agora são entregues por slots
  `QObject` na thread da GUI (antes, lambdas mutavam modelo/QML na thread do
  worker).
- **Encerramento seguro**: threads que não respondem ao cancelamento não são
  mais destruídas vivas (evita `0xC0000409`); há espera, terminate e saída de
  emergência sem destruir QThreads.
- **Instalação do ffmpeg**: URL do Windows corrigida para o build
  `essentials` e fallback para winget/choco/scoop; macOS usa a API atual do
  evermeet em vez do endpoint removido.
- **Download Individual**: fila própria, não inicia mais o lote inteiro;
  valida o link, não limpa o campo em erro e ganhou cancelar/retentar/detalhes
  de erro.
- **Compressão no download**: o original é preservado, todas as trilhas
  (áudio/legendas) são mapeadas e o arquivo leva sufixo `_h264`/`_h265`.
- **Nomes/qualidade**: modo título inclui o ID para evitar colisão; qualidade
  e “apenas vídeo” não caem mais em formatos que violam a escolha.
- **Configurações**: INI corrompido não derruba o app; pasta vazia usa o
  padrão em vez do diretório de trabalho.
- **Janela inicial**: é limitada à área disponível da tela; geometria normal
  é preservada ao maximizar.
- **Dependências**: instalar/atualizar agora pede confirmação.

### Alterado (P1/P2)
- **Tema e contraste**: tokens semânticos para claro/escuro; textos, botões
  flat/preenchidos, badges de status, erros e diálogos agora mantêm contraste
  AA; o corpo dos diálogos é opaco (não herda fundo claro no tema escuro).
- **Layout**: aba Compressão com rolagem nas opções e fila mínima visível;
  linhas de ações usam `Flow` (sem cortar botões em PT/RU); Configurações com
  scrollbar vertical correta e sem barra horizontal.
- **Atalhos**: detecção de foco em campos corrigida (`root.activeFocusItem`);
  `Ctrl+Enter` e `Delete` são escopados e não agem durante a digitação.
- **Fechamento**: confirmação quando há downloads/compressões ativos.
- **Playlists**: cancelar carregamento, filtro com contagem e proteção contra
  IDs de outros sites virarem URLs do YouTube.
- **Compressão/ffmpeg**: detecção de `ffprobe`, fallback ffmpeg respeitando
  modo/contêiner/referer/cookies, encoder efetivo para 10-bit/x265 e GPU QSV
  detectada no startup; refresh de encoders após instalar ffmpeg.
- **Startup**: detecção de dependências/encoders fora da thread da GUI.
- **Alto DPI**: escala automática não multiplica o scaling do Windows.
- **i18n/acessibilidade**: filtros de arquivo, terminal, dicas e botões da
  janela traduzidos nos 8 idiomas; nomes acessíveis nos controles do título.

### Segurança/arquitetura (P2)
- **Integridade dos downloads**: yt-dlp é verificado contra o
  `SHA2-256SUMS` oficial (todos os canais), o ffmpeg Windows contra o
  `.sha256` do Gyan e o build Linux contra o `.md5` publicado. Sidecar
  ausente, digest inválido ou divergência abortam a instalação e removem o
  arquivo temporário; no macOS, onde o evermeet não publica hash, o tamanho
  exato informado pela API é conferido.
- **Privacidade dos logs**: URLs assinadas (query/fragmento), credenciais
  embutidas, cabeçalhos `Authorization`/`Cookie` e caminhos de cookies são
  redigidos antes de chegar aos arquivos de log.
- **Encerramento de QThreads**: a lógica de cancelar/aguardar/terminar foi
  extraída para `lifecycle.shutdown_threads`, usada pelas filas de download e
  compressão.
- **Diálogos e bandeja**: `QMessageBox` nativos usam o botão OK traduzido;
  a janela ganhou ícone próprio e ícone de bandeja (mostrar janela/sair),
  quando o ambiente oferece suporte.

## [1.3.0] — 2026-11-02

### Adicionado
- Abas **Download Individual**, **Lote**, **Playlists** e **Configurações**.
- **Aba de Playlists** (YouTube e sites em geral): carregar itens, selecionar e enfileirar/baixar.
- **Aba de Compressão local**: HEVC com QSV/NVENC/AMF/x265, qualidade 1–51, paralelismo, validação e substituição segura.
- **Codecs e contêineres na compressão**: HEVC/H.264/AV1, MP4/MKV/WebM/MOV/AVI, sugestões e estimativa de economia por formato; preset **muito lenta** (máxima qualidade).
- **Kvazaar (`libkvazaar`)** como opção de HEVC software rápido, além de **10-bit** (`yuv420p10le`) e **ajuste fino do x265** (`aq-mode`, `psy-rd`, `psy-rdoq`, `deblock`).
- **Metadados HDR preservados** na compressão (primárias, transferência, espaço de cor e faixa) e **encoder real** exibido por arquivo (ex.: `QSV HEVC · Intel Arc B580`).
- **Notificação de conclusão** da compressão (toast + diálogo quando há erros).
- **Filtro na fila de lote** (título/URL) com ícone de pesquisa, **debounce de 220 ms** e **cabeçalhos de tabela maiores/destacados**, além de mais tooltips/ícones (tema claro/escuro, ações).
- **Console de instalação estilo terminal** no log de dependências (Configurações → Dependências e diálogo de instalação): fundo escuro, fonte monoespaçada e botão de copiar saída.
- **Escala automática da interface** conforme a tela (até 128%), com `--ui-scale`/`HLSDL_UI_SCALE` para ajuste manual; fonte, ícones e espaçamentos escalam juntos.
- **Diagnóstico integrado** (`python diagnostico.py` ou `--diagnose`): relatório com Python/Qt, telas, DPI/escala, caminhos, geometria salva, ffmpeg/yt-dlp, GPUs e encoders.
- **Crash log e avisos do Qt/QML**: `hlsdl-crash.log` via `faulthandler`, hooks para exceções não tratadas (thread principal e workers) e mensagens do Qt gravadas no log rotativo.
- **Exportação de pacotes** (`python exportar.py`): ZIP de código-fonte, ZIP portátil do build `onedir` e `SHA256SUMS.txt`.
- **Atalho `iniciar.cmd`** para abrir o app pelo `.venv` (ou `py -3`/`python`).
- **Cursor de mão** (indicador) em botões, abas, combos, checkboxes e switches.
- **Atualizador**: verifica a release, baixa o instalador e valida o SHA-256 antes de executar.
- **Modos de extração**: vídeo + áudio, apenas vídeo, somente áudio.
- **Qualidade de 144p a 4K** e escolha de **arquivo** (mp4/mkv/webm/avi/mov; mp3/m4a/wav/flac/opus).
- **Compressão H.264 / H.265 (HEVC)** com níveis Leve/Média/Forte.
- **Nome do arquivo**: ID estável (hash) ou título da página.
- **8 idiomas**: PT, EN, ES, IT, FR, RU, JA, ZH.
- **Gerenciador de dependências** com download de binários (yt-dlp/ffmpeg), canais do yt-dlp (Stable/Nightly/Master) e prompt inicial.
- **Modo portátil** (`--portable` ou `portable.flag`).
- Instalador **Inno Setup** (por usuário, sem admin) e ZIP portátil.

### Alterado
- Migração de **PyQt6 → PySide6** (mantém a licença MIT).
- Build Windows em **`--onedir`** (startup mais rápido, menos falsos positivos) + `--icon`/`--version-file`.
- Log rotativo, encerramento gracioso e instância única (lock de SO + ativação da janela).
- Interface de configurações com cards dimensionados pelo conteúdo.
- Aba **Lote** compacta: opções avançadas em diálogo; resumo do perfil na linha.
- Ícones **SVG** (tema claro/escuro), nomes acessíveis e accent alinhado ao ícone do app.

### Corrigido
- Dessincronização entre modelo e fila ao limpar itens.
- Configurações não persistiam no binário empacotado.
- Aba travada por quebra de binding do `SwipeView`.
- Detecção de ffmpeg instalado fora do PATH (winget/choco).
- Alinhamento do aviso de dependências e do campo de edição da fila.
- **Janelas de console** de yt-dlp/ffmpeg não aparecem mais no build Windows;
  cancelar/fechar encerra a árvore de processos.
- **Pausar/Retomar** funciona e a fila volta ao estado ocioso ao terminar.
- A aba **Download Individual** não exibe mais o progresso de itens do lote/playlist.
- Botões de diálogo localizados (sem “OK/Cancel” fixos em inglês) e textos
  como “0 = sem limite” traduzidos.
- **GPU dedicada no QSV**: o modo Auto detecta os dispositivos (`-qsv_device`)
  e escolhe a Arc/dGPU; há seletor de GPU na aba Compressão.
- Campos de URL e caminho de cookies usam **placeholder simples** (sem
  floating label) onde o rótulo não agrega.
- **Modo áudio** no download individual agora recolhe também a linha de
  codec/compressão, sem deixar espaço vazio.
- **Aba Lote** usa apenas placeholder no campo de links (sem floating label),
  e o espaço entre “formato” e o botão foi normalizado no modo somente áudio.
- **Tabela de comprimidos**: o rótulo de conclusão foi centralizado/elidido
  dentro do badge e o motivo de itens ignorados não aparece mais em vermelho.
- **Filtro do lote** ganhou espaço em relação aos cabeçalhos e ícone de busca.
- Tooltips em `Label` (ex.: “Rede”) agora aparecem de fato (via `HoverHandler`),
  com exemplos para **ID estável × título** e para o filtro.
- Botões e controles clicáveis usam **cursor de mão**.
- **Estilo Material restaurado**: os componentes de cursor não substituem mais
  os tipos originais (`Button`, `ComboBox`, etc.), que voltaram a usar o tema
  Material em vez do estilo Basic.
- **Compressão em modo Auto** agora filtra NVENC/AMF/QSV pela GPU realmente
  presente e testa o encoder escolhido; se ele falhar, cai para software em vez
  de abortar a fila (corrige o erro de `hevc_nvenc` em máquinas Intel).
- **Erros da compressão** mostram as últimas linhas do ffmpeg no diálogo e no
  tooltip da linha, em vez de apenas “ocorreu um erro”.
- **Tabela de compressão**: o badge de status/progresso voltou a exibir o texto
  (o delegate usava `root.st` em vez do próprio `st`) e os botões de ação
  aparecem conforme o estado.
- **Saída de atualizações** fica sempre visível em Configurações → Dependências,
  com placeholder quando ainda não há log.
- Avisos de QML/Qt e exceções de threads não ficam mais silenciosos no build
  `--windowed`: são gravados no log rotativo e no crash log.
- Diálogos agora usam `contentItem` como pai (sem avisos de `parent` inválido),
  e bindings de `lastItem`/tooltips não geram mais `undefined`/`hovered`.
- Janela restaurada é **limitada à área disponível da tela**, evitando ficar
  maior que o monitor após mudança de escala/DPI.

## [1.2.3] — anterior
- Controle de rede: limite de velocidade e conexões por download.

## [1.2.2]
- Nomes de arquivo curtos e estáveis (hash da URL).

## [1.2.1]
- Retry para extensões incomuns (`.php`) + guarda de conteúdo.

## [1.2.0]
- Erro visível na linha + diálogo com detalhes; log em pasta estável.

## [1.1.0]
- Multi-idioma PT/EN, instância única, miniaturas temporárias.
