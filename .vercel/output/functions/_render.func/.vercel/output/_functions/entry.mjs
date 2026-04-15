import { renderers } from './renderers.mjs';
import { c as createExports } from './chunks/entrypoint_Dw776Apa.mjs';
import { manifest } from './manifest_DxFng1JR.mjs';

const _page0 = () => import('./pages/_image.astro.mjs');
const _page1 = () => import('./pages/aviso-legal.astro.mjs');
const _page2 = () => import('./pages/cookies.astro.mjs');
const _page3 = () => import('./pages/privacidad.astro.mjs');
const _page4 = () => import('./pages/index.astro.mjs');

const pageMap = new Map([
    ["node_modules/astro/dist/assets/endpoint/generic.js", _page0],
    ["src/pages/aviso-legal.astro", _page1],
    ["src/pages/cookies.astro", _page2],
    ["src/pages/privacidad.astro", _page3],
    ["src/pages/index.astro", _page4]
]);
const serverIslandMap = new Map();
const _manifest = Object.assign(manifest, {
    pageMap,
    serverIslandMap,
    renderers,
    middleware: () => import('./_noop-middleware.mjs')
});
const _args = {
    "middlewareSecret": "0191af1b-df9c-41b8-ad96-226b47be57a9",
    "skewProtection": false
};
const _exports = createExports(_manifest, _args);
const __astrojsSsrVirtualEntry = _exports.default;

export { __astrojsSsrVirtualEntry as default, pageMap };
