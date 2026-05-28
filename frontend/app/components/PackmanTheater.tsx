"use client";

import { useEffect, useRef, useState } from "react";

export const SEGMENT_COLORS = [
  "#F5C518",
  "#4FC3F7",
  "#81C784",
  "#FF8A65",
  "#CE93D8",
];

type Agent = {
  id: number;
  segment: string;
  x: number;
  y: number;
  baseY: number;
  color: string;
  state: "moving" | "paused" | "jumping" | "exited";
  pauseFrames: number;
  jumpFrame: number;
  speed: number;
  totalAgents: number;
  exited: boolean;
};

const OBSTACLES = [
  { x: 120, y: 70, w: 15, h: 40 },
  { x: 220, y: 70, w: 15, h: 40 },
  { x: 340, y: 70, w: 15, h: 40 },
  { x: 460, y: 70, w: 15, h: 40 },
];

const ALL_DOTS: number[] = [];
for (let x = 20; x <= 620; x += 18) ALL_DOTS.push(x);

const MAP_0 = [
  "    HHHHHHHH    ",
  "    HHHHHHHH    ",
  "   HHHHHHHHHH   ",
  "    SSSSSSSS    ",
  "    SSSSSSSS    ",
  "    SSSSSSSS    ",
  "   SSSSSSSSSS   ",
  "   JJJWWJJJJJ   ",
  "   JJJJJJJJJJ   ",
  "   JJJJJJJJJJ   ",
  "  JJJJJJJJJJJJ  ",
  "  JJJJJJJJJJJJ  ",
  "  JJJJJJJJJJJJ  ",
  "   PPPP  PPPP   ",
  "   PPPP  PPPP   ",
  "   PPPP  PPPP   ",
  "   PPPP  PPPP   ",
  "   BBBB  BBBB   ",
  "   BBBB  BBBB   ",
  "  BBBBB  BBBBB  ",
];

const MAP_1 = [
  "    HHHHHHHH    ",
  "    HHHHHHHH    ",
  "   HHHHHHHHHH   ",
  "    SSSSSSSS    ",
  "    SSSSSSSS    ",
  "    SSSSSSSS    ",
  "   SSSSSSSSSS   ",
  "   JJJWWJJJJJ   ",
  "   JJJJJJJJJJ   ",
  "   JJJJJJJJJJ   ",
  "  JJJJJJJJJJJJ  ",
  "  JJJJJJJJJJJJ  ",
  "  JJJJJJJJJJJJ  ",
  "     PPPPPP     ",
  "     PPPPPP     ",
  "     PPPPPP     ",
  "     PPPPPP     ",
  "     BBBBBB     ",
  "     BBBBBB     ",
  "    BBBBBBBB    ",
];

function drawAgent(ctx: CanvasRenderingContext2D, x: number, y: number, color: string, frame: number) {
  const map = frame === 0 ? MAP_0 : MAP_1;
  const colors: Record<string, string> = {
    'H': '#5C3A1E',
    'S': '#F5CBA7',
    'J': color,
    'W': '#FFFFFF',
    'P': '#2C3E50',
    'B': '#1A1A1A'
  };

  const startX = Math.floor(x - 8);
  const startY = Math.floor(y - 10);

  for (let row = 0; row < 20; row++) {
    for (let col = 0; col < 16; col++) {
      const char = map[row][col];
      if (char !== ' ') {
        ctx.fillStyle = colors[char];
        ctx.fillRect(startX + col, startY + row, 1, 1);
      }
    }
  }
}

export default function PackmanTheater({
  run,
  fallback,
}: {
  run: any;
  fallback: React.ReactNode;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const countRef = useRef<HTMLSpanElement>(null);
  const [skipped, setSkipped] = useState(false);

  // Mutable refs — reading these inside the render loop never restarts the animation
  const runRef = useRef<any>(run);
  const agentsRef = useRef<Agent[]>([]);
  const eatenDotsRef = useRef<Set<number>>(new Set());

  // Keep runRef current and initialise agents once when scenarios arrive
  useEffect(() => {
    runRef.current = run;

    if (agentsRef.current.length === 0 && run?.scenarios?.length > 0) {
      const scenarios: any[] = run.scenarios;
      const segments: string[] = Array.from(new Set(scenarios.map((s) => s.segment as string)));
      const agentsPerSeg: Record<string, number> = {};
      for (const s of scenarios) {
        agentsPerSeg[s.segment] = (agentsPerSeg[s.segment] || 0) + 1;
      }
      agentsRef.current = segments.map((segment, index) => ({
        id: index,
        segment,
        x: -20 - index * 15,
        y: 90 + (index - (segments.length - 1) / 2) * 15,
        baseY: 90 + (index - (segments.length - 1) / 2) * 15,
        color: SEGMENT_COLORS[index % SEGMENT_COLORS.length],
        state: "moving",
        pauseFrames: 0,
        jumpFrame: 0,
        speed: 1.5,
        totalAgents: agentsPerSeg[segment] || 0,
        exited: false,
      }));
    }
  }, [run]);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) setSkipped(true);
  }, []);

  // Animation loop — depends only on skipped, reads live data via refs
  useEffect(() => {
    if (skipped) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let frame = 0;

    const render = () => {
      frame++;
      const agents = agentsRef.current;
      const eatenDots = eatenDotsRef.current;
      const currentRun = runRef.current;

      // Completion counts from latest run data
      const simResults: any[] = currentRun?.simulation_results || [];
      const completedBySeg: Record<string, number> = {};
      for (const r of simResults) {
        completedBySeg[r.scenario_segment] = (completedBySeg[r.scenario_segment] || 0) + 1;
      }

      // Background
      ctx.fillStyle = "#2C2520";
      ctx.fillRect(0, 0, 640, 180);

      // Obstacles
      ctx.fillStyle = "#3D3530";
      for (const o of OBSTACLES) ctx.fillRect(o.x, o.y, o.w, o.h);

      // Dots
      ctx.fillStyle = "#6B5E55";
      for (const dotX of ALL_DOTS) {
        if (!eatenDots.has(dotX)) {
          ctx.beginPath();
          ctx.arc(dotX, 90, 4, 0, 2 * Math.PI);
          ctx.fill();
        }
      }

      let exitedCount = 0;
      for (const agent of agents) {
        if (agent.exited) { exitedCount++; continue; }

        const completed = completedBySeg[agent.segment] || 0;
        if (completed > 0 && agent.totalAgents > 0) {
          agent.speed = 1.5 + (completed / agent.totalAgents) * 1.5;
        }

        if (agent.state === "paused") {
          agent.pauseFrames--;
          if (agent.pauseFrames <= 0) { agent.state = "jumping"; agent.jumpFrame = 0; }
        } else if (agent.state === "jumping") {
          agent.jumpFrame++;
          agent.x += agent.speed * 0.5;
          agent.y = agent.baseY - Math.sin(Math.PI * (agent.jumpFrame / 20)) * 15;
          if (agent.jumpFrame >= 20) { agent.y = agent.baseY; agent.state = "moving"; }
        } else if (agent.state === "moving") {
          agent.x += agent.speed;
          for (let bi = 0; bi < OBSTACLES.length; bi++) {
            if (bi % 3 !== agent.id % 3) continue;
            const o = OBSTACLES[bi];
            if (agent.x + 10 >= o.x && agent.x + 10 < o.x + agent.speed + 1) {
              agent.state = "paused";
              agent.pauseFrames = 72;
              agent.x = o.x - 10;
              break;
            }
          }
        }

        // Eat dots
        for (const dotX of ALL_DOTS) {
          if (!eatenDots.has(dotX)) {
            const dx = agent.x - dotX;
            const dy = agent.y - 90;
            if (dx * dx + dy * dy < 100) eatenDots.add(dotX);
          }
        }

        if (agent.x > 650) { agent.exited = true; exitedCount++; }

        // Draw Agent
        let currentFrame = 0;
        if (agent.state === "jumping") {
          currentFrame = 1;
        } else if (agent.state === "moving") {
          currentFrame = Math.floor(frame / 6) % 2;
        }
        drawAgent(ctx, agent.x, agent.y, agent.color, currentFrame);
      }

      // CRT scanlines
      ctx.fillStyle = "rgba(0,0,0,0.03)";
      for (let i = 0; i < 180; i += 4) ctx.fillRect(0, i, 640, 2);

      // Vignette
      const g = ctx.createRadialGradient(320, 90, 150, 320, 90, 340);
      g.addColorStop(0, "rgba(0,0,0,0)");
      g.addColorStop(1, "rgba(0,0,0,0.5)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, 640, 180);

      if (countRef.current) {
        const total = Math.max(agents.length, 1);
        countRef.current.innerText = `${exitedCount} / ${total}`;
      }

      if (agents.length > 0 && exitedCount === agents.length) {
        setSkipped(true);
      } else {
        animId = requestAnimationFrame(render);
      }
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [skipped]); // run intentionally excluded — read via runRef

  if (skipped) return <>{fallback}</>;

  return (
    <div className="w-full max-w-[640px] mx-auto">
      <div className="relative rounded-lg overflow-hidden border-2 border-neutral-700 bg-[#2C2520]">
        <div className="absolute top-0 right-0 p-2 z-10">
          <button
            onClick={() => setSkipped(true)}
            className="pointer-events-auto px-2 py-1 bg-black/50 hover:bg-black/80 text-white border border-white/20 text-[10px] font-mono rounded"
          >
            SKIP ANIMATION
          </button>
        </div>
        <canvas
          ref={canvasRef}
          width={640}
          height={180}
          className="w-full h-auto block"
          style={{ imageRendering: "pixelated", aspectRatio: "640/180" }}
        />
      </div>
      <p className="text-center text-xs text-neutral-400 mt-2 font-mono">
        Agents doing their job… <span ref={countRef}>0 / 0</span>
      </p>
    </div>
  );
}
