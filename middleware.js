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
