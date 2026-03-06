import QtQuick
import QtQuick3D

Node {
    id: rOOT
    /** 贴图路径，可动态更换；支持相对路径（相对 Dvd.qml 所在目录）或 file:// 绝对路径 */
    property string textureSource: "maps/0.png"

    Model {
        id: cube_006
        x: 0.134917
        y: 0.0950568
        z: -0.000185236
        source: "meshes/cube_006.mesh"

        PrincipledMaterial {
            id: pic_001_material
            baseColorMap: Texture {
                source: rOOT.textureSource
                tilingModeHorizontal: Texture.Repeat
                tilingModeVertical: Texture.Repeat
            }
            opacityChannel: Material.A
            metalness: 0
            roughness: 0.5
            cullMode: Material.NoCulling
        }

        PrincipledMaterial {
            id: trans_material
            baseColor: "#b2cccccc"
            metalness: 0
            roughness: 0.5
            cullMode: Material.NoCulling
            alphaMode: PrincipledMaterial.Blend
        }
        materials: [
            pic_001_material,
            trans_material
        ]
    }

    Model {
        id: cube_007
        x: 0.148917
        y: 0.0950568
        z: -0.000185236
        source: "meshes/cube_007.mesh"
        materials: [
            pic_001_material,
            trans_material
        ]
    }

    Model {
        id: cube_008
        x: 0.141917
        y: 0.0950568
        z: -0.0676852
        source: "meshes/cube_008.mesh"
        materials: [
            pic_001_material
        ]
    }
}
