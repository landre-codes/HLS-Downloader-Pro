import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"
import "../tablefilter.js" as TableFilter

        Item {
    id: page
    objectName: "compressionPage"
    property var appRoot
    property var strings: ({})
    property alias filterField: compFilter
    property int compSection: 0
    property string compFilterText: ""
    property bool compSettingsCollapsed: false
    readonly property bool showHero: width >= 1050 && height >= 650

    // Larguras compartilhadas por cabeçalho e delegate. Sem isso, o cabeçalho
    // e as linhas divergem quando a janela encolhe (o antigo "Arquivo" saía
    // do lugar e os demais títulos desalinhavam).
    readonly property int compColStatus: 112
    readonly property int compColProgress: 148
    readonly property int compColResult: 214
    readonly property int compColActions: 140
    readonly property int compColGap: 10

    readonly property var compFilterAliases: ({
        "status": "status",
        "progresso": "progress",
        "progress": "progress",
        "nome": "name",
        "arquivo": "name",
        "name": "name",
        "url": "name",
        "erro": "error",
        "error": "error",
        "tamanho": "size",
        "size": "size",
        "economia": "saving",
        "saving": "saving"
    })
    readonly property var compFilterTokens: TableFilter.tokenize(compFilterText,
                                                                compFilterAliases)

    function compRowFields(row) {
        return {
            "name": [row.name || "", row.path || "", row.encoder || "",
                     row.output || ""],
            "status": [appRoot.statusText(row.status)],
            "progress": [String(Math.round(Number(row.progress) || 0)) + "%",
                         String(row.progress || "")],
            "size": [String(row.sizeBefore || ""), String(row.sizeAfter || ""),
                     appRoot.formatBytes(row.sizeBefore || 0),
                     appRoot.formatBytes(row.sizeAfter || 0)],
            "saving": [String(row.saving || "") + "%",
                       String(row.bitrateAfter || ""),
                       String(row.ssim || "")],
            "error": [row.error || "", row.qualityWarning || ""]
        }
    }

    function compRowMatches(row) {
        return TableFilter.matches(compRowFields(row), compFilterTokens)
    }

    function toggleSettings() {
        compSettingsCollapsed = !compSettingsCollapsed
    }

    // Diagnóstico de layout: posições X das células da linha (usado pelos
    // testes para garantir que o cabeçalho e o delegate compartilham colunas).
    function rowCellXsAt(row) {
        var item = compList.itemAtIndex(row)
        if (!item || item.children.length === 0)
            return []
        var layout = item.children[0]
        var xs = []
        for (var i = 0; i < layout.children.length; i++)
            xs.push(layout.children[i].x)
        return xs
    }

    function compDetailTip(row) {
        var lines = []
        if (row.error && row.error.length > 0)
            lines.push(row.error)
        if (row.bitrateBefore > 0 || row.bitrateAfter > 0)
            lines.push("Bitrate: " + appRoot.formatBitrate(row.bitrateBefore)
                       + " → " + appRoot.formatBitrate(row.bitrateAfter))
        if (row.widthBefore > 0 || row.widthAfter > 0)
            lines.push(row.widthBefore + "x" + row.heightBefore
                       + " → " + row.widthAfter + "x" + row.heightAfter)
        if (row.ssim > 0)
            lines.push("SSIM: " + Number(row.ssim).toFixed(3))
        if (row.qualityWarning && row.qualityWarning.length > 0)
            lines.push(strings.compress_quality_bitrate_warning)
        if (row.saving > 0)
            lines.push(row.saving + "% " + strings.compress_saving)
        if (row.backup && row.backup !== "")
            lines.push(strings.compress_backup_kept + ": " + row.backup)
        if (row.sha256 && row.sha256 !== "")
            lines.push(strings.compress_hash + ": " + row.sha256)
        return lines.join("\n")
    }

    readonly property real compContentHeight: compStack.children[compStack.currentIndex]
                                                 ? compStack.children[compStack.currentIndex].implicitHeight : 0

    ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    // Em janelas baixas o painel de ajustes cede espaço para a
                    // fila; o conteúdo continua acessível pela rolagem interna.
                    Layout.preferredHeight: page.compSettingsCollapsed
                        ? compHero.implicitHeight + 32
                        : Math.max(
                            appRoot.height < 700 ? 240 : 300,
                            Math.min(
                                appRoot.height - 440,
                                32 + compHero.implicitHeight + 12
                                + compPresetRow.implicitHeight + 12
                                + compTabsRow.implicitHeight + 12
                                + page.compContentHeight
                            )
                        )
                    radius: 12
                    color: appRoot.theme.cardBg
                    border.color: appRoot.theme.cardBorder
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        PageHero {
                            id: compHero
                            Layout.fillWidth: true
                            compact: !page.showHero
                            theme: appRoot.theme
                            title: strings.compress_title
                            description: strings.hero_compress_desc
                            AppButton {
                                text: strings.compress_add_files
                                variant: "secondary"
                                icon.source: appRoot.iconPath("file")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                onClicked: bridge.addCompressionFiles()
                            }
                            AppButton {
                                text: strings.compress_add_folder
                                variant: "secondary"
                                icon.source: appRoot.iconPath("open")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                enabled: !bridge.compressionScanBusy
                                onClicked: bridge.addCompressionFolder()
                            }
                            AppButton {
                                objectName: "compSettingsToggle"
                                text: page.compSettingsCollapsed
                                      ? "▾ " + strings.compress_settings_show
                                      : "▴ " + strings.compress_settings_hide
                                variant: "tertiary"
                                size: "compact"
                                Accessible.name: page.compSettingsCollapsed
                                                 ? strings.compress_settings_show
                                                 : strings.compress_settings_hide
                                tipTitle: page.compSettingsCollapsed
                                          ? strings.compress_settings_show
                                          : strings.compress_settings_hide
                                tipText: page.compSettingsCollapsed
                                         ? strings.compress_settings_show_tip
                                         : strings.compress_settings_hide_tip
                                onClicked: page.toggleSettings()
                            }
                        }

                        RowLayout {
                            id: compPresetRow
                            objectName: "compPresetRow"
                            visible: !page.compSettingsCollapsed
                            Layout.fillWidth: true
                            spacing: 12
                            Label {
                                text: strings.compress_preset
                                font.pixelSize: 12
                                color: appRoot.theme.textSecondary
                            }
                            AppComboBox {
                                id: compPreset
                                Layout.preferredWidth: 260
                                model: [
                                    { text: strings.compress_preset_custom, value: "custom" },
                                    { text: strings.compress_preset_fast_h264, value: "fast_h264" },
                                    { text: strings.compress_preset_balanced_hevc, value: "balanced_hevc" },
                                    { text: strings.compress_preset_quality_hevc, value: "quality_hevc" },
                                    { text: strings.compress_preset_archive_hevc, value: "archive_hevc" },
                                    { text: strings.compress_preset_av1_balanced, value: "av1_balanced" }
                                ]
                                textRole: "text"
                                valueRole: "value"
                                currentIndex: {
                                    for (var i = 0; i < model.length; i++)
                                        if (model[i].value === bridge.compressionPreset)
                                            return i
                                    return 0
                                }
                                tipText: strings.compress_preset_tip
                                onActivated: {
                                    if (currentValue !== "custom")
                                        bridge.applyCompressionPreset(currentValue)
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: strings.compress_preset_tip
                                font.pixelSize: 11
                                color: appRoot.theme.textMuted
                                elide: Text.ElideRight
                            }
                        }

                        TabBar {
                            id: compTabsRow
                            visible: !page.compSettingsCollapsed
                            Layout.fillWidth: true
                            contentHeight: 40
                            currentIndex: page.compSection
                            onCurrentIndexChanged: page.compSection = currentIndex
                            background: Rectangle {
                                color: appRoot.theme.tabBg
                                radius: 8
                            }
                            AppTabButton {
                                text: strings.compress_tab_general
                                font.pixelSize: 13
                                implicitWidth: 115
                            }
                            AppTabButton {
                                text: strings.compress_tab_video
                                font.pixelSize: 13
                                implicitWidth: 105
                            }
                            AppTabButton {
                                text: strings.compress_tab_tracks
                                font.pixelSize: 13
                                implicitWidth: 170
                            }
                            AppTabButton {
                                text: strings.compress_tab_advanced
                                font.pixelSize: 13
                                implicitWidth: 130
                            }
                        }

                        StackLayout {
                            id: compStack
                            visible: !page.compSettingsCollapsed
                            currentIndex: page.compSection
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            ScrollView {
                                id: generalScroll
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AlwaysOn
                                contentWidth: availableWidth

                                ColumnLayout {
                                    width: generalScroll.availableWidth
                                    spacing: 12

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: width > 1180 ? 4 : (width > 900 ? 3 : 2)
                                        columnSpacing: 24
                                        rowSpacing: 12

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_codec; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                id: compCodec
                                                Layout.fillWidth: true
                                                model: bridge.compressionCodecs
                                                textRole: "name"
                                                valueRole: "key"
                                                currentIndex: {
                                                    for (var i = 0; i < model.length; i++)
                                                        if (model[i].key === bridge.compressionCodec)
                                                            return i
                                                    return 0
                                                }
                                                tipText: strings.compress_codec_tip
                                                onActivated: bridge.setCompressionCodec(currentValue)
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_container; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                id: compContainer
                                                Layout.fillWidth: true
                                                model: bridge.compressionContainers
                                                currentIndex: Math.max(0, model.indexOf(bridge.compressionContainer))
                                                tipText: strings.compress_container_tip
                                                onActivated: bridge.setCompressionContainer(currentText)
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_quality_rf; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            RowLayout {
                                                spacing: 10
                                                AppSpinBox {
                                                    id: compQuality
                                                    Layout.preferredWidth: 130
                                                    from: 1; to: bridge.compressionQualityMax
                                                    value: bridge.compressionQuality
                                                    editable: true
                                                    tipText: strings.compress_quality_rf_tip
                                                    onValueChanged: if (value !== bridge.compressionQuality) bridge.setCompressionQuality(value)
                                                }
                                                AppTipLabel {
                                                    Layout.fillWidth: true
                                                    text: strings.compress_estimate + " ~" + bridge.compressionEstimate + "%"
                                                    tip: strings.compress_estimate_tip
                                                    font.pixelSize: 11
                                                    color: appRoot.theme.textSecondary
                                                }
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_min_bitrate; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            RowLayout {
                                                spacing: 10
                                                AppSpinBox {
                                                    Layout.preferredWidth: 130
                                                    from: 0; to: 90; stepSize: 5
                                                    value: bridge.compressionBitrateTargetSupported
                                                           ? bridge.compressionMinBitrate : 0
                                                    editable: true
                                                    enabled: bridge.compressionBitrateTargetSupported
                                                    tipText: bridge.compressionBitrateTargetSupported
                                                             ? strings.compress_min_bitrate_tip
                                                             : strings.compress_min_bitrate_av1_qsv
                                                    onValueChanged: if (value !== bridge.compressionMinBitrate) bridge.setCompressionMinBitrate(value)
                                                }
                                                AppTipLabel {
                                                    Layout.fillWidth: true
                                                    text: !bridge.compressionBitrateTargetSupported
                                                          ? strings.compress_min_bitrate_av1_qsv
                                                          : (bridge.compressionMinBitrate === 0
                                                             ? strings.compress_min_bitrate_off
                                                             : bridge.compressionMinBitrate + "%")
                                                    tip: bridge.compressionBitrateTargetSupported
                                                         ? strings.compress_min_bitrate_tip
                                                         : strings.compress_min_bitrate_av1_qsv
                                                    font.pixelSize: 11
                                                    color: appRoot.theme.textSecondary
                                                    wrapMode: Text.Wrap
                                                }
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_speed; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                id: compSpeed
                                                Layout.fillWidth: true
                                                model: [
                                                    { text: strings.compress_speed_fast, value: "fast" },
                                                    { text: strings.compress_speed_balanced, value: "balanced" },
                                                    { text: strings.compress_speed_slow, value: "slow" },
                                                    { text: strings.compress_speed_slower, value: "slower" }
                                                ]
                                                textRole: "text"
                                                valueRole: "value"
                                                currentIndex: {
                                                    for (var i = 0; i < model.length; i++)
                                                        if (model[i].value === bridge.compressionSpeed)
                                                            return i
                                                    return 1
                                                }
                                                tipText: strings.compress_speed_tip
                                                onActivated: bridge.setCompressionSpeed(currentValue)
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_encoder; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                id: compEncoder
                                                Layout.fillWidth: true
                                                model: bridge.compressionEncoders
                                                textRole: "name"
                                                valueRole: "key"
                                                currentIndex: {
                                                    for (var i = 0; i < model.length; i++)
                                                        if (model[i].key === bridge.compressionEncoder)
                                                            return i
                                                    return 0
                                                }
                                                tipText: strings.compress_encoder_tip
                                                onActivated: bridge.setCompressionEncoder(currentValue)
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            visible: bridge.compressionEncoder === "auto"
                                                     || bridge.compressionEncoder === "qsv"
                                            Label { text: strings.compress_gpu; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            RowLayout {
                                                spacing: 6
                                                AppComboBox {
                                                    id: compGpu
                                                    Layout.fillWidth: true
                                                    model: bridge.compressionQsvDevices
                                                    textRole: "name"
                                                    valueRole: "index"
                                                    currentIndex: {
                                                        for (var i = 0; i < model.length; i++)
                                                            if (model[i].index === bridge.compressionQsvDevice)
                                                                return i
                                                        return 0
                                                    }
                                                    tipText: strings.compress_gpu_tip
                                                    onActivated: bridge.setCompressionQsvDevice(currentValue)
                                                }
                                                AppToolButton {
                                                    display: AbstractButton.IconOnly
                                                    icon.source: appRoot.iconPath("retry")
                                                    icon.width: 16
                                                    icon.height: 16
                                                    tipText: strings.compress_gpu_tip
                                                    Accessible.name: strings.compress_gpu
                                                    onClicked: bridge.refreshCompressionEncoders()
                                                }
                                            }
                                        }


                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_parallel; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppSpinBox {
                                                id: compParallel
                                                Layout.preferredWidth: 130
                                                from: 1; to: 8
                                                value: bridge.compressionParallel
                                                editable: true
                                                tipText: strings.compress_parallel_tip
                                                onValueChanged: if (value !== bridge.compressionParallel) bridge.setCompressionParallel(value)
                                            }
                                        }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_min_size; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppSpinBox {
                                                id: compMinSize
                                                Layout.preferredWidth: 130
                                                from: 0; to: 100000
                                                stepSize: 100
                                                value: bridge.compressionMinSizeMB
                                                editable: true
                                                tipText: strings.compress_min_size_tip
                                                onValueChanged: if (value !== bridge.compressionMinSizeMB) bridge.setCompressionMinSizeMB(value)
                                            }
                                        }
                                    }
                                }
                            }

                            ScrollView {
                                id: videoScroll
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AlwaysOn
                                contentWidth: availableWidth

                                ColumnLayout {
                                    width: videoScroll.availableWidth
                                    spacing: 12

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: width > 1180 ? 4 : (width > 900 ? 3 : 2)
                                        columnSpacing: 24
                                        rowSpacing: 12

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_deinterlace; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                Layout.fillWidth: true
                                                model: [
                                                    { text: strings.compress_deinterlace_auto, value: "auto" },
                                                    { text: strings.compress_deinterlace_off, value: "off" },
                                                    { text: strings.compress_deinterlace_on, value: "on" }
                                                ]
                                                textRole: "text"
                                                valueRole: "value"
                                                currentIndex: {
                                                    for (var i = 0; i < model.length; i++)
                                                        if (model[i].value === bridge.compressionDeinterlace)
                                                            return i
                                                    return 0
                                                }
                                                tipText: strings.compress_deinterlace_tip
                                                onActivated: bridge.setCompressionDeinterlace(currentValue)
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_denoise; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                Layout.fillWidth: true
                                                model: [
                                                    { text: strings.compress_denoise_off, value: "off" },
                                                    { text: strings.compress_denoise_light, value: "light" },
                                                    { text: strings.compress_denoise_medium, value: "medium" },
                                                    { text: strings.compress_denoise_strong, value: "strong" }
                                                ]
                                                textRole: "text"
                                                valueRole: "value"
                                                currentIndex: {
                                                    for (var i = 0; i < model.length; i++)
                                                        if (model[i].value === bridge.compressionDenoise)
                                                            return i
                                                    return 0
                                                }
                                                tipText: strings.compress_denoise_tip
                                                onActivated: bridge.setCompressionDenoise(currentValue)
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_hdr_policy; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                Layout.fillWidth: true
                                                model: [
                                                    { text: strings.compress_hdr_skip, value: "skip" },
                                                    { text: strings.compress_hdr_preserve, value: "preserve" },
                                                    { text: strings.compress_hdr_tonemap, value: "tonemap" }
                                                ]
                                                textRole: "text"
                                                valueRole: "value"
                                                currentIndex: bridge.compressionSkipHdr
                                                              ? 0
                                                              : (bridge.compressionHdrTonemap ? 2 : 1)
                                                tipText: strings.compress_hdr_tip
                                                onActivated: {
                                                    if (currentValue === "skip") {
                                                        bridge.setCompressionSkipHdr(true)
                                                        bridge.setCompressionHdrTonemap(false)
                                                    } else if (currentValue === "preserve") {
                                                        bridge.setCompressionSkipHdr(false)
                                                        bridge.setCompressionHdrTonemap(false)
                                                    } else {
                                                        bridge.setCompressionSkipHdr(false)
                                                        bridge.setCompressionHdrTonemap(true)
                                                    }
                                                }
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_rotate; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                Layout.fillWidth: true
                                                model: [
                                                    { text: "0°", value: 0 },
                                                    { text: "90°", value: 90 },
                                                    { text: "180°", value: 180 },
                                                    { text: "270°", value: 270 }
                                                ]
                                                textRole: "text"
                                                valueRole: "value"
                                                currentIndex: {
                                                    for (var i = 0; i < model.length; i++)
                                                        if (model[i].value === bridge.compressionRotate)
                                                            return i
                                                    return 0
                                                }
                                                onActivated: bridge.setCompressionRotate(currentValue)
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_fps; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppSpinBox {
                                                Layout.preferredWidth: 130
                                                from: 0; to: 240
                                                value: bridge.compressionFps
                                                editable: true
                                                onValueChanged: if (value !== bridge.compressionFps)
                                                                    bridge.setCompressionFps(value)
                                                tipText: strings.compress_fps_tip
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_scale; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            RowLayout {
                                                spacing: 8
                                                AppSpinBox {
                                                    id: scaleWidth
                                                    Layout.preferredWidth: 120
                                                    from: 0; to: 7680; stepSize: 2
                                                    value: bridge.compressionScaleWidth
                                                    editable: true
                                                    onValueChanged: if (value !== bridge.compressionScaleWidth)
                                                                        bridge.setCompressionScaleWidth(value)
                                                    tipText: strings.compress_scale_tip
                                                }
                                                Label { text: "×"; color: appRoot.theme.textSecondary }
                                                AppSpinBox {
                                                    id: scaleHeight
                                                    Layout.preferredWidth: 120
                                                    from: 0; to: 4320; stepSize: 2
                                                    value: bridge.compressionScaleHeight
                                                    editable: true
                                                    onValueChanged: if (value !== bridge.compressionScaleHeight)
                                                                        bridge.setCompressionScaleHeight(value)
                                                }
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_crop; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppHintField {
                                                id: cropField
                                                Layout.fillWidth: true
                                                hint: "w:h:x:y"
                                                text: bridge.compressionCrop
                                                onEditingFinished: bridge.setCompressionCrop(text)
                                                tipText: strings.compress_crop_tip
                                            }
                                        }
                                    }

                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 16
                                        AppCheckBox {
                                            text: strings.compress_ten_bit
                                            visible: bridge.compressionCodec === "hevc"
                                                     && (bridge.compressionEffectiveEncoder === "libx265"
                                                         || bridge.compressionEffectiveEncoder === "libkvazaar")
                                            checked: bridge.compressionTenBit
                                            tipText: strings.compress_ten_bit_tip
                                            onToggled: bridge.setCompressionTenBit(checked)
                                        }
                                        AppCheckBox {
                                            text: strings.compress_x265_tuning
                                            visible: bridge.compressionCodec === "hevc"
                                                     && bridge.compressionEffectiveEncoder === "libx265"
                                            checked: bridge.compressionX265Tuning
                                            tipText: strings.compress_x265_tuning_tip
                                            onToggled: bridge.setCompressionX265Tuning(checked)
                                        }
                                        AppCheckBox {
                                            text: strings.compress_hw_decode
                                            checked: bridge.compressionHwDecode
                                            tipText: strings.compress_hw_decode_tip
                                            onToggled: bridge.setCompressionHwDecode(checked)
                                        }
                                    }
                                }
                            }

                            ScrollView {
                                id: tracksScroll
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AlwaysOn
                                contentWidth: availableWidth

                                ColumnLayout {
                                    width: tracksScroll.availableWidth
                                    spacing: 14

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: width > 760 ? 2 : 1
                                        columnSpacing: 24
                                        rowSpacing: 14

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_audio_mode; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                Layout.fillWidth: true
                                                model: [
                                                    { text: strings.compress_audio_auto, value: "auto" },
                                                    { text: strings.compress_audio_copy, value: "copy" },
                                                    { text: strings.compress_audio_aac, value: "aac" }
                                                ]
                                                textRole: "text"
                                                valueRole: "value"
                                                currentIndex: {
                                                    for (var i = 0; i < model.length; i++)
                                                        if (model[i].value === bridge.compressionAudioMode)
                                                            return i
                                                    return 0
                                                }
                                                tipText: strings.compress_audio_tip
                                                onActivated: bridge.setCompressionAudioMode(currentValue)
                                            }
                                            Label {
                                                Layout.fillWidth: true
                                                text: strings.compress_audio_tip
                                                font.pixelSize: 11
                                                color: appRoot.theme.textMuted
                                                wrapMode: Text.Wrap
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_subtitle_mode; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            AppComboBox {
                                                Layout.fillWidth: true
                                                model: [
                                                    { text: strings.compress_subtitle_auto, value: "auto" },
                                                    { text: strings.compress_subtitle_all, value: "all" },
                                                    { text: strings.compress_subtitle_none, value: "none" }
                                                ]
                                                textRole: "text"
                                                valueRole: "value"
                                                currentIndex: {
                                                    for (var i = 0; i < model.length; i++)
                                                        if (model[i].value === bridge.compressionSubtitleMode)
                                                            return i
                                                    return 0
                                                }
                                                tipText: strings.compress_subtitle_tip
                                                onActivated: bridge.setCompressionSubtitleMode(currentValue)
                                            }
                                            Label {
                                                Layout.fillWidth: true
                                                text: strings.compress_subtitle_tip
                                                font.pixelSize: 11
                                                color: appRoot.theme.textMuted
                                                wrapMode: Text.Wrap
                                            }
                                        }
                                    }
                                }
                            }

                            ScrollView {
                                id: advancedScroll
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AlwaysOn
                                contentWidth: availableWidth

                                ColumnLayout {
                                    width: advancedScroll.availableWidth
                                    spacing: 14

                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 16
                                        AppCheckBox {
                                            text: strings.compress_only_smaller
                                            checked: bridge.compressionOnlyIfSmaller
                                            tipText: strings.compress_only_smaller_tip
                                            onToggled: bridge.setCompressionOnlyIfSmaller(checked)
                                        }
                                        AppCheckBox {
                                            id: replaceOriginalCheck
                                            text: strings.compress_replace_original
                                            checked: bridge.compressionReplaceOriginal
                                            tipText: strings.compress_replace_original_tip
                                            onClicked: {
                                                if (checked)
                                                    confirmReplace.open()
                                                else
                                                    bridge.setCompressionReplaceOriginal(false)
                                            }
                                        }
                                        AppCheckBox {
                                            text: strings.compress_reencode_hevc
                                            checked: bridge.compressionReencodeHevc
                                            tipText: strings.compress_reencode_hevc_tip
                                            onToggled: bridge.setCompressionReencodeHevc(checked)
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10
                                        AppButton {
                                            text: strings.compress_suggestions
                                            tipText: strings.compress_suggestions_tip
                                            onClicked: appRoot.openCompressionSuggestions()
                                        }
                                        AppButton {
                                            text: strings.similar_title
                                            icon.source: appRoot.iconPath("search")
                                            icon.width: 16; icon.height: 16
                                            display: AbstractButton.TextBesideIcon
                                            tipText: strings.similar_subtitle
                                            onClicked: appRoot.openSimilarityDialog()
                                        }
                                        Item { Layout.fillWidth: true }
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: strings.compress_hint
                                        font.pixelSize: 11
                                        color: appRoot.theme.textSecondary
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 100
                    radius: 12
                    color: appRoot.theme.cardBg
                    border.color: appRoot.theme.cardBorder
                    border.width: 1
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Label { text: strings.compress_queue; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Label {
                                visible: bridge.compressionScanBusy
                                text: strings.compress_scanning
                                font.pixelSize: 11
                                color: appRoot.theme.busyText
                            }
                            Item { Layout.fillWidth: true }
                            AppHintField {
                                id: compFilter
                                objectName: "compFilter"
                                Layout.preferredWidth: 310
                                Layout.preferredHeight: 38
                                hint: strings.compress_filter_placeholder
                                leadingIcon: appRoot.iconPath("search")
                                selectByMouse: true
                                tipTitle: strings.compress_filter_title
                                tipText: strings.compress_filter_tip
                                tipShortcut: "Ctrl+F"
                                onTextChanged: {
                                    if (text.length === 0) {
                                        compFilterDebounce.stop()
                                        page.compFilterText = ""
                                    } else {
                                        compFilterDebounce.restart()
                                    }
                                }
                                Keys.onEscapePressed: clear()
                            }
                            Timer {
                                id: compFilterDebounce
                                interval: 180
                                onTriggered: page.compFilterText = compFilter.text
                            }
                            AppToolButton {
                                display: AbstractButton.IconOnly
                                icon.source: appRoot.iconPath("cancel")
                                icon.width: 14
                                icon.height: 14
                                opacity: compFilter.text.length > 0 ? 1 : 0
                                enabled: compFilter.text.length > 0
                                Accessible.name: strings.filter_clear
                                tipTitle: strings.filter_clear
                                tipText: strings.filter_clear_tip
                                tipShortcut: "Esc"
                                onClicked: compFilter.clear()
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            radius: 6
                            color: appRoot.theme.tableHeaderBg

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: page.compColGap

                                TableSortHeader {
                                    objectName: "compHeaderName"
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Layout.minimumWidth: 160
                                    label: strings.compress_col_file
                                    sortKey: "name"
                                    activeKey: compressionModel.sortKey
                                    ascending: compressionModel.sortAscending
                                    textColor: appRoot.theme.tableHeaderText
                                    mutedColor: appRoot.theme.textMuted
                                    hoverColor: appRoot.theme.hover
                                    accentColor: appRoot.theme.accentText
                                    tipTitle: strings.compress_col_file
                                    tipText: strings.sort_tip
                                    tipFooter: strings.sort_name_tip
                                    sortStateText: compressionModel.sortAscending
                                                   ? strings.sort_ascending
                                                   : strings.sort_descending
                                    onActivated: compressionModel.sortBy("name")
                                }
                                TableSortHeader {
                                    objectName: "compHeaderStatus"
                                    Layout.preferredWidth: page.compColStatus
                                    Layout.minimumWidth: page.compColStatus
                                    Layout.maximumWidth: page.compColStatus
                                    Layout.fillHeight: true
                                    label: strings.h_status
                                    sortKey: "status"
                                    activeKey: compressionModel.sortKey
                                    ascending: compressionModel.sortAscending
                                    horizontalAlignment: Text.AlignHCenter
                                    textColor: appRoot.theme.tableHeaderText
                                    mutedColor: appRoot.theme.textMuted
                                    hoverColor: appRoot.theme.hover
                                    accentColor: appRoot.theme.accentText
                                    tipTitle: strings.h_status
                                    tipText: strings.sort_tip
                                    tipFooter: strings.sort_status_tip
                                    sortStateText: compressionModel.sortAscending
                                                   ? strings.sort_ascending
                                                   : strings.sort_descending
                                    onActivated: compressionModel.sortBy("status")
                                }
                                TableSortHeader {
                                    objectName: "compHeaderProgress"
                                    Layout.preferredWidth: page.compColProgress
                                    Layout.minimumWidth: page.compColProgress
                                    Layout.maximumWidth: page.compColProgress
                                    Layout.fillHeight: true
                                    label: strings.h_progress
                                    sortKey: "progress"
                                    activeKey: compressionModel.sortKey
                                    ascending: compressionModel.sortAscending
                                    horizontalAlignment: Text.AlignHCenter
                                    textColor: appRoot.theme.tableHeaderText
                                    mutedColor: appRoot.theme.textMuted
                                    hoverColor: appRoot.theme.hover
                                    accentColor: appRoot.theme.accentText
                                    tipTitle: strings.h_progress
                                    tipText: strings.sort_tip
                                    tipFooter: strings.sort_progress_tip
                                    sortStateText: compressionModel.sortAscending
                                                   ? strings.sort_ascending
                                                   : strings.sort_descending
                                    onActivated: compressionModel.sortBy("progress")
                                }
                                TableSortHeader {
                                    objectName: "compHeaderResult"
                                    Layout.preferredWidth: page.compColResult
                                    Layout.minimumWidth: page.compColResult
                                    Layout.maximumWidth: page.compColResult
                                    Layout.fillHeight: true
                                    label: strings.compress_col_result
                                    sortKey: "size"
                                    activeKey: compressionModel.sortKey
                                    ascending: compressionModel.sortAscending
                                    textColor: appRoot.theme.tableHeaderText
                                    mutedColor: appRoot.theme.textMuted
                                    hoverColor: appRoot.theme.hover
                                    accentColor: appRoot.theme.accentText
                                    tipTitle: strings.compress_col_result
                                    tipText: strings.sort_tip
                                    tipFooter: strings.sort_result_tip
                                    sortStateText: compressionModel.sortAscending
                                                   ? strings.sort_ascending
                                                   : strings.sort_descending
                                    onActivated: compressionModel.sortBy("size")
                                }
                                Item {
                                    Layout.preferredWidth: page.compColActions
                                    Layout.minimumWidth: page.compColActions
                                    Layout.maximumWidth: page.compColActions
                                    Layout.fillHeight: true
                                    Text {
                                        anchors.centerIn: parent
                                        text: strings.h_actions
                                        color: appRoot.theme.tableHeaderText
                                        font.pixelSize: 13
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.theme.cardBorder }

                        ListView {
                            id: compList
                            objectName: "compressionList"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: compressionModel
                            spacing: 0
                            ScrollBar.vertical: ScrollBar {}
                            boundsBehavior: Flickable.StopAtBounds

                            Rectangle {
                                anchors.fill: parent
                                visible: compList.count === 0
                                color: "transparent"
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 6
                                    Image {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        visible: compList.height >= 140
                                        source: appRoot.iconPath("file")
                                        sourceSize.width: 28
                                        sourceSize.height: 28
                                        opacity: 0.45
                                    }
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: strings.compress_empty
                                        font.pixelSize: 13
                                        color: appRoot.theme.textSecondary
                                    }
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        visible: compList.height >= 90
                                        text: strings.compress_empty_hint
                                        font.pixelSize: 11
                                        color: appRoot.theme.textMuted
                                    }
                                }
                            }

                            Column {
                                anchors.centerIn: parent
                                spacing: 4
                                visible: compList.count > 0
                                         && page.compFilterText.length > 0
                                         && compList.contentHeight <= 0
                                Label {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: strings.filter_no_results
                                    font.pixelSize: 13
                                    color: appRoot.theme.textSecondary
                                }
                                Label {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: strings.filter_no_results_hint
                                    font.pixelSize: 11
                                    color: appRoot.theme.textMuted
                                }
                            }

                            delegate: Item {
                                id: compRow
                                width: compList.width
                                property bool matches: page.compRowMatches(model)
                                height: matches ? 58 : 0
                                visible: matches
                                property string st: model.status
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: page.compColGap
                                    ColumnLayout {
                                        objectName: "compCellName"
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 160
                                        spacing: 0
                                        Label {
                                            Layout.fillWidth: true
                                            text: model.name
                                            elide: Text.ElideMiddle
                                            font.pixelSize: 12
                                            font.weight: Font.DemiBold
                                        }
                                        Label {
                                            Layout.fillWidth: true
                                            text: model.encoder
                                            visible: model.encoder.length > 0
                                            elide: Text.ElideRight
                                            font.pixelSize: 9
                                            color: appRoot.theme.textSecondary
                                        }
                                    }
                                    Item {
                                        objectName: "compCellStatus"
                                        Layout.preferredWidth: page.compColStatus
                                        Layout.minimumWidth: page.compColStatus
                                        Layout.maximumWidth: page.compColStatus
                                        Rectangle {
                                            width: 104; height: 24; radius: 12
                                            anchors.centerIn: parent
                                            color: appRoot.badgeColor(compRow.st)
                                            Label {
                                                anchors.fill: parent
                                                anchors.margins: 4
                                                text: appRoot.statusText(compRow.st)
                                                color: appRoot.theme.onAccent
                                                font.pixelSize: 11
                                                font.bold: true
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                    Column {
                                        objectName: "compCellProgress"
                                        Layout.preferredWidth: page.compColProgress
                                        Layout.minimumWidth: page.compColProgress
                                        Layout.maximumWidth: page.compColProgress
                                        spacing: 2
                                        ProgressBar {
                                            width: parent.width; height: 6
                                            from: 0; to: 100
                                            value: model.progress
                                            indeterminate: compRow.st === "analyzing"
                                        }
                                        Label {
                                            anchors.right: parent.right
                                            text: compRow.st === "done" ? "100%" : Math.round(model.progress) + "%"
                                            font.pixelSize: 10
                                            color: appRoot.theme.textSecondary
                                        }
                                    }
                                    Column {
                                        objectName: "compCellResult"
                                        Layout.preferredWidth: page.compColResult
                                        Layout.minimumWidth: page.compColResult
                                        Layout.maximumWidth: page.compColResult
                                        spacing: 2
                                        Label {
                                            width: parent.width
                                            text: appRoot.formatBytes(model.sizeBefore) + " \u2192 "
                                                  + (model.sizeAfter > 0 ? appRoot.formatBytes(model.sizeAfter) : "-")
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                        Label {
                                            id: compDetail
                                            width: parent.width
                                            text: {
                                                if (model.error.length > 0)
                                                    return model.error
                                                var parts = []
                                                if (model.saving > 0)
                                                    parts.push(model.saving + "%")
                                                if (model.ssim > 0)
                                                    parts.push("SSIM " + Number(model.ssim).toFixed(3))
                                                if (model.bitrateAfter > 0)
                                                    parts.push(appRoot.formatBitrate(model.bitrateAfter))
                                                return parts.length > 0 ? parts.join(" · ") : model.speed
                                            }
                                            font.pixelSize: 10
                                            color: compRow.st === "error"
                                                   ? appRoot.theme.errorText
                                                   : (model.qualityWarning.length > 0
                                                      ? appRoot.theme.warningText
                                                      : appRoot.theme.textSecondary)
                                            elide: Text.ElideRight
                                            AppToolTip {
                                                target: compDetail
                                                title: model.name
                                                text: page.compDetailTip(model)
                                                available: text.length > 0
                                                delay: 400
                                            }
                                        }
                                    }
                                    Item {
                                        objectName: "compCellActions"
                                        Layout.preferredWidth: page.compColActions
                                        Layout.minimumWidth: page.compColActions
                                        Layout.maximumWidth: page.compColActions
                                        Row {
                                            anchors.centerIn: parent
                                            spacing: 4
                                            AppToolButton {
                                                width: 32; height: 28
                                                display: AbstractButton.IconOnly
                                                icon.source: appRoot.iconPath("cancel")
                                                icon.width: 16; icon.height: 16
                                                visible: compRow.st === "waiting" || compRow.st === "analyzing" || compRow.st === "encoding"
                                                Accessible.name: strings.tip_cancel
                                                tipTitle: strings.tip_cancel
                                                tipText: strings.compress_cancel_tip
                                                onClicked: bridge.cancelCompressionItem(model.sourceIndex)
                                            }
                                            AppToolButton {
                                                width: 32; height: 28
                                                display: AbstractButton.IconOnly
                                                icon.source: appRoot.iconPath("retry")
                                                icon.width: 16; icon.height: 16
                                                visible: compRow.st === "error" || compRow.st === "skipped"
                                                         || compRow.st === "cancelled"
                                                Accessible.name: strings.compress_retry
                                                tipTitle: strings.compress_retry
                                                tipText: strings.compress_retry_tip
                                                onClicked: bridge.retryCompressionItem(model.sourceIndex)
                                            }
                                            AppToolButton {
                                                width: 32; height: 28
                                                display: AbstractButton.IconOnly
                                                icon.source: appRoot.iconPath("open")
                                                icon.width: 16; icon.height: 16
                                                visible: compRow.st === "done" && model.output !== ""
                                                Accessible.name: strings.tip_open
                                                tipTitle: strings.tip_open
                                                tipText: model.output
                                                onClicked: bridge.openCompressionOutput(model.output)
                                            }
                                            AppToolButton {
                                                width: 32; height: 28
                                                display: AbstractButton.IconOnly
                                                icon.source: appRoot.iconPath("trash")
                                                icon.width: 16; icon.height: 16
                                                visible: compRow.st === "done" || compRow.st === "error"
                                                         || compRow.st === "cancelled" || compRow.st === "skipped"
                                                Accessible.name: strings.ctx_remove
                                                tipTitle: strings.ctx_remove
                                                tipText: strings.compress_remove_tip
                                                onClicked: bridge.removeCompressionItem(model.sourceIndex)
                                            }
                                        }
                                    }
                                }
                                Rectangle {
                                    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                                    height: 1
                                    color: appRoot.theme.divider
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Label {
                        Layout.fillWidth: true
                        text: appRoot.compWait + " " + strings.compress_stat_waiting + " · "
                              + appRoot.compWork + " " + strings.compress_stat_working + " · "
                              + appRoot.compDone + " " + strings.compress_stat_done + " · "
                              + appRoot.compErr + " " + strings.compress_stat_errors + " · "
                              + appRoot.compSkip + " " + strings.compress_stat_skipped
                        font.pixelSize: 12
                        color: appRoot.theme.textSecondary
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                    AppButton {
                        text: strings.compress_scan_cancel
                        variant: "secondary"
                        icon.source: appRoot.iconPath("stop")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: bridge.compressionScanBusy
                        tipTitle: strings.compress_scan_cancel
                        tipText: strings.compress_scan_cancel_tip
                        onClicked: bridge.cancelCompressionScan()
                    }
                    AppButton {
                        text: bridge.compressionDetecting ? strings.compress_detecting_ui : strings.btn_start
                        highlighted: !bridge.compressionDetecting
                        icon.source: appRoot.iconPath("play")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: !bridge.compressionActive
                        enabled: !bridge.compressionDetecting && appRoot.compWait > 0
                        tipTitle: strings.btn_start
                        tipText: strings.compress_start_tip
                        onClicked: bridge.startCompression()
                    }
                    AppButton {
                        text: strings.btn_pause
                        icon.source: appRoot.iconPath("pause")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: bridge.compressionActive && !bridge.compressionPaused
                        tipTitle: strings.btn_pause
                        tipText: strings.btn_pause_tip
                        onClicked: bridge.pauseCompression()
                    }
                    AppButton {
                        text: strings.btn_resume
                        icon.source: appRoot.iconPath("play")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: bridge.compressionActive && bridge.compressionPaused
                        highlighted: true
                        tipTitle: strings.btn_resume
                        tipText: strings.btn_resume_tip
                        onClicked: bridge.resumeCompression()
                    }
                    AppButton {
                        text: strings.btn_cancel_all
                        variant: "secondary"
                        icon.source: appRoot.iconPath("stop")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        enabled: appRoot.compWork + appRoot.compWait > 0
                        tipTitle: strings.btn_cancel_all
                        tipText: strings.btn_cancel_all_tip
                        onClicked: bridge.cancelCompression()
                    }
                    AppButton {
                        text: strings.btn_clear_finished
                        variant: "secondary"
                        icon.source: appRoot.iconPath("trash")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        enabled: appRoot.compDone + appRoot.compErr + appRoot.compSkip > 0
                        tipTitle: strings.btn_clear_finished
                        tipText: strings.compress_clear_finished_tip
                        onClicked: bridge.clearCompressionFinished()
                    }
                }
            }

        Dialog {
            id: confirmReplace
            parent: appRoot.contentItem
            modal: true
            title: strings.compress_replace_original
            width: 500
            x: (appRoot.width - width) / 2
            y: (appRoot.height - height) / 2
            standardButtons: Dialog.NoButton
            onClosed: {
                if (!bridge.compressionReplaceOriginal)
                    replaceOriginalCheck.checked = false
            }
            contentItem: AppDialogSurface {
                theme: appRoot.theme
                Label {
                    Layout.fillWidth: true
                    text: strings.compress_replace_original_tip
                    wrapMode: Text.Wrap
                }
                Label {
                    Layout.fillWidth: true
                    text: strings.compress_backup_kept
                          + ": <nome>.hlsdl-backup-<data>.<ext>"
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                    color: appRoot.theme.textSecondary
                }
            }
            footer: DialogButtonBox {
                AppButton {
                    text: strings.confirm_ok
                    DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                    onClicked: {
                        bridge.setCompressionReplaceOriginal(true)
                        confirmReplace.close()
                    }
                }
                AppButton {
                    text: strings.confirm_cancel
                    DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                    onClicked: {
                        bridge.setCompressionReplaceOriginal(false)
                        replaceOriginalCheck.checked = false
                        confirmReplace.close()
                    }
                }
            }
        }
    }
