# Plano de remediação — auditoria de 2026-11-17

Base: snapshot `HLSDownloaderPro-audit-2026-11-17.zip`, branch
`feat/media-integrity-similarity`, commit `e236962` + alterações locais.
Este documento registra o que foi efetivamente alterado e o que permanece
dependente de ambiente (hardware, SO ou validação visual).

> Resposta à reauditoria de 18/11: `REAUDIT_RESPONSE.md`. Modelo de ameaça:
> `THREAT_MODEL.md`.

## F0 — Baseline

| Item | Status | Evidência |
|---|---|---|
| Suíte antes das mudanças | verificado | `247 passed` |
| Suíte depois das mudanças | verificado | `295 passed` com `HLSDL_TEST_QSV=1`; sem a variável, `293 passed, 2 skipped` |
| `compileall` | verificado | exit 0 |
| `ruff check` | verificado | `All checks passed!` |
| `mypy` (módulos de segurança) | verificado | `netpolicy`, `release_manifest`, `update_trust` sem erros |
| `pyside6-qmllint` | verificado (estático) | exit 0; warnings preexistentes de `unqualified` |
| Wheel instalável | verificado | `pip wheel .` gerou wheel com `netpolicy.py`, `release_manifest.py`, QML e `bridge_parts` |
| `smoke_test.py` | verificado | `SMOKE TEST OK` |
| `_i18n_test.py` | verificado | `I18N QML OK` |
| `functional_test.py` | verificado | `TODOS OS TESTES FUNCIONAIS PASSARAM` (asserção antiga de status corrigida) |

## F1 — Fronteiras de rede

| Tarefa | Status | Arquivos | Evidência |
|---|---|---|---|
| NET-01 / P1-01 — política única de `Referer` | verificado | `hlsdl/netpolicy.py`, `hlsdl/services/scraper.py`, `hlsdl/downloader.py` | testes de canário same-origin/cross-origin em `tests/test_netpolicy.py`; `Referer` sem query/userinfo |
| NET-02 / P2-01 — somente HTTP/HTTPS | verificado | `hlsdl/netpolicy.py`, `tests/test_netpolicy.py` | `file://`, `ftp://`, `data:` e URL sem host rejeitadas |
| NET-02 / P2-02 — redirects e limite de resposta | verificado em código/teste | `hlsdl/services/scraper.py` | redirect manual (máx. 5), bloqueio público→privado, limite de 4 MiB, `Content-Type` validado |
| Redownload direto pelo yt-dlp | limitação documentada | `hlsdl/downloader.py` | URL inicial validada; redirects internos do yt-dlp/ffmpeg ficam fora do controle do app |

## F2 — Atualização e supply chain

| Tarefa | Status | Arquivos | Evidência |
|---|---|---|---|
| REL-01 / P2-03 — manifesto assinado com identidade | verificado (testes) | `hlsdl/release_manifest.py`, `hlsdl/updater.py`, `scripts/gen_release_manifest.py`, `.github/workflows/ci.yml` | assinatura antes do parsing; versão/tag/nome/tamanho/hash estritos; replay/downgrade rejeitados; e2e local com chave de teste |
| Compatibilidade com manifesto legado | verificado | `hlsdl/updater.py`, `tests/test_updater.py` | `SHA256SUMS-*.txt` só aceito se o nome do asset citar a versão da tag |
| REL-02 / P2-05 — proveniência do FFmpeg | parcial (falta validação real por SO) | `hlsdl/deps.py`, `tests/test_deps_download.py` | macOS falha fechado sem pin/consentimento; Linux alerta MD5 e registra SHA-256; Windows mantém SHA-256 |
| P2-08 — advisories Qt 6.12.0 | pendente de upstream | `constraints.txt` | sem wheel 6.12.1 no ambiente; manter inventário e atualizar quando disponível |

## F3 — Dados e ciclo de vida

| Tarefa | Status | Arquivos | Evidência |
|---|---|---|---|
| DAT-01 / P3-01 — colisão `final == source` | verificado | `hlsdl/integrity.py`, `tests/test_integrity.py` | erro `source_equals_final` antes de backup; dados intactos |
| RUN-01 / P2-07 — shutdown coordenado | verificado em testes | `hlsdl/updater.py`, `hlsdl/deps.py`, `hlsdl/similarity.py`, `hlsdl/compress.py`, `hlsdl/bridge.py` | cancelamento + `join` com timeout; callbacks suprimidos; threads auxiliares e detecção QSV rastreadas; 16 execuções consecutivas estáveis |
| Cancelamento durante assinatura/agrupamento | verificado | `hlsdl/media.py`, `hlsdl/similarity.py` | `cancel` entre frames, áudio e pares de comparação |

## F4 — Fidelidade multimídia

| Tarefa | Status | Arquivos | Evidência |
|---|---|---|---|
| MED-01 / P2-04 — HDR10 completo | verificado com QSV real (MKV/MP4) | `hlsdl/media.py`, `hlsdl/compress.py`, `tests/test_transactional_compress.py`, `tests/test_hdr_hardware.py` | mastering e content-light comparados em todos os encoders; QSV preservou metadados reais; falha vira `hdr_metadata:<motivo>` |
| Testes reais por encoder | QSV verificado; NVENC/AMF pendentes | `tests/test_hdr_hardware.py`, `.github/workflows/hardware.yml` | runner QSV roda o teste; sem NVIDIA/AMD nesta máquina |

## F5 — Interface

| Item | Status | Evidência |
|---|---|---|
| UI-04 — foco em botões da barra e cabeçalhos | verificado em código | `TitleBarButton.qml`, `CompressionPage.qml`; `qmllint` exit 0 |
| UI-01 — 940×620 sem truncamento essencial | verificado com captura e corrigido | rodapé do Lote, rodapé da compressão e scrollbars; `docs/ui-review/940x620-light-batch.png` |
| UI-03 — densidade da compressão | mitigado | painel de ajustes rolável com scrollbar visível e rodapé acessível em 940×620; sem redesign |
| UI-06 — mensagens longas no toast | verificado com captura | 3 linhas, 2,6–8 s, dispensa por clique; `1160x800-light-toast.png` |
| Contraste de botões primários no tema claro | verificado com captura e corrigido | `AppButton` com fundo/texto explícitos; `1160x800-light-single.png` |
| Diálogo de erro | verificado com captura e corrigido | padding e legibilidade; `1160x800-light-error.png` |
| Cabeçalho descritivo por aba (inspirado no DiskPilot) | verificado com captura | `PageHero` com degradê, descrição e ações; ativo ≥1050×650, oculto em 940×620; `1160x800-light-batch-hero.png` |
| UI-02/07/08/09 | pendente de validação | microtexto, placeholders, janela sem moldura em múltiplos monitores e status apenas por cor |

| UI-05 — tokens | parcial (componentes existentes mantidos) | sem redesign; novo foco usa `Material.accent` |

## F6 — Qualidade e release

| Tarefa | Status | Evidência |
|---|---|---|
| QA-01 / P2-06 — gates de CI | verificado em YAML | `qmllint`/smoke sem `|| true`; exit code, marcador de inicialização e encerramento prematuro |
| QA-02 / P3-05/06 — i18n, tipos e cobertura | verificado | paridade completa backend/UI/QML; mypy dos módulos de segurança; gate de cobertura 60% (baseline 67%) |
| QA-03 / P3-02/03 — migrações e SBOM | verificado (escopo mínimo) | `PRAGMA user_version=1`, FK por conexão; SBOM com licenças, escopo e hashes dos arquivos do bundle PyInstaller |
| P3-04 — sidecars POSIX | verificado em código/teste de caminho | novos sidecars com ponto inicial no Linux/macOS; sidecars legados continuam legíveis; execução real em POSIX pendente |
| BOMs e documentação | verificado | BOM removido de `bridge_parts`; README/CHANGELOG atualizados |

## Pendências antes de release

1. Rodar CI real em tag e anexar os resultados.
2. Testar manifesto assinado contra uma release de teste no GitHub (não apenas fixtures).
3. Validar FFmpeg/atualização em Windows, Linux e macOS reais.
4. Matriz visual de telas/temas/DPI e navegação por teclado.
5. Testes de encode HDR10 em QSV/NVENC/AMF com fixtures reais.
6. Atualizar PySide6/Qt quando houver wheel corrigida para os advisories 6.12.x.
