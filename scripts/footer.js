// 统一 footer 组件
(function() {
  const footerHTML = `
    <div id="footer-widget" style="margin-bottom:20px;padding:16px;background:var(--bg-secondary);border-radius:var(--radius);max-width:600px;margin-left:auto;margin-right:auto;text-align:left;">
      <div id="quote-text" style="font-size:14px;color:var(--text-secondary);font-style:italic;margin-bottom:8px;">加载中...</div>
      <div id="quote-author" style="font-size:13px;color:var(--text-tertiary);text-align:right;"></div>
    </div>
    <div class="footer-text">每日更新 · 值得关注</div>
    <a href="https://github.com/xiaoxiehang/news" target="_blank" class="footer-link">GitHub 仓库</a>
  `;

  function fetchQuote() {
    fetch('https://api.quotable.io/random?tags=technology|programming')
      .then(r => r.json())
      .then(data => {
        const qEl = document.getElementById('quote-text');
        const aEl = document.getElementById('quote-author');
        if (qEl) qEl.textContent = '"' + (data.content || data.text) + '"';
        if (aEl) aEl.textContent = '— ' + (data.author || 'Unknown');
      })
      .catch(() => {
        const quotes = [
          {text:"Any fool can write code that a computer can understand. Good programmers write code that humans can understand.",author:"Martin Fowler"},
          {text:"First, solve the problem. Then, write the code.",author:"John Johnson"},
          {text:"The best error message is the one that never shows up.",author:"Thomas Fuchs"},
          {text:"Code is like humor. When you have to explain it, it's bad.",author:"Cory House"},
          {text:"Make it work, make it right, make it fast.",author:"Kent Beck"},
          {text:"Simplicity is the soul of efficiency.",author:"Austin Freeman"}
        ];
        const q = quotes[Math.floor(Math.random() * quotes.length)];
        const qEl = document.getElementById('quote-text');
        const aEl = document.getElementById('quote-author');
        if (qEl) qEl.textContent = '"' + q.text + '"';
        if (aEl) aEl.textContent = '— ' + q.author;
      });
  }

  function init() {
    const footer = document.querySelector('.footer');
    if (footer) {
      footer.innerHTML = footerHTML;
      fetchQuote();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
