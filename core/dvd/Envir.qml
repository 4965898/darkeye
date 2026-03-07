import QtQuick
import QtQuick3D

Node {
    id: rOOT
    y:-0.095//整体向上移动
    z:0.1//整体向里移动

    Model {
        id: shelf_001
        scale.x: 0.824632
        scale.z: 0.0984435
        source: (typeof meshesPath !== "undefined" ? meshesPath : "meshes/") + "shelf_001.mesh"

        PrincipledMaterial {
            id: material_001_material
            baseColor: "#ffcca92c"
            metalness: 0
            roughness: 0.5
            cullMode: Material.NoCulling
        }
        materials: [
            material_001_material
        ]
    }

    Model {
        id: shelf_003
        scale.x: 0.824632
        scale.z: 0.0984435
        source: (typeof meshesPath !== "undefined" ? meshesPath : "meshes/") + "shelf_003.mesh"
        materials: [
            material_001_material
        ]
    }

    Model {
        id: shelf_002
        scale.x: 0.824632
        scale.z: 0.0984435
        source: (typeof meshesPath !== "undefined" ? meshesPath : "meshes/") + "shelf_002.mesh"
        materials: [
            material_001_material
        ]
    }
}
