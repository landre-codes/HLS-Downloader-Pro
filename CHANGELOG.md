# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o versionamento segue [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado] — padrão-ouro: catálogo, SSIM, HDR, fila e CLI

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
- **QML no CI**: `pyside6-qmllint` bloqueia erros de sintaxe/tipo em todas as telas.
- **Teste Windows no CI** e testes de catálogo/CLI/persistência/SSIM/HDR.
- **SBOM CycloneDX em todas as plataformas** (`*-sbom.json`), com hash incluído nos `SHA256SUMS` de Windows e Linux.
- **CI valida o wheel** instalável: `bridge_parts/` e as subpastas QML (`pages/`, `components/`, `dialogs/`) precisam estar presentes.

### Alterado
- Ciclo de vida de QThreads centralizado em `hlsdl/jobs.py`.
- `detect_encoders` passou a considerar apenas encoders de vídeo.
- Presets agora resetam filtros/políticas e permanecem selecionados; alterações individuais marcam “Personalizado”.
- Atualização de dependências bloqueada com jobs ativos e PySide6 não é mais atualizado in-process.
- Extração de ffmpeg/ffprobe e downloads de ferramentas agora são atômicas.
- `pyproject.toml` inclui `hlsdl.bridge_parts` e todo o QML modular no pacote instalável.

### Corrigido
- **Ícones após a extração QML**: `iconPath()` agora devolve URL absoluta; páginas e componentes não procuram mais `pages/icons` ou `components/icons`.
- **Estilo Material na GUI extraída**: páginas, diálogos e componentes agora importam `QtQuick.Controls.Material`; ComboBox/SpinBox/Switch/CheckBox deixam de aparecer como barras pretas e voltam ao tema claro/escuro correto.
- **Probes QSV concorrentes**: a detecção de dispositivos QSV usa cache global e lock, evitando vários `ffmpeg` simultâneos ao criar múltiplos managers; `refresh_encoders` invalida o cache.
- **Mapeamento QSV**: o regex aceita o BDF completo (`0000:00:02.0`), então GPUs Intel Arc/UHD voltam a ser associadas ao índice `-qsv_device` correto.
- **Download de atualização atômico**: o instalador é gravado em `.part`, verificado por SHA-256 e só então movido para o nome final; falhas removem o parcial.

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

## [Não lançado] — compressor inspirado no HandBrake

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
