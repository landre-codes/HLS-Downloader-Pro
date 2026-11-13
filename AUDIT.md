# Auditoria técnica — HLS Downloader Pro

**Data:** 13/11/2026  
**Versão:** 1.4.0  
**Commit base:** `4c225c1`  
**Escopo:** integridade de mídia, concorrência, segurança, QML/UX, compressão, testes, empacotamento e distribuição.

## Veredito

O projeto está em um nível **bom e acima da média para um app desktop Python/Qt**, com uma base de integridade e recuperação bem pensada. Ainda **não é “padrão-ouro”** por três motivos principais: a cadeia de atualização não tem autenticidade criptográfica, o build de release não é totalmente reproduzível e a validação real de hardware/encoders não está no CI.

**Conceito sugerido:** **B+ (aprovado com ressalvas)**.

## Evidências executadas

- `pytest -q`: **216 testes passando**.
- `ruff check`: limpo.
- `pyside6-qmllint`: sem erros de sintaxe/tipo.
- `pip check`: sem dependências quebradas.
- Wheel construído e instalado fora do repositório; QML carregado a partir do pacote instalado.
- Executável PyInstaller testado 20 s em modo offscreen, sem erros de carga/import.
- Revisão visual das 5 abas, barra de título, diálogo de similares e aba Compressão em 1400×950, 1160×800 e 1000×700.
- Revisão estática de `subprocess`, threads, tratamento de exceções, sidecars, journals, CI e empacotamento.

## Scorecard

| Área | Avaliação | Observação |
|---|---|---|
| Integridade e recuperação | **A-** | Journal, backup, hash, sidecar e recuperação são consistentes; faltam testes de falha real em mais cenários. |
| Compressão/HandBrake | **A-** | Boa cobertura de filtros, HDR, áudio, legendas e validação; paridade hardware ainda depende de testes manuais. |
| Concorrência/encerramento | **B-** | QThreads principais têm lifecycle; threads auxiliares ainda são daemon sem join explícito. |
| Segurança de suprimentos | **C** | Checksums bons, mas atualização e build sem assinatura/pinagem fortes. |
| Testes | **B** | 216 testes e boa cobertura de lógica; faltam integração real, UI e hardware no CI. |
| UX/QML | **B+** | Evolução grande; falta teste visual automatizado e alguns erros ainda são códigos internos. |
| Distribuição | **B** | Wheel, SBOM e instalador funcionam; CI ainda frágil e sem code signing. |
| Manutenibilidade | **B-** | Módulos grandes, exceções amplas, BOM/mojibake e ausência de mypy/cobertura no CI. |
| Documentação | **A-** | Boa documentação funcional; falta runbook de release/recuperação e matriz de testes. |

## Achados

### P1 — Alta prioridade

#### P1-01 — Atualização automática sem prova de autenticidade

**Evidência:** `hlsdl/updater.py:104-159` valida SHA-256 do instalador, mas o hash vem do mesmo release (`SHA256SUMS-windows.txt`). `hlsdl/bridge_parts/updates.py:111-126` executa o instalador silenciosamente.

**Impacto:** um comprometimento da conta/release do GitHub pode substituir instalador e checksum juntos. SHA-256 garante integridade de transporte, não autoria.

**Recomendação:** assinar o instalador com Authenticode e verificar a assinatura; assinar o manifesto de hashes com Ed25519/minisign e embutir a chave pública no app; nunca executar atualização sem as duas verificações.

#### P1-02 — Build de release não reproduzível e CI frágil

**Evidência:** dependências usam `>=` em `requirements.txt`/`pyproject.toml`; GitHub Actions usam tags móveis (`actions/checkout@v4`, `setup-python@v5`, `softprops/action-gh-release@v2`); o CI procura apenas `Inno Setup 6` e instala via `choco install innosetup` sem versão fixa (`.github/workflows/ci.yml:219-224`). A máquina local já usa Inno Setup 7.

**Impacto:** builds podem quebrar sozinhos, instalar versões diferentes de PySide6/yt-dlp e gerar binários não reproduzíveis. O caminho fixo do Inno 6 pode falhar no runner atual.

**Recomendação:** lockfile (`uv.lock`/`pip-compile`), pinagem de Actions por SHA, pinagem do Inno Setup (ou detecção 6/7) e registro da versão exata do Python/PyInstaller no artefato.

#### P1-03 — Validação real de hardware/encoders não está no CI

**Evidência:** testes QSV são pulados sem hardware (`tests/test_compress.py:301-308`); os testes principais usam probes sintéticos; downloads reais ficam em scripts manuais. O bug `hevc_qsv` com `color_primaries=reserved` chegou ao usuário apesar da suíte verde.

**Impacto:** regressões específicas de QSV/NVENC/AMF, HDR e containers só aparecem em produção.

**Recomendação:** job noturno em Windows com GPU ou self-hosted runner; matriz mínima de fixtures: HDR10, HLG, `reserved`/`unknown`, múltiplas faixas de áudio, legendas PGS, arquivo truncado e retry. No CI comum, rodar pelo menos encodes reais de software (`libx264`/`libx265`).

### P2 — Média prioridade

#### P2-01 — Threads auxiliares não entram no shutdown coordenado

**Evidência:** `Bridge.shutdown` (`hlsdl/bridge.py:651-673`) encerra filas principais, mas threads de recuperação, detecção inicial, dependências, playlist, similaridade, updater e QSV são `daemon=True` (`bridge.py:254,309-311`; `deps.py:421,750,771`; `playlist.py:80`; `similarity.py:88`; `updater.py:70,112`; `compress.py:1431,1510,1580`). Não há join/timeout para elas.

**Impacto:** saída do processo com I/O ou objeto Qt ainda em uso; risco de corrupção de estado, logs incompletos e falhas intermitentes de encerramento.

**Recomendação:** registrar todas as threads auxiliares em um lifecycle comum, com `cancel()` + `join(timeout)` no shutdown; bloquear novas operações quando `_shutting_down` estiver ativo.

#### P2-02 — Erros técnicos chegam crus à UI

**Evidência:** `compress.py:1277-1279` e `1286-1288` exibem `(audio_count)`, `(resolution)`, `(bit_depth)` etc.; `1359` pode exibir mensagem de exceção do ffmpeg. O QML mostra `model.error`.

**Impacto:** usuário vê códigos internos em vez de uma explicação acionável; piora a percepção de qualidade.

**Recomendação:** mapear cada `reason` para uma string traduzida (“áudio perdido”, “resolução mudou”, “HDR não preservado”) e manter o detalhe técnico em tooltip/log.

#### P2-03 — Sidecars JSON ainda visíveis fora do Windows

**Evidência:** `integrity.py:150-166` aplica atributo oculto apenas em `os.name == "nt"`. No Linux/macOS os `.hlsdl.json` continuam visíveis; arquivos antigos só são ocultados quando lidos/regravados.

**Impacto:** o usuário continua vendo arquivos JSON na pasta no Linux; experiência inconsistente entre plataformas.

**Recomendação:** usar uma pasta oculta por diretório (`.hlsdl/`) ou prefixo `.` no POSIX, com fallback de leitura do caminho legado e migração opcional. Alternativamente, oferecer configuração “gerar sidecars” desligada por padrão.

#### P2-04 — Ausência de gate de tipos e cobertura

**Evidência:** `mypy` está nas dependências de desenvolvimento, mas não é executado no CI; não há `coverage`/threshold. O projeto usa muitos limites dinâmicos (QML, dicionários, `object`).

**Impacto:** erros de contrato entre bridge, mixins, modelos e workers não são detectados até o runtime; regressões de cobertura passam despercebidas.

**Recomendação:** mypy nos módulos de domínio (excluindo QML), cobertura mínima em `hlsdl/` e testes de contrato para `Bridge`, `DownloadWorker` e `CompressionWorker`.

#### P2-05 — Cancelamento da busca de similares é grosseiro

**Evidência:** `SimilarityScanner._run` checa `_cancel` entre arquivos (`similarity.py:118-142`); `build_signature` pode executar ffmpeg por vários segundos por arquivo. `group_similar` compara pares, O(n²).

**Impacto:** “Cancelar” pode demorar; pastas grandes consomem CPU/memória e travam a percepção de responsividade.

**Recomendação:** cancelar subprocessos ffmpeg ativos, limitar quantidade/tamanho de arquivos, agrupar por hash/duração e permitir pausar/retomar.

#### P2-06 — HDR10 estático validado apenas para libx265

**Evidência:** `compress.py:940-948` valida `mastering` apenas quando `encoder == "libx265"`. QSV/NVENC podem perder `master-display`/`max-cll` sem reprovar a saída.

**Impacto:** a promessa de preservação HDR10 pode não valer para encoders de hardware.

**Recomendação:** validar metadados HDR para todos os encoders que dizem preservar HDR, ou documentar explicitamente que apenas libx265 preserva mastering metadata.

#### P2-07 — Falta de teste visual/interação no CI

**Evidência:** os testes QML carregam o engine e checam um combo; não cobrem filtros, abas internas, diálogos, estados maximizado/restaurado, tooltips ou layout em resoluções diferentes. A regressão dos combos pretos foi pega manualmente.

**Impacto:** regressões visuais passam com a suíte verde.

**Recomendação:** testes de componente QML ou golden screenshots em 2–3 resoluções; no mínimo, testes de propriedades para visibilidade, foco, tooltip e estado dos controles.

### P3 — Baixa prioridade / manutenibilidade

- **P3-01 — BOM UTF-8:** os oito arquivos de `hlsdl/bridge_parts/` começam com BOM. Python importa, mas ferramentas e parsers podem tropeçar. Remover BOM para consistência.
- **P3-02 — Exceções amplas e `pass`:** há dezenas de `except Exception`/`pass` em limpeza e shutdown. Muitos são justificados, mas perdem diagnóstico; registrar em `debug`/`warning` os casos não triviais.
- **P3-03 — Migrações do catálogo:** `catalog.py` não usa `PRAGMA user_version` nem migrações; mudanças futuras de schema podem falhar em bancos existentes. Adicionar versão e migrações incrementais.
- **P3-04 — `install_output` com `final == source`:** a API removeria `source` após instalar com sucesso se `final` fosse o próprio original; o fluxo atual de compressão usa sufixo, então não é acionado, mas a API deve proteger esse caso.
- **P3-05 — Janela de crash no download:** o arquivo final é publicado antes do sidecar. Um crash entre os dois deixa mídia válida sem sidecar (não perde dados, mas pode causar redownload). Journal de download ou varredura de recuperação resolveria.
- **P3-06 — SBOM mínimo:** `scripts/gen_sbom.py` lista componentes sem hashes, licenças ou relações. Para padrão-ouro, gerar CycloneDX com `purl`, hashes e dependências diretas.
- **P3-07 — Textos/comentários com mojibake:** vários arquivos têm caracteres `�` em comentários/docstrings. Funciona, mas prejudica manutenção e revisão.
- **P3-08 — i18n sem teste de paridade:** as novas chaves de UI são traduzidas, mas não há teste automatizado de que todas as chaves existem nos 8 idiomas; adicionar um teste de paridade ao `i18n.js`.

## Pontos fortes confirmados

- `subprocess` sempre com lista de argumentos (sem `shell=True`); sem injeção trivial por nome/URL.
- Escrita atômica com retry, journal, backup por hard link/cópia, rollback e recovery.
- Sidecar com SHA-256/BLAKE3, validação profunda de mídia e catálogo SQLite.
- Redação de tokens/cookies em logs e verificação de checksums de ferramentas.
- Instância única, geometria de janela, escalonamento de QThreads e tratamento de erros de inicialização.
- QML modular, com `main.qml` como shell, componentes compartilhados e lint no CI.
- Documentação e CHANGELOG consistentes; SBOM, wheel e instalador gerados.

## Plano de remediação sugerido

1. **Bloqueadores de release:** corrigir/detectar Inno 7 no CI, pinar Actions/dependências e implementar assinatura do instalador + manifesto.
2. **Confiabilidade:** lifecycle único para threads auxiliares, join no shutdown e testes de encerramento com jobs ativos.
3. **Qualidade de mídia:** job de hardware noturno + fixtures HDR/áudio/legendas + mensagens de validação traduzidas.
4. **Qualidade de engenharia:** mypy/coverage no CI, teste de paridade i18n e testes QML de interação/visual.
5. **Polimento:** sidecars ocultos no POSIX, migrações do catálogo, limpeza de BOM/mojibake e SBOM mais completo.

## Conclusão

A base é sólida e a evolução recente foi grande. O que separa o projeto do “padrão-ouro” agora **não é a linguagem** (Python/Qt continua adequado), mas **processo de release, assinatura, testes reais de hardware e automação de qualidade visual**.
