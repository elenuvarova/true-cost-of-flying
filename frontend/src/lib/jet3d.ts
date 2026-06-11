// 3D hero jet — frosted-glass cartoon liner flying the hero contrail.
// Lazy-loaded on desktop only (mobile + prefers-reduced-motion keep the SVG delta glyph).
// Model: "Airplane" by jeremy via Poly Pizza (CC-BY) → /jet.glb, Loop-subdivided ×2 at load
// (split:true, preserveEdges:true — the combination that keeps the engine pods clean).
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { LoopSubdivision } from 'three-subdivide'

const CAM_Z = 10
// presentation pose (3/4 "beauty" view): a touch of yaw toward the viewer + a base roll
// so the wing plan reads throughout the flight instead of an edge-on side view
const POSE_YAW = -0.5 // rad, nose toward the camera
const POSE_ROLL = -0.4 // rad, top of the wings tipped toward the viewer

export interface Jet3D {
  /** position the jet at viewport pixel coords, heading `angDeg` (screen deg, cw), banked by `bankDeg` */
  place(xPx: number, yPx: number, angDeg: number, bankDeg: number, visible: boolean): void
  dispose(): void
}

export async function mountJet3D(host: HTMLElement): Promise<Jet3D> {
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.1
  const el = renderer.domElement
  el.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;'
  host.appendChild(el)

  const scene = new THREE.Scene()
  const pmrem = new THREE.PMREMGenerator(renderer)
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture

  // orthographic, 1 world unit = 1 css px — no off-axis perspective skew, so the jet
  // stays aligned with its trail anywhere on screen (with a perspective cam it appears
  // to yaw "sideways" near the screen edges)
  // frustum shrunk so 1 world unit = JET_PX css px — keeps the model (and its glass
  // material's world-space thickness/attenuation) at sane unit scale
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100)
  cam.position.set(0, 0, CAM_Z)

  // brand light rig: warm amber from below (the contrail), cool blue above, white rim behind
  scene.add(new THREE.AmbientLight(0x223a55, 1.3))
  const warm = new THREE.DirectionalLight(0xef8a43, 5.2)
  warm.position.set(-1.5, -1.2, 2.5)
  scene.add(warm)
  const cool = new THREE.DirectionalLight(0x4fb0f5, 3.0)
  cool.position.set(1, 2.4, -1.2)
  scene.add(cool)
  const rim = new THREE.DirectionalLight(0xffffff, 3.4)
  rim.position.set(2.6, 0.6, -2.2)
  scene.add(rim)

  // outer group: screen placement + heading; inner: bank around the flight axis; model: axis alignment
  const outer = new THREE.Group()
  const banker = new THREE.Group()
  outer.add(banker)
  scene.add(outer)

  const gltf = await new GLTFLoader().loadAsync('./jet.glb')
  const model = gltf.scene
  const frosted = new THREE.MeshPhysicalMaterial({
    transmission: 1, roughness: 0.42, thickness: 1.6, ior: 1.4, color: 0xcfe2f5,
    metalness: 0, attenuationColor: new THREE.Color(0x9fc8f5), attenuationDistance: 2.5,
    clearcoat: 0.6, clearcoatRoughness: 0.3, envMapIntensity: 0.7,
    emissive: new THREE.Color(0x16314e), emissiveIntensity: 0.55, // keeps the ghost readable over the dark copy zone
  })
  model.traverse((o: any) => {
    if (!o.isMesh) return
    o.geometry = LoopSubdivision.modify(o.geometry, 2, { split: true, preserveEdges: true, flatOnly: false })
    o.geometry.computeVertexNormals()
    o.material = frosted
  })
  // normalise: centre at origin, length = 1 world unit. This model is authored
  // nose-along-+X, fin up (verified empirically with a 0/90/180/270° probe render).
  const box = new THREE.Box3().setFromObject(model)
  const size = box.getSize(new THREE.Vector3())
  const centre = box.getCenter(new THREE.Vector3())
  model.position.sub(centre)
  const wrap = new THREE.Group()
  wrap.add(model)
  wrap.scale.setScalar(1 / Math.max(size.x, size.z))
  wrap.rotation.y = POSE_YAW
  banker.add(wrap)

  let vw = 1, vh = 1, jetPx = 190
  const resize = () => {
    vw = host.clientWidth || 1
    vh = host.clientHeight || 1
    jetPx = Math.min(190, vw * 0.34) // phones get a clearly smaller jet
    renderer.setSize(vw, vh, false)
    cam.left = -vw / 2 / jetPx; cam.right = vw / 2 / jetPx
    cam.top = vh / 2 / jetPx; cam.bottom = -vh / 2 / jetPx
    cam.updateProjectionMatrix()
  }
  resize()
  const ro = new ResizeObserver(resize)
  ro.observe(host)

  return {
    place(xPx, yPx, angDeg, bankDeg, visible) {
      outer.visible = visible
      if (!visible) { renderer.render(scene, cam); return }
      const rad = (-angDeg * Math.PI) / 180
      // anchor: tail/engines meet the trail head — forward along heading, plus a small
      // perpendicular nudge that compensates the 3/4 presentation pose
      const lead = 0.36
      const perp = 6 / jetPx
      const cos = Math.cos(rad), sin = Math.sin(rad)
      outer.position.set(
        (xPx - vw / 2) / jetPx + cos * lead - sin * perp,
        -(yPx - vh / 2) / jetPx + sin * lead + cos * perp,
        0,
      )
      outer.rotation.z = rad
      banker.rotation.x = POSE_ROLL + (bankDeg * Math.PI) / 180
      renderer.render(scene, cam)
    },
    dispose() {
      ro.disconnect()
      renderer.dispose()
      pmrem.dispose()
      el.remove()
    },
  }
}
