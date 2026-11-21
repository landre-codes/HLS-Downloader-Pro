# HLS Downloader Pro

Downloader de vídeos (HLS / m3u8) com interface **Qt Quick (QML) + Material Design**.

## Funcionalidades

- **Duas abas de download**: **Download Individual** (um link, com progresso dedicado) e **Downloads** (fila com dezenas/centenas de links)
- **Playlist na própria aba Downloads**: carrega itens de uma playlist (**YouTube** ou sites em geral) em um diálogo, já marca todos por padrão e adiciona à mesma fila; é possível desmarcar exceções, filtrar e limpar a lista
- **Aba de Compressão local**: fila de arquivos/pastas, codecs **HEVC, H.264 e AV1**, contêineres **MP4/MKV/WebM/MOV/AVI**, aceleração por **Intel QSV, NVIDIA NVENC, AMD AMF, Kvazaar ou software** (`libx265`/`libx264`/`libsvtav1`), qualidade **RF 1–51 (AV1 até 63)**, presets de velocidade (**rápida → muito lenta**), **presets prontos** (Rápido, Equilibrado, Qualidade, Arquivo 10-bit e AV1), filtros de **desentrelaçamento e redução de ruído**, política de **HDR** (pular, preservar 10-bit ou tone mapping para SDR), modos de **áudio** (automático/cópia/AAC-Opus) e **legendas** (texto/todas/nenhuma, preservando PGS e fontes em MKV). Inclui paralelismo, **sugestões/estimativa de economia por formato**, validação da saída (duração, vídeo e áudio) e substituição atômica. O modo **Auto** prioriza a **GPU dedicada** (Arc/NVIDIA/AMD), filtra encoders pela GPU realmente presente e testa o escolhido, caindo para software se ele falhar; o dispositivo QSV pode ser escolhido na interface. Inclui **10-bit** e **ajuste fino do x265** (`aq-mode`/`psy`), além de **preservar e verificar metadados HDR10** (primárias, transferência, espaço de cor, faixa, mastering display e content-light) e mostrar o **encoder real** usado em cada arquivo (ex.: `QSV HEVC · Intel Arc B580`).
- **Interface**: busca nas filas de download e compressão (nome, caminho, encoder, status, saída e erro) com ícone de pesquisa, cabeçalhos de tabela maiores/destacados e **ordenação por clique** na fila de compressão (nome, status, progresso e economia), **console de instalação estilo terminal** no log de dependências (com copiar saída), cursor de mão em ações e **tooltips com exemplos**. A escala da interface acompanha o tamanho da tela (até 128%) sem desalinhar as tabelas.
- **Integridade de mídia**: identidade estável (ID do extractor ou hash de manifesto HLS), **catálogo SQLite** (`catalog.sqlite3`), validação profunda de resolução/bit depth/HDR/áudio/legendas, **SSIM amostral** e recusa de saídas truncadas. Sidecars `<arquivo>.hlsdl.json` são **opcionais** (padrão desligado em Configurações → Integridade, com botão para remover os existentes); no Linux/macOS novos sidecars usam ponto inicial para ficarem ocultos. Downloads inválidos são preservados como `*.invalid`.
- **Fila persistente + CLI**: a fila de downloads/compressão é salva em `queue.json` e restaurada ao abrir (itens concluídos são omitidos). O comando `hlsdl` oferece `probe`, `verify`, `similar`, `compress` e `download` para automação.
- **Compressor avançado**: além de presets/filtros/tone mapping, inclui **decodificação por hardware** (`-hwaccel auto`), metadados HDR10 (`master-display`/`max-cll`) no x265 e validação de frames/áudio/legendas. Saídas HDR10 só são aceitas quando mastering display **e** content-light sobrevivem ao encode, em qualquer encoder anunciado.
- **Preservação do original**: a compressão grava em `.part` único, usa journal de transação e backup por hard link/cópia. Em erro, hash divergente, perda de energia ou falha de áudio, o original é mantido/restaurado; “Apagar original” só ocorre após validação e deixa um backup recuperável.
- **Qualidade mensurável**: a tabela e o log mostram bitrate, resolução e SSIM antes/depois. Bitrate é consequência do CRF/ICQ: uma queda grande com **SSIM ≥ 0,95** é eficiência do codec e não gera aviso; SSIM abaixo de **0,90** rejeita a saída. Quedas acima de 50% com SSIM entre 0,90 e 0,95 pedem confirmação antes de substituir o original. O campo opcional **Bitrate mínimo** (padrão **0/desativado**) fica disponível para quem quiser um piso VBR em QSV/NVENC/AMF.
- **Busca de similares (VDF/Czkawka-inspired)**: assinatura multi-frame dHash + aHash + envelope RMS de áudio, com fallbacks por hash amostral, metadados, duração/resolução e nome. Disponível na aba Compressão → “Mídias similares”.
- **Atualizações**: verifica a última release, baixa o instalador e valida a **assinatura Ed25519** de um manifesto canônico que vincula **versão, tag, nome, tamanho e SHA-256 do asset**; manifestos antigos/replay e downgrades são rejeitados (Windows; no portátil abre a página da release)
- **Modo de extração** (Individual e Lote): **Vídeo + áudio**, **Apenas vídeo** ou **Somente áudio**
- **Qualidade de 144p a 4K** (2160p) e **escolha do arquivo** de saída: **mp4, mkv, webm, avi, mov** (ou **mp3, m4a, wav, flac, opus** no modo áudio)
- **Compressão de vídeo**: mantenha o original (sem reencode) ou recomprima para **H.264** ou **H.265 (HEVC)**, com nível **Leve / Média / Forte**. O arquivo recomprimido ganha sufixo `_h264`/`_h265` e o original é preservado; se a compressão falhar, o original permanece intacto
- **Nome do arquivo**: escolha entre o **ID estável** (hash da URL, `vid_XXXXXXXXXX`) ou o **título da página** com o ID entre colchetes (metadados do vídeo), para evitar colisão entre títulos iguais
- **13 idiomas**: Português (Brasil), Português (Portugal), English, Español, Deutsch, Italiano, Français, Русский, العربية, עברית, 日本語, 한국어 e 中文 (简体)
- **RTL**: árabe e hebraico espelham navegação, tabelas e alinhamento de texto
- **Aba Sobre**: versão, atualizações, licença MIT, repositório, issues e atalhos para logs/pasta de saída
- **Termos técnicos**: codec, bitrate, container, preset, stream, playlist, checksum, encoder e afins permanecem em inglês para manter a nomenclatura da indústria
- Baixa vídeos de URLs de playlist `.m3u8` e links de vídeo diretos
- Fluxo de engenharia em camadas: `yt-dlp` → raspagem do HTML (`requests` + `BeautifulSoup`) → `ffmpeg` como fallback final
- **Gerenciador de dependências**: detecta `yt-dlp`, `ffmpeg`, `requests`, `beautifulsoup4` e `PySide6` e permite **instalar/atualizar** direto na aba Configurações → Dependências (com confirmação), incluindo a escolha do **canal do yt-dlp** (Estável / Nightly / Master)
- **Rede amigável ao WiFi**: limite de velocidade (`--limit-rate`) e conexões por download (`--concurrent-fragments`) configuráveis — evita derrubar o WiFi de roteadores domésticos em downloads pesados
- **Extensões incomuns (`.php`, `.aspx`, ...)**: quando o yt-dlp recusa a URL por segurança (CVE-2024-38519), o app **não** reativa `allow-unsafe-ext`; informa a recusa e mantém o fluxo seguro de raspagem/ffmpeg
- Múltiplos downloads simultâneos, com **pausar a fila** (os downloads ativos continuam), **retomar** e **cancelar** (individual ou tudo)
- **Anti-duplicado**: evita links duplicados na fila e não re-baixa arquivos já existentes no disco
- **Edição inline** do link (duplo clique ou botão ✎), **copiar link**, **tentar novamente** e **abrir pasta**
- **Menu de contexto** (clique com o botão direito) e **atalhos**: `Ctrl+V` (colar da área de transferência), `Ctrl+Enter` (adicionar), `F5` (iniciar), `Delete` (remover)
- **Arrastar e soltar** links ou arquivos `.txt` na janela
- **Miniaturas** geradas automaticamente de cada vídeo baixado (ffmpeg)
- **Erros com detalhes**: a linha com falha mostra a mensagem em vermelho; clique para ver o erro completo (com botão de copiar). Log rotativo em `%APPDATA%\HLSDownloaderPro` (Windows) / `~/.config/HLSDownloaderPro` (Linux)
- **Idioma PT/EN** completo, inclusive das mensagens de erro do backend
- **Nomes de arquivo curtos e estáveis**: hash da URL (`vid_XXXXXXXXXX.mp4`), sem caracteres especiais nem colisões
- **Instância única**: abrir o app de novo traz a janela existente para frente
- **Miniaturas temporárias** (apagadas ao fechar) e **encerramento gracioso** (mata downloads pendentes)
- Barra de título personalizada (sem borda), arrastável
- Persistência de configurações em `settings.ini` (tema, idioma, concorrência, janela, cookies)
- Compatível com **Windows e Linux** (e macOS para os caminhos de arquivo abertos)

## Requisitos

- Python 3.10+
- PySide6 (Qt 6)
- yt-dlp
- ffmpeg (fallback + miniaturas)
- requests + beautifulsoup4 (opcionais em runtime; incluídas nas dependências pip e no build empacotado para habilitar o fallback de raspagem)

Todas podem ser instaladas pelo próprio app (Configurações → Dependências).

### Política de rede e atualizações

O modelo de ameaça completo, incluindo a fronteira de yt-dlp/FFmpeg e riscos
residuais, está em [`THREAT_MODEL.md`](THREAT_MODEL.md).

- O download aceita apenas URLs `http`/`https` com host válido; `file:`,
  `ftp:`, `data:` e esquemas semelhantes são recusados antes de chegar ao
  yt-dlp/ffmpeg.
- O scraper segue redirecionamentos manualmente (máximo de 5), revalidando o
  destino a cada salto. Uma página pública não pode redirecionar para
  loopback/rede privada; servidores LAN continuam suportados quando a URL
  inicial também é local.
- O cabeçalho `Referer` só é enviado entre a mesma origem (esquema, host e
  porta), sem query string, fragmento ou credenciais. Tokens da URL original
  não vazam para CDNs de outra origem.
- A resposta HTML é lida em streaming com limite de 4 MiB descompactados e
  `Content-Type` validado, evitando consumo ilimitado de memória.
- Atualizações usam `release-manifest-*.json` assinado (Ed25519) com versão,
  tag e identidade do asset. O formato legado `SHA256SUMS-*.txt` só é aceito
  quando o nome do instalador cita a versão da tag; qualquer divergência de
  versão, tag, nome, tamanho ou hash bloqueia a instalação.
- Em Linux/macOS o gerenciador de pacotes do sistema é o caminho preferido
  para o FFmpeg. No macOS, o download estático do evermeet só ocorre com hash
  fixado no projeto ou consentimento explícito
  (`HLSDL_ALLOW_UNVERIFIED_FFMPEG=1`); tamanho isolado não é tratado como
  autenticação.

## Instalação

### Linux — binário pronto (Releases)

Baixe **HLS-Downloader-Pro-linux-x86_64.tar.gz** na seção
[Releases](https://github.com/landre-codes/HLS-Downloader-Pro/releases)
(Qt 6 embutido, não precisa de Python):

```bash
tar -xzf HLS-Downloader-Pro-linux-x86_64.tar.gz
cd HLS-Downloader-Pro-linux-x86_64
sudo apt install ffmpeg yt-dlp libxcb-cursor0   # ou instale pelo app
./HLS-Downloader-Pro
```

**Atalho clicável no menu de aplicativos** (instala o binário, ícone, entrada no
menu, **ffmpeg** e o **yt-dlp mais recente via pip**):

```bash
cd HLS-Downloader-Pro-linux-x86_64
./install-desktop.sh
```

> Se aparecer `qt.qpa.plugin: ... xcb-cursor0`: falta a lib do Qt —
> `sudo apt install libxcb-cursor0` (o `install-desktop.sh` instala tudo).

### Linux — via script (código-fonte)

```bash
git clone https://github.com/landre-codes/HLS-Downloader-Pro.git
cd HLS-Downloader-Pro
./install.sh        # instala ffmpeg/python, cria .venv e o atalho
hls-downloader-pro  # (ou .venv/bin/python main.py)
```

### Windows

**Instalador (recomendado)** — baixe `HLS-Downloader-Pro-<versão>-setup.exe` nas
[Releases](https://github.com/landre-codes/HLS-Downloader-Pro/releases).
Instala **por usuário, sem administrador**, cria atalho no Menu Iniciar,
desinstalador e abre o app ao final. O instalador **não inclui** ffmpeg/yt-dlp:
o próprio app oferece baixá-los em Configurações → Dependências.

**Portátil (sem instalar)** — baixe
`HLS-Downloader-Pro-<versão>-portable-win64.zip`, extraia e rode
`HLS-Downloader-Pro.exe`. O `portable.flag` mantém configurações, logs e
ferramentas dentro da própria pasta (bom para pen drive).

Os artefatos têm **SHA-256** publicado (`SHA256SUMS-windows.txt`) e o build
Windows usa `--onedir` (startup mais rápido e menos falsos positivos de
antivírus). Sem certificado de assinatura, o SmartScreen pode avisar na
primeira execução — confira o hash.

As releases também publicam um **SBOM CycloneDX** por plataforma
(`HLS-Downloader-Pro-<versão>-sbom.json` no Windows e
`HLS-Downloader-Pro-linux-x86_64-sbom.json` no Linux); os hashes dos SBOMs
entram nos respectivos `SHA256SUMS`.

### Windows — código-fonte

```powershell
pip install -r requirements.txt
python main.py            # ou: python main.py --portable
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install ffmpeg python3-pip
python3 -m pip install -r requirements.txt
python3 main.py
```

Se a janela der problema no Wayland: `QT_QPA_PLATFORM=xcb python3 main.py`.

## Como usar

1. **Download Individual**: cole a URL, escolha o formato, a qualidade (144p–4K), o arquivo e a compressão (H.264/H.265), e clique em **Baixar agora**. O progresso aparece na mesma aba.
2. **Downloads**: cole vários links (um por linha) – ou importe/arraste um `.txt` –, ajuste formato/qualidade/arquivo/compressão e clique em **Adicionar à Fila**. Use **Carregar playlist** para importar uma playlist no mesmo fluxo; os itens entram selecionados por padrão e podem ser filtrados, desmarcados ou limpos antes de enviar à fila. Use o campo **Filtrar** para achar itens por título/URL.
3. **Compressão**: adicione arquivos/pastas (ou arraste vídeos), escolha um **preset** ou ajuste as seções **Geral**, **Vídeo**, **Áudio e legendas** e **Avançado**; clique em **Iniciar**. O botão **Sugestões** compara economia × compatibilidade. **Mídias similares** procura duplicados/reencodes na fila ou em uma pasta. O original só é apagado se você marcar "Apagar original após sucesso", e mesmo assim um backup é mantido.
4. Em **Configurações → Downloads** você escolhe o **nome do arquivo** (ID estável ou título da página).
5. Em **Configurações → Sobre** você vê a versão e pode **Verificar atualizações**.
6. Clique em **Iniciar Fila** e acompanhe status, percentual, velocidade e tamanho.
7. Ao concluir, o botão **Abrir** mostra a pasta do arquivo; botões laterais permitem editar, copiar, tentar novamente e cancelar.
8. Duplo clique em um link para editá-lo (campo de edição na própria linha); botão direito abre o menu de contexto.

### Cookies (sites protegidos)

Habilite na seção **Cookies** e escolha o navegador (usa os cookies dele) ou um
arquivo `cookies.txt` (formato Netscape), que tem prioridade.

### Dependências

Em **Configurações → Dependências** o app lista cada ferramenta com estado,
versão e botões **Instalar/Atualizar** — sem exigir conhecimento de Python:

- **yt-dlp**: baixa o binário oficial autônomo para a pasta do usuário
  (`%APPDATA%\HLSDownloaderPro\tools` / `~/.config/HLSDownloaderPro/tools`) e o
  coloca no PATH automaticamente. Você escolhe o **canal**: Estável, Nightly ou
  Master.
- **ffmpeg**: instala pelo gerenciador de pacotes quando disponível
  (`winget`/`choco`/`scoop`, `apt`/`dnf`/`pacman`, `brew`); se não houver,
  baixa um build estático e extrai `ffmpeg`/`ffprobe` na mesma pasta.
- **PySide6 / requests / beautifulsoup4**: já vêm embutidos no binário; em
  ambiente de desenvolvimento podem ser atualizados via pip.

Na primeira execução, se faltar algo obrigatório, o app **pergunta** se deseja
instalar agora (e não volta a perguntar depois que você escolhe "continuar").

## Modo portátil

Para manter tudo ao lado do executável (sem gravar em `%APPDATA%`):

- na versão portátil (ZIP), já existe um `portable.flag`;
- no executável/atalho, use `HLS-Downloader-Pro.exe --portable`;
- ou crie manualmente um arquivo `portable.flag` na pasta do executável.

Nesse modo, `settings.ini`, `hls_downloader.log` e `tools/` ficam na mesma pasta.

## Escala da interface

O app detecta a largura lógica da tela e aumenta **fonte, ícones e espaçamentos
juntos** (via `QT_SCALE_FACTOR`), preservando o alinhamento das tabelas:

| Tela (largura lógica) | Escala |
|---|---|
| até 1600 px | 100% |
| 1920 px (1080p) | ~110% |
| 2560 px (1440p) | ~126% |
| 3840 px (4K a 100%) | 128% (limite) |

Para forçar outro valor (sem alterar o sistema):

```powershell
HLS-Downloader-Pro.exe --ui-scale 1.25
# ou: --ui-scale=1.25 / variável HLSDL_UI_SCALE=1.25
```

A escala automática pode ser desativada com `--ui-scale 1`. Quando o Windows
já aplica escala de DPI (125%, 150%, 200%), o app **não soma** outro fator, para
evitar texto gigante e layout cortado; o `--ui-scale` explícito continua
funcionando.

A geometria salva é limitada à área disponível da tela, então mudar a escala
não deixa a janela maior que o monitor.

## Diagnóstico

Se a janela abrir com tamanho estranho, escala errada, ferramenta não encontrada
ou a interface parecer cortada:

```powershell
python diagnostico.py
# no executável empacotado:
HLS-Downloader-Pro.exe --diagnose
```

Gera `diagnostico-hlsdl.txt` ao lado do projeto (em dev) ou na pasta de
configuração, com:

- versão do app, Python, PySide6, Qt, sistema e modo portátil;
- telas, geometria, área disponível, `devicePixelRatio` e escala calculada;
- caminhos de configuração, log, crash log, ferramentas e saída;
- geometria salva da janela;
- versões de ffmpeg/ffprobe/yt-dlp;
- GPUs detectadas, fornecedores e encoders de hardware/software disponíveis.

O diagnóstico **não abre a janela principal nem altera arquivos do usuário**.

## Logs e recuperação de falhas

- **Log rotativo**: `%APPDATA%\HLSDownloaderPro\hls_downloader.log` (ou ao lado
  do executável no modo portátil). Em desenvolvimento também é gravado
  `hls_downloader.log` na raiz do projeto.
- **Crash log**: `hlsdl-crash.log` na pasta de configuração, via `faulthandler`
  (captura falhas nativas do Qt/ffmpeg e o stack de todas as threads).
- **Avisos do Qt/QML** (bindings quebrados, propriedades inexistentes) vão para
  o mesmo log — inclusive no build `--windowed`, sem console.
- **Exceções não tratadas** na thread principal e nas threads de
  download/compressão são registradas com traceback.
- **Dados sensíveis**: URLs assinadas (query/fragmento), credenciais embutidas,
  cabeçalhos `Authorization`/`Cookie` e caminhos de cookies são redigidos antes
  de serem gravados no log.
- Use `--verbose` para elevar o nível para `DEBUG`.

## Integridade das ferramentas

As ferramentas baixadas pelo próprio app são conferidas antes da instalação:

| Ferramenta | Verificação |
|---|---|
| yt-dlp (stable/nightly/master) | SHA-256 do `SHA2-256SUMS` oficial |
| ffmpeg Windows (Gyan) | SHA-256 do `.sha256` publicado |
| ffmpeg Linux (johnvansickle) | MD5 do `.md5` publicado |
| ffmpeg macOS (evermeet) | tamanho exato informado pela API (o site não publica hash) |

Se o sidecar não estiver disponível, o digest for inválido ou o arquivo não
conferir, a instalação é abortada e o binário temporário é removido. No Windows
e no Linux, o ffmpeg ainda pode ser instalado pelo gerenciador de pacotes do
sistema como alternativa.

## CLI (automação)

O pacote instala o comando `hlsdl`:

```bash
hlsdl probe video.mp4                 # streams, duração, HDR
hlsdl verify video.mp4                # sidecar + SHA-256/BLAKE3
hlsdl similar --threshold 85 ./Videos # grupos de mídias similares
hlsdl compress in.mp4 --codec hevc --container mp4 --quality 24
hlsdl download https://youtu.be/... --outdir ./Videos
```

`compress` mantém o original por padrão; `--replace` remove após validação e ainda deixa o backup. O journal/recuperação é o mesmo da GUI. No modo headless, uma queda extrema de bitrate é recusada por segurança; use `--allow-quality-drop` para aceitar a saída.

## Integridade, similares e recuperação

- **Sidecar de conclusão**: cada download/compressão validado grava um sidecar `arquivo.ext.hlsdl.json` oculto no Explorer do Windows, com tamanho, duração, resumo do `ffprobe`, SHA-256, encoder e configurações. O app não confia apenas em “arquivo existe”.
- **Identidade de mídia**: YouTube/Vimeo usam o ID do extractor; HLS usa o hash do manifesto (segmentos e `EXT-X-ENDLIST`, ignorando tokens); demais URLs usam host/path com parâmetros voláteis removidos.
- **Compressão transacional**: `.part` único por job, journal em `%APPDATA%\HLSDownloaderPro\jobs` (ou `jobs/` no portátil), backup do original e `os.replace` somente após validação profunda. Na inicialização, journals pendentes são recuperados: parcial é descartado, original é restaurado e saída só é mantida se o hash/tamanho conferirem.
- **Validação de saída**: duração/streams, resolução, bit depth, cor/HDR, contagem/codec/canais de áudio, legendas e contagem de frames. Falha de áudio ou hash aborta a substituição.
- **Mídias similares**: na aba Compressão, “Mídias similares” analisa a fila ou uma pasta. Usa dHash multi-frame + aHash + envelope RMS de áudio; se faltar vídeo/áudio, cai para hash amostral, duração/resolução e similaridade de nome. O resultado é uma triagem, não uma exclusão automática.
- **Backups**: “Apagar original” deixa um `*.hlsdl-backup-*` ao lado do arquivo. A remoção do backup é manual, para preservar dados em caso de erro tardio.

## Exportar

Para gerar pacotes de distribuição e conferir integridade:

```powershell
python exportar.py
```

Saída em `dist/`:

- `HLS-Downloader-Pro-<versão>-source.zip` — código, testes e documentação;
- `HLS-Downloader-Pro-<versão>-portable-win64.zip` — build `onedir` com
  `portable.flag` e documentação (quando `dist/HLS-Downloader-Pro` existe);
- `SHA256SUMS.txt` e `SHA256SUMS-windows.txt` — hashes dos pacotes e do instalador, quando presente.

## Assinatura de atualizações

O manifesto `SHA256SUMS-windows.txt` é assinado com Ed25519. O app embute a
chave pública em `hlsdl/update_trust.py` e recusa atualizações sem assinatura
válida. O CI também assina `SHA256SUMS-linux.txt` e publica o `.sig` ao lado do
pacote, para verificação manual.

Gere a chave uma única vez e guarde o PEM fora do repositório:

```powershell
python scripts/gen_update_key.py --out C:\caminho\seguro\update_signing_key.pem
```

No GitHub, configure o segredo `UPDATE_SIGNING_KEY` com o conteúdo do PEM. O CI
assina os manifestos automaticamente em releases; localmente:

```powershell
python scripts/sign_release.py SHA256SUMS-windows.txt --key C:\caminho\seguro\update_signing_key.pem
python scripts/sign_release.py SHA256SUMS-linux.txt --key C:\caminho\seguro\update_signing_key.pem
```

O `constraints.txt` fixa as versões usadas no CI e nos builds de release.
O workflow `Hardware encoders` roda o teste QSV em um runner self-hosted com os
labels `self-hosted`, `windows`, `x64` e `qsv`.

No dia a dia de desenvolvimento, `iniciar.cmd` abre o app usando o `.venv`
(ou `py -3`/`python` como fallback).

## Testes

A suíte principal usa **pytest** e é offscreen (sem rede por padrão):

```bash
pip install -e ".[dev]"     # ou: pip install pytest ruff
python -m pytest -q
ruff check hlsdl tests main.py worker.py diagnostico.py exportar.py
```

Scripts de integração/manuais (requerem rede ou ffmpeg):

```bash
python smoke_test.py         # backend + carregamento do QML
python functional_test.py    # fluxo completo com servidor HLS local
python integration_test.py   # downloads reais (Apple sample streams)
python _i18n_test.py         # troca de idiomas no QML
python _error_dialog_test.py # diálogo de detalhes do erro
python _single_instance_test.py  # bloqueio de segunda instância
python php_flow_test.py      # fluxo .php: bloqueio do yt-dlp → retry → scraper/ffmpeg
python layout_debug.py       # dump da geometria do layout
```

## Estrutura

| Arquivo | Papel |
|---|---|
| `hlsdl/app.py` | Entry point: logging rotativo, crash log, hooks de exceção/Qt, instância única e shutdown gracioso |
| `hlsdl/bridge.py` | Fachada QML enxuta + composição dos mixins; núcleo de settings/lifecycle |
| `hlsdl/bridge_parts/` | Mixins por domínio: settings, downloads, compression, similarity, updates, playlist, dependencies, signals |
| `hlsdl/config.py` | Caminhos (inclui build congelado), constantes, preferências |
| `hlsdl/model.py` | `DownloadModel` — **dono único** da lista de itens |
| `hlsdl/queue.py` | `QueueManager` — escalonador de threads/concorrência |
| `hlsdl/downloader.py` | `DownloadWorker` — yt-dlp, ffmpeg e progresso |
| `hlsdl/compress.py` | Fila/worker de compressão local (QSV/NVENC/AMF/Kvazaar/x265) |
| `hlsdl/updater.py` | Verificação/download de atualizações com SHA-256 e assinatura Ed25519 |
| `hlsdl/update_trust.py` | Chave pública e verificação do manifesto de atualizações |
| `hlsdl/playlist.py` | Carregador de itens de playlist (YouTube/site) |
| `hlsdl/formats.py` | Modos, qualidades e contêineres suportados |
| `hlsdl/deps.py` | Detecção/instalação/atualização de dependências |
| `hlsdl/i18n.py` | Mensagens do backend (13 idiomas, incluindo RTL) |
| `hlsdl/status.py` | Enum de status (fonte única de verdade) |
| `hlsdl/media.py` | `ffprobe`, identidade de mídia, HDR metadata, dHash/aHash, envelope RMS, SSIM |
| `hlsdl/integrity.py` | Sidecar de conclusão, SHA-256/BLAKE3, backup, journal e recuperação transacional |
| `hlsdl/catalog.py` | Índice SQLite de mídia, hashes, validação e jobs |
| `hlsdl/similarity.py` | Busca de mídias similares (perceptual + fallbacks) |
| `hlsdl/jobs.py` | Ciclo de vida compartilhado de QThreads |
| `hlsdl/persistence.py`, `hlsdl/cli.py` | Fila persistente e automação headless |
| `hlsdl/naming.py`, `hlsdl/urlutils.py` | Nomes de arquivo e URLs |
| `hlsdl/services/` | Scraper HTML e utilitários de processo/ffmpeg |
| `hlsdl/diagnostics.py`, `diagnostico.py` | Relatório de ambiente, telas, escala, ferramentas e encoders |
| `hlsdl/exporter.py`, `exportar.py` | Pacotes de código-fonte/portátil e `SHA256SUMS.txt` |
| `hlsdl/ui/main.qml` | Shell da janela: título, abas, atalhos, drop zone e tema |
| `hlsdl/ui/pages/` | Páginas QML extraídas: Individual, Downloads, Compressão e Configurações |
| `hlsdl/ui/components/` | Componentes reutilizáveis (botões, combos, campos, painel de terminal, seletores e superfície de diálogo) |
| `hlsdl/ui/dialogs/` | Diálogos modulares: erro, confirmações, dependências, opções do lote, sugestões, similaridade e recuperação |
| `hlsdl/ui/i18n.js` | Traduções e retradução da interface |
| `installer/` | Script Inno Setup do instalador Windows |
| `scripts/` | Geração do ícone e dos metadados de versão do exe |
| `assets/` | Ícone (`icon.ico`/`icon.png`) |
| `LICENSE`, `THIRD_PARTY_NOTICES.md`, `CHANGELOG.md` | Licença e documentação legal |
| `main.py`, `worker.py` | Fachadas de compatibilidade (empacotamento/scripts) |
| `iniciar.cmd` | Atalho de desenvolvimento (`.venv` → `main.py`) |

## Notas de arquitetura

- **Uma só lista de itens** compartilhada por modelo e gerente (evita corrupção de índices).
- **Status como enum**, nunca strings de apresentação na lógica.
- **Motores e serviços isolados** (`services/`) e injetáveis (`worker_factory`).
- **Configuração tipada** e ciente de build empacotado (Windows: `--onedir`; Linux: `--onefile`).
- **Testes** cobrem deduplicação, ciclo de vida da fila, persistência e o carregamento do QML.
- **UI modular**: `main.qml` é só o shell; cada aba vive em `hlsdl/ui/pages/` e os controles
  compartilhados em `hlsdl/ui/components/`. O CI roda `pyside6-qmllint` para bloquear erros
  de sintaxe/tipo (warnings de `unqualified access` não falham o build).

## Licença

MIT — ver [LICENSE](LICENSE). Avisos de bibliotecas de terceiros em
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). O aplicativo usa
**PySide6/Qt (LGPL)** e baixa yt-dlp/ffmpeg em tempo de execução (não os
redistribui no instalador).
