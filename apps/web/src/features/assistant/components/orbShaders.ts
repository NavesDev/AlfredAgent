// Ashima/Stefan Gustavson 3D simplex noise (MIT).
const noise = /* glsl */ `
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 1.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute(permute(permute(
    i.z + vec4(0.0, i1.z, i2.z, 1.0)) +
    i.y + vec4(0.0, i1.y, i2.y, 1.0)) +
    i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}
`

export const vertexShader = /* glsl */ `
#define DISPLACE 1
uniform float uTime;
uniform float uAmp;
uniform float uDetail;
varying vec3 vNormal;
varying vec3 vView;
varying float vDisp;
${noise}

float field(vec3 p) {
  return snoise(p * uDetail + vec3(0.0, uTime * 0.6, uTime * 0.3)) * 0.7
       + snoise(p * uDetail * 2.3 - uTime * 0.4) * 0.3;
}

void main() {
  vec3 pos = position;
  vec3 n = normal;
#if DISPLACE
  float d = field(normal);
  pos += normal * d * uAmp;
  vDisp = d;
  // Re-derive the normal from neighbouring displaced points so lighting follows the bumps.
  vec3 t = normalize(cross(normal, abs(normal.y) < 0.99 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
  vec3 b = cross(normal, t);
  float e = 0.02;
  vec3 pt = normalize(normal + t * e);
  vec3 pb = normalize(normal + b * e);
  vec3 at = pt * (1.0 + field(pt) * uAmp);
  vec3 ab = pb * (1.0 + field(pb) * uAmp);
  n = normalize(cross(at - pos, ab - pos));
#else
  vDisp = 0.0;
#endif
  vec4 mv = modelViewMatrix * vec4(pos, 1.0);
  vNormal = normalize(normalMatrix * n);
  vView = normalize(-mv.xyz);
  gl_Position = projectionMatrix * mv;
}
`

export const fragmentShader = /* glsl */ `
uniform vec3 uCore;
uniform vec3 uRim;
uniform float uLevel;
varying vec3 vNormal;
varying vec3 vView;
varying float vDisp;

void main() {
  float fres = pow(1.0 - max(dot(vNormal, vView), 0.0), 2.2);
  float light = max(dot(vNormal, normalize(vec3(0.4, 0.7, 0.6))), 0.0);
  vec3 col = mix(uCore, uRim, smoothstep(-0.6, 0.9, vDisp) * 0.55);
  col += uRim * light * 0.25;
  col += uRim * fres * (1.1 + uLevel * 1.5);
  gl_FragColor = vec4(col, 1.0);
}
`

export const haloFragmentShader = /* glsl */ `
uniform vec3 uRim;
uniform float uLevel;
varying vec3 vNormal;
varying vec3 vView;
varying float vDisp;

void main() {
  float glow = pow(max(-dot(vNormal, vView), 0.0), 3.0);
  gl_FragColor = vec4(uRim, glow * (0.35 + uLevel * 0.6));
}
`
