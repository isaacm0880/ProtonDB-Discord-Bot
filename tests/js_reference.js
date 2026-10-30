function jsHash(e){let t=0;e=String(e)+"m";for(let n=0;n<e.length;n++){t=(t<<5)-t+e.charCodeAt(n);t&=t}return Math.abs(t)}
function r(e,t,n){return `${t}p${e*(t%n)}`}
const [,, appid, reports, ts, page, tail] = process.argv;
const s = "p"+r(Number(appid),reports,Number(ts))+"*vRT"+r(Number(page),appid,Number(ts))+tail;
console.log(s); console.log(String(jsHash(s)));
