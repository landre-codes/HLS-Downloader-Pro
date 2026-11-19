# Resposta à reauditoria sênior — 2026-11-18

Base: `HLSDownloaderPro-audit-2026-11-18.zip` + alterações desta rodada.
Este documento registra o que foi implementado, o que foi apenas documentado e
o que permanece dependente de ambiente/CI.

## Achados da reauditoria

| ID | Status | Evidência / arquivo |
|---|---|---|
| SEC-18-01 — isolamento de subprocessos | documentado; sem sandbox | `THREAT_MODEL.md`; limites explícitos para scraper vs yt-dlp/FFmpeg; modo LAN preservado |
| SEC-18-02 — `allow-unsafe-ext` | endurecido | `downloader._looks_like_non_video` agora exige `ffprobe` com vídeo/áudio ou assinatura de contêiner conhecida; HTML/playlist/binário desconhecido são descartados; teste em `tests/test_p1_regressions.py` |
| REL-18-01 — endpoints/limites do update | corrigido | `updater._trusted_release_url` limita a `github.com`/`*.githubusercontent.com`; manifesto ≤1 MiB, assinatura ≤16 KiB, API ≤2 MiB; instalador verifica tamanho declarado durante o streaming e host final após redirect |
| REL-18-02 — parser de versão | corrigido | `updater.version_key` trata prerelease/build metadata; `_check` e checagem anti-downgrade usam a chave semântica; testes em `tests/test_updater.py` |
| UX-18-03 — diálogo de erro | corrigido | resumo humano + “Detalhes técnicos” expansível, área rolável e copiar/fechar; capturas `docs/ui-review/1160x800-light-error*.png` |
| UX-18-05 — hero abaixo do breakpoint | corrigido | `PageHero` compacto (40 px sem ações, 52 px com ações) em vez de sumir; continua substituindo o título simples |
| Barra de título / botões | corrigido | gradiente sutil, divisor, versão em pill; hover/pressed/scale/transição em `TitleBarButton`, `AppButton` e `AppToolButton` |
| UX-18-01 — densidade da compressão | mitigado | hero compacto, scrollbars visíveis e rodapé acessível em 940×620; ainda exige rolagem no painel de ajustes |
| UX-18-07 — diálogos auxiliares | parcial | toast, erro (resumo/detalhes) capturados; dependências/qualidade/recuperação/similaridade ainda não |
| UX-18-02 / 18-04 / 18-06 | pendente | tipografia fina, estado vazio do progresso e acessibilidade real (teclado/leitor de tela/contraste medido) |
| DATA-18-01 — stress de SO | pendente | não foram simulados disco cheio, permissão negada e 50+ encerramentos nesta rodada |
| DEP-18-01 — FFmpeg multiplataforma | parcial | política documentada; QSV validado localmente; Linux/macOS reais pendentes |
| QA-18-01 — cobertura por risco | parcial | gate 60%, cobertura global 67,44%; sem branch coverage/mutation testing |
| P2-08 — PySide6 6.12.0 | aberto | 6.12.1 ainda indisponível no índice no momento da validação |

## Evidências executadas

- `295 passed` com `HLSDL_TEST_QSV=1`; sem a variável, `293 passed, 2 skipped`.
- Cobertura: `8638` statements, `2796` missed, `67,63%`; gate de 60%.
- `ruff`, `mypy` (módulos de segurança), `compileall` e `pyside6-qmllint`: limpos.
- `smoke_test.py`, `_i18n_test.py` e `functional_test.py`: OK.
- HDR10/QSV real: mastering display e content-light preservados em MKV/MP4.
- Wheel contém `netpolicy.py`, `release_manifest.py`, QML e `bridge_parts`.

## Limitações que permanecem

1. Não há sandbox de rede para yt-dlp/FFmpeg; a política do app cobre a URL inicial e o scraper, não redirects internos das ferramentas.
2. 940×620 ainda exige rolagem na configuração de compressão; não houve redesign para painel único rolável.
3. Tipografia fina e estados vazios não foram redesenhados sem validação com usuários.
4. Acessibilidade real (Tab completo, leitor de tela, contraste WCAG medido) continua pendente.
5. Não houve stress de I/O/50+ encerramentos, NVENC/AMF, Linux/macOS reais nem CI em SHA imutável.
6. O pacote não contém `.git`; a rastreabilidade de commit depende do repositório.

## Próximo passo recomendado

Fechar o release candidate com CI real em SHA imutável, teste de update assinado,
stress de encerramento/IO e matriz visual dos diálogos restantes. Não é
necessário redesenhar a arquitetura nem adicionar mais estruturas.
