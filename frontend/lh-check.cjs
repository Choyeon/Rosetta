const path = process.argv[2] || '';
if (!path) { console.log('Usage: node lh-check.js <report.json>'); process.exit(1); }
const r = require(path);
const c = r.audits['color-contrast'];
console.log('SCORE:', c.score, 'items:', (c.details && c.details.items && c.details.items.length) || 0);
if (c.details && c.details.items) {
  c.details.items.slice(0, 15).forEach((i, idx) => {
    const exp = i.node.explanation || '';
    console.log(`---${idx}--- selector=${i.node.selector}`);
    const match = exp.match(/contrast of ([\d.]+).*?font size: ([\d.]+pt) \(14px\), font weight: (\w+)/);
    if (match) console.log(`  contrast=${match[1]} size=${match[2]} weight=${match[3]}`);
    else console.log(`  explain=${exp.substring(0, 200)}`);
  });
}
