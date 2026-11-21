# Avisos de terceiros / Third-party notices

O HLS Downloader Pro é distribuído sob a licença **MIT** (ver `LICENSE`).
Ele utiliza as bibliotecas abaixo, cada uma com sua própria licença.

## Bibliotecas embutidas no aplicativo

| Componente | Licença | Uso |
|---|---|---|
| **PySide6 / Qt for Python** | LGPLv3 (ou comercial) | Interface gráfica (Qt 6) |
| **Qt 6** | LGPLv3 / GPLv3 / comercial | Framework de UI |
| **requests** | Apache-2.0 | Raspagem HTML (fallback) |
| **beautifulsoup4** | MIT | Parsing HTML (fallback) |
| **Python** | PSF License | Runtime |
| **PyInstaller** (apenas build) | GPLv2 com exceção de bootloader | Empacotamento |

PySide6 e Qt são usados dinamicamente; os avisos e a possibilidade de
substituição das bibliotecas (LGPL) são preservados no pacote distribuído.

## Ferramentas obtidas em tempo de execução (não distribuídas)

Estas ferramentas **não são incluídas** no instalador. O aplicativo pode
baixá-las a pedido do usuário, na pasta de ferramentas do próprio app:

| Ferramenta | Licença | Observação |
|---|---|---|
| **yt-dlp** | Unlicense | Binário oficial baixado do GitHub |
| **ffmpeg / ffprobe** | GPLv3 ou LGPLv2.1+ (depende do build) | Builds do Gyan/johnvansickle/evermeet; o usuário escolhe instalar |

Caso você redistribua builds do ffmpeg junto com o aplicativo, as obrigações
da licença correspondente (GPL/LGPL) passam a se aplicar à sua distribuição.
Por isso o projeto mantém o download em tempo de execução.

## Ícones de navegadores

Os ícones dos navegadores são usados apenas para identificar a origem dos
cookies na interface:

- Chrome, Firefox, Opera, Vivaldi e Brave: glifos do projeto
  [Simple Icons](https://simpleicons.org/), disponibilizados sob CC0 1.0.
- Microsoft Edge e Chromium: arquivos do Wikimedia Commons; consulte as
  páginas dos respectivos arquivos para licença e regras de uso.
- As marcas e logotipos pertencem aos seus titulares. O projeto não é
  afiliado a nenhum navegador.

As bandeiras do seletor de idioma são desenhos SVG locais e simplificados,
usados apenas como apoio visual; o nome do idioma continua sendo a
identidade principal.

## Marcas

YouTube, Qt, FFmpeg e demais nomes são marcas de seus respectivos titulares.
Este projeto não é afiliado a nenhum deles.
