# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o versionamento segue [SemVer](https://semver.org/lang/pt-BR/).

## [1.3.0] — 2026-11-02

### Adicionado
- Abas **Download Individual**, **Lote**, **Playlists** e **Configurações**.
- **Aba de Playlists** (YouTube e sites em geral): carregar itens, selecionar e enfileirar/baixar.
- **Aba de Compressão local**: HEVC com QSV/NVENC/AMF/x265, qualidade 1–51, paralelismo, validação e substituição segura.
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
