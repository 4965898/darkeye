import QtQuick
import QtQuick3D
import QtQuick3D.AssetUtils
import QtQuick3D.Helpers

View3D {
    id: view3d
    anchors.fill: parent
    camera: orbitCamera
    property int hoveredDelegateIndex: -1

    environment: SceneEnvironment {
        clearColor: "#1a1a2e"
        backgroundMode: SceneEnvironment.Color
        antialiasingMode: SceneEnvironment.MSAA
        antialiasingQuality: SceneEnvironment.High
        tonemapMode: SceneEnvironment.TonemapModeFilmic
        aoEnabled: true
        aoStrength: 0.4
        aoDistance: 50
        aoSoftness: 20
        aoSampleRate: 2
        debugSettings: DebugSettings {
            wireframeEnabled: showWireframe
        }
    }

    // 轨道控制器要求：相机在 (0,0,z)，仅改 z 才能正确缩放；用 orbitOrigin 旋转实现俯视角度
    Node {
        id: orbitOrigin
        position: Qt.vector3d(0, 0, 0)
        eulerRotation.x: -35
        eulerRotation.y: 45

        PerspectiveCamera {
            id: orbitCamera
            position: Qt.vector3d(0, 0, cameraDistance)
            clipNear: 0.001
            clipFar: 100000
        }
    }

    // 主光源：暖色主光，开启阴影增强立体感
    DirectionalLight {
        id: keyLight
        eulerRotation.x: -40
        eulerRotation.y: -50
        color: Qt.rgba(1.0, 0.96, 0.92, 1.0)
        ambientColor: Qt.rgba(0.2, 0.2, 0.22, 1.0)
        brightness: 1.8
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

        // 复制多份 Dvd.qml：model 为份数，每份间距 dvdSpacing
        // 每份贴图来自 dvdTextureSources[index]，未指定则用 maps/0.png
        Repeater3D {
            id: dvdRepeater
            model: dvdCount
            delegate: Node {
                property string tex: (dvdTextureSources && index < dvdTextureSources.length)
                    ? dvdTextureSources[index] : "maps/0.png"
                x: index * dvdSpacing
                z: view3d.hoveredDelegateIndex === index ? 0.8 : 0
                Behavior on z { NumberAnimation { duration: 120 } }
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

    OrbitCameraController {
        anchors.fill: parent
        origin: orbitOrigin
        camera: orbitCamera
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        propagateComposedEvents: true
        onPositionChanged: function(mouse) {
            var result = view3d.pick(mouse.x, mouse.y)
            if (result && result.objectHit) {
                var hitParent = result.objectHit.parent
                if (hitParent && typeof hitParent.delegateIndex !== "undefined" && hitParent.delegateIndex >= 0)
                    view3d.hoveredDelegateIndex = hitParent.delegateIndex
                else
                    view3d.hoveredDelegateIndex = -1
            } else {
                view3d.hoveredDelegateIndex = -1
            }
            mouse.accepted = false
        }
        onPressed: function(mouse) { mouse.accepted = false }
        onReleased: function(mouse) { mouse.accepted = false }
        onExited: view3d.hoveredDelegateIndex = -1
    }

    DebugView {
        source: view3d
        anchors.right: parent.right
        anchors.top: parent.top
    }
}
