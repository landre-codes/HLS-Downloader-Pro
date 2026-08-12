# HLS Downloader Pro

Downloader de vídeos (HLS / m3u8) com interface **Qt Quick (QML) + Material Design**.

## Funcionalidades

- Baixa vídeos de URLs de playlist `.m3u8` e links de vídeo diretos
- Fluxo de engenharia em camadas: `yt-dlp` → raspagem do HTML (`requests` + `BeautifulSoup`) → `ffmpeg` como fallback final
- Múltiplos downloads simultâneos (concorrência configurável)
- **Anti-duplicado**: evita links duplicados na fila e não re-baixa arquivos já existentes no disco
- **Edição inline** do link na tabela (duplo clique) e **copiar link** para a área de transferência
- **Miniaturas** geradas automaticamente de cada vídeo baixado (ffmpeg)
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
sudo apt install ffmpeg yt-dlp   # requisitos do download
./HLS-Downloader-Pro
```

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
python layout_debug.py      # dump da geometria do layout
```

## Estrutura

| Arquivo | Papel |
|---|---|
| `main.py` | Janela QML + ponte Python↔QML + persistência |
| `worker.py` | Motor de download: modelo da fila, threads QThread, yt-dlp/ffmpeg |
| `ui.qml` | Interface completa (Material Design, tema claro/escuro) |
