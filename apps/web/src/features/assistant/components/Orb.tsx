import { Canvas, useFrame } from '@react-three/fiber'
import { useMemo, useRef, type RefObject } from 'react'
import * as THREE from 'three'
import type { VoiceState } from '../../../api/events'
import type { Level } from '../hooks/useVoice'
import { fragmentShader, haloFragmentShader, vertexShader } from './orbShaders'

type Look = {
  core: string
  rim: string
  /** Base displacement, always present. */
  amp: number
  /** Extra displacement per unit of audio level. */
  react: number
  /** Noise speed. */
  speed: number
  /** Noise frequency over the surface. */
  detail: number
  spin: number
  scale: number
}

const LOOKS: Record<VoiceState, Look> = {
  idle: {
    core: '#14213d',
    rim: '#5b7cfa',
    amp: 0.06,
    react: 0,
    speed: 0.25,
    detail: 1.4,
    spin: 0.08,
    scale: 1,
  },
  listening: {
    core: '#063b4a',
    rim: '#5eead4',
    amp: 0.08,
    react: 0.4,
    speed: 0.7,
    detail: 1.8,
    spin: 0.15,
    scale: 1.08,
  },
  transcribing: {
    core: '#2e1065',
    rim: '#c084fc',
    amp: 0.14,
    react: 0,
    speed: 1.6,
    detail: 2.6,
    spin: 0.6,
    scale: 1.02,
  },
  thinking: {
    core: '#451a03',
    rim: '#fbbf24',
    amp: 0.12,
    react: 0,
    speed: 1.1,
    detail: 3.2,
    spin: 1.2,
    scale: 0.96,
  },
  speaking: {
    core: '#052e2b',
    rim: '#34d399',
    amp: 0.07,
    react: 0.5,
    speed: 0.8,
    detail: 1.6,
    spin: 0.2,
    scale: 1.05,
  },
}

/** Level events stop arriving between utterances; fade instead of freezing on the last value. */
const LEVEL_TTL_MS = 250

function Blob({ state, level }: { state: VoiceState; level: RefObject<Level> }) {
  const mesh = useRef<THREE.Mesh>(null)
  const halo = useRef<THREE.Mesh>(null)
  const smooth = useRef({
    level: 0,
    time: 0,
    speed: 0.25,
    spin: 0.08,
    scale: 1,
    amp: 0.06,
    react: 0,
    detail: 1.4,
  })

  const material = useRef<THREE.ShaderMaterial>(null)
  // Initial values only; useFrame updates them through the material refs.
  const { uniforms, haloUniforms } = useMemo(() => {
    const shared = {
      uRim: { value: new THREE.Color(LOOKS.idle.rim) },
      uLevel: { value: 0 },
    }
    return {
      uniforms: {
        ...shared,
        uTime: { value: 0 },
        uAmp: { value: 0.06 },
        uDetail: { value: 1.4 },
        uCore: { value: new THREE.Color(LOOKS.idle.core) },
      },
      haloUniforms: shared,
    }
  }, [])

  useFrame((_, delta) => {
    const look = LOOKS[state]
    const s = smooth.current
    const k = 1 - Math.exp(-delta * 4)
    const fresh = performance.now() - level.current.at < LEVEL_TTL_MS
    const target = fresh ? level.current.value : 0
    // Fast attack, slower release, so syllables read as pulses.
    s.level += (target - s.level) * (1 - Math.exp(-delta * (target > s.level ? 18 : 6)))
    for (const key of ['speed', 'spin', 'scale', 'amp', 'react', 'detail'] as const) {
      s[key] += (look[key] - s[key]) * k
    }
    s.time += delta * (s.speed + s.level * 1.5)

    const u = material.current?.uniforms
    if (u) {
      u.uTime.value = s.time
      u.uAmp.value = s.amp + s.level * s.react
      u.uDetail.value = s.detail
      u.uLevel.value = s.level * s.react // shared with the halo
      u.uCore.value.lerp(new THREE.Color(look.core), k)
      u.uRim.value.lerp(new THREE.Color(look.rim), k)
    }

    if (mesh.current) {
      mesh.current.rotation.y += delta * s.spin
      mesh.current.rotation.x += delta * s.spin * 0.35
      mesh.current.scale.setScalar(s.scale + s.level * s.react * 0.12)
    }
    if (halo.current) halo.current.scale.setScalar(s.scale * 1.35 + s.level * s.react * 0.25)
  })

  return (
    <>
      <mesh ref={halo}>
        <sphereGeometry args={[1, 48, 48]} />
        <shaderMaterial
          uniforms={haloUniforms}
          vertexShader={vertexShader.replace('#define DISPLACE 1', '#define DISPLACE 0')}
          fragmentShader={haloFragmentShader}
          side={THREE.BackSide}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      <mesh ref={mesh}>
        <icosahedronGeometry args={[1, 64]} />
        <shaderMaterial
          ref={material}
          uniforms={uniforms}
          vertexShader={vertexShader}
          fragmentShader={fragmentShader}
        />
      </mesh>
    </>
  )
}

/** Keeps the whole orb in view when the canvas is taller than wide (phones, open transcript). */
function FitCamera() {
  useFrame(({ camera, size }) => {
    camera.position.z = 4.2 / Math.min(1, size.width / size.height)
  })
  return null
}

export function Orb({ state, level }: { state: VoiceState; level: RefObject<Level> }) {
  return (
    <Canvas
      camera={{ position: [0, 0, 4.2], fov: 45 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
    >
      <FitCamera />
      <Blob state={state} level={level} />
    </Canvas>
  )
}
