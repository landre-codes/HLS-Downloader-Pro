# HLS Downloader Pro

Downloader de vídeos (HLS / m3u8) com interface **Qt Quick (QML) + Material Design**.

## Funcionalidades

- **Duas abas de download**: **Download Individual** (um link, com progresso dedicado) e **Lote** (fila com dezenas/centenas de links)
- **Aba de Playlists**: carrega os itens de uma playlist (**YouTube** ou sites em geral), permite selecionar os desejados e enviá-los à fila
- **Aba de Compressão local**: fila de arquivos/pastas, codecs **HEVC, H.264 e AV1**, contêineres **MP4/MKV/WebM/MOV/AVI**, aceleração por **Intel QSV, NVIDIA NVENC, AMD AMF, Kvazaar ou software** (`libx265`/`libx264`/`libsvtav1`), qualidade 1–51, presets de velocidade (**rápida → muito lenta**), paralelismo, **sugestões/estimativa de economia por formato**, validação da saída e substituição atômica (original preservado por padrão). O modo **Auto** prioriza a **GPU dedicada** (Arc/NVIDIA/AMD), filtra encoders pela GPU realmente presente e testa o escolhido, caindo para software se ele falhar; o dispositivo QSV pode ser escolhido na interface. Inclui **10-bit** e **ajuste fino do x265** (`aq-mode`/`psy`), além de **preservar metadados HDR** (primárias, transferência, espaço de cor e faixa) e mostrar o **encoder real** usado em cada arquivo (ex.: `QSV HEVC · Intel Arc B580`).
- **Interface**: busca na fila com ícone de pesquisa, cabeçalhos de tabela maiores/destacados, **console de instalação estilo terminal** no log de dependências (com copiar saída), cursor de mão em ações e **tooltips com exemplos**. A escala da interface acompanha o tamanho da tela (até 128%) sem desalinhar as tabelas.
- **Atualizações**: verifica a última release, baixa o instalador e **valida o SHA-256** antes de executar (Windows; no portátil abre a página da release)
- **Modo de extração** (Individual e Lote): **Vídeo + áudio**, **Apenas vídeo** ou **Somente áudio**
- **Qualidade de 144p a 4K** (2160p) e **escolha do arquivo** de saída: **mp4, mkv, webm, avi, mov** (ou **mp3, m4a, wav, flac, opus** no modo áudio)
- **Compressão de vídeo**: mantenha o original (sem reencode) ou recomprima para **H.264** ou **H.265 (HEVC)**, com nível **Leve / Média / Forte**. O arquivo recomprimido ganha sufixo `_h264`/`_h265` e o original é preservado; se a compressão falhar, o original permanece intacto
- **Nome do arquivo**: escolha entre o **ID estável** (hash da URL, `vid_XXXXXXXXXX`) ou o **título da página** com o ID entre colchetes (metadados do vídeo), para evitar colisão entre títulos iguais
- **8 idiomas**: Português, English, Español, Italiano, Français, Русский, 日本語 e 中文 (简体)
- Baixa vídeos de URLs de playlist `.m3u8` e links de vídeo diretos
- Fluxo de engenharia em camadas: `yt-dlp` → raspagem do HTML (`requests` + `BeautifulSoup`) → `ffmpeg` como fallback final
- **Gerenciador de dependências**: detecta `yt-dlp`, `ffmpeg`, `requests`, `beautifulsoup4` e `PySide6` e permite **instalar/atualizar** direto na aba Configurações → Dependências (com confirmação), incluindo a escolha do **canal do yt-dlp** (Estável / Nightly / Master)
- **Rede amigável ao WiFi**: limite de velocidade (`--limit-rate`) e conexões por download (`--concurrent-fragments`) configuráveis — evita derrubar o WiFi de roteadores domésticos em downloads pesados
- **Extensões incomuns (`.php`, `.aspx`, ...)**: quando o yt-dlp recusa a URL por segurança (CVE-2024-38519), o app tenta UMA vez com `--compat-options allow-unsafe-ext` e extensão `.mp4` forçada; se o resultado não for vídeo, o download é descartado e o fluxo segue para a raspagem/ffmpeg
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
- requests + beautifulsoup4 (opcionais, habilitam o fallback de raspagem)

Todas podem ser instaladas pelo próprio app (Configurações → Dependências).

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
2. **Lote**: cole vários links (um por linha) — ou importe/arraste um `.txt` —, ajuste formato/qualidade/arquivo/compressão e clique em **Adicionar à Fila**. Use o campo **Filtrar** para achar itens por título/URL.
3. **Playlists**: cole a URL de uma playlist (YouTube ou site), clique em **Carregar itens**, marque os desejados e use **Adicionar selecionados à fila** (ou **Baixar selecionados agora**).
4. **Compressão**: adicione arquivos/pastas (ou arraste vídeos), escolha **codec/contêiner/qualidade/velocidade/paralelismo** e clique em **Iniciar**. O botão **Sugestões** compara economia × compatibilidade; o original só é apagado se você marcar “Apagar original após sucesso”.
5. Em **Configurações → Downloads** você escolhe o **nome do arquivo** (ID estável ou título da página).
6. Em **Configurações → Sobre** você vê a versão e pode **Verificar atualizações**.
7. Clique em **Iniciar Fila** e acompanhe status, percentual, velocidade e tamanho.
8. Ao concluir, o botão **Abrir** mostra a pasta do arquivo; botões laterais permitem editar, copiar, tentar novamente e cancelar.
9. Duplo clique em um link para editá-lo (campo de edição na própria linha); botão direito abre o menu de contexto.

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

## Exportar

Para gerar pacotes de distribuição e conferir integridade:

```powershell
python exportar.py
```

Saída em `dist/`:

- `HLS-Downloader-Pro-<versão>-source.zip` — código, testes e documentação;
- `HLS-Downloader-Pro-<versão>-portable-win64.zip` — build `onedir` com
  `portable.flag` e documentação (quando `dist/HLS-Downloader-Pro` existe);
- `SHA256SUMS.txt` — hashes dos pacotes e do instalador, quando presente.

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
| `hlsdl/bridge.py` | Ponte Python↔QML (slots, sinais, persistência, dependências) |
| `hlsdl/config.py` | Caminhos (inclui build congelado), constantes, preferências |
| `hlsdl/model.py` | `DownloadModel` — **dono único** da lista de itens |
| `hlsdl/queue.py` | `QueueManager` — escalonador de threads/concorrência |
| `hlsdl/downloader.py` | `DownloadWorker` — yt-dlp, ffmpeg e progresso |
| `hlsdl/compress.py` | Fila/worker de compressão local (QSV/NVENC/AMF/Kvazaar/x265) |
| `hlsdl/updater.py` | Verificação/download de atualizações com SHA-256 |
| `hlsdl/playlist.py` | Carregador de itens de playlist (YouTube/site) |
| `hlsdl/formats.py` | Modos, qualidades e contêineres suportados |
| `hlsdl/deps.py` | Detecção/instalação/atualização de dependências |
| `hlsdl/i18n.py` | Mensagens do backend (8 idiomas) |
| `hlsdl/status.py` | Enum de status (fonte única de verdade) |
| `hlsdl/naming.py`, `hlsdl/urlutils.py` | Nomes de arquivo e URLs |
| `hlsdl/services/` | Scraper HTML e utilitários de processo/ffmpeg |
| `hlsdl/diagnostics.py`, `diagnostico.py` | Relatório de ambiente, telas, escala, ferramentas e encoders |
| `hlsdl/exporter.py`, `exportar.py` | Pacotes de código-fonte/portátil e `SHA256SUMS.txt` |
| `hlsdl/ui/main.qml`, `hlsdl/ui/i18n.js` | Interface completa |
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

## Licença

MIT — ver [LICENSE](LICENSE). Avisos de bibliotecas de terceiros em
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). O aplicativo usa
**PySide6/Qt (LGPL)** e baixa yt-dlp/ffmpeg em tempo de execução (não os
redistribui no instalador).
