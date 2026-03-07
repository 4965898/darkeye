import QtQuick
import QtCore
import QtQuick3D
import QtQuick3D.AssetUtils
import QtQuick3D.Helpers

View3D {
    id: view3d
    anchors.fill: parent
    camera: orbitCamera
    // 相机在书架上的横向位置（范围由外部约束到 [0, dvdShelfLength]）。
    property real cameraX: 0
    // 右键拖拽控制的俯仰与偏航角。
    property real orbitRotationX: -5
    property real orbitRotationY: 0
    // 可见窗口内的悬停/选中/展开/按下索引。
    property int hoveredDelegateIndex: -1
    property int selectedDelegateIndex: -1
    property int expandedDelegateIndex: -1
    property int pressedDelegateIndex: -1
    // 左键按下时命中的 3D 对象，用于区分 CD 与盒体点击。
    property var pressedObjectHit: null

    // 展开态操作按钮（爱心/编辑/删除）的 3D 锚点映射，key=delegate index。
    property var actionAnchorByIndex: ({})
    // 展开态 title/story 的 front 面锚点映射，key=delegate index。
    property var frontInfoAnchorByIndex: ({})

    // 将可见窗口内索引映射回全量列表索引。
    function expandedVirtualIndexFor(delegateIndex) {
        return (typeof dvdVisibleStart !== "undefined" ? dvdVisibleStart : 0) + delegateIndex
    }

    // 场景环境：天空盒、探针、抗锯齿与 AO。
    environment: SceneEnvironment {
        clearColor: "#1a1a2e"
        backgroundMode: SceneEnvironment.SkyBox
        lightProbe: Texture {
            source: (typeof hdrPath !== "undefined" ? hdrPath : "/") + "lebombo_2k.hdr"//fireplace_2k,lebombo_2k
        }
        probeOrientation: Qt.vector3d(0, 155, 0)
        antialiasingMode: SceneEnvironment.MSAA
        antialiasingQuality: SceneEnvironment.High
        tonemapMode: SceneEnvironment.TonemapModeFilmic
        aoEnabled: true
        aoStrength: 0.18
        aoDistance: 1.5
        aoSoftness: 15
        aoSampleRate: 2
        debugSettings: DebugSettings {
            wireframeEnabled: showWireframe
        }
    }


    // 轨道相机节点：位置跟随 cameraX，朝向由 orbitRotationX/Y 控制。
    Node {
        id: orbitOrigin
        position: Qt.vector3d(0, 0, 0)

        PerspectiveCamera {
            id: orbitCamera
            position: Qt.vector3d((typeof dvdBridge !== "undefined" && dvdBridge) ? dvdBridge.cameraX : view3d.cameraX, 0, cameraDistance)
            eulerRotation.x: view3d.orbitRotationX
            eulerRotation.y: view3d.orbitRotationY
            clipNear: 0.001
            clipFar: 100000
            fieldOfView: 60


            // 相机前方固定点：选中时用于把 DVD 拉到镜头前。
            Node {
                id: cameraFront
                position: Qt.vector3d(0, 0, -(typeof selectedDvdDistance !== "undefined" ? selectedDvdDistance : 1.5))
            }
        }
    }


    // 主光。
    DirectionalLight {
        id: keyLight
        eulerRotation.x: -40
        eulerRotation.y: -50
        color: Qt.rgba(1.0, 0.96, 0.92, 1.0)
        ambientColor: Qt.rgba(0.2, 0.2, 0.22, 1.0)
        brightness: 4
        castsShadow: true
        shadowMapQuality: Light.ShadowMapQualityHigh
        shadowMapFar: 50
    }


    // 补光。
    DirectionalLight {
        id: fillLight
        eulerRotation.x: -25
        eulerRotation.y: 100
        color: Qt.rgba(0.6, 0.75, 1.0, 1.0)
        ambientColor: Qt.rgba(0.05, 0.06, 0.1, 1.0)
        brightness: 0.8
    }


    // 轮廓光。
    DirectionalLight {
        id: rimLight
        eulerRotation.x: -5
        eulerRotation.y: 180
        color: Qt.rgba(1.0, 0.98, 0.95, 1.0)
        brightness: 0.6
    }

    // 3D 场景根节点。
    Node {
        id: sceneRoot





        // DVD 虚拟化可见窗口：只渲染 dvdCount 个可见项。
        Repeater3D {
            id: dvdRepeater
            model: dvdCount
            delegate: Node {
                // virtualIndex 是全量 work 列表索引；index 是可见窗口索引。
                property int virtualIndex: (typeof dvdVisibleStart !== "undefined" ? dvdVisibleStart : 0) + index
                // 每个 DVD 的封面纹理；缺失时回退默认贴图。
                property string tex: (dvdTextureSources && index < dvdTextureSources.length)
                    ? dvdTextureSources[index] : ((typeof mapsPath !== "undefined" ? mapsPath : "maps/") + "0.png")
                property bool selected: view3d.selectedDelegateIndex === index
                property bool hovered: view3d.hoveredDelegateIndex === index
                // 选中时移动到镜头前，未选中按书架间距排布。
                x: selected ? cameraFront.scenePosition.x : (virtualIndex * dvdSpacing)
                y: selected ? cameraFront.scenePosition.y : 0
                z: selected ? cameraFront.scenePosition.z : (hovered ? 0.05 : 0)

                // 旋转中心，避免旋转时出现“飘移”。
                pivot: Qt.vector3d(-0.00979297 * modelScale, 5.68405e-05 * modelScale, -0.0676852 * modelScale)

                // 选中/悬停位移动画。
                Behavior on x { enabled: selected; NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
                Behavior on y { enabled: selected; NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
                Behavior on z { enabled: selected || hovered; NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }


                // 选中时让 DVD 面向相机；未选中恢复书架朝向。
                LookAtNode {
                    id: lookAtNode
                    target: selected ? orbitCamera : null

                    Binding {
                        target: lookAtNode
                        property: "eulerRotation"
                        value: Qt.vector3d(0, 0, 0)
                        when: !selected
                    }
                    Node {

                        // 选中时切到封面视角。
                        eulerRotation.y: selected ? 90 : 0
                        Behavior on eulerRotation.y { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
                        Loader3D {
                            id: dvdLoader
                            source: dvdQmlUrl
                            scale: Qt.vector3d(modelScale, modelScale, modelScale)
                            onStatusChanged: {
                                if (status === Loader3D.Error) console.warn("Dvd.qml load error")
                            }
                            // item 变化时同步贴图、索引、锚点与 CD 点击回调。
                            onItemChanged: {
                                view3d.actionAnchorByIndex[index] = null
                                view3d.frontInfoAnchorByIndex[index] = null
                                if (item) {
                                    if (typeof item.textureSource !== "undefined") item.textureSource = tex
                                    if (typeof item.delegateIndex !== "undefined") item.delegateIndex = index
                                    if (typeof item.actionAnchorNode !== "undefined")
                                        view3d.actionAnchorByIndex[index] = item.actionAnchorNode
                                    if (typeof item.frontInfoAnchorNode !== "undefined")
                                        view3d.frontInfoAnchorByIndex[index] = item.frontInfoAnchorNode
                                    if (typeof item.cdClicked !== "undefined") {
                                        item.cdClicked.connect(function() {
                                            var vIdx = (typeof dvdVisibleStart !== "undefined" ? dvdVisibleStart : 0) + index
                                            if (typeof dvdBridge !== "undefined" && dvdBridge)
                                                dvdBridge.onCdClicked(vIdx)
                                        })
                                    }
                                }
                            }
                            Binding {
                                target: dvdLoader.item
                                property: "expanded"
                                value: view3d.expandedDelegateIndex === index
                                // 将展开态同步给 Dvd.qml（开盒动画）。
                                when: dvdLoader.item && typeof dvdLoader.item.expanded !== "undefined"
                            }
                        }

                    }
                }
                // 可见窗口复用时，贴图变化需同步到现有 item。
                onTexChanged: {
                    if (dvdLoader.item && typeof dvdLoader.item.textureSource !== "undefined")
                        dvdLoader.item.textureSource = tex
                }
                // 销毁时清理锚点映射，避免索引复用时残留引用。
                Component.onDestruction: {
                    if (view3d.actionAnchorByIndex[index])
                        view3d.actionAnchorByIndex[index] = null
                    if (view3d.frontInfoAnchorByIndex[index])
                        view3d.frontInfoAnchorByIndex[index] = null
                }
            }
        }

        // 兜底模型加载器：当没有 DVD 列表时显示外部模型。
        RuntimeLoader {
            id: modelLoader
            visible: dvdQmlUrl === "" || dvdCount === 0
            source: modelUrl
            scale: Qt.vector3d(modelScale, modelScale, modelScale)

            onStatusChanged: {
                if (status === RuntimeLoader.Error) {
                    console.warn("Model load error:", errorString)
                }
            }
        }


    }



    // 从拾取命中的对象向上回溯到所属 delegate，返回其 index。
    function findDelegateIndex(obj) {
        var n = obj
        while (n) {
            if (typeof n.delegateIndex !== "undefined" && n.delegateIndex >= 0)
                return n.delegateIndex
            n = n.parent
        }
        return -1
    }

    // 统一鼠标交互层：滚轮平移书架，右键拖拽旋转，左键点选/展开/DVD-CD 点击。
    MouseArea {
        z: 1
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: true
        propagateComposedEvents: true
        property real _lastMouseX: 0
        property real _lastMouseY: 0
        property bool _rightDragging: false
        // 右键旋转灵敏度。
        property real _rotSensitivity: 0.15



        // 滚轮：沿书架 X 方向移动相机，并收起选中/展开态。
        onWheel: function(wheel) {
            view3d.selectedDelegateIndex = -1
            view3d.expandedDelegateIndex = -1
            var shelfLen = (typeof dvdShelfLength !== "undefined" && dvdShelfLength > 0) ? dvdShelfLength : 1.5
            var step = (typeof dvdSpacing !== "undefined" ? dvdSpacing : 0.0145) * 3
            var delta = wheel.angleDelta.y > 0 ? -step : step
            if (typeof dvdBridge !== "undefined" && dvdBridge) {
                var newVal = Math.max(0, Math.min(shelfLen, dvdBridge.cameraX + delta))
                dvdBridge.setCameraX(newVal)
            } else {
                view3d.cameraX = Math.max(0, Math.min(shelfLen, view3d.cameraX + delta))
            }
            wheel.accepted = true
        }
        // 鼠标移动：右键拖拽时旋转相机，否则更新悬停项。
        onPositionChanged: function(mouse) {
            if (_rightDragging) {
                var dx = mouse.x - _lastMouseX
                var dy = mouse.y - _lastMouseY
                _lastMouseX = mouse.x
                _lastMouseY = mouse.y
                view3d.orbitRotationY = Math.max(-20, Math.min(20, view3d.orbitRotationY - dx * _rotSensitivity))
                view3d.orbitRotationX = Math.max(-10, Math.min(10, view3d.orbitRotationX - dy * _rotSensitivity))
                mouse.accepted = true
                return
            }
            var result = view3d.pick(mouse.x, mouse.y)
            if (result && result.objectHit) {
                view3d.hoveredDelegateIndex = view3d.findDelegateIndex(result.objectHit)
            } else {
                view3d.hoveredDelegateIndex = -1
            }
            mouse.accepted = false
        }
        // 按下：记录拖拽起点与按下命中的对象。
        onPressed: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                _rightDragging = true
                _lastMouseX = mouse.x
                _lastMouseY = mouse.y
                mouse.accepted = true
                return
            }
            if (mouse.button !== Qt.LeftButton) {
                mouse.accepted = false
                return
            }
            var result = view3d.pick(mouse.x, mouse.y)
            if (result && result.objectHit) {
                view3d.pressedDelegateIndex = view3d.findDelegateIndex(result.objectHit)
                view3d.pressedObjectHit = result.objectHit
            } else {
                view3d.pressedDelegateIndex = -1
                view3d.pressedObjectHit = null
            }
            mouse.accepted = true
        }
        // 释放：处理 CD 点击、选中切换与展开切换。
        onReleased: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                _rightDragging = false
                mouse.accepted = true
                return
            }
            if (mouse.button !== Qt.LeftButton) {
                mouse.accepted = false
                return
            }
            if (view3d.pressedDelegateIndex >= 0) {
                var idx = view3d.pressedDelegateIndex
                var hitCd = view3d.pressedObjectHit && view3d.pressedObjectHit.objectName === "cD"
                if (hitCd) {

                    var root = view3d.pressedObjectHit.parent
                    if (root && typeof root.cdClicked !== "undefined")
                        root.cdClicked()
                } else {
                    if (view3d.selectedDelegateIndex === idx) {

                        view3d.expandedDelegateIndex = (view3d.expandedDelegateIndex === idx) ? -1 : idx
                    } else {
                        view3d.selectedDelegateIndex = idx
                        view3d.expandedDelegateIndex = -1
                    }
                }
            } else {
                view3d.selectedDelegateIndex = -1
                view3d.expandedDelegateIndex = -1
            }
            view3d.pressedDelegateIndex = -1
            view3d.pressedObjectHit = null
            mouse.accepted = true
        }
        onExited: {
            view3d.hoveredDelegateIndex = -1
            _rightDragging = false
        }
    }


    // front 面信息层：title/story 的 2D 投影，仅展开后显示。
    Item {
        id: workInfoOverlay
        z: 2
        readonly property real _overlayWidth: (typeof workInfoOverlayWidth !== "undefined")
            ? workInfoOverlayWidth
            : Math.min(360, Math.max(240, view3d.width * 0.35))
        width: _overlayWidth
        height: contentColumn.implicitHeight + 24
        property var expandedAnchor: (view3d.expandedDelegateIndex >= 0)
            ? view3d.frontInfoAnchorByIndex[view3d.expandedDelegateIndex]
            : null
        property point projectedPoint: {
            if (!expandedAnchor)
                return Qt.point(-99999, -99999)
            var _cameraTick = orbitCamera.position.x + orbitCamera.position.y + orbitCamera.position.z
                + orbitCamera.eulerRotation.x + orbitCamera.eulerRotation.y + orbitCamera.eulerRotation.z
                + view3d.width + view3d.height
            var p = view3d.mapFrom3DScene(expandedAnchor.scenePosition)
            return Qt.point(p.x + _cameraTick * 0, p.y)
        }
        x: projectedPoint.x - width * 0.5
        y: projectedPoint.y - height * 0.5
        visible: view3d.expandedDelegateIndex >= 0
            && expandedAnchor
            && isFinite(projectedPoint.x)
            && isFinite(projectedPoint.y)

        property int expandedVirtualIndex: view3d.expandedDelegateIndex >= 0
            ? view3d.expandedVirtualIndexFor(view3d.expandedDelegateIndex)
            : -1

        // 展示状态变化/展开索引变化时，向 Python 请求当前 work 的 title/story。
        onVisibleChanged: {
            if (typeof dvdBridge !== "undefined" && dvdBridge)
                dvdBridge.refreshExpandedWorkMeta(visible ? expandedVirtualIndex : -1)
        }
        Connections {
            target: view3d
            function onExpandedDelegateIndexChanged() {
                if (typeof dvdBridge !== "undefined" && dvdBridge)
                    dvdBridge.refreshExpandedWorkMeta(workInfoOverlay.expandedVirtualIndex)
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: 10
            color: "#CC101622"
            border.color: "#99ffffff"
            border.width: 1
        }

        // 文本内容：标题 + 简介 + 番号 + 发布日期，高度随内容自动收缩
        Column {
            id: contentColumn
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 12
            spacing: 8
            Text {
                width: parent.width
                color: "#ffffff"
                font.pixelSize: 16
                font.bold: true
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                text: (typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkTitle)
                    ? dvdBridge.expandedWorkTitle : ""
            }
            Text {
                width: parent.width
                color: "#e8ecf5"
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                maximumLineCount: 6
                elide: Text.ElideRight
                text: (typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkStory)
                    ? dvdBridge.expandedWorkStory : ""
            }
            Text {
                width: parent.width
                color: "#a0a8b8"
                font.pixelSize: 12
                wrapMode: Text.NoWrap
                elide: Text.ElideRight
                visible: text !== ""
                text: (typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkCode)
                    ? ("番号: " + dvdBridge.expandedWorkCode) : ""
            }
            Text {
                width: parent.width
                color: "#a0a8b8"
                font.pixelSize: 12
                wrapMode: Text.NoWrap
                elide: Text.ElideRight
                visible: text !== ""
                text: (typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkReleaseDate)
                    ? ("发布日期: " + dvdBridge.expandedWorkReleaseDate) : ""
            }

            // 作品标签
            Column {
                width: parent.width - 24
                spacing: 4
                visible: typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkTags
                    && dvdBridge.expandedWorkTags.length > 0
                Text {
                    text: "作品标签"
                    color: "#a0a8b8"
                    font.pixelSize: 11
                }
                Flow {
                    width: parent.width
                    spacing: 4
                    Repeater {
                        model: (typeof dvdBridge !== "undefined" && dvdBridge) ? dvdBridge.expandedWorkTags : []
                        delegate: Rectangle {
                            width: tagLabel.implicitWidth + 10
                            height: tagLabel.implicitHeight + 4
                            radius: 4
                            color: (modelData && modelData.color) ? modelData.color : "#cccccc"
                            Text {
                                id: tagLabel
                                anchors.centerIn: parent
                                text: modelData ? modelData.tag_name : ""
                                font.pixelSize: 11
                                color: (modelData && modelData.text_color) ? modelData.text_color : "#333333"
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                hoverEnabled: true
                                onClicked: {
                                    if (typeof dvdBridge !== "undefined" && dvdBridge && modelData)
                                        dvdBridge.onTagClicked(modelData.tag_id)
                                }
                            }
                        }
                    }
                }
            }

            // 女优
            Column {
                width: parent.width - 24
                spacing: 4
                visible: typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkActresses
                    && dvdBridge.expandedWorkActresses.length > 0
                Text {
                    text: "女优"
                    color: "#a0a8b8"
                    font.pixelSize: 11
                }
                Flow {
                    width: parent.width
                    spacing: 4
                    Repeater {
                        model: (typeof dvdBridge !== "undefined" && dvdBridge) ? dvdBridge.expandedWorkActresses : []
                        delegate: Rectangle {
                            width: actressLabel.implicitWidth + 10
                            height: actressLabel.implicitHeight + 4
                            radius: 4
                            color: "#ffffff"
                            Text {
                                id: actressLabel
                                anchors.centerIn: parent
                                text: modelData ? modelData.actress_name : ""
                                font.pixelSize: 11
                                color: "#333333"
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof dvdBridge !== "undefined" && dvdBridge && modelData)
                                        dvdBridge.onActressClicked(modelData.actress_id)
                                }
                            }
                        }
                    }
                }
            }

            // 男优
            Column {
                width: parent.width - 24
                spacing: 4
                visible: typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkActors
                    && dvdBridge.expandedWorkActors.length > 0
                Text {
                    text: "男优"
                    color: "#a0a8b8"
                    font.pixelSize: 11
                }
                Flow {
                    width: parent.width
                    spacing: 4
                    Repeater {
                        model: (typeof dvdBridge !== "undefined" && dvdBridge) ? dvdBridge.expandedWorkActors : []
                        delegate: Rectangle {
                            width: actorLabel.implicitWidth + 10
                            height: actorLabel.implicitHeight + 4
                            radius: 4
                            color: "#ffffff"
                            Text {
                                id: actorLabel
                                anchors.centerIn: parent
                                text: modelData ? modelData.actor_name : ""
                                font.pixelSize: 11
                                color: "#333333"
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof dvdBridge !== "undefined" && dvdBridge && modelData)
                                        dvdBridge.onActorClicked(modelData.actor_id)
                                }
                            }
                        }
                    }
                }
            }

            // 导演
            Row {
                width: parent.width
                spacing: 4
                visible: typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkDirector
                    && dvdBridge.expandedWorkDirector.length > 0
                Text {
                    text: "导演: "
                    color: "#a0a8b8"
                    font.pixelSize: 12
                }
                Item {
                    width: directorText.implicitWidth
                    height: directorText.implicitHeight
                    Text {
                        id: directorText
                        text: (typeof dvdBridge !== "undefined" && dvdBridge) ? dvdBridge.expandedWorkDirector : ""
                        color: "#e8ecf5"
                        font.pixelSize: 12
                        font.underline: directorMouseArea.containsMouse
                    }
                    MouseArea {
                        id: directorMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof dvdBridge !== "undefined" && dvdBridge)
                                dvdBridge.onDirectorClicked()
                        }
                    }
                }
            }

            // 厂商
            Row {
                width: parent.width
                spacing: 4
                visible: typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkStudio
                    && dvdBridge.expandedWorkStudio.length > 0
                Text {
                    text: "厂商: "
                    color: "#a0a8b8"
                    font.pixelSize: 12
                }
                Item {
                    width: studioText.implicitWidth
                    height: studioText.implicitHeight
                    Text {
                        id: studioText
                        text: (typeof dvdBridge !== "undefined" && dvdBridge) ? dvdBridge.expandedWorkStudio : ""
                        color: "#e8ecf5"
                        font.pixelSize: 12
                        font.underline: studioMouseArea.containsMouse
                    }
                    MouseArea {
                        id: studioMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof dvdBridge !== "undefined" && dvdBridge)
                                dvdBridge.onStudioClicked()
                        }
                    }
                }
            }
        }
    }

    // spine 中心操作层：爱心、编辑、删除按钮的 2D 投影。
    Item {
        id: actionOverlay
        z: 2
        width: 48
        height: actionColumn.height
        property var expandedAnchor: (view3d.expandedDelegateIndex >= 0)
            ? view3d.actionAnchorByIndex[view3d.expandedDelegateIndex]
            : null
        property point projectedPoint: {
            if (!expandedAnchor)
                return Qt.point(-99999, -99999)

            // Keep bindings reactive to camera movement.
            var _cameraTick = orbitCamera.position.x + orbitCamera.position.y + orbitCamera.position.z
                + orbitCamera.eulerRotation.x + orbitCamera.eulerRotation.y + orbitCamera.eulerRotation.z
                + view3d.width + view3d.height
            var p = view3d.mapFrom3DScene(expandedAnchor.scenePosition)
            return Qt.point(p.x + _cameraTick * 0, p.y)
        }
        x: projectedPoint.x - width * 0.5
        y: projectedPoint.y - height * 0.5
        visible: view3d.expandedDelegateIndex >= 0
            && expandedAnchor
            && isFinite(projectedPoint.x)
            && isFinite(projectedPoint.y)

        property int expandedVirtualIndex: view3d.expandedDelegateIndex >= 0
            ? view3d.expandedVirtualIndexFor(view3d.expandedDelegateIndex)
            : -1

        // 展示状态变化/展开索引变化时，刷新收藏状态。
        onVisibleChanged: {
            if (visible && typeof dvdBridge !== "undefined" && dvdBridge)
                dvdBridge.refreshExpandedFavoriteState(expandedVirtualIndex)
        }
        Connections {
            target: view3d
            function onExpandedDelegateIndexChanged() {
                if (actionOverlay.visible && view3d.expandedDelegateIndex >= 0
                    && typeof dvdBridge !== "undefined" && dvdBridge)
                    dvdBridge.refreshExpandedFavoriteState(actionOverlay.expandedVirtualIndex)
            }
        }

        Column {
            id: actionColumn
            spacing: 8
            anchors.horizontalCenter: parent.horizontalCenter


            // 收藏按钮（爱心）。
            Item {
                width: 40
                height: 40
                Image {
                    id: heartImg
                    anchors.centerIn: parent
                    width: 28
                    height: 28
                    source: (typeof dvdBridge !== "undefined" && dvdBridge && dvdBridge.expandedWorkFavorited)
                        ? Qt.resolvedUrl("icons/love-on.svg")
                        : Qt.resolvedUrl("icons/love-off.svg")
                    fillMode: Image.PreserveAspectFit
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof dvdBridge !== "undefined" && dvdBridge)
                            dvdBridge.onHeartClicked(actionOverlay.expandedVirtualIndex)
                    }
                }
            }


            // 编辑按钮。
            Item {
                width: 40
                height: 40
                Image {
                    anchors.centerIn: parent
                    width: 24
                    height: 24
                    source: Qt.resolvedUrl("icons/square-pen.svg")
                    fillMode: Image.PreserveAspectFit
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof dvdBridge !== "undefined" && dvdBridge)
                            dvdBridge.onEditClicked(actionOverlay.expandedVirtualIndex)
                    }
                }
            }


            // 删除按钮。
            Item {
                width: 40
                height: 40
                Image {
                    anchors.centerIn: parent
                    width: 24
                    height: 24
                    source: Qt.resolvedUrl("icons/trash-2.svg")
                    fillMode: Image.PreserveAspectFit
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof dvdBridge !== "undefined" && dvdBridge)
                            dvdBridge.onDeleteClicked(actionOverlay.expandedVirtualIndex)
                    }
                }
            }
        }
    }
}
