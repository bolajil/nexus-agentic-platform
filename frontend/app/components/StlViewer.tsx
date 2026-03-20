'use client';
import { useEffect, useRef, useState } from 'react';

interface Props {
  url: string;
  className?: string;
}

export default function StlViewer({ url, className = '' }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<'loading' | 'parsing' | 'ready' | 'error'>('loading');

  useEffect(() => {
    const el = mountRef.current;
    if (!el) return;

    let animId: number;
    let disposed = false;
    setStatus('loading');
    setError(null);

    (async () => {
      try {
        const THREE = await import('three');
        const { STLLoader } = await import('three/examples/jsm/loaders/STLLoader.js' as string);

        // Wait one frame so the DOM has computed layout
        await new Promise(r => requestAnimationFrame(r));
        if (disposed) return;

        const w = el.clientWidth  || 800;
        const h = 420;

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0b0b1a);

        const grid = new THREE.GridHelper(400, 20, 0x1a1a3e, 0x12122a);
        grid.position.y = -100;
        scene.add(grid);

        const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 500000);

        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        el.appendChild(renderer.domElement);

        scene.add(new THREE.AmbientLight(0x334466, 3));
        const key = new THREE.DirectionalLight(0x6688cc, 4);
        key.position.set(200, 300, 200);
        key.castShadow = true;
        scene.add(key);
        const fill = new THREE.DirectionalLight(0x4455aa, 2);
        fill.position.set(-200, 100, -150);
        scene.add(fill);
        const rim = new THREE.DirectionalLight(0x8899ff, 1.5);
        rim.position.set(0, -200, -200);
        scene.add(rim);

        setStatus('parsing');

        const loader = new (STLLoader as any)();
        loader.load(
          url,
          (geometry: import('three').BufferGeometry) => {
            if (disposed) return;

            geometry.computeVertexNormals();
            geometry.center();

            const material = new THREE.MeshPhongMaterial({
              color:     0x3366cc,
              specular:  0x99aaff,
              shininess: 80,
              side: THREE.DoubleSide,
            });

            const mesh = new THREE.Mesh(geometry, material);
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            const box = new THREE.Box3().setFromObject(mesh);
            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z, 1);
            const scale = 180 / maxDim;
            mesh.scale.setScalar(scale);
            scene.add(mesh);

            const dist = maxDim * scale * 1.8;
            camera.position.set(dist * 0.7, dist * 0.5, dist);
            camera.lookAt(0, 0, 0);

            let dragging = false, lastX = 0, lastY = 0;
            let rotY = 0.3, rotX = -0.2;

            const onDown = (e: MouseEvent) => { dragging = true; lastX = e.clientX; lastY = e.clientY; };
            const onUp   = ()              => { dragging = false; };
            const onMove = (e: MouseEvent) => {
              if (!dragging) return;
              rotY += (e.clientX - lastX) * 0.008;
              rotX += (e.clientY - lastY) * 0.005;
              rotX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotX));
              lastX = e.clientX; lastY = e.clientY;
            };
            renderer.domElement.addEventListener('mousedown', onDown);
            window.addEventListener('mouseup', onUp);
            window.addEventListener('mousemove', onMove);

            setStatus('ready');

            const animate = () => {
              animId = requestAnimationFrame(animate);
              if (!dragging) rotY += 0.004;
              mesh.rotation.y = rotY;
              mesh.rotation.x = rotX;
              renderer.render(scene, camera);
            };
            animate();
          },
          undefined,
          (err: unknown) => {
            if (!disposed) {
              setError(`Failed to load STL: ${String(err)}`);
              setStatus('error');
            }
          }
        );

        return () => {
          disposed = true;
          cancelAnimationFrame(animId);
          renderer.dispose();
          if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
        };
      } catch (e) {
        if (!disposed) {
          setError(`3D viewer error: ${String(e)}`);
          setStatus('error');
        }
      }
    })();

    return () => { disposed = true; cancelAnimationFrame(animId); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  return (
    <div className={`relative ${className}`} style={{ height: 420 }}>
      {status === 'loading' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#0b0b1a] rounded-xl z-10">
          <div className="w-10 h-10 border-2 border-indigo-500/30 border-t-indigo-400 rounded-full animate-spin" />
          <span className="text-sm text-slate-300 font-medium">Fetching geometry…</span>
        </div>
      )}
      {status === 'parsing' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#0b0b1a] rounded-xl z-10">
          <div className="w-10 h-10 border-2 border-purple-500/30 border-t-purple-400 rounded-full animate-spin" />
          <span className="text-sm text-slate-300 font-medium">Parsing mesh — large files may take a moment…</span>
          <span className="text-xs text-slate-500">STL loaded · building scene</span>
        </div>
      )}
      {status === 'error' && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0b0b1a] rounded-xl z-10 p-6 text-center">
          <div>
            <div className="text-red-400 text-sm font-medium mb-1">3D viewer failed</div>
            <div className="text-slate-500 text-xs">{error}</div>
          </div>
        </div>
      )}
      <div ref={mountRef} className="w-full rounded-xl overflow-hidden" style={{ height: 420 }} />
    </div>
  );
}
