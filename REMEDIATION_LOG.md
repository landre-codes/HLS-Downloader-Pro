# Registro de remediação — auditoria de 2026-11-17

## Ambiente

- Windows 11 (host), Python 3.14.10 no `.venv` do projeto
- PySide6 6.12.0, pytest 9.1.1
- Data: 2026-11-17
- Base já possuía alterações não commitadas; este trabalho foi aplicado por
  cima delas e não gerou commit/release.

## Comandos e resultados

### Baseline

```text
python -m pytest -q
247 passed
```

### Depois das mudanças

```text
python -m pytest -q
295 passed (com HLSDL_TEST_QSV=1; sem a variável: 293 passed, 2 skipped)

python -m compileall -q hlsdl scripts tests main.py worker.py
exit 0

ruff check hlsdl tests main.py worker.py scripts
All checks passed!

mypy hlsdl/netpolicy.py hlsdl/release_manifest.py hlsdl/update_trust.py
Success: no issues found in 3 source files

python -m pip wheel . --no-deps -w <temp>
hls_downloader_pro-1.5.0-py3-none-any.whl (273 KB)
netpolicy.py, release_manifest.py, QML e bridge_parts presentes no wheel

python -m pytest --cov=hlsdl --cov-report=term
TOTAL 8638 statements, 2796 missed, 67.63%

python smoke_test.py
SMOKE TEST OK

python _i18n_test.py
I18N QML OK

python functional_test.py
TODOS OS TESTES FUNCIONAIS PASSARAM
```

O `functional_test.py` tinha uma asserção antiga esperando o rótulo
“Baixando”; foi alinhada ao ID estável `downloading`. Uma execução inicial
teve timeout no caminho ffmpeg direto; a repetição completa passou. O
`smoke_test.py` imprime um aviso intencional sobre cookie inexistente e retorna
0.

### QML

```text
pyside6-qmllint <main/pages/dialogs/components>
exit 0
```

Há warnings preexistentes de `unqualified access`; nenhum erro de sintaxe,
tipo ausente ou propriedade inexistente introduzido pelas mudanças.

### Manifesto assinado (ponta a ponta, chave de teste)

```text
scripts/gen_update_key.py --out <temp>/key.pem
scripts/gen_release_manifest.py --version 1.5.1 --tag v1.5.1 \
    --output <temp>/release-manifest-windows.json <assets...>
scripts/sign_release.py <temp>/release-manifest-windows.json --key <temp>/key.pem
```

Resultado da verificação:

```text
manifesto verificado: 1.5.1 v1.5.1
asset: HLS-Downloader-Pro-1.5.1-setup.exe 14 8ba67ba3cb224a45...
```

## Decisões

- **`Referer`**: política same-origin, sem query/fragmento/userinfo. Isso
  remove o envio de `Referer` para CDNs de outra origem, uma mudança
  intencional de compatibilidade em troca de não vazar tokens. Teste
  `test_ffmpeg_fallback_audio_respects_mode_and_headers` foi atualizado.
- **Redes locais**: não foram bloqueadas globalmente. O usuário pode baixar de
  um servidor LAN; o bloqueio automático vale apenas para saltos de uma origem
  pública para um destino privado.
- **Manifesto legado**: mantido por compatibilidade, mas o nome do asset
  precisa conter a versão da tag. Sem isso, um manifesto assinado antigo
  poderia ser reapresentado como release nova.
- **macOS/FFmpeg**: sem SHA-256 publicado pelo evermeet, o download estático
  falha fechado. A saída é Homebrew ou consentimento explícito
  `HLSDL_ALLOW_UNVERIFIED_FFMPEG=1`; tamanho sozinho não é tratado como
  autenticação.
- **HDR**: falha de metadados agora bloqueia a instalação da saída (original
  preservado), inclusive em QSV/NVENC/AMF. Não foi adicionado caminho de
  “confirmar mesmo assim”, porque a auditoria pede bloqueio ou confirmação
  explícita; a mensagem inclui o motivo (`hdr_metadata:...`).
- **Cobertura**: gate em 60% após medir 67% no Linux local; não foi imposto um
  valor agressivo sem baseline.
- **Sidecars POSIX**: não foram movidos/renomeados para não quebrar
  compatibilidade; permanece como melhoria de UX separada.

## Arquivos novos

- `hlsdl/netpolicy.py`
- `hlsdl/release_manifest.py`
- `scripts/gen_release_manifest.py`
- `scripts/ui_snapshot.py`
- `hlsdl/ui/components/PageHero.qml`
- `tests/test_netpolicy.py`
- `tests/test_release_manifest.py`
- `docs/ui-review/` (capturas selecionadas)
- `REMEDIATION_PLAN.md`, `REMEDIATION_LOG.md`, `UI_REVIEW.md`
- `REAUDIT_RESPONSE.md`, `THREAT_MODEL.md`

## Arquivos principais alterados

`hlsdl/services/scraper.py`, `hlsdl/downloader.py`, `hlsdl/updater.py`,
`hlsdl/update_trust.py`, `hlsdl/deps.py`, `hlsdl/integrity.py`,
`hlsdl/catalog.py`, `hlsdl/media.py`, `hlsdl/compress.py`,
`hlsdl/similarity.py`, `hlsdl/bridge.py`, `hlsdl/bridge_parts/updates.py`,
`hlsdl/i18n.py`, `hlsdl/ui/components/TitleBarButton.qml`,
`hlsdl/ui/pages/CompressionPage.qml`, `.github/workflows/ci.yml`,
`README.md`, `CHANGELOG.md`, `scripts/gen_sbom.py` e testes correlatos.

## Limitações / não executado

- CI do GitHub não foi executada neste ambiente; os comandos foram validados
  localmente.
- Nenhum encode real HDR10/QSV/NVENC/AMF foi executado; a validação de HDR usa
  fixtures e a matriz de hardware continua pendente.
- Não houve captura de telas nem validação visual em DPI/temas.
- Não houve download real de release assinada pelo GitHub.
- Não foram executados testes em Linux/macOS reais nesta máquina.
- A árvore já estava suja antes do trabalho; não há diff limpo contra
  `e236962` que isole apenas estas mudanças.

## Estabilidade de teardown Qt

Durante a validação inicial, execuções da suíte terminavam com access violation
(0xC0000005) ou `Fatal Python error: Aborted`. O stack apontou para uma
`QThread` de teste e para a thread `hlsdl-qsv-detect` ainda executando
`ffmpeg`/`ffprobe` enquanto o processo principal avançava. Causas:

- `CompressionManager` criava a detecção QSV em thread daemon sem rastreá-la.
- Testes descartavam `Bridge`, `CompressionManager` e `QueueManager` sem
  chamar shutdown; a destruição de um `QThread` ainda vivo aborta o processo.

Correções aplicadas:

- `CompressionManager` rastreia `_qsv_thread`, marca `_closing` e faz `join`
  no `shutdown()`; a thread não emite sinais depois do teardown.
- O fixture autouse `_shutdown_qt_helpers` em `tests/conftest.py` encerra
  Bridges, CompressionManagers e QueueManagers criados no teste, reproduzindo
  o ciclo de vida de produção.

Resultado: **16 execuções consecutivas com 282 passed** (8 com `-s` e 8 com
captura normal), sem crash. Depois foram adicionados o teste de frame side
data HDR e 2 testes reais QSV; após os testes adicionais da reauditoria
(updater, versão e `allow-unsafe-ext`), a suíte final ficou em **295 passed** em
execuções locais; a matriz de UX R3 adicionou 4 testes.

## HDR10 com hardware real (QSV)

Foi gerado um fixture HDR10 sintético com `libx265` (BT.2020/PQ, mastering
display e max-cll) e codificado com `hevc_qsv` em MKV e MP4. Resultado:

- o `ffprobe` expõe mastering/content-light no **primeiro frame** (SEI), não
  em `stream.side_data_list`; `probe_media` foi corrigido para ler também
  `frames[0].side_data_list`;
- QSV preservou mastering display e content-light nos dois contêineres;
- `validate_output_quality` retornou `""` nos dois casos.

Isso valida o caminho de HDR10 que antes só existia em fixtures. O teste exige
`HLSDL_TEST_QSV=1` (definido no workflow de hardware) para não rodar por engano
em runner sem GPU. NVENC e AMF não estão disponíveis nesta máquina e continuam
como teste pendente.

## UI real (capturas offscreen)

Foi criado um harness local com `QQuickWindow.grabWindow()`, fontes do sistema
e as 5 abas. Foram geradas capturas em 940×620, 1160×800, 1366×768 e
1920×1080, temas claro/escuro, escalas 100/125/150/200%, toast e diálogo de
erro. Uma seleção está em `docs/ui-review/`.

Defeitos encontrados e corrigidos:

1. **Contraste no tema claro**: `Material.background` na janela pintava o fundo
   de botões `highlighted` com a cor da janela; o texto branco desaparecia.
   Removido o `Material.background` (substituído por `ApplicationWindow.background`)
   e `AppButton` passou a definir fundo/texto explícitos, inclusive desabilitado.
2. **Rodapé do Lote em 940×620**: contadores truncados; agora quebram em até
   duas linhas e a barra de progresso some abaixo de 1050 px.
3. **Rodapé da Compressão em 940×620**: os cards empurravam as ações para fora
   da janela; alturas mínimas ajustadas, rodapé fixo e scrollbars visíveis.
4. **Toast longo**: até 3 linhas, largura maior, 2,6–8 s e dispensa por clique.
5. **Diálogo de erro**: conteúdo tocava as bordas; `AppDialogSurface` ganhou
   16 px de margem.
6. **Cabeçalho descritivo**: novo `PageHero` com degradê, descrição e ações
   contextuais, inspirado no DiskPilot. Ativa em janelas ≥1050×650; em 940×620
   mantém o título simples para não reduzir a área útil.
7. **Sidecars POSIX**: novos sidecars usam `.` inicial no Linux/macOS
   (`.video.mp4.hlsdl.json`); a leitura e a busca aceitam também o nome antigo
   sem ponto, sem migração destrutiva.

As capturas não substituem Linux/macOS, leitor de tela ou usuários reais.
Ficou documentado em `UI_REVIEW.md` que a compressão em 940×620 ainda exige
rolagem e que o estado vazio da fila fica comprimido nesse tamanho.

