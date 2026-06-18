// 统一 footer 组件
(function() {
  const footerHTML = `
    <div id="misc-widget" style="margin-bottom:20px;padding:16px;background:var(--bg-secondary);border-radius:var(--radius);max-width:600px;margin-left:auto;margin-right:auto;text-align:left;">
      <div id="quote-text" style="font-size:14px;color:var(--text-secondary);font-style:italic;margin-bottom:8px;"></div>
      <div id="quote-author" style="font-size:13px;color:var(--text-tertiary);text-align:right;"></div>
      <div id="weather-info" style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border);font-size:13px;color:var(--text-secondary);"></div>
    </div>
    <div class="footer-text">每日更新 · 值得关注</div>
    <a href="https://github.com/xiaoxiehang/news" target="_blank" class="footer-link">GitHub 仓库</a>
  `;

  function loadMiscWidget() {
    fetch('data/misc.json?t=' + Date.now())
      .then(r => r.json())
      .then(data => {
        if (data.quote) {
          const quoteEl = document.getElementById('quote-text');
          const authorEl = document.getElementById('quote-author');
          if (quoteEl) quoteEl.textContent = '"' + data.quote.text + '"';
          if (authorEl) authorEl.textContent = '— ' + data.quote.author;
        }
        if (data.weather) {
          const weatherEl = document.getElementById('weather-info');
          if (weatherEl) {
            const w = data.weather;
            weatherEl.innerHTML =
              '🌤️ ' + w.city + ' ' + w.temperature + '°C ' + w.weather +
              ' | 💧 ' + w.humidity + '% | 🌬️ ' + w.wind_speed + 'm/s';
          }
        }
      })
      .catch(err => console.error('加载misc失败:', err));
  }

  // 页面加载完成后插入 footer 并加载数据
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      const footer = document.querySelector('.footer');
      if (footer) {
        footer.innerHTML = footerHTML;
        loadMiscWidget();
      }
    });
  } else {
    const footer = document.querySelector('.footer');
    if (footer) {
      footer.innerHTML = footerHTML;
      loadMiscWidget();
    }
  }
})();
