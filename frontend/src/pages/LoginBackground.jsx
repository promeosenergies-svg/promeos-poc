/**
 * PROMEOS — LoginBackground
 * Composant purement visuel : canvas particles + SVG skyline avec flux lumineux.
 * Aucune logique metier. Decoratif uniquement.
 */
import { useRef, useEffect } from 'react';
import './LoginBackground.css';

// ── Buildings data ──────────────────────────────────────────
const BUILDINGS_LEFT = [
  { x: 40, y: 130, w: 75, h: 170, fill: ['#1e4470', '#15325a'] },
  { x: 145, y: 85, w: 100, h: 215, fill: ['#224b7a', '#193d65'] },
  { x: 278, y: 155, w: 60, h: 145, fill: ['#1e4470', '#15325a'] },
  { x: 380, y: 180, w: 48, h: 120, fill: ['#224b7a', '#193d65'] },
];
const BUILDINGS_RIGHT = [
  { x: 750, y: 110, w: 85, h: 190, fill: ['#1e4470', '#15325a'] },
  { x: 870, y: 65, w: 110, h: 235, fill: ['#224b7a', '#193d65'] },
  { x: 1015, y: 140, w: 65, h: 160, fill: ['#1e4470', '#15325a'] },
  { x: 1110, y: 175, w: 50, h: 125, fill: ['#224b7a', '#193d65'] },
];
const ALL_BUILDINGS = [...BUILDINGS_LEFT, ...BUILDINGS_RIGHT];

// ── Windows grid for a building ─────────────────────────────
function buildingWindows(b, idx) {
  const windows = [];
  const cols = Math.max(2, Math.floor(b.w / 18));
  const rows = Math.max(3, Math.floor(b.h / 22));
  const ww = 6,
    wh = 8;
  const gapX = (b.w - cols * ww) / (cols + 1);
  const gapY = (b.h - rows * wh) / (rows + 1);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const wx = b.x + gapX + c * (ww + gapX);
      const wy = b.y + gapY + r * (wh + gapY);
      // Deterministic pseudo-random: some windows lit, most dark
      const seed = (idx * 97 + r * 13 + c * 7) % 10;
      const lit = seed < 3;
      windows.push(
        <rect
          key={`w-${idx}-${r}-${c}`}
          x={wx}
          y={wy}
          width={ww}
          height={wh}
          rx="1"
          fill={lit ? '#2dd4bf' : '#1a3d65'}
          opacity={lit ? 0.12 + (seed % 3) * 0.09 : 0.9}
        />
      );
    }
  }
  return windows;
}

// ── Connection lines between adjacent rooftops ──────────────
function buildConnections() {
  const rooftops = ALL_BUILDINGS.map((b) => ({ cx: b.x + b.w / 2, cy: b.y }));
  const connections = [];
  const particles = [];

  // Connect adjacent buildings (left group, right group, and cross)
  const pairs = [
    [0, 1],
    [1, 2],
    [2, 3], // left group
    [4, 5],
    [5, 6],
    [6, 7], // right group
    [3, 4], // cross (left-to-right)
  ];

  pairs.forEach(([a, b], i) => {
    const p1 = rooftops[a];
    const p2 = rooftops[b];
    const gradId = i % 2 === 0 ? 'glow-teal' : 'glow-cyan';
    const dur = 3 + (i % 3);
    const particleDur = 4 + (i % 3);
    const particleColor = i % 2 === 0 ? '#2dd4bf' : '#38bdf8';
    const pathId = `conn-path-${i}`;
    const pathD = `M${p1.cx},${p1.cy} L${p2.cx},${p2.cy}`;

    connections.push(
      <g key={`conn-${i}`}>
        <path id={pathId} d={pathD} fill="none" />
        <line
          className="connection-line"
          x1={p1.cx}
          y1={p1.cy}
          x2={p2.cx}
          y2={p2.cy}
          stroke={`url(#${gradId})`}
          strokeWidth="1.5"
          style={{ animationDuration: `${dur}s`, animationDelay: `${i * 0.4}s` }}
        />
      </g>
    );

    particles.push(
      <circle key={`particle-${i}`} r={1.8 + (i % 3) * 0.35} fill={particleColor}>
        <animateMotion dur={`${particleDur}s`} repeatCount="indefinite">
          <mpath href={`#${pathId}`} />
        </animateMotion>
        <animate
          attributeName="opacity"
          values="0;0.9;0"
          dur={`${particleDur}s`}
          repeatCount="indefinite"
        />
      </circle>
    );
  });

  return { connections, particles };
}

// ── Rooftop glowing nodes ───────────────────────────────────
function rooftopNodes() {
  return ALL_BUILDINGS.map((b, i) => {
    const cx = b.x + b.w / 2;
    const cy = b.y;
    const color = i % 2 === 0 ? '#2dd4bf' : '#38bdf8';
    const r = 2.5 + (i % 3) * 0.75;
    return (
      <circle
        key={`node-${i}`}
        className="rooftop-node"
        cx={cx}
        cy={cy}
        r={r}
        fill={color}
        style={{ animationDelay: `${i * 0.3}s` }}
      />
    );
  });
}

// ── Canvas Particles Hook ───────────────────────────────────
function useParticles(canvasRef) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let animId;
    let particles = [];
    const PARTICLE_COUNT = 35;
    const COLORS = ['45,212,191', '56,189,248']; // teal, cyan

    function resize() {
      canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
      canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
      ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    }

    function initParticles() {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      particles = [];
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push({
          x: Math.random() * w,
          y: Math.random() * h * 0.65,
          vx: (Math.random() - 0.5) * 0.25,
          vy: (Math.random() - 0.5) * 0.12,
          r: Math.random() * 1.2 + 0.4,
          opacity: Math.random() * 0.15 + 0.03,
          color: COLORS[i % 2],
        });
      }
    }

    function draw() {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      ctx.clearRect(0, 0, w, h);

      // Connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 140) {
            const alpha = 0.06 * (1 - dist / 140);
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(45,212,191,${alpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      // Particles
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;

        // Bounce within bounds
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h * 0.65) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${p.color},${p.opacity})`;
        ctx.fill();
      }

      animId = requestAnimationFrame(draw);
    }

    resize();
    initParticles();
    draw();

    const handleResize = () => {
      resize();
      initParticles();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
    };
  }, [canvasRef]);
}

// ── Main Component ──────────────────────────────────────────
export default function LoginBackground() {
  const canvasRef = useRef(null);
  useParticles(canvasRef);

  const { connections, particles: movingParticles } = buildConnections();

  return (
    <div className="login-bg" aria-hidden="true">
      {/* Canvas particles */}
      <canvas ref={canvasRef} className="login-bg__canvas" />

      {/* SVG Skyline */}
      <div className="login-bg__skyline">
        <svg viewBox="0 0 1200 300" preserveAspectRatio="xMidYMax slice">
          <defs>
            {/* Building gradients */}
            {ALL_BUILDINGS.map((b, i) => (
              <linearGradient key={`bg-${i}`} id={`building-${i}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={b.fill[0]} />
                <stop offset="100%" stopColor={b.fill[1]} />
              </linearGradient>
            ))}
            {/* Glow gradients for connection lines */}
            <linearGradient id="glow-teal" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0" />
              <stop offset="50%" stopColor="#2dd4bf" stopOpacity="0.7" />
              <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="glow-cyan" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0" />
              <stop offset="50%" stopColor="#38bdf8" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Ground line */}
          <rect x="0" y="298" width="1200" height="2" fill="#1a3358" />

          {/* Buildings */}
          {ALL_BUILDINGS.map((b, i) => (
            <g key={`b-${i}`}>
              <rect
                x={b.x}
                y={b.y}
                width={b.w}
                height={300 - b.y}
                fill={`url(#building-${i})`}
                stroke="#2a5a8a"
                strokeWidth="0.7"
                rx="2"
              />
              {buildingWindows(b, i)}
            </g>
          ))}

          {/* Connection lines */}
          {connections}

          {/* Rooftop nodes */}
          {rooftopNodes()}

          {/* Moving particles on connections */}
          {movingParticles}
        </svg>
      </div>
    </div>
  );
}
