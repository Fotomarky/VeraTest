"use client";

import { useEffect, useRef, useState } from "react";

export const SEGMENT_COLORS = [
  "#F5C518", // warm yellow
  "#4FC3F7", // sky blue
  "#81C784", // muted green
  "#FF8A65", // soft orange
  "#CE93D8", // lavender
];

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

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mediaQuery.matches) {
      setSkipped(true);
    }
  }, []);

  useEffect(() => {
    if (skipped) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let frameCount = 0;

    const scenarios = run?.scenarios || [];
    const segments = Array.from(new Set(scenarios.map((s: any) => s.segment)));
    
    // Group scenarios by segment to count agents per segment
    const agentsPerSegment: Record<string, number> = {};
    for (const s of scenarios) {
      agentsPerSegment[s.segment] = (agentsPerSegment[s.segment] || 0) + 1;
    }

    const agents = segments.map((segment: any, index) => ({
      id: index,
      segment,
      x: -20 - index * 15,
      y: 90 + (index - (segments.length - 1) / 2) * 15,
      baseY: 90 + (index - (segments.length - 1) / 2) * 15,
      color: SEGMENT_COLORS[index % SEGMENT_COLORS.length],
      state: "moving", // moving, paused, jumping, exited
      pauseFrames: 0,
      jumpFrame: 0,
      speed: 1.5,
      totalAgents: agentsPerSegment[segment] || 0,
      completedAgents: 0,
      exited: false,
    }));

    const obstacles = [
      { x: 120, y: 70, w: 15, h: 40 },
      { x: 220, y: 70, w: 15, h: 40 },
      { x: 340, y: 70, w: 15, h: 40 },
      { x: 460, y: 70, w: 15, h: 40 },
    ];

    const dots = new Set<number>();
    for (let x = 20; x <= 620; x += 18) {
      dots.add(x);
    }
    const eatenDots = new Set<number>();

    const render = () => {
      frameCount++;

      const simResults = run?.simulation_results || [];
      const completedBySegment: Record<string, number> = {};
      for (const res of simResults) {
        completedBySegment[res.scenario_segment] = (completedBySegment[res.scenario_segment] || 0) + 1;
      }

      ctx.fillStyle = "#2C2520";
      ctx.fillRect(0, 0, 640, 180);

      // Draw obstacles
      ctx.fillStyle = "#3D3530";
      for (const obs of obstacles) {
        ctx.fillRect(obs.x, obs.y, obs.w, obs.h);
      }

      // Draw dots
      ctx.fillStyle = "#6B5E55";
      for (const dotX of dots) {
        if (!eatenDots.has(dotX)) {
          ctx.beginPath();
          ctx.arc(dotX, 90, 4, 0, 2 * Math.PI);
          ctx.fill();
        }
      }

      // Update and draw agents
      let exitedCount = 0;
      for (const agent of agents) {
        if (agent.exited) {
          exitedCount++;
          continue;
        }

        agent.completedAgents = completedBySegment[agent.segment] || 0;
        const hasSomeResults = agent.completedAgents > 0;
        
        if (hasSomeResults && agent.totalAgents > 0) {
           agent.speed = 1.5 + (agent.completedAgents / agent.totalAgents) * 1.5; 
        }

        if (agent.state === "paused") {
          agent.pauseFrames--;
          if (agent.pauseFrames <= 0) {
            agent.state = "jumping";
            agent.jumpFrame = 0;
          }
        } else if (agent.state === "jumping") {
          agent.jumpFrame++;
          agent.x += agent.speed * 0.5; // Move forward during jump
          const progress = agent.jumpFrame / 20;
          agent.y = agent.baseY - Math.sin(Math.PI * progress) * 15;
          if (agent.jumpFrame >= 20) {
            agent.y = agent.baseY;
            agent.state = "moving";
          }
        } else if (agent.state === "moving") {
          agent.x += agent.speed;

          // Check obstacle collision
          for (let bIdx = 0; bIdx < obstacles.length; bIdx++) {
            if (bIdx % 3 !== agent.id % 3) continue;
            const obs = obstacles[bIdx];
            // Leading edge reaches block's left edge
            if (agent.x + 10 >= obs.x && agent.x + 10 < obs.x + agent.speed) {
              agent.state = "paused";
              agent.pauseFrames = 72; // 1.2s at 60fps
              agent.x = obs.x - 10;
              break;
            }
          }
        }

        // Eat dots
        for (const dotX of dots) {
          if (!eatenDots.has(dotX)) {
             const dx = agent.x - dotX;
             const dy = agent.y - 90;
             if (dx * dx + dy * dy < 100) {
               eatenDots.add(dotX);
             }
          }
        }

        if (agent.x > 650) {
           agent.exited = true;
           exitedCount++;
        }

        // Draw agent
        ctx.fillStyle = agent.color;
        ctx.beginPath();
        const isMoving = agent.state === "moving" || agent.state === "jumping";
        let mouthOpen = 0;
        if (isMoving) {
          const cycle = frameCount % 24;
          mouthOpen = cycle < 12 ? (cycle / 12) * 0.25 : ((24 - cycle) / 12) * 0.25;
        }
        
        ctx.arc(agent.x, agent.y, 10, mouthOpen * Math.PI, (2 - mouthOpen) * Math.PI);
        ctx.lineTo(agent.x, agent.y);
        ctx.fill();
      }

      // CRT effects
      ctx.fillStyle = "rgba(0, 0, 0, 0.03)";
      for (let i = 0; i < 180; i += 4) {
        ctx.fillRect(0, i, 640, 2);
      }

      // Vignette
      const gradient = ctx.createRadialGradient(320, 90, 150, 320, 90, 340);
      gradient.addColorStop(0, "rgba(0,0,0,0)");
      gradient.addColorStop(1, "rgba(0,0,0,0.5)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 640, 180);

      if (countRef.current) {
        countRef.current.innerText = `${exitedCount} / ${agents.length}`;
      }

      if (agents.length > 0 && exitedCount === agents.length) {
        setSkipped(true);
      } else {
        animationId = requestAnimationFrame(render);
      }
    };

    animationId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animationId);
  }, [skipped, run]);

  if (skipped) {
    return <>{fallback}</>;
  }

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
          style={{
            imageRendering: "pixelated",
            aspectRatio: "640/180",
          }}
        />
      </div>
      <p className="text-center text-xs text-neutral-400 mt-2 font-mono">
        Agents doing their job... <span ref={countRef}>0 / 0</span>
      </p>
    </div>
  );
}
