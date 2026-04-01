"use client";
/**
 * PCForge AI — Retro Particle Background
 * Canvas-based constellation with white + faint red nodes.
 * Sits at z-index 0, never occludes content.
 */
import { useEffect, useRef, useCallback } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  alpha: number;
  isRed: boolean;
  pulse: number;       // phase offset for pulsing red nodes
}

const LINK_DIST    = 110;   // max distance to draw a line
const RED_CHANCE   = 0.06;  // 6% of particles glow red
const SPEED_MAX    = 0.28;
const DENSITY      = 14000; // 1 particle per N px²

export default function ParticleCanvas() {
  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const animRef    = useRef<number>(0);
  const timeRef    = useRef<number>(0);

  const buildParticles = useCallback(
    (w: number, h: number): Particle[] => {
      const count = Math.max(30, Math.min(200, Math.floor((w * h) / DENSITY)));
      return Array.from({ length: count }, () => ({
        x:      Math.random() * w,
        y:      Math.random() * h,
        vx:     (Math.random() - 0.5) * SPEED_MAX * 2,
        vy:     (Math.random() - 0.5) * SPEED_MAX * 2,
        radius: Math.random() * 1.2 + 0.4,
        alpha:  Math.random() * 0.4 + 0.1,
        isRed:  Math.random() < RED_CHANCE,
        pulse:  Math.random() * Math.PI * 2,
      }));
    },
    []
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let particles: Particle[] = [];

    // ── Resize handler ───────────────────────────────────────────
    const resize = () => {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
      particles = buildParticles(canvas.width, canvas.height);
    };

    resize();
    const resizeHandler = () => resize();
    window.addEventListener("resize", resizeHandler);

    // ── Animation loop ───────────────────────────────────────────
    const draw = (ts: number) => {
      const dt = Math.min(ts - timeRef.current, 50); // cap at 50ms
      timeRef.current = ts;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const w = canvas.width;
      const h = canvas.height;

      // Move particles
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        // Wrap
        if (p.x < 0)  p.x = w;
        if (p.x > w)  p.x = 0;
        if (p.y < 0)  p.y = h;
        if (p.y > h)  p.y = 0;
        p.pulse += 0.012;
      }

      // Draw links (O(n²) — kept low by density cap)
      ctx.lineWidth = 0.4;
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b   = particles[j];
          const dx  = a.x - b.x;
          const dy  = a.y - b.y;
          const d2  = dx * dx + dy * dy;
          if (d2 > LINK_DIST * LINK_DIST) continue;

          const t     = 1 - Math.sqrt(d2) / LINK_DIST;
          const alpha = t * 0.12;

          if (a.isRed || b.isRed) {
            ctx.strokeStyle = `rgba(255, 40, 40, ${alpha * 1.5})`;
          } else {
            ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
          }

          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      // Draw particles
      for (const p of particles) {
        if (p.isRed) {
          // Pulsing red node
          const pAlpha = p.alpha * (0.7 + 0.3 * Math.sin(p.pulse));
          const pRad   = p.radius * (1 + 0.25 * Math.sin(p.pulse));

          // Outer glow
          const grd = ctx.createRadialGradient(
            p.x, p.y, 0,
            p.x, p.y, pRad * 4
          );
          grd.addColorStop(0, `rgba(255, 30, 30, ${pAlpha * 0.6})`);
          grd.addColorStop(1, "rgba(255, 0, 0, 0)");
          ctx.beginPath();
          ctx.arc(p.x, p.y, pRad * 4, 0, Math.PI * 2);
          ctx.fillStyle = grd;
          ctx.fill();

          // Core dot
          ctx.beginPath();
          ctx.arc(p.x, p.y, pRad, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255, 60, 60, ${pAlpha})`;
          ctx.fill();
        } else {
          // White particle
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`;
          ctx.fill();
        }
      }

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resizeHandler);
    };
  }, [buildParticles]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
        display: "block",
      }}
    />
  );
}
