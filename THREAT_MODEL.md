# Threat model — HLS Downloader Pro

**Atualizado:** 18/11/2026  
**Escopo:** URLs fornecidas pelo usuário, HTML raspado, metadados de playlists,
manifestos/segmentos HLS, atualizações e binários auxiliares.

## Ativos e fronteiras

| Ativo | Confiança | Controle |
|---|---|---|
| URL digitada/colada pelo usuário | não confiável | `netpolicy.validate_http_url`; somente HTTP/HTTPS com host válido |
| HTML de página raspada | não confiável | redirect manual, bloqueio público→privado, limite de 4 MiB, `Content-Type` |
| Manifesto/segmento HLS | não confiável | entregue ao yt-dlp/FFmpeg após validação da URL inicial |
| Cookies e cabeçalhos | sensível | escopo de domínio; `Referer` same-origin sem query/userinfo; logs redigidos |
| Manifesto de atualização | não confiável até a assinatura | Ed25519 antes do parsing; identidade versão/tag/asset |
| Instalador de atualização | não confiável até hash/tamanho | host GitHub permitido, limite de bytes, SHA-256 do manifesto assinado |
| FFmpeg/yt-dlp baixados | não confiável até verificação | SHA-256 (Windows), política restritiva no macOS, MD5+alerta no Linux |
| Arquivos de mídia locais | dados do usuário | transação com journal, backup e verificação antes de substituir |

## Modelo de ameaça

O aplicativo é desktop e o usuário escolhe deliberadamente as URLs. O objetivo
não é bloquear toda rede local — downloads de servidores LAN são legítimos.
O objetivo é impedir que conteúdo remoto não confiável (página, redirect ou
playlist) redirecione silenciosamente o app para loopback, link-local,
metadados de nuvem ou serviços internos.

### Scraper (fronteira controlada pelo app)

- esquemas diferentes de HTTP/HTTPS são recusados;
- cada redirect é revalidado (máximo 5);
- uma página pública não pode redirecionar para destino privado/loopback;
- `Referer` só é enviado na mesma origem e sem query/fragmento/credenciais;
- corpo é lido em streaming com teto de 4 MiB descompactados.

### yt-dlp e FFmpeg (fronteira de terceiros)

`yt-dlp` e `ffmpeg` resolvem DNS e seguem redirecionamentos internamente. A
validação do app cobre a URL inicial e a descoberta via scraper, mas **não é
um sandbox de rede**. Um redirect interno dessas ferramentas pode alcançar um
destino que o scraper bloquearia. Isso é uma limitação arquitetural conhecida,
não uma garantia de isolamento total.

Mitigações possíveis no futuro: proxy local com allowlist, modo estrito para
URLs públicas, ou execução em sandbox de SO. Nenhuma foi implementada nesta
versão; o modo LAN continua permitido.

## Decisões de compatibilidade

- **`allow-unsafe-ext` do yt-dlp:** removido. O app não reativa a opção
  insegura; a recusa de extensão incomum é tratada como erro e o fluxo segue
  para raspagem/ffmpeg. `_looks_like_non_video` permanece como defesa em
  profundidade na validação de mídia.
- **Manifesto de atualização legado:** aceito somente quando o nome do asset
  contém a versão exata da tag. O formato novo assinado é preferido.
- **FFmpeg:** gerenciador de pacotes do sistema é preferido em Linux/macOS.
  No macOS o download estático é fail-closed sem pin ou consentimento
  explícito (`HLSDL_ALLOW_UNVERIFIED_FFMPEG=1`). No Linux o fornecedor publica
  apenas MD5; o app registra o SHA-256 observado e alerta sobre a garantia
  limitada.
- **Sidecars:** no POSIX novos sidecars começam com ponto; os nomes antigos
  continuam legíveis.

## Riscos residuais

1. DNS rebinding/TOCTOU entre a validação e a conexão do `requests`/yt-dlp/FFmpeg.
2. Redirects e resolução de DNS internos das ferramentas externas.
3. Provedor de FFmpeg Linux sem SHA-256/assinatura independente.
4. PySide6 6.12.0 sujeito a advisories upstream até wheel corrigida.
5. Ausência de sandbox de SO para subprocessos.
6. Cobertura de testes não substitui execução em Windows/Linux/macOS reais,
   hardware NVENC/AMF e CI em SHA imutável.

## Gate de release

Antes de publicar uma versão 1.5.x:

- CI verde em commit imutável, com logs anexados;
- release de teste assinada, incluindo tentativa de replay/downgrade;
- smoke real nos SOs suportados;
- HDR validado por encoder anunciado ou limitação documentada;
- checklist de UI/teclado/contraste;
- SBOM do bundle e hashes conferidos por segunda pessoa.
