/*
 * Royal Venue — hero fireflies
 * Soft golden bokeh dots that drift, twinkle and scatter away from the cursor.
 * Colours are read from the site's CSS variables (--gold-bright, --gold, --cream),
 * so they always match the theme.
 */
(() => {
  'use strict';

  const hero = document.querySelector('.hero');
  const canvas = hero && hero.querySelector('.hero__fireflies');
  const ctx = canvas && canvas.getContext('2d');
  if (!hero || !canvas || !ctx) return;

  /* ---------- Easy settings (tweak these) ---------- */
  const DENSITY = 15000;      // bigger number = fewer dots (px² of hero per dot)
  const MIN_DOTS = 26;
  const MAX_DOTS = 90;
  const HOVER_RADIUS = [110, 190]; // [min, max] px, scales with hero width
  const PUSH_STRENGTH = 1800; // how hard the cursor scatters dots
  const SWIRL_STRENGTH = 380; // sideways curl, makes the motion feel alive
  /* ------------------------------------------------- */

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const css = getComputedStyle(document.documentElement);

  const hexToRgb = (value, fallback) => {
    const hex = (value || '').trim().replace('#', '');
    if (!/^[0-9a-f]{6}$/i.test(hex)) return fallback;
    return [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
  };

  // pull the cream towards gold so it glows warm instead of looking grey
  const warm = ([r, g, b]) => [r, Math.round(g * 0.93), Math.round(b * 0.72)];

  const PALETTE = [
    { rgb: hexToRgb(css.getPropertyValue('--gold-bright'), [219, 189, 128]), weight: 6 },
    { rgb: hexToRgb(css.getPropertyValue('--gold'), [193, 163, 107]), weight: 3 },
    { rgb: warm(hexToRgb(css.getPropertyValue('--cream'), [244, 240, 232])), weight: 1 },
  ];

  // One pre-rendered soft glowing disc per colour (much cheaper than gradients every frame).
  const makeSprite = ([r, g, b]) => {
    const size = 128;
    const c = document.createElement('canvas');
    c.width = c.height = size;
    const x = c.getContext('2d');
    const grad = x.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    grad.addColorStop(0, 'rgba(255,248,222,1)');
    grad.addColorStop(0.25, `rgba(${r},${g},${b},1)`);
    grad.addColorStop(0.5, `rgba(${r},${g},${b},0.92)`);
    grad.addColorStop(0.66, `rgba(${r},${g},${b},0.34)`);
    grad.addColorStop(1, `rgba(${r},${g},${b},0)`);
    x.fillStyle = grad;
    x.fillRect(0, 0, size, size);
    return c;
  };
  PALETTE.forEach((p) => { p.sprite = makeSprite(p.rgb); });

  const totalWeight = PALETTE.reduce((s, p) => s + p.weight, 0);
  const pickColour = () => {
    let n = Math.random() * totalWeight;
    for (const p of PALETTE) { if ((n -= p.weight) <= 0) return p.sprite; }
    return PALETTE[0].sprite;
  };

  const rand = (a, b) => a + Math.random() * (b - a);

  let w = 0;
  let h = 0;
  let dots = [];
  const mouse = { x: 0, y: 0, on: false };
  const parallax = { x: 0, y: 0 }; // smoothed cursor offset from centre

  const createDot = (spread = true) => {
    const roll = Math.random();
    // mostly tiny sparks, some medium dots, a few big soft bokeh circles
    const size = roll < 0.45 ? rand(1.1, 2.6) : roll < 0.8 ? rand(4, 9) : rand(10, 24);
    const depth = Math.min(1, 0.35 + size / 22);
    return {
      x: rand(0, w),
      y: spread ? rand(0, h) : h + size * 2,
      r: size,
      depth,
      sprite: pickColour(),
      alpha: size > 9 ? rand(0.5, 0.8) : rand(0.8, 1),
      ang: rand(0, Math.PI * 2),
      speed: rand(5, 18) * (0.6 + depth * 0.6),
      rise: rand(2, 8),
      wob: rand(0.15, 0.6),
      phase: rand(0, Math.PI * 2),
      twinkle: rand(0.6, 1.8),
      vx: 0,
      vy: 0,
      glow: 0,
    };
  };

  const targetCount = () => {
    const base = Math.round((w * h) / DENSITY);
    return Math.max(MIN_DOTS, Math.min(MAX_DOTS, w < 700 ? Math.round(base * 0.7) : base));
  };

  const resize = () => {
    const rect = hero.getBoundingClientRect();
    const prevW = w || rect.width;
    const prevH = h || rect.height;
    w = rect.width;
    h = rect.height;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    dots.forEach((d) => { d.x *= w / prevW; d.y *= h / prevH; });
    const want = targetCount();
    while (dots.length < want) dots.push(createDot(true));
    if (dots.length > want) dots.length = want;
    if (reduceMotion) draw(0);
  };

  const smooth = (t) => { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); };

  const update = (dt, time) => {
    const radius = Math.max(HOVER_RADIUS[0], Math.min(HOVER_RADIUS[1], w * 0.13));
    const damp = Math.exp(-2.4 * dt);

    // gentle parallax that follows the cursor
    const tx = mouse.on ? (mouse.x - w / 2) / w : 0;
    const ty = mouse.on ? (mouse.y - h / 2) / h : 0;
    const ease = 1 - Math.exp(-2.5 * dt);
    parallax.x += (tx - parallax.x) * ease;
    parallax.y += (ty - parallax.y) * ease;

    for (const d of dots) {
      // slow, wandering drift
      d.ang += Math.sin(time * d.wob + d.phase) * 0.9 * dt;
      const driftX = Math.cos(d.ang) * d.speed;
      const driftY = Math.sin(d.ang) * d.speed - d.rise;

      // cursor interaction: scatter + curl
      let target = 0;
      if (mouse.on) {
        const dx = d.x - mouse.x;
        const dy = d.y - mouse.y;
        const dist = Math.hypot(dx, dy);
        if (dist < radius && dist > 0.01) {
          const f = 1 - dist / radius;
          const push = f * f * PUSH_STRENGTH * (0.55 + d.depth) * dt;
          const swirl = f * SWIRL_STRENGTH * dt;
          d.vx += (dx / dist) * push + (-dy / dist) * swirl;
          d.vy += (dy / dist) * push + (dx / dist) * swirl;
          target = f;
        }
      }
      d.vx *= damp;
      d.vy *= damp;
      d.glow += (target - d.glow) * Math.min(1, dt * 7);

      d.x += (driftX + d.vx) * dt;
      d.y += (driftY + d.vy) * dt;

      // wrap around softly off-screen
      const m = d.r * 3 + 20;
      if (d.x < -m) d.x = w + m;
      else if (d.x > w + m) d.x = -m;
      if (d.y < -m) d.y = h + m;
      else if (d.y > h + m) d.y = -m;
    }
  };

  const draw = (time) => {
    ctx.clearRect(0, 0, w, h);
    ctx.globalCompositeOperation = 'lighter';
    const narrow = w < 700;

    for (const d of dots) {
      const tw = 0.6 + 0.4 * Math.sin(time * d.twinkle + d.phase);
      // keep the headline area calmer on desktop
      const calm = narrow ? 0.75 : 0.6 + 0.4 * smooth(d.x / (w * 0.55));
      const alpha = Math.min(1, d.alpha * tw * calm * (1 + d.glow * 0.9));
      if (alpha < 0.02) continue;

      const radius = d.r * 1.55 * (1 + d.glow * 0.35);
      const px = d.x + parallax.x * d.depth * 26;
      const py = d.y + parallax.y * d.depth * 18;
      ctx.globalAlpha = alpha;
      ctx.drawImage(d.sprite, px - radius, py - radius, radius * 2, radius * 2);
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  };

  /* ---------- loop (pauses when hero is off-screen / tab hidden) ---------- */
  let raf = 0;
  let last = 0;
  let visible = true;

  const frame = (now) => {
    const dt = Math.min(0.05, (now - last) / 1000 || 0.016);
    last = now;
    update(dt, now / 1000);
    draw(now / 1000);
    raf = requestAnimationFrame(frame);
  };
  const start = () => { if (!raf && visible && !document.hidden) { last = performance.now(); raf = requestAnimationFrame(frame); } };
  const stop = () => { cancelAnimationFrame(raf); raf = 0; };

  /* ---------- input ---------- */
  const setMouse = (e) => {
    const rect = hero.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
    mouse.on = true;
  };

  /* ---------- init ---------- */
  resize();
  if ('ResizeObserver' in window) new ResizeObserver(resize).observe(hero);
  else window.addEventListener('resize', resize);

  if (reduceMotion) { draw(0); return; } // static dots only

  hero.addEventListener('pointermove', setMouse, { passive: true });
  hero.addEventListener('pointerdown', setMouse, { passive: true });
  hero.addEventListener('pointerleave', () => { mouse.on = false; });
  hero.addEventListener('pointercancel', () => { mouse.on = false; });
  hero.addEventListener('pointerup', (e) => { if (e.pointerType !== 'mouse') mouse.on = false; });

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      visible ? start() : stop();
    }).observe(hero);
  }
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
  start();
})();
