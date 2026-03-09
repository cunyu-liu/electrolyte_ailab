import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

// Ensure `process` exists in browser env to avoid libs that reference process.env
if (typeof (window as any).process === 'undefined') {
  (window as any).process = { env: {} };
}

type MoleculeThreeViewerProps = {
  smilesList: string[];
  width?: number;
  height?: number;
  background?: string;
};

type Atom = { x: number; y: number; z: number; elem: string };
type Bond = { a: number; b: number; order: number };

const ELEMENT_COLOR: Record<string, number> = {
  H: 0xFFFFFF,
  C: 0x909090,
  N: 0x3050F8,
  O: 0xFF0D0D,
  F: 0x90E050,
  P: 0xFF8000,
  S: 0xFFFF30,
  CL: 0x1FF01F,
  BR: 0xA62929,
  I: 0x940094,
  HE: 0xD9FFFF,
  NE: 0xB3E3F5,
  AR: 0x80D1E3,
  LI: 0xCC80FF,
  NA: 0xAB5CF2,
  K: 0x8F40D4,
  MG: 0x8AFF00,
  CA: 0x3DFF00,
  FE: 0xE06633,
  CU: 0xC88033,
  ZN: 0x7D80B0,
  NI: 0x50D050,
  CO: 0xF090A0,
  B: 0xFFB5B5,
  SI: 0xDCDCDC,
  SE: 0xFFA100,
  TI: 0xBFC2C7,
  AU: 0xFFD700,
  AG: 0xC0C0C0,
  HG: 0xB8B8D0,
  PB: 0x575961,
  U: 0x008FFF,
};

const COVALENT_RADII: Record<string, number> = {
  H: 0.41,
  C: 0.76,
  N: 0.71,
  O: 0.66,
  F: 0.57,
  P: 1.07,
  S: 1.05,
  CL: 1.02,
  BR: 1.2,
  I: 1.39,
};

// Parse MOL/SDF block to atoms & bonds (simple parser, assumes standard V2000 mol block)
function parseSDF(sdf: string): { atoms: Atom[]; bonds: Bond[] } {
  const lines = sdf.split(/\r?\n/);
  // find counts line which usually is line 3 (0-indexed 3)
  // but be resilient: search for first line that matches counts pattern: "nnnmmm..."
  let countsLineIndex = -1;
  for (let i = 0; i < Math.min(lines.length, 20); i++) {
    const l = lines[i];
    if (/^\s*\d+\s+\d+\s+\d+/.test(l)) {
      countsLineIndex = i;
      break;
    }
  }
  if (countsLineIndex === -1) {
    throw new Error('Unable to find counts line in SDF');
  }
  const countsParts = lines[countsLineIndex].trim().split(/\s+/);
  const atomCount = parseInt(countsParts[0], 10);
  const bondCount = parseInt(countsParts[1], 10);

  const atoms: Atom[] = [];
  const bonds: Bond[] = [];

  const atomStart = countsLineIndex + 1;
  for (let i = 0; i < atomCount; i++) {
    const line = lines[atomStart + i];
    if (!line) continue;
    // atom line format: xxxxx.xxx yyyyy.yyy zzzzz.zzz elem ...
    const parts = line.trim().split(/\s+/);
    const x = parseFloat(parts[0]);
    const y = parseFloat(parts[1]);
    const z = parseFloat(parts[2]);
    let elem = parts[3] || '';
    elem = elem.replace(/[^A-Za-z]/g, '');
    atoms.push({ x, y, z, elem });
  }

  const bondStart = atomStart + atomCount;
  for (let i = 0; i < bondCount; i++) {
    const line = lines[bondStart + i];
    if (!line) continue;
    const parts = line.trim().split(/\s+/);
    const a = parseInt(parts[0], 10) - 1; // SDF is 1-indexed
    const b = parseInt(parts[1], 10) - 1;
    const order = parseInt(parts[2], 10);
    bonds.push({ a, b, order });
  }

  return { atoms, bonds };
}

// Create cylinder between two points
function createBondMesh(a: THREE.Vector3, b: THREE.Vector3, radius: number, material: THREE.Material) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const len = dir.length();
  const midpoint = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5);

  // Cylinder aligned to Y by default; compute quaternion to rotate
  const geom = new THREE.CylinderGeometry(radius, radius, len, 8, 1);
  const mesh = new THREE.Mesh(geom, material);

  mesh.position.copy(midpoint);

  const up = new THREE.Vector3(0, 1, 0);
  const quat = new THREE.Quaternion().setFromUnitVectors(up, dir.clone().normalize());
  mesh.setRotationFromQuaternion(quat);
  return mesh;
}

async function fetchSDFFromPubChem(smiles: string): Promise<string> {
  // PubChem PUG REST: /compound/smiles/{smiles}/SDF?record_type=3d
  const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/${encodeURIComponent(smiles)}/SDF?record_type=3d`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`PubChem request failed: ${res.status}`);
  const text = await res.text();
  return text;
}

const MoleculeThreeViewer: React.FC<MoleculeThreeViewerProps> = ({ smilesList, width = 600, height = 480, background = '#ffffff' }) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!mountRef.current) return;
    let mounted = true;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(background);
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 80);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    // Avoid direct references to encoding/toneMapping constants which may not be
    // exported by the installed three build in some bundler configs.
    // Leave defaults and adjust lights/materials for better appearance.
    renderer.setSize(width, height);
    mountRef.current.innerHTML = '';
    mountRef.current.appendChild(renderer.domElement);

    const hemi = new THREE.HemisphereLight(0xffffff, 0x111111, 0.6);
    scene.add(hemi);
    const key = new THREE.PointLight(0xffffff, 2.2);
    key.position.set(40, 90, 80);
    scene.add(key);
    const fill = new THREE.PointLight(0xffffff, 1.2);
    fill.position.set(-40, -30, 60);
    scene.add(fill);
    const back = new THREE.DirectionalLight(0xffffff, 0.8);
    back.position.set(20, 10, 50);
    scene.add(back);
    const ambientLow = new THREE.AmbientLight(0xffffff, 0.06);
    scene.add(ambientLow);

    const group = new THREE.Group();
    scene.add(group);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.autoRotate = false;

    let animId: number | undefined;

    const renderLoop = () => {
      controls.update();
      renderer.render(scene, camera);
      animId = requestAnimationFrame(renderLoop);
    };

    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth || width;
      const h = mountRef.current.clientHeight || height;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    (async () => {
      setLoading(true);
      setError(null);
      try {
        for (let i = 0; i < smilesList.length; i++) {
          const smiles = smilesList[i];
          let sdf = '';
          try {
            sdf = await fetchSDFFromPubChem(smiles);
          } catch (err) {
            console.warn('PubChem fetch failed for', smiles, err);
            // try without 3d record_type
            try {
              const fallback = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/${encodeURIComponent(smiles)}/SDF`;
              const r = await fetch(fallback);
              if (r.ok) sdf = await r.text();
            } catch (e) {
              throw err;
            }
          }

          if (!sdf) continue;

          // SDF can contain multiple molecule blocks separated by $$$$
          const blocks = sdf.split('\n$$$$');
          const block = blocks[0];
          const { atoms, bonds } = parseSDF(block);

          // create atom meshes
          const atomMeshes: THREE.Object3D[] = [];
          for (let ai = 0; ai < atoms.length; ai++) {
            const at = atoms[ai];
            const color = ELEMENT_COLOR[at.elem.toUpperCase()] ?? 0x888888;
            const radius = (COVALENT_RADII[at.elem.toUpperCase()] ?? 0.7) * 0.5; // scale down for view
            const geom = new THREE.SphereGeometry(radius, 32, 32);
            const threeColor = new THREE.Color(color);
            if (typeof (threeColor as any).convertSRGBToLinear === 'function') {
              (threeColor as any).convertSRGBToLinear();
            }
            const mat = new THREE.MeshStandardMaterial({ color: threeColor, roughness: 0.08, metalness: 0.04 });
            const m = new THREE.Mesh(geom, mat);
            m.position.set(at.x, at.y, at.z);
            atomMeshes.push(m);
            group.add(m);
          }

          // create bonds
          for (let bi = 0; bi < bonds.length; bi++) {
            const b = bonds[bi];
            const aPos = new THREE.Vector3(atoms[b.a].x, atoms[b.a].y, atoms[b.a].z);
            const bPos = new THREE.Vector3(atoms[b.b].x, atoms[b.b].y, atoms[b.b].z);
            const bondColor = new THREE.Color(0xCCCCCC);
            if (typeof (bondColor as any).convertSRGBToLinear === 'function') (bondColor as any).convertSRGBToLinear();
            const mat = new THREE.MeshStandardMaterial({ color: bondColor, roughness: 0.15, metalness: 0.02 });
            // single bond creates one cylinder; higher order bonds could be drawn as multi-cylinders offset slightly
            const bondMesh = createBondMesh(aPos, bPos, 0.12, mat);
            group.add(bondMesh);
          }

          // After adding molecule, center and scale
          // compute bounding box
          const bbox = new THREE.Box3().setFromObject(group);
          const size = new THREE.Vector3();
          bbox.getSize(size);
          const maxDim = Math.max(size.x, size.y, size.z);
          if (maxDim > 0) {
            const scale = 40 / maxDim;
            group.scale.setScalar(scale * (1 - i * 0.0));
            // center
            bbox.getCenter(size);
            group.position.set(-size.x * scale, -size.y * scale, -size.z * scale);
          }
        }

        if (!mounted) return;
        renderLoop();
      } catch (err: any) {
        console.error('Molecule render error', err);
        setError(String(err?.message || err));
      } finally {
        setLoading(false);
      }
    })();

    // cleanup
    return () => {
      mounted = false;
      if (animId) cancelAnimationFrame(animId);
      controls.dispose();
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      mountRef.current && (mountRef.current.innerHTML = '');
    };
  }, [smilesList.join('|')]);

  return (
    <div>
      <div ref={mountRef} style={{ width, height, border: '1px solid #ddd' }} />
      {loading && <div style={{ marginTop: 6 }}>加载中...</div>}
      {error && <div style={{ color: 'red', marginTop: 6 }}>{error}</div>}
    </div>
  );
};

export default MoleculeThreeViewer;
