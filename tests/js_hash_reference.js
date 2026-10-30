// Reads one string per line from stdin, prints the classic JS string hash for each.
const lines = require("fs").readFileSync(0, "utf8").split("\n").filter(l => l.length);
for (const s of lines) {
  let t = 0;
  const v = s + "m";
  for (let n = 0; n < v.length; n++) { t = (t << 5) - t + v.charCodeAt(n); t &= t; }
  console.log(Math.abs(t));
}
