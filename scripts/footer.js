// 统一 footer 组件：简洁三段式
(function() {
  const footerHTML = `
    <div class="footer-inner">
      <div class="footer-brand"><span class="brand-mark">鸡</span>鸡仔</div>
      <p class="footer-tagline">为自己打磨的小产品，顺手分享出来。</p>
      <div class="footer-links">
        <a href="https://xiaojj.pro">首页</a>
        <span class="footer-dot">·</span>
        <a href="https://github.com/xiaoxiehang/news" target="_blank" rel="noopener">GitHub</a>
      </div>
      <p class="footer-copy">© 2026 鸡仔</p>
    </div>
  `;
  function init() {
    const footer = document.querySelector('.footer');
    if (footer) footer.innerHTML = footerHTML;
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
