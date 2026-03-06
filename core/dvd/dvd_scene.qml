import QtQuick
import QtCore
import QtQuick3D
import QtQuick3D.AssetUtils
import QtQuick3D.Helpers

View3D {
    id: view3d
    anchors.fill: parent
    camera: orbitCamera
    property real cameraX: 0.2  // 滚轮控制，范围 [0, 1.4]
    property real orbitRotationX: -5   // 俯仰，范围 [-10, 10]
    property real orbitRotationY: 0    // 偏航，范围 [-20, 20]
    property int hoveredDelegateIndex: -1
    property int selectedDelegateIndex: -1
    property int expandedDelegateIndex: -1
    property int pressedDelegateIndex: -1
    property var pressedObjectHit: null  // 按下时拾取到的 3D 对象，用于区分 CD 点击

    environment: SceneEnvironment {
        clearColor: "#1a1a2e"
        backgroundMode: SceneEnvironment.SkyBox
        lightProbe: Texture {
            source: "lebombo_2k.hdr"
        }
        probeOrientation: Qt.vector3d(0, 155, 0)  // 欧拉角 (x,y,z) 度，改 y 可水平旋转
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

    // 相机位置固定 (cameraX, 0, cameraDistance)，旋转只改变可视角度（朝向），不改变位置
    Node {
        id: orbitOrigin
        position: Qt.vector3d(0, 0, 0)

        PerspectiveCamera {
            id: orbitCamera
            position: Qt.vector3d(cameraX, 0, cameraDistance)
            eulerRotation.x: view3d.orbitRotationX
            eulerRotation.y: view3d.orbitRotationY
            clipNear: 0.001
            clipFar: 100000
            fieldOfView: 60

            // 镜头前方占位：相机局部 -Z 为朝向，position (0,0,-d) 即镜头前 d 单位
            Node {
                id: cameraFront
                position: Qt.vector3d(0, 0, -(typeof selectedDvdDistance !== "undefined" ? selectedDvdDistance : 1.5))
            }
        }
    }

    // 主光源：暖色主光，开启阴影增强立体感
    DirectionalLight {
        id: keyLight
        eulerRotation.x: -40
        eulerRotation.y: -50
        color: Qt.rgba(1.0, 0.96, 0.92, 1.0)
        ambientColor: Qt.rgba(0.2, 0.2, 0.22, 1.0)
        brightness: 5
        castsShadow: true
        shadowMapQuality: Light.ShadowMapQualityHigh
        shadowMapFar: 500
    }

    // 补光：冷色从另一侧，减少主光阴影过重
    DirectionalLight {
        id: fillLight
        eulerRotation.x: -25
        eulerRotation.y: 100
        color: Qt.rgba(0.6, 0.75, 1.0, 1.0)
        ambientColor: Qt.rgba(0.05, 0.06, 0.1, 1.0)
        brightness: 0.8
    }

    // 轮廓光：从后方打亮边缘，增强轮廓
    DirectionalLight {
        id: rimLight
        eulerRotation.x: -5
        eulerRotation.y: 180
        color: Qt.rgba(1.0, 0.98, 0.95, 1.0)
        brightness: 0.6
    }

    Node {
        id: sceneRoot

        // 场景环境：书架等静态模型
        /*
        Loader3D {
            id: envirLoader
            source: Qt.resolvedUrl("Envir.qml")
            onStatusChanged: {
                if (status === Loader3D.Error) console.warn("Envir.qml load error:", errorString)
            }
        }
        */

        // 复制多份 Dvd.qml：model 为份数，每份间距 dvdSpacing
        // 每份贴图来自 dvdTextureSources[index]，未指定则用 maps/0.png
        Repeater3D {
            id: dvdRepeater
            model: dvdCount
            delegate: Node {
                property string tex: (dvdTextureSources && index < dvdTextureSources.length)
                    ? dvdTextureSources[index] : "maps/0.png"
                property bool selected: view3d.selectedDelegateIndex === index
                x: selected ? cameraFront.scenePosition.x : (index * dvdSpacing)
                y: selected ? cameraFront.scenePosition.y : 0
                z: selected ? cameraFront.scenePosition.z : (view3d.hoveredDelegateIndex === index ? 0.05 : 0)
                // 以 DVD 几何中心为旋转轴，避免旋转时“飞走”
                pivot: Qt.vector3d(-0.00979297 * modelScale, 5.68405e-05 * modelScale, -0.0676852 * modelScale)
                Behavior on x { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
                Behavior on y { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
                Behavior on z { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }

                // 选中时用 LookAtNode 使封面正对镜头（垂直于视线）；未选中时 spine 视图
                LookAtNode {
                    id: lookAtNode
                    target: selected ? orbitCamera : null
                    // target 为 null 时复位到 spine 视图
                    Binding {
                        target: lookAtNode
                        property: "eulerRotation"
                        value: Qt.vector3d(0, 0, 0)
                        when: !selected
                    }
                    Node {
                        // 选中时 -90 显示封面，未选中时 0 显示 spine
                        eulerRotation.y: selected ? 90 : 0
                        Behavior on eulerRotation.y { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
                        Loader3D {
                            id: dvdLoader
                            source: dvdQmlUrl
                            scale: Qt.vector3d(modelScale, modelScale, modelScale)
                            onStatusChanged: {
                                if (status === Loader3D.Error) console.warn("Dvd.qml load error")
                            }
                            onItemChanged: {
                                if (item) {
                                    if (typeof item.textureSource !== "undefined") item.textureSource = tex
                                    if (typeof item.delegateIndex !== "undefined") item.delegateIndex = index
                                    if (typeof item.cdClicked !== "undefined") {
                                        item.cdClicked.connect(function() {
                                            console.log("[Dvd] cdClicked 信号，index:", index)
                                        })
                                    }
                                }
                            }
                            Binding {
                                target: dvdLoader.item
                                property: "expanded"
                                value: view3d.expandedDelegateIndex === index
                                when: dvdLoader.item && typeof dvdLoader.item.expanded !== "undefined"
                            }
                        }
                    }
                }
                onTexChanged: {
                    if (dvdLoader.item && typeof dvdLoader.item.textureSource !== "undefined")
                        dvdLoader.item.textureSource = tex
                }
            }
        }

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

    // 右键仅控制方向，由下方 MouseArea 实现，俯仰 ±10°、偏航 ±20°

    function findDelegateIndex(obj) {
        var n = obj
        while (n) {
            if (typeof n.delegateIndex !== "undefined" && n.delegateIndex >= 0)
                return n.delegateIndex
            n = n.parent
        }
        return -1
    }

    MouseArea {
        z: 1
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: true
        propagateComposedEvents: true
        property real _lastMouseX: 0
        property real _lastMouseY: 0
        property bool _rightDragging: false
        property real _rotSensitivity: 0.15  // 像素转角度

        // 滚轮仅控制相机 x 位置 [0, 1.4]，不控制缩放
        onWheel: function(wheel) {
            var step = 0.05
            var delta = wheel.angleDelta.y > 0 ? step : -step
            view3d.cameraX = Math.max(0.1, Math.min(1.3, view3d.cameraX + delta))
            wheel.accepted = true
        }
        onPositionChanged: function(mouse) {
            if (_rightDragging) {
                var dx = mouse.x - _lastMouseX
                var dy = mouse.y - _lastMouseY
                _lastMouseX = mouse.x
                _lastMouseY = mouse.y
                view3d.orbitRotationY = Math.max(-20, Math.min(20, view3d.orbitRotationY + dx * _rotSensitivity))
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
                    // 点击 CD 盘面：仅发射信号，不改变选中/展开状态
                    var root = view3d.pressedObjectHit.parent
                    if (root && typeof root.cdClicked !== "undefined")
                        root.cdClicked()
                } else {
                    if (view3d.selectedDelegateIndex === idx) {
                        // 横着状态下再次点击：切换展开/收起
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
}
