import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

        Item {
    id: page
    property var appRoot
    property var strings: ({})
    property int compSection: 0
    readonly property real compContentHeight: compStack.children[compStack.currentIndex]
                                                 ? compStack.children[compStack.currentIndex].implicitHeight : 0

    ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(
                        280,
                        Math.min(
                            appRoot.height - 300,
                            32 + compHeader.implicitHeight + 12
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

                        RowLayout {
                            id: compHeader
                            Layout.fillWidth: true
                            spacing: 8
                            Label {
                                text: strings.compress_title
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                            }
                            Item { Layout.fillWidth: true }
                            AppButton {
                                text: strings.compress_add_files
                                icon.source: appRoot.iconPath("file")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                onClicked: bridge.addCompressionFiles()
                            }
                            AppButton {
                                text: strings.compress_add_folder
                                icon.source: appRoot.iconPath("open")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                onClicked: bridge.addCompressionFolder()
                            }
                        }

                        RowLayout {
                            id: compPresetRow
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
                                ToolTip.text: strings.compress_preset_tip
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
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

                        RowLayout {
                            id: compTabsRow
                            Layout.fillWidth: true
                            spacing: 6
                            Repeater {
                                model: [
                                    { label: strings.compress_tab_general, index: 0 },
                                    { label: strings.compress_tab_video, index: 1 },
                                    { label: strings.compress_tab_tracks, index: 2 },
                                    { label: strings.compress_tab_advanced, index: 3 }
                                ]
                                delegate: Item {
                                    implicitWidth: tabButton.implicitWidth
                                    implicitHeight: tabButton.height + 4
                                    AppButton {
                                        id: tabButton
                                        anchors.top: parent.top
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: modelData.label
                                        highlighted: page.compSection === modelData.index
                                        height: 32
                                        onClicked: page.compSection = modelData.index
                                    }
                                    Rectangle {
                                        anchors.bottom: parent.bottom
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        width: tabButton.width
                                        height: 2
                                        radius: 1
                                        color: page.compSection === modelData.index
                                               ? appRoot.theme.accentText
                                               : "transparent"
                                    }
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        StackLayout {
                            id: compStack
                            currentIndex: page.compSection
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            ScrollView {
                                id: generalScroll
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded
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
                                                ToolTip.text: strings.compress_codec_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                                ToolTip.text: strings.compress_container_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
                                                onActivated: bridge.setCompressionContainer(currentText)
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_quality_rf; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            RowLayout {
                                                spacing: 10
                                                SpinBox {
                                                    id: compQuality
                                                    Layout.preferredWidth: 130
                                                    from: 1; to: bridge.compressionQualityMax
                                                    value: bridge.compressionQuality
                                                    editable: true
                                                    ToolTip.text: strings.compress_quality_rf_tip
                                                    ToolTip.visible: hovered; ToolTip.delay: 500
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
                                                ToolTip.text: strings.compress_speed_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                                ToolTip.text: strings.compress_encoder_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                                    ToolTip.text: strings.compress_gpu_tip
                                                    ToolTip.visible: hovered
                                                    ToolTip.delay: 500
                                                    onActivated: bridge.setCompressionQsvDevice(currentValue)
                                                }
                                                AppToolButton {
                                                    display: AbstractButton.IconOnly
                                                    icon.source: appRoot.iconPath("retry")
                                                    icon.width: 16
                                                    icon.height: 16
                                                    ToolTip.text: strings.compress_gpu_tip
                                                    ToolTip.visible: hovered
                                                    ToolTip.delay: 500
                                                    Accessible.name: strings.compress_gpu
                                                    onClicked: bridge.refreshCompressionEncoders()
                                                }
                                            }
                                        }


                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_parallel; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            SpinBox {
                                                id: compParallel
                                                Layout.preferredWidth: 130
                                                from: 1; to: 8
                                                value: bridge.compressionParallel
                                                editable: true
                                                ToolTip.text: strings.compress_parallel_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
                                                onValueChanged: if (value !== bridge.compressionParallel) bridge.setCompressionParallel(value)
                                            }
                                        }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_min_size; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            SpinBox {
                                                id: compMinSize
                                                Layout.preferredWidth: 130
                                                from: 0; to: 100000
                                                stepSize: 100
                                                value: bridge.compressionMinSizeMB
                                                editable: true
                                                ToolTip.text: strings.compress_min_size_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded
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
                                                ToolTip.text: strings.compress_deinterlace_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                                ToolTip.text: strings.compress_denoise_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                                ToolTip.text: strings.compress_hdr_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                            SpinBox {
                                                Layout.preferredWidth: 130
                                                from: 0; to: 240
                                                value: bridge.compressionFps
                                                editable: true
                                                onValueChanged: if (value !== bridge.compressionFps)
                                                                    bridge.setCompressionFps(value)
                                                ToolTip.text: strings.compress_fps_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: strings.compress_scale; font.pixelSize: 11; color: appRoot.theme.textSecondary }
                                            RowLayout {
                                                spacing: 8
                                                SpinBox {
                                                    id: scaleWidth
                                                    Layout.preferredWidth: 120
                                                    from: 0; to: 7680; stepSize: 2
                                                    value: bridge.compressionScaleWidth
                                                    editable: true
                                                    onValueChanged: if (value !== bridge.compressionScaleWidth)
                                                                        bridge.setCompressionScaleWidth(value)
                                                    ToolTip.text: strings.compress_scale_tip
                                                    ToolTip.visible: hovered
                                                    ToolTip.delay: 500
                                                }
                                                Label { text: "×"; color: appRoot.theme.textSecondary }
                                                SpinBox {
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
                                                ToolTip.text: strings.compress_crop_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                            ToolTip.text: strings.compress_ten_bit_tip
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
                                            onToggled: bridge.setCompressionTenBit(checked)
                                        }
                                        AppCheckBox {
                                            text: strings.compress_x265_tuning
                                            visible: bridge.compressionCodec === "hevc"
                                                     && bridge.compressionEffectiveEncoder === "libx265"
                                            checked: bridge.compressionX265Tuning
                                            ToolTip.text: strings.compress_x265_tuning_tip
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
                                            onToggled: bridge.setCompressionX265Tuning(checked)
                                        }
                                        AppCheckBox {
                                            text: strings.compress_hw_decode
                                            checked: bridge.compressionHwDecode
                                            ToolTip.text: strings.compress_hw_decode_tip
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
                                            onToggled: bridge.setCompressionHwDecode(checked)
                                        }
                                    }
                                }
                            }

                            ScrollView {
                                id: tracksScroll
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded
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
                                                ToolTip.text: strings.compress_audio_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                                ToolTip.text: strings.compress_subtitle_tip
                                                ToolTip.visible: hovered
                                                ToolTip.delay: 500
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
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded
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
                                            ToolTip.text: strings.compress_only_smaller_tip
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
                                            onToggled: bridge.setCompressionOnlyIfSmaller(checked)
                                        }
                                        AppCheckBox {
                                            id: replaceOriginalCheck
                                            text: strings.compress_replace_original
                                            checked: bridge.compressionReplaceOriginal
                                            ToolTip.text: strings.compress_replace_original_tip
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
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
                                            ToolTip.text: strings.compress_reencode_hevc_tip
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
                                            onToggled: bridge.setCompressionReencodeHevc(checked)
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10
                                        AppButton {
                                            text: strings.compress_suggestions
                                            ToolTip.text: strings.compress_suggestions_tip
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
                                            onClicked: appRoot.openCompressionSuggestions()
                                        }
                                        AppButton {
                                            text: strings.similar_title
                                            icon.source: appRoot.iconPath("search")
                                            icon.width: 16; icon.height: 16
                                            display: AbstractButton.TextBesideIcon
                                            ToolTip.text: strings.similar_subtitle
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
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
                    Layout.minimumHeight: 150
                    radius: 12
                    color: appRoot.theme.cardBg
                    border.color: appRoot.theme.cardBorder
                    border.width: 1
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8
                        Label { text: strings.compress_queue; font.pixelSize: 15; font.weight: Font.DemiBold }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            radius: 6
                            color: appRoot.theme.tableHeaderBg

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 10
                                Item { Layout.fillWidth: true; Layout.minimumWidth: 160 }
                                Label { text: strings.h_status; Layout.preferredWidth: 110; font.pixelSize: 13; font.bold: true; color: appRoot.theme.tableHeaderText }
                                Label { text: strings.h_progress; Layout.preferredWidth: 150; font.pixelSize: 13; font.bold: true; color: appRoot.theme.tableHeaderText; horizontalAlignment: Text.AlignHCenter }
                                Label { text: strings.compress_col_result; Layout.preferredWidth: 190; font.pixelSize: 13; font.bold: true; color: appRoot.theme.tableHeaderText }
                                Item { Layout.preferredWidth: 108 }
                            }
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.theme.cardBorder }

                        ListView {
                            id: compList
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
                                Label {
                                    anchors.centerIn: parent
                                    text: strings.compress_empty
                                    font.pixelSize: 13
                                    color: appRoot.theme.textSecondary
                                }
                            }

                            delegate: Item {
                                id: compRow
                                width: compList.width
                                height: 58
                                property string st: model.status
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: 10
                                    ColumnLayout {
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
                                        Layout.preferredWidth: 110
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
                                        Layout.preferredWidth: 150
                                        spacing: 2
                                        ProgressBar {
                                            width: 150; height: 6
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
                                        Layout.preferredWidth: 190
                                        spacing: 2
                                        Label {
                                            width: parent.width
                                            text: appRoot.formatBytes(model.sizeBefore) + " → "
                                                  + (model.sizeAfter > 0 ? appRoot.formatBytes(model.sizeAfter) : "—")
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                        Label {
                                            width: parent.width
                                            text: model.saving > 0
                                                  ? (model.saving + "% " + strings.compress_saving)
                                                  : (model.error.length > 0 ? model.error : model.speed)
                                            font.pixelSize: 10
                                            color: compRow.st === "error"
                                                   ? (appRoot.theme.errorText)
                                                   : appRoot.theme.textSecondary
                                            elide: Text.ElideRight
                                            HoverHandler { id: compErrHover }
                                            ToolTip.text: model.error
                                                + (model.backup !== "" ? "\n" + strings.compress_backup_kept + ": " + model.backup : "")
                                                + (model.sha256 !== "" ? "\n" + strings.compress_hash + ": " + model.sha256 : "")
                                            ToolTip.visible: compErrHover.hovered
                                                             && (model.error.length > 0 || model.backup !== "" || model.sha256 !== "")
                                            ToolTip.delay: 400
                                        }
                                    }
                                    Row {
                                        Layout.preferredWidth: 108
                                        spacing: 4
                                        AppToolButton {
                                            width: 32; height: 28
                                            display: AbstractButton.IconOnly
                                            icon.source: appRoot.iconPath("cancel")
                                            icon.width: 16; icon.height: 16
                                            visible: compRow.st === "waiting" || compRow.st === "analyzing" || compRow.st === "encoding"
                                            Accessible.name: strings.tip_cancel
                                            ToolTip.text: strings.tip_cancel
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
                                            onClicked: bridge.cancelCompressionItem(index)
                                        }
                                        AppToolButton {
                                            width: 32; height: 28
                                            display: AbstractButton.IconOnly
                                            icon.source: appRoot.iconPath("retry")
                                            icon.width: 16; icon.height: 16
                                            visible: compRow.st === "error" || compRow.st === "skipped"
                                                     || compRow.st === "cancelled"
                                            Accessible.name: strings.compress_retry
                                            ToolTip.text: strings.compress_retry
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
                                            onClicked: bridge.retryCompressionItem(index)
                                        }
                                        AppToolButton {
                                            width: 32; height: 28
                                            display: AbstractButton.IconOnly
                                            icon.source: appRoot.iconPath("open")
                                            icon.width: 16; icon.height: 16
                                            visible: compRow.st === "done" && model.output !== ""
                                            Accessible.name: strings.tip_open
                                            ToolTip.text: strings.tip_open
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
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
                                            ToolTip.text: strings.ctx_remove
                                            ToolTip.visible: hovered
                                            ToolTip.delay: 500
                                            onClicked: bridge.removeCompressionItem(index)
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
                        elide: Text.ElideRight
                    }
                    AppButton {
                        text: bridge.compressionDetecting ? strings.compress_detecting_ui : strings.btn_start
                        highlighted: !bridge.compressionDetecting
                        icon.source: appRoot.iconPath("play")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: !bridge.compressionActive
                        enabled: !bridge.compressionDetecting
                        onClicked: bridge.startCompression()
                    }
                    AppButton {
                        text: strings.btn_pause
                        icon.source: appRoot.iconPath("pause")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: bridge.compressionActive && !bridge.compressionPaused
                        onClicked: bridge.pauseCompression()
                    }
                    AppButton {
                        text: strings.btn_resume
                        icon.source: appRoot.iconPath("play")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: bridge.compressionActive && bridge.compressionPaused
                        highlighted: true
                        onClicked: bridge.resumeCompression()
                    }
                    AppButton {
                        text: strings.btn_cancel_all
                        icon.source: appRoot.iconPath("stop")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        onClicked: bridge.cancelCompression()
                    }
                    AppButton {
                        text: strings.btn_clear_finished
                        icon.source: appRoot.iconPath("trash")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
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
