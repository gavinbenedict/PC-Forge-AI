"use client";
/**
 * PCForge AI — Retro Particle Background
 * Canvas-based constellation with theme-aware colors.
 * Dark mode: white nodes + faint red accents.
 * Light mode: dark nodes (subtle, not distracting) + warm red accents.
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
  pulse: number;
}

const LINK_DIST    = 110;
const RED_CHANCE   = 0.06;
const SPEED_MAX    = 0.28;
const DENSITY      = 14000;

export default function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef   = useRef<number>(0);
  const timeRef   = useRef<number>(0);

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

    const resize = () => {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
      particles = buildParticles(canvas.width, canvas.height);
    };

    resize();
    const resizeHandler = () => resize();
    window.addEventListener("resize", resizeHandler);

    const draw = (ts: number) => {
      const dt = Math.min(ts - timeRef.current, 50);
      timeRef.current = ts;

      ctx.clearRect(0, 0, canvas.width, canvas.height);


      const w = canvas.width;
      const h = canvas.height;

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;
        p.pulse += 0.012;
      }

      // ── Theme helpers — called per-draw so toggle is instant ──
      const getTheme = () =>
        document.documentElement.getAttribute("data-theme") || "dark";

      const getNodeColor = (alpha: number) => {
        return getTheme() === "dark"
          ? `rgba(255,255,255,${(alpha * 0.35).toFixed(3)})`
          : `rgba(0,0,0,${(alpha * 0.12).toFixed(3)})`;
      };

      const getLinkColor = (alpha: number, isRedLink: boolean) => {
        if (isRedLink) {
          const r = getTheme() === "dark" ? "255,40,40" : "220,60,30";
          return `rgba(${r},${(alpha * (getTheme() === "dark" ? 0.18 : 0.12)).toFixed(3)})`;
        }
        return getTheme() === "dark"
          ? `rgba(255,255,255,${(alpha * 0.12).toFixed(3)})`
          : `rgba(0,0,0,${(alpha * 0.08).toFixed(3)})`;
      };

      const getRedColor = (alpha: number) => {
        const r = getTheme() === "dark" ? "255,40,40" : "220,60,30";
        return `rgba(${r},${alpha.toFixed(3)})`;
      };

      // Draw links
      ctx.lineWidth = 0.4;
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b  = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 > LINK_DIST * LINK_DIST) continue;

          const t     = 1 - Math.sqrt(d2) / LINK_DIST;
          ctx.strokeStyle = getLinkColor(t, a.isRed || b.isRed);
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      // Draw particles — color computed per particle so theme switch is instant
      for (const p of particles) {
        if (p.isRed) {
          const pAlpha = p.alpha * (0.7 + 0.3 * Math.sin(p.pulse));
          const pRad   = p.radius * (1 + 0.25 * Math.sin(p.pulse));

          // Outer glow
          const grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, pRad * 4);
          grd.addColorStop(0, getRedColor(pAlpha * 0.6));
          grd.addColorStop(1, getRedColor(0));
          ctx.beginPath();
          ctx.arc(p.x, p.y, pRad * 4, 0, Math.PI * 2);
          ctx.fillStyle = grd;
          ctx.fill();

          // Core dot
          ctx.beginPath();
          ctx.arc(p.x, p.y, pRad, 0, Math.PI * 2);
          ctx.fillStyle = getRedColor(pAlpha);   // computed per particle
          ctx.fill();
        } else {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
          ctx.fillStyle = getNodeColor(p.alpha);  // computed per particle
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
