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

  const LOCAL_QUOTES = [
    {text:"Any fool can write code that a computer can understand. Good programmers write code that humans can understand.",author:"Martin Fowler"},
    {text:"First, solve the problem. Then, write the code.",author:"John Johnson"},
    {text:"The best error message is the one that never shows up.",author:"Thomas Fuchs"},
    {text:"Code is like humor. When you have to explain it, it's bad.",author:"Cory House"},
    {text:"Make it work, make it right, make it fast.",author:"Kent Beck"},
    {text:"Simplicity is the soul of efficiency.",author:"Austin Freeman"},
    {text:"Before software can be reusable it first has to be usable.",author:"Ralph Johnson"},
    {text:"The most damaging phrase in the language is.. it's always been done this way",author:"Grace Hopper"}
  ];

  function setQuote(text, author) {
    const qEl = document.getElementById('quote-text');
    const aEl = document.getElementById('quote-author');
    if (qEl) qEl.textContent = '"' + text + '"';
    if (aEl) aEl.textContent = '— ' + author;
  }

  function showFallbackQuote() {
    const q = LOCAL_QUOTES[Math.floor(Math.random() * LOCAL_QUOTES.length)];
    setQuote(q.text, q.author);
  }

  function fetchFromAdviceSlip() {
    return fetch('https://api.adviceslip.com/advice')
      .then(r => r.json())
      .then(data => {
        const slip = data.slip || {};
        if (slip.advice) {
          setQuote(slip.advice, 'Daily Wisdom');
          return true;
        }
        return false;
      });
  }

  function fetchQuote() {
    fetch('data/misc.json?t=' + Date.now())
      .then(r => r.json())
      .then(data => {
        if (data && data.quote && data.quote.text) {
          setQuote(data.quote.text, data.quote.author || 'Unknown');
        } else {
          return fetchFromAdviceSlip();
        }
      })
      .catch(() => {
        return fetchFromAdviceSlip().catch(() => {
          showFallbackQuote();
        });
      })
      .catch(() => {
        showFallbackQuote();
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
