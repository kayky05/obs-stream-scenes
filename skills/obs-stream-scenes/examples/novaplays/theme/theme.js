/*
  Theme "arcade" motion: a scrolling perspective grid and scanlines on the backdrop (pure CSS, so it
  costs OBS almost nothing), and a short glitch on big texts whenever they change live.
*/
window.THEME = {
  backdrop(node) {
    for (const cls of ['grid', 'scan']) {
      const d = document.createElement('div');
      d.className = cls;
      node.appendChild(d);
    }
  },
  textChanged(node, key, ctx) {
    if (ctx.frozen) return;
    node.animate([
      { transform: 'translateX(-6px)', filter: 'hue-rotate(90deg)' },
      { transform: 'translateX(4px)' },
      { transform: 'translateX(0)', filter: 'none' },
    ], { duration: 260, easing: 'steps(4)' });
  },
};
