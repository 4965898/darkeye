import QtQuick
import QtQuick3D

Node {
        id: rOOT
    /** 贴图路径，可动态更换；支持相对路径（相对 Dvd.qml 所在目录）或 file:// 绝对路径 */
    property string textureSource: "maps/0.png"
    /** 由 dvd_scene 注入，用于 hover 判断 */
    property int delegateIndex: -1
Model {
    
    id: cube_002
    x: 0.436592
    y: 0.0950568
    z: -0.0676852
    source: "meshes/cube_002.mesh"
    pickable: true
    PrincipledMaterial {
        id: pic_material
        baseColorMap: Texture {
            source: rOOT.textureSource
            tilingModeHorizontal: Texture.Repeat
            tilingModeVertical: Texture.Repeat
        }
        opacityChannel: Material.A
        metalness: 0
        roughness: 0.08
        cullMode: Material.NoCulling
    }

    PrincipledMaterial {
        id: trans_material
        baseColor: "#b294c1cc"
        metalness: 0
        roughness: 0.3
        cullMode: Material.NoCulling
        alphaMode: PrincipledMaterial.Blend
    }
    materials: [
        pic_material,
        trans_material
    ]
}
}