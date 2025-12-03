import React, { useRef, useEffect, useCallback } from 'react';

const SyncWave = ({ 
  width = 300, 
  height = 150, 
  amplitude = 0.5, 
  speed = 0.02,
  colorScheme = 'idle' // 'idle', 'bot', 'user'
}) => {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const phaseRef = useRef(0);
  const targetAmplitudeRef = useRef(amplitude);
  const currentAmplitudeRef = useRef(amplitude);

  // Color schemes - RGB colors that blend to white when overlapping
  const getColors = useCallback(() => {
    switch (colorScheme) {
      case 'bot':
        return [
          { r: 255, g: 200, b: 0, a: 0.9 },     // yellow
          { r: 255, g: 80, b: 0, a: 0.8 },      // orange-red
          { r: 255, g: 0, b: 80, a: 0.7 },      // red-magenta
        ];
      case 'user':
        return [
          { r: 0, g: 255, b: 120, a: 0.9 },     // green
          { r: 0, g: 200, b: 255, a: 0.8 },     // cyan
          { r: 80, g: 100, b: 255, a: 0.7 },    // blue
        ];
      default: // idle - complementary colors that mix to white
        return [
          { r: 255, g: 0, b: 100, a: 0.9 },     // magenta/pink
          { r: 0, g: 255, b: 200, a: 0.85 },    // cyan/turquoise  
          { r: 200, g: 100, b: 255, a: 0.8 },   // purple/violet
        ];
    }
  }, [colorScheme]);

  useEffect(() => {
    targetAmplitudeRef.current = amplitude;
  }, [amplitude]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const colors = getColors();
    
    // 5 waves: center, left, right, further left, further right
    // Each has different speed, phase delay, and max height for organic feel
    const waves = [
      { xOffset: 0, phaseDelay: 0, speedMultiplier: 1.0, colorIndex: 0, heightScale: 1.0 },        // center - tallest
      { xOffset: -30, phaseDelay: 0.5, speedMultiplier: 0.75, colorIndex: 1, heightScale: 0.85 },  // left 1
      { xOffset: 30, phaseDelay: 0.8, speedMultiplier: 0.7, colorIndex: 1, heightScale: 0.9 },     // right 1
      { xOffset: -60, phaseDelay: 1.3, speedMultiplier: 0.55, colorIndex: 2, heightScale: 0.7 },   // left 2 - shorter
      { xOffset: 60, phaseDelay: 1.6, speedMultiplier: 0.5, colorIndex: 2, heightScale: 0.75 },    // right 2
    ];

    const drawWave = (color, wave, phase, amp) => {
      const centerX = width / 2 + wave.xOffset;
      const centerY = height / 2;
      
      // Breathing effect - each wave has its own speed multiplier
      const breathPhase = (phase * wave.speedMultiplier) + wave.phaseDelay;
      const breathScale = 0.6 + 0.4 * Math.sin(breathPhase); // oscillates between 0.2 and 1.0
      const currentAmp = amp * breathScale;
      
      const maxWidth = width * 0.55; // wider lens shape
      // Apply individual height scale for each wave
      const maxHeight = (height / 2) * 0.85 * currentAmp * wave.heightScale;
      
      ctx.beginPath();
      
      // Draw lens/eye shape centered at centerX
      const steps = 100;
      
      // Top curve (left to right)
      for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const x = centerX - maxWidth / 2 + t * maxWidth;
        
        // Sine envelope for lens shape
        const envelope = Math.sin(t * Math.PI);
        const y = centerY - envelope * maxHeight;
        
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      
      // Bottom curve (right to left)
      for (let i = steps; i >= 0; i--) {
        const t = i / steps;
        const x = centerX - maxWidth / 2 + t * maxWidth;
        
        const envelope = Math.sin(t * Math.PI);
        const y = centerY + envelope * maxHeight;
        
        ctx.lineTo(x, y);
      }
      
      ctx.closePath();
      
      // Solid vibrant fill with subtle gradient for depth
      const gradient = ctx.createRadialGradient(
        centerX, centerY, 0,
        centerX, centerY, maxHeight * 1.2
      );
      // More solid colors - less fade
      gradient.addColorStop(0, `rgba(${Math.min(255, color.r + 30)}, ${Math.min(255, color.g + 30)}, ${Math.min(255, color.b + 30)}, ${color.a})`);
      gradient.addColorStop(0.5, `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a * 0.9})`);
      gradient.addColorStop(1, `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a * 0.7})`);
      
      ctx.fillStyle = gradient;
      ctx.fill();
    };

    const drawSupportLine = () => {
      const centerY = height / 2;
      
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.lineWidth = 1.5;
      ctx.moveTo(0, centerY);
      ctx.lineTo(width, centerY);
      ctx.stroke();
    };

    const animate = () => {
      // Smooth amplitude interpolation
      const lerpSpeed = 0.05;
      currentAmplitudeRef.current += (targetAmplitudeRef.current - currentAmplitudeRef.current) * lerpSpeed;
      
      // Update phase for breathing animation (slower)
      phaseRef.current += speed;
      
      // Clear canvas
      ctx.clearRect(0, 0, width, height);
      
      const currentColors = getColors();
      const amp = currentAmplitudeRef.current;
      const phase = phaseRef.current;
      
      // Draw support line first (behind waves)
      ctx.globalCompositeOperation = 'source-over';
      drawSupportLine();
      
      // Enable additive color blending - colors add up to white where they overlap
      ctx.globalCompositeOperation = 'lighter';
      
      // Draw waves from back to front (outer ones first)
      for (let i = waves.length - 1; i >= 0; i--) {
        const wave = waves[i];
        const color = currentColors[wave.colorIndex] || currentColors[0];
        drawWave(color, wave, phase, amp);
      }
      
      // Reset composite operation
      ctx.globalCompositeOperation = 'source-over';
      
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [width, height, speed, getColors]);

  return (
    <canvas 
      ref={canvasRef} 
      width={width} 
      height={height}
      style={{ display: 'block' }}
    />
  );
};

export default SyncWave;
