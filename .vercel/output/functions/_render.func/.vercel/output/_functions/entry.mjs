import { renderers } from './renderers.mjs';
import { c as createExports } from './chunks/entrypoint_CvNmB7JB.mjs';
import { manifest } from './manifest_D3oMKTvD.mjs';

const _page0 = () => import('./pages/_image.astro.mjs');
const _page1 = () => import('./pages/404.astro.mjs');
const _page2 = () => import('./pages/aviso-legal.astro.mjs');
const _page3 = () => import('./pages/coming-soon.astro.mjs');
const _page4 = () => import('./pages/cookies.astro.mjs');
const _page5 = () => import('./pages/mantenimiento.astro.mjs');
const _page6 = () => import('./pages/privacidad.astro.mjs');
const _page7 = () => import('./pages/index.astro.mjs');

const pageMap = new Map([
    ["node_modules/astro/dist/assets/endpoint/generic.js", _page0],
    ["src/pages/404.astro", _page1],
    ["src/pages/aviso-legal.astro", _page2],
    ["src/pages/coming-soon.astro", _page3],
    ["src/pages/cookies.astro", _page4],
    ["src/pages/mantenimiento.astro", _page5],
    ["src/pages/privacidad.astro", _page6],
    ["src/pages/index.astro", _page7]
]);
const serverIslandMap = new Map();
const _manifest = Object.assign(manifest, {
    pageMap,
    serverIslandMap,
    renderers,
    middleware: () => import('./_noop-middleware.mjs')
});
const _args = {
    "middlewareSecret": "d9bb5049-f7ac-4fc9-a609-69b40d41ddc2",
    "skewProtection": false
};
const _exports = createExports(_manifest, _args);
const __astrojsSsrVirtualEntry = _exports.default;

export { __astrojsSsrVirtualEntry as default, pageMap };
