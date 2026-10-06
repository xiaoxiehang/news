// 统一 footer 组件：一行极简
(function() {
  const footerHTML = `
    <div class="footer-inner footer-simple">
      <span class="footer-copy">© 2026 鸡仔</span>
      <span class="footer-dot">·</span>
      <a href="https://github.com/xiaoxiehang/news" target="_blank" rel="noopener">GitHub</a>
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
