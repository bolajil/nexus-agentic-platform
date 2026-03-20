'use client';
import { useEffect, useRef, useState } from 'react';

interface Props {
  url: string;
  className?: string;
}

export default function StlViewer({ url, className = '' }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const el = mountRef.current;
    if (!el) return;

    let animId: number;
    let disposed = false;

    (async () => {
      try {
        const THREE = await import('three');
        const { STLLoader } = await import('three/examples/jsm/loaders/STLLoader.js' as string);

        const w = el.clientWidth  || 640;
        const h = el.clientHeight || 400;

        // Scene
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x080814);

        // Grid
        const grid = new THREE.GridHelper(400, 20, 0x1a1a3e, 0x12122a);
        grid.position.y = -100;
        scene.add(grid);

        // Camera
        const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 500000);

        // Renderer
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        el.appendChild(renderer.domElement);

        // Lights
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

        // Load STL
        const loader = new (STLLoader as any)();
        loader.load(
          url,
          (geometry: THREE.BufferGeometry) => {
            if (disposed) return;

            geometry.computeVertexNormals();
            geometry.center();

            const material = new THREE.MeshPhongMaterial({
              color:     0x3355bb,
              specular:  0x99aaff,
              shininess: 80,
              transparent: true,
              opacity:   0.90,
              side: THREE.DoubleSide,
            });

            const mesh = new THREE.Mesh(geometry, material);
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            // Fit to view
            const box = new THREE.Box3().setFromObject(mesh);
            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);
            const scale = 180 / Math.max(maxDim, 1);
            mesh.scale.setScalar(scale);

            scene.add(mesh);

            // Position camera
            const dist = maxDim * scale * 1.6;
            camera.position.set(dist * 0.7, dist * 0.5, dist);
            camera.lookAt(0, 0, 0);

            // Drag to rotate
            let dragging = false;
            let lastX = 0;
            let lastY = 0;
            let rotY = 0.3;
            let rotX = -0.2;

            const onDown = (e: MouseEvent) => { dragging = true; lastX = e.clientX; lastY = e.clientY; };
            const onUp   = ()              => { dragging = false; };
            const onMove = (e: MouseEvent) => {
              if (!dragging) return;
              rotY += (e.clientX - lastX) * 0.008;
              rotX += (e.clientY - lastY) * 0.005;
              rotX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotX));
              lastX = e.clientX;
              lastY = e.clientY;
            };

            renderer.domElement.addEventListener('mousedown', onDown);
            window.addEventListener('mouseup', onUp);
            window.addEventListener('mousemove', onMove);

            setLoading(false);

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
            if (!disposed) setError(`Failed to load STL: ${String(err)}`);
            setLoading(false);
          }
        );

        return () => {
          disposed = true;
          cancelAnimationFrame(animId);
          renderer.dispose();
          if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
        };
      } catch (e) {
        setError(`3D viewer error: ${String(e)}`);
        setLoading(false);
      }
    })();

    return () => { disposed = true; cancelAnimationFrame(animId); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  return (
    <div className={`relative ${className}`} style={{ minHeight: 400 }}>
      {loading && !error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 bg-[#080814] rounded-xl z-10">
          <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-3" />
          <span className="text-xs">Loading 3D geometry…</span>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center text-red-400 text-xs bg-[#080814] rounded-xl z-10 p-4 text-center">
          {error}
        </div>
      )}
      <div ref={mountRef} className="w-full rounded-xl overflow-hidden" style={{ height: 400 }} />
    </div>
  );
}
