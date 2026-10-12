import { Canvas, useFrame } from '@react-three/fiber'
import { useRef, useState } from 'react'
import * as THREE from 'three'
import { fragmentShader, vertexShader } from './shaders'

export type MiniLook = { core: string; rim: string; active: boolean }

function Blob({ core, rim, active }: MiniLook) {
  const mesh = useRef<THREE.Mesh>(null)
  const material = useRef<THREE.ShaderMaterial>(null)
  // Initial values only; useFrame eases toward new colors.
  const [uniforms] = useState(() => ({
    uTime: { value: 0 },
    uAmp: { value: 0.06 },
    uDetail: { value: 1.6 },
    uLevel: { value: 0 },
    uCore: { value: new THREE.Color(core) },
    uRim: { value: new THREE.Color(rim) },
  }))

  useFrame((_, delta) => {
    const u = material.current?.uniforms
    if (!u) return
    const k = 1 - Math.exp(-delta * 4)
    u.uTime.value += delta * (active ? 1.3 : 0.25)
    u.uAmp.value += ((active ? 0.13 : 0.05) - u.uAmp.value) * k
    u.uCore.value.lerp(new THREE.Color(core), k)
    u.uRim.value.lerp(new THREE.Color(rim), k)
    if (mesh.current) mesh.current.rotation.y += delta * (active ? 1 : 0.1)
  })

  return (
    <mesh ref={mesh}>
      <icosahedronGeometry args={[1, 24]} />
      <shaderMaterial
        ref={material}
        uniforms={uniforms}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
      />
    </mesh>
  )
}

/** Small animated orb for an agent card; shares the shaders of Alfred's orb. */
export function MiniOrb(look: MiniLook) {
  return (
    <Canvas camera={{ position: [0, 0, 2.7], fov: 45 }} dpr={[1, 2]} gl={{ alpha: true }}>
      <Blob {...look} />
    </Canvas>
  )
}
