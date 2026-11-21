"""Contratos visuais dos diálogos, menus e ajustes de layout."""

from __future__ import annotations

from pathlib import Path

from hlsdl.config import qml_path
from hlsdl.i18n import LANGUAGES


def _ui() -> Path:
    return Path(qml_path()).parent


def test_dialog_surface_has_gradient_header_and_window_controls():
    text = (_ui() / "components" / "AppDialogSurface.qml").read_text(encoding="utf-8")
    for token in (
        "gradient: Gradient",
        "id: dragArea",
        "id: resizeGrip",
        "function toggleMaximized",
        "function restoreGeometry",
        "Text.ElideRight",
        "showCloseButton",
        "resizable",
        # O título acompanha o raio da janela nos cantos superiores.
        "topLeftRadius: surface.radius",
        "topRightRadius: surface.radius",
        "bottomLeftRadius: 0",
        "bottomRightRadius: 0",
        # O grip tem três traços, não um único que pareça scrollbar.
        "id: gripCanvas",
        "for (var i = 0; i < 3; i++)",
    ):
        assert token in text, token


def test_destructive_buttons_use_red_hover():
    tool = (_ui() / "components" / "AppToolButton.qml").read_text(encoding="utf-8")
    assert "property bool danger: false" in tool
    assert "hoverEnabled: true" in tool
    assert '"#4a2b2b"' in tool
    assert '"#fde8e8"' in tool

    button = (_ui() / "components" / "AppButton.qml").read_text(encoding="utf-8")
    assert "property bool dangerHover: false" in button
    assert "hoverEnabled: true" in button
    assert "_dangerHoverColor" in button
    assert "_dangerDownColor" in button

    batch = (_ui() / "pages" / "BatchPage.qml").read_text(encoding="utf-8")
    assert 'objectName: "batchRemoveButton"' in batch
    assert "danger: true" in batch
    assert "dangerHover: true" in batch

    compression = (_ui() / "pages" / "CompressionPage.qml").read_text(
        encoding="utf-8"
    )
    assert "danger: true" in compression
    assert "dangerHover: true" in compression

    playlist = (
        _ui() / "dialogs" / "PlaylistImportDialog.qml"
    ).read_text(encoding="utf-8")
    assert "dangerHover: true" in playlist


def test_playlist_dialog_buttons_and_header_are_consistent():
    text = (
        _ui() / "dialogs" / "PlaylistImportDialog.qml"
    ).read_text(encoding="utf-8")
    # Nenhuma ação principal pode continuar parecendo texto simples.
    assert 'variant: "tertiary"' not in text
    assert text.count('variant: "secondary"') >= 4
    assert "showCloseButton: true" in text
    assert "resizable: true" in text
    for name in ("playlistClearList", "playlistSelectAll", "playlistSelectNone"):
        assert f'objectName: "{name}"' in text, name


def test_playlist_url_validates_empty_before_backend_call():
    text = (
        _ui() / "dialogs" / "PlaylistImportDialog.qml"
    ).read_text(encoding="utf-8")
    assert "function submitPlaylist()" in text
    assert "value.length === 0" in text
    assert "onAccepted: dialog.submitPlaylist()" in text
    assert "objectName: \"playlistUrlField\"" in text
    # A única chamada ao backend fica atrás do validador.
    assert text.count("dialog.appRoot.loadPlaylist(") == 1
    assert "onClicked: bridge.playlistLoading" in text


def test_confirm_dialogs_use_centered_card_and_real_buttons():
    text = (_ui() / "dialogs" / "ConfirmDialog.qml").read_text(encoding="utf-8")
    assert "ConfirmSurface" in text
    assert "title: dialog.title" in text
    assert "destructive: dialog.destructive" in text
    assert 'iconText: dialog.destructive ? "!" : "?"' in text
    assert "onAccepted: dialog.confirmed()" in text
    assert "header: null" in text and "footer: null" in text
    assert "background: Rectangle" in text and "radius: 24" in text

    surface = (_ui() / "components" / "ConfirmSurface.qml").read_text(
        encoding="utf-8"
    )
    for token in ("Layout.preferredHeight: 72", "Layout.preferredHeight: 48",
                  "radius: 10", "horizontalAlignment: Text.AlignHCenter",
                  "surface.destructive", "surface.accepted()",
                  "surface.cancelled()"):
        assert token in surface, token

    for name in ("ConfirmDepsDialog.qml", "DepsDialog.qml",
                 "QualityConfirmDialog.qml"):
        other = (_ui() / "dialogs" / name).read_text(encoding="utf-8")
        assert "ConfirmSurface" in other, name
        assert "header: null" in other and "footer: null" in other, name
        assert "background: Rectangle" in other, name
        assert "footer: DialogButtonBox" not in other, name

    compression = (_ui() / "pages" / "CompressionPage.qml").read_text(
        encoding="utf-8"
    )
    replace = compression.split('objectName: "confirmReplaceDialog"', 1)[1]
    replace = replace.split("contentItem: ConfirmSurface", 1)
    assert len(replace) == 2
    assert 'destructive: true' in replace[1]
    assert "onAccepted: bridge.setCompressionReplaceOriginal(true)" in replace[1]

    main = (_ui() / "main.qml").read_text(encoding="utf-8")
    assert main.count("destructive: true") >= 3


def test_batch_options_dialog_uses_expressive_surface():
    text = (
        _ui() / "dialogs" / "BatchOptionsDialog.qml"
    ).read_text(encoding="utf-8")
    assert "AppDialogSurface" in text
    assert "showCloseButton: true" in text
    assert "resizable: false" in text
    assert "draggable: false" in text
    assert "batch_options_hint" in text


def test_hint_fields_use_localized_context_menu():
    for name in ("AppHintArea.qml", "AppHintField.qml"):
        text = (_ui() / "components" / name).read_text(encoding="utf-8")
        assert "Menu {" in text
        for key in ("menu_undo", "menu_cut", "menu_copy", "menu_paste",
                    "menu_delete", "menu_select_all"):
            assert key in text, (name, key)

    i18n = (_ui() / "i18n.js").read_text(encoding="utf-8")
    assert i18n.count("menu_undo:") >= len(LANGUAGES)
    assert i18n.count("menu_select_all:") >= len(LANGUAGES)


def test_text_inputs_have_clear_button_and_escape():
    for name in ("AppHintField.qml", "AppHintArea.qml"):
        text = (_ui() / "components" / name).read_text(encoding="utf-8")
        assert "showClearButton: true" in text
        assert "_hasClearButton" in text
        assert "Keys.onEscapePressed" in text
        assert "clearField()" in text
        assert "clip: true" in text
        assert "btn_clear" in text
        assert "btn_clear_tip" in text
        assert "hintFieldClearButton" in text or "hintAreaClearButton" in text


def test_inputs_and_tables_use_darker_theme_tokens():
    main = (_ui() / "main.qml").read_text(encoding="utf-8")
    for token in ("inputBg:", "inputBorder:", "tableBg:"):
        assert token in main, token

    for name in ("AppHintField.qml", "AppHintArea.qml", "AppSpinBox.qml",
                 "AppComboBox.qml"):
        text = (_ui() / "components" / name).read_text(encoding="utf-8")
        assert "inputBg" in text or "#14191e" in text, name
        assert ("background: Rectangle" in text
                or (name == "AppHintArea.qml" and "Rectangle {" in text)), name

    assert "theme.inputBg" in (
        _ui() / "components" / "FolderPickerField.qml"
    ).read_text(encoding="utf-8")


def test_settings_cards_have_icon_headers_and_styled_folder_buttons():
    settings = (_ui() / "pages" / "SettingsPage.qml").read_text(encoding="utf-8")
    assert settings.count("SectionHeader {") == 6
    for icon in ("moon", "download", "shield", "network", "cookie",
                 "package"):
        assert f'settingsIcon("{icon}")' in settings, icon
    for icon in ("sun", "moon", "download", "shield", "network", "cookie",
                 "package", "info"):
        assert (_ui() / "icons" / f"{icon}_blue.svg").exists(), icon
    folder = (_ui() / "components" / "FolderPickerField.qml").read_text(
        encoding="utf-8"
    )
    for token in ("changeIcon", "openIcon", "AbstractButton.TextBesideIcon"):
        assert token in folder, token


def test_project_license_is_gplv3():
    root = Path(qml_path()).parents[2]
    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in license_text
    assert "Version 3" in license_text
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = { text = "GPL-3.0-only" }' in pyproject
    i18n = (_ui() / "i18n.js").read_text(encoding="utf-8")
    assert i18n.count('about_license_value: "GPLv3"') >= len(LANGUAGES)
    about = (_ui() / "pages" / "AboutPage.qml").read_text(encoding="utf-8")
    assert "strings.about_license_value" in about


def test_about_page_has_identity_updates_and_resources():
    about = (_ui() / "pages" / "AboutPage.qml").read_text(encoding="utf-8")
    assert 'objectName: "aboutPage"' in about
    assert about.count("SectionHeader {") == 3
    for icon in ("info", "download", "package"):
        assert f'settingsIcon("{icon}")' in about, icon
    for token in ("bridge.appVersion", "bridge.checkForUpdates()",
                  "bridge.downloadUpdate()", "bridge.openReleasePage()",
                  "bridge.openLogFolder()", "bridge.openOutputFolder()",
                  "appRoot.goToSettingsTab()",
                  "https://github.com/landre-codes/HLS-Downloader-Pro"):
        assert token in about, token


def test_primary_button_icons_use_accent_variants():
    assert 'iconPath("add", enabled)' in (
        _ui() / "pages" / "BatchPage.qml"
    ).read_text(encoding="utf-8")
    assert 'iconPath("play", enabled)' in (
        _ui() / "pages" / "SinglePage.qml"
    ).read_text(encoding="utf-8")
    assert 'iconPath("download", enabled)' in (
        _ui() / "pages" / "AboutPage.qml"
    ).read_text(encoding="utf-8")
    for name in ("add", "play", "retry", "stop", "download"):
        assert (_ui() / "icons" / f"{name}_accent.svg").exists(), name


def test_scroll_areas_reserve_a_gutter():
    settings = (_ui() / "pages" / "SettingsPage.qml").read_text(encoding="utf-8")
    assert "scrollGutter" in settings
    batch = (_ui() / "pages" / "BatchPage.qml").read_text(encoding="utf-8")
    assert "scrollGutter" in batch
    compression = (_ui() / "pages" / "CompressionPage.qml").read_text(
        encoding="utf-8"
    )
    assert "compScrollGutter" in compression
    assert "rightPadding: 16" in (
        _ui() / "components" / "AppTerminalPanel.qml"
    ).read_text(encoding="utf-8")


def test_page_hero_titles_are_larger_and_clipped():
    text = (_ui() / "components" / "PageHero.qml").read_text(encoding="utf-8")
    assert "font.pixelSize: hero.compact ? 19 : 24" in text
    assert "font.pixelSize: 14" in text
    assert "maximumLineCount: 1" in text
    assert "clip: true" in text


def test_compression_scroll_views_reserve_scrollbar_gutter():
    text = (
        _ui() / "pages" / "CompressionPage.qml"
    ).read_text(encoding="utf-8")
    assert "compScrollGutter" in text
    assert text.count("availableWidth - page.compScrollGutter") == 4


def test_batch_edit_has_cancel_and_actions_have_remove():
    text = (_ui() / "pages" / "BatchPage.qml").read_text(encoding="utf-8")
    assert 'objectName: "batchEditCancel"' in text
    assert "focusPolicy: Qt.NoFocus" in text
    assert 'objectName: "batchRemoveButton"' in text
    assert "bridge.removeItem(rowItem.sourceIndex)" in text
    # A coluna de ações cresceu para caber a lixeira sem sobrepor a barra.
    assert text.count("Layout.preferredWidth: 168") >= 2


def test_compression_table_supports_selection_and_remove_any_status():
    text = (_ui() / "pages" / "CompressionPage.qml").read_text(encoding="utf-8")
    for token in (
        'objectName: "compSelectAll"',
        'objectName: "compRemoveSelected"',
        'objectName: "compRowSelect"',
        "function removeSelectedCompression",
        "function removeCompressionItem",
        "sourceIndexAt",
        "id: compRowMenu",
        'text: strings.ctx_remove',
        'objectName: "compHeaderSize"',
        'objectName: "compCellSize"',
    ):
        assert token in text, token
    assert "appRoot.iconPath(\"trash\", enabled)" in text
    # Resultado (economia) e Tamanho não compartilham a mesma chave de sort.
    assert 'sortKey: "saving"' in text
    assert 'sortKey: "size"' in text
    assert '"size_before"' in text and '"size_after"' in text
    assert '"resultado": "saving"' in text


def test_titlebar_has_theme_and_language_icons():
    main = (_ui() / "main.qml").read_text(encoding="utf-8")
    for token in ("themeToggleButton", "navMenuButton",
                  "bridge.setDark(!root.dark)"):
        assert token in main, token
    assert "userAvatar" not in main
    assert not (_ui() / "components" / "SidebarUser.qml").exists()
    assert "readonly property bool isRtl: bridge.isRtl" in main
    assert "LayoutMirroring.enabled: root.isRtl" in main
    assert "LayoutMirroring.childrenInherit: true" in main

    settings = (_ui() / "pages" / "SettingsPage.qml").read_text(encoding="utf-8")
    assert "LanguageComboBox" in settings
    assert "onClicked: bridge.setDark" not in settings

    combo = (_ui() / "components" / "LanguageComboBox.qml").read_text(
        encoding="utf-8"
    )
    assert "../icons/flags/" in combo
    assert "modelData.flag" in combo
    for flag in ("br", "pt", "us", "es", "de", "it", "fr", "ru",
                 "ar", "il", "jp", "kr", "cn"):
        assert (_ui() / "icons" / "flags" / f"{flag}.svg").exists(), flag


def test_single_page_has_vertical_scroll_for_small_windows():
    text = (_ui() / "pages" / "SinglePage.qml").read_text(encoding="utf-8")
    assert 'objectName: "singleScroll"' in text
    assert "ScrollBar.vertical.policy: ScrollBar.AlwaysOn" in text
    assert "singleScroll.availableHeight - singleCard.height" in text


def test_compression_progress_uses_status_icons():
    text = (_ui() / "pages" / "CompressionPage.qml").read_text(encoding="utf-8")
    batch = (_ui() / "pages" / "BatchPage.qml").read_text(encoding="utf-8")
    assert "progressIconName" in text
    assert "progressIconName" in batch
    assert "check_light.svg" not in text
    for name in ("check", "alert"):
        assert (_ui() / "icons" / f"{name}_light.svg").exists()
        assert (_ui() / "icons" / f"{name}_dark.svg").exists()


def test_button_palette_uses_cobalt_and_semantic_colors():
    button = (_ui() / "components" / "AppButton.qml").read_text(encoding="utf-8")
    for token in ('"primary"', '"tonal"', '"success"', '"warning"',
                  '"danger"', "#2563eb", "#1d4ed8", "#1e40af",
                  "#15803d", "#b42332", "#b45309",
                  "property int radius: 8", "? 8 : 0"):
        assert token in button, token
    # Cobalto executa; verde e vermelho ficam reservados a estados.
    assert "_cyan" not in button
    assert "_violet" not in button
    compression = (_ui() / "pages" / "CompressionPage.qml").read_text(
        encoding="utf-8"
    )
    assert 'variant: bridge.compressionDetecting ? "secondary" : "primary"' in compression
    assert 'variant: "primary"' in compression
    assert 'variant: "cyan"' not in compression
    playlist = (
        _ui() / "dialogs" / "PlaylistImportDialog.qml"
    ).read_text(encoding="utf-8")
    assert 'variant: bridge.playlistLoading ? "danger" : "tonal"' in playlist
    assert 'variant: "primary"' in playlist
    for name in ("copy", "file", "retry", "open", "add"):
        for theme in ("light", "dark"):
            assert (_ui() / "icons" / f"{name}_tonal_{theme}.svg").exists(), (
                name, theme
            )


def test_action_hierarchy_uses_cobalt_for_execution():
    batch = (_ui() / "pages" / "BatchPage.qml").read_text(encoding="utf-8")
    single = (_ui() / "pages" / "SinglePage.qml").read_text(encoding="utf-8")
    compression = (_ui() / "pages" / "CompressionPage.qml").read_text(
        encoding="utf-8"
    )
    playlist = (
        _ui() / "dialogs" / "PlaylistImportDialog.qml"
    ).read_text(encoding="utf-8")
    similar = (_ui() / "dialogs" / "SimilarityDialog.qml").read_text(
        encoding="utf-8"
    )

    # Executar/confirmar é cobalto; o verde não inicia mais nenhuma operação.
    assert 'strings.btn_add; variant: "primary"' in batch
    assert 'strings.btn_start; variant: "primary"' in batch
    assert 'strings.btn_download_now; variant: "primary"' in single
    assert compression.count('"primary"') >= 2
    assert playlist.count('variant: "primary"') >= 1
    for page in (batch, single, compression, playlist):
        assert 'variant: "success"' not in page

    # Importar/colar/adicionar/analisar usam a camada tonal.
    assert batch.count('variant: "tonal"') >= 3
    assert compression.count('variant: "tonal"') >= 2
    assert playlist.count('"tonal"') >= 2
    assert 'variant: "tonal"' in similar

    # Controles de baixa prioridade continuam transparentes.
    assert 'variant: "tertiary"' in compression


def test_compression_comboboxes_use_wider_columns():
    text = (_ui() / "pages" / "CompressionPage.qml").read_text(encoding="utf-8")
    assert "Layout.preferredWidth: 320" in text
    assert "columns: width > 1650 ? 4 : (width > 1280 ? 3 : 2)" in text


def test_compression_spin_boxes_fit_large_values():
    text = (_ui() / "pages" / "CompressionPage.qml").read_text(encoding="utf-8")
    for name in ("compQualitySpin", "compBitrateSpin", "compParallelSpin",
                 "compMinSizeSpin", "compFpsSpin", "compScaleWidthSpin",
                 "compScaleHeightSpin"):
        assert f'objectName: "{name}"' in text, name
    assert text.count("Layout.preferredWidth: 200") >= 8
    assert "Layout.preferredWidth: 120" not in text
    assert "Layout.preferredWidth: 130" not in text
    assert "Layout.preferredWidth: 180" not in text


def test_compression_remove_button_has_stable_width_and_filter_height():
    text = (_ui() / "pages" / "CompressionPage.qml").read_text(encoding="utf-8")
    assert 'objectName: "compRemoveSelected"' in text
    assert "Layout.preferredWidth: 200" in text
    assert "Layout.minimumWidth: 200" in text
    assert "Layout.maximumWidth: 200" in text
    assert "Layout.preferredHeight: 56" in text
    assert "Layout.minimumHeight: 56" in text
    assert "Layout.maximumHeight: 56" in text
    assert "enabled: compList.count > 0" in text


def test_compression_size_filter_supports_common_formats():
    text = (_ui() / "pages" / "CompressionPage.qml").read_text(encoding="utf-8")
    assert "function compDisplayedSize" in text
    assert '"size": compSizeValues(compDisplayedSize(row))' in text
    assert 'formatted.replace(" ", "")' in text
    filters = (_ui() / "tablefilter.js").read_text(encoding="utf-8")
    assert r"text.replace(/(\d),(\d)/g" in filters


def test_filter_fields_use_readable_aligned_placeholders():
    batch = (_ui() / "pages" / "BatchPage.qml").read_text(encoding="utf-8")
    compression = (_ui() / "pages" / "CompressionPage.qml").read_text(
        encoding="utf-8"
    )
    assert batch.count("Layout.preferredHeight: 56") >= 1
    assert compression.count("Layout.preferredHeight: 56") >= 1
    assert batch.count("showClearButton: true") >= 1
    assert compression.count("showClearButton: true") >= 1

    field = (_ui() / "components" / "AppHintField.qml").read_text(
        encoding="utf-8"
    )
    button = (_ui() / "components" / "AppButton.qml").read_text(encoding="utf-8")
    assert "anchors.fill: parent" in field
    assert "anchors.fill: parent" in button
    assert "topPadding: 8" in field and "bottomPadding: 8" in field
    area = (_ui() / "components" / "AppHintArea.qml").read_text(encoding="utf-8")
    # Campo pequeno: hint na mesma linha do cursor; campo grande: hint no topo.
    assert "y: hintField.cursorRectangle.y" in field
    assert "height: hintField.cursorRectangle.height" in field
    assert "text: hintField.hint" in field
    assert "objectName: \"hintFieldClearButton\"" in field
    assert "y: area.topPadding" in area
    assert "text: root.hint" in area


def test_compression_select_all_first_click_checks():
    text = (_ui() / "pages" / "CompressionPage.qml").read_text(encoding="utf-8")
    assert "nextCheckState: function()" in text
    assert "? Qt.Unchecked : Qt.Checked" in text


def test_settings_uses_neon_icons_and_icon_browser_combo():
    settings = (_ui() / "pages" / "SettingsPage.qml").read_text(encoding="utf-8")
    assert "BrowserComboBox" in settings
    assert "browserIcon:" not in settings
    for browser in ("Chrome", "Chromium", "Edge", "Firefox", "Opera",
                    "Vivaldi", "Brave"):
        assert f'"{browser}"' in settings, browser
    combo = (_ui() / "components" / "BrowserComboBox.qml").read_text(
        encoding="utf-8"
    )
    assert "../icons/browsers/" in combo
    # Os logotipos têm fundo próprio e são rasterizados em resolução maior
    # para não sumirem no tema escuro nem borrar em telas HiDPI.
    assert 'color: "#ffffff"' in combo
    assert "radius: 8" in combo
    assert "sourceSize.width: 48" in combo
    assert "width: 24" in combo
    assert "implicitHeight: 40" in combo
    assert combo.count("mipmap: true") == 2
    assert combo.count("Layout.preferredWidth: 32") == 2
    base_combo = (_ui() / "components" / "AppComboBox.qml").read_text(
        encoding="utf-8"
    )
    assert "popup.background: Rectangle" in base_combo
    assert "popup.height: Math.min" in base_combo
    for browser in ("chrome", "chromium", "edge", "firefox", "opera",
                    "vivaldi", "brave"):
        assert (_ui() / "icons" / "browsers" / f"{browser}.svg").exists(), browser
    for icon in ("sun", "moon", "download", "shield", "network", "cookie",
                 "package", "info"):
        assert (_ui() / "icons" / f"{icon}_blue.svg").exists(), icon
    assert "settingsIcon(" in settings
