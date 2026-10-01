// middleware.js
// Vercel Routing Middleware — 框架无关，零依赖。
// 把二级域名的请求路由到各自的产品目录。
// 协议：返回带 `x-middleware-rewrite` 头的 Response 做重写，
// 返回带 `x-middleware-next: 1` 头的 Response 继续正常流程。

export default function middleware(request) {
  const url = new URL(request.url);
  const host = (request.headers.get('host') || '').split(':')[0].toLowerCase();
  const pathname = url.pathname;

  // 共享路径：永远直通（接口、静态资源、数据、共享脚本）
  if (
    pathname.startsWith('/api/') ||
    pathname.startsWith('/assets/') ||
    pathname.startsWith('/data/') ||
    pathname.startsWith('/scripts/')
  ) {
    return next();
  }

  // 旧页面 301 跳转（2026-10 网站结构重组：资讯/创作聚合页）
  const LEGACY_REDIRECTS = {
    '/zaobao.html': '/news.html',
    '/github.html': '/news.html#github',
    '/hackernews.html': '/news.html#hn',
    '/archive.html': '/news.html#archive',
    '/quiz.html': '/news.html#quiz',
    '/xhs.html': '/studio.html',
    '/xhs-tool.html': '/studio.html#tool',
  };
  if (LEGACY_REDIRECTS[pathname] && host !== 'stock.xiaojj.pro' && host !== 'price.xiaojj.pro') {
    return new Response(null, {
      status: 301,
      headers: { Location: LEGACY_REDIRECTS[pathname] },
    });
  }

  let prefix = '';
  if (host === 'stock.xiaojj.pro') {
    prefix = '/stock';
  } else if (host === 'price.xiaojj.pro') {
    prefix = '/price';
  } else {
    return next();
  }

  // 已经在产品目录里：原样服务，避免重复加前缀
  if (pathname === prefix || pathname.startsWith(prefix + '/')) {
    return next();
  }

  // 重写到产品目录
  url.pathname = pathname === '/' ? prefix + '/index.html' : prefix + pathname;
  return rewrite(url);
}

function next() {
  return new Response(null, { headers: { 'x-middleware-next': '1' } });
}

function rewrite(url) {
  return new Response(null, { headers: { 'x-middleware-rewrite': url.toString() } });
}
