# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.

## [Não lançado] — correções P0 da auditoria

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
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o versionamento segue [SemVer](https://semver.org/lang/pt-BR/).

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
