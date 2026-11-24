/*
  Theme "placa" motion: warm glows, thin flowing lines along the bottom (echo of the landing page) and
  one champagne comet sliding down a rail beside the text column. Respects ctx.frozen (static frame).
  Contract: window.THEME = { backdrop(node, element, ctx), decorate?(node, element, ctx), after?(stage, ctx),
  elements?: { customType(element, ctx) -> node }, textChanged?(node, key, ctx) }.
*/
window.THEME = {
  backdrop(node, e, ctx) {
    const [CW, CH] = ctx.canvas;
    const accent = ctx.css('--accent');
    const g = { right: ['85%', '0%'], left: ['15%', '100%'], center: ['50%', '50%'] }[e.glow || 'right'];
    const glow = document.createElement('div');
    glow.className = 'glow';
    glow.style.background =
      `radial-gradient(70% 60% at ${g[0]} 0%, rgba(${ctx.css('--accent-rgb')}, .10), rgba(${ctx.css('--accent-rgb')}, 0) 60%),` +
      `radial-gradient(50% 60% at ${g[1]} 100%, rgba(${ctx.css('--accent-2-rgb')}, .10), rgba(${ctx.css('--accent-2-rgb')}, 0) 60%),` +
      'linear-gradient(rgba(255,255,255,.025), rgba(0,0,0,.15))';
    node.appendChild(glow);

    const sx = CW / 1920, sy = CH / 1080;
    const P = (x, y) => `${(x * sx).toFixed(1)} ${(y * sy).toFixed(1)}`;
    let paths = '';
    for (let i = 0; i < 14; i++) {
      const o = i * 9;
      paths += `<path d="M${P(-50, 980 - o)} C ${P(420, 860 - o)}, ${P(700, 1120 - o)}, ${P(1100, 960 - o)} S ${P(1700, 560 - o * 1.6)}, ${P(1990, 300 - o * 1.2)}" stroke="${accent}" stroke-opacity="${0.05 + (i % 4) * 0.05}" stroke-width="1" fill="none"/>`;
    }
    const x = e.rail_x;
    const dir = x != null && x < CW / 2 ? -1 : 1;
    const rail = x != null ? `M${x} -20 C ${x + 30 * dir} ${CH * .28}, ${x + 20 * dir} ${CH * .65}, ${x + 8 * dir} ${CH + 20}` : null;
    if (rail) {
      paths += `<path class="rail" d="${rail}" stroke="${accent}" stroke-opacity=".55" stroke-width="1.5" fill="none"/>`;
      paths += [[220, .18, 3], [130, .35, 2], [60, .8, 1.6]].map(([len, op, w]) =>
        `<path class="trail" data-len="${len}" d="${rail}" stroke="${accent}" stroke-opacity="${op}" stroke-width="${w}" stroke-linecap="round" fill="none"/>`).join('');
      paths += `<g class="comet"><circle r="22" fill="${accent}" fill-opacity=".14"/><circle r="11" fill="${accent}" fill-opacity=".22"/><circle r="5" fill="${accent}"/></g>`;
    }
    const svg = document.createElement('div');
    svg.style.cssText = 'position:absolute;inset:0';
    svg.innerHTML = `<svg width="${CW}" height="${CH}" viewBox="0 0 ${CW} ${CH}">${paths}</svg>`;
    node.appendChild(svg);
    const grain = document.createElement('div');
    grain.className = 'grain';
    node.appendChild(grain);
    if (!rail) return;

    const railEl = svg.querySelector('.rail');
    const cometEl = svg.querySelector('.comet');
    const trails = [...svg.querySelectorAll('.trail')];
    const L = railEl.getTotalLength();
    const place = (s) => {
      const p = railEl.getPointAtLength(Math.min(s, L));
      cometEl.setAttribute('transform', `translate(${p.x} ${p.y})`);
      trails.forEach((t) => { const len = +t.dataset.len; t.setAttribute('stroke-dasharray', `${len} ${L + len}`); t.setAttribute('stroke-dashoffset', `${len - s}`); });
    };
    if (ctx.frozen) return place(L * 0.29);
    const TRAVEL = 7000, PAUSE = 1800;
    const ease = (t) => -(Math.cos(Math.PI * t) - 1) / 2;
    const t0 = performance.now();
    const tick = (now) => { const k = ((now - t0) % (TRAVEL + PAUSE)) / TRAVEL; place(k >= 1 ? L + 400 : ease(k) * L); requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  },
};
