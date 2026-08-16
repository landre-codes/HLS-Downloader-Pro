# HLS Downloader Pro

Downloader de vídeos (HLS / m3u8) com interface **Qt Quick (QML) + Material Design**.

## Funcionalidades

- Baixa vídeos de URLs de playlist `.m3u8` e links de vídeo diretos
- Fluxo de engenharia em camadas: `yt-dlp` → raspagem do HTML (`requests` + `BeautifulSoup`) → `ffmpeg` como fallback final
- Múltiplos downloads simultâneos (concorrência configurável)
- **Anti-duplicado**: evita links duplicados na fila e não re-baixa arquivos já existentes no disco
- **Edição inline** do link na tabela (duplo clique) e **copiar link** para a área de transferência
- **Miniaturas** geradas automaticamente de cada vídeo baixado (ffmpeg)
- **Erros com detalhes**: a linha com falha mostra a mensagem em vermelho; clique para ver o erro completo em um diálogo (também gravado em `~/.config/HLSDownloaderPro/hls_downloader.log` no Linux / `%APPDATA%\HLSDownloaderPro` no Windows)
- **Idioma PT/EN**: seletor em Configurações → Aparência (preferência persistida)
- **Nomes de arquivo limitados a 20 caracteres** — evita erros de salvamento com títulos muito longos
- **Instância única**: abrir o app duas vezes mostra um aviso (sem downloads duplicados acidentais)
- **Miniaturas temporárias**: ficam em pasta do sistema e são apagadas ao fechar o app
- **Cancelamento** individual ou de toda a fila
- Barra de título personalizada (sem borda), arrastável, com botões de minimizar/maximizar/fechar
- Persistência de configurações em `settings.ini` (tema, concorrência, janela, cookies)
- Compatível com **Windows e Linux** (pastas padrão e abertura de pasta adaptadas por SO)

## Requisitos

- Python 3.10+
- PyQt6 (Qt 6)
- yt-dlp
- ffmpeg (fallback + miniaturas)
- requests + beautifulsoup4 (opcionais, habilitam o fallback de raspagem)

## Instalação

### Linux — binário pronto (Releases)

Baixe **HLS-Downloader-Pro-linux-x86_64.tar.gz** na seção [Releases](https://github.com/landre-codes/HLS-Downloader-Pro/releases) (Qt 6 embutido, não precisa de Python):

```bash
tar -xzf HLS-Downloader-Pro-linux-x86_64.tar.gz
cd HLS-Downloader-Pro-linux-x86_64
sudo apt install ffmpeg yt-dlp libxcb-cursor0   # requisitos do download + Qt
./HLS-Downloader-Pro
```

**Atalho clicável no menu de aplicativos** (instala binário em `~/.local/bin`, ícone, entrada no menu, **ffmpeg** e o **yt-dlp mais recente via pip** — o do `apt` é antigo e quebra em vários sites):

```bash
cd HLS-Downloader-Pro-linux-x86_64
./install-desktop.sh
```

> **Se aparecer `qt.qpa.plugin: ... xcb-cursor0`**: falta a lib do Qt —
> `sudo apt install libxcb-cursor0` (o `install-desktop.sh` instala tudo).

### Linux — via script (código-fonte)

```bash
git clone https://github.com/landre-codes/HLS-Downloader-Pro.git
cd HLS-Downloader-Pro
./install.sh        # instala ffmpeg/python, cria .venv e o atalho
hls-downloader-pro  # (ou .venv/bin/python main.py)
```

### Windows

```powershell
pip install PyQt6 yt-dlp requests beautifulsoup4
choco install ffmpeg   # ou coloque o ffmpeg.exe no PATH
python main.py
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install ffmpeg python3-pip
python3 -m pip install PyQt6 yt-dlp requests beautifulsoup4
python3 main.py
```

Se a janela der problema no Wayland: `QT_QPA_PLATFORM=xcb python3 main.py`.

## Como usar

1. Cole os links na caixa de texto (um por linha) e clique em **Baixar** — ou importe de um arquivo `.txt`
2. Acompanhe o progresso na tabela: status, percentual, velocidade e tamanho
3. Ao concluir, o botão **Abrir** mostra a pasta do arquivo
4. Duplo clique em um link para editá-lo; `⧉` copia o link; `✕` cancela o download individual
5. **Baixar** de novo um link já finalizado tenta novamente sem duplicar arquivos

### Cookies (sites protegidos)

Habilite na seção **Cookies** com `browser:chrome` (usa os cookies do navegador) ou `file:caminho/para/cookies.txt` (formato Netscape).

## Testes

```bash
python smoke_test.py        # modelo, fila, dedup, cancelamento, QML carrega
python functional_test.py   # fluxo completo com servidor HLS local
python integration_test.py  # downloads reais (Apple sample streams)
python _i18n_test.py        # troca de idioma PT/EN no QML
python _error_dialog_test.py  # diálogo de detalhes do erro
python _single_instance_test.py  # bloqueio de segunda instância
python layout_debug.py      # dump da geometria do layout
```

## Estrutura

| Arquivo | Papel |
|---|---|
| `main.py` | Janela QML + ponte Python↔QML + persistência |
| `worker.py` | Motor de download: modelo da fila, threads QThread, yt-dlp/ffmpeg |
| `ui.qml` | Interface completa (Material Design, tema claro/escuro) |
