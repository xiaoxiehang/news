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
            weatherEl.innerHTML = `
              <span style="display:inline-flex;align-items:center;gap:4px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="5"/>
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                </svg>
                ${w.city} ${w.temperature}°C ${w.weather}
              </span>
              <span style="display:inline-flex;align-items:center;gap:4px;margin-left:16px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
                </svg>
                ${w.humidity}%
              </span>
              <span style="display:inline-flex;align-items:center;gap:4px;margin-left:16px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>
                </svg>
                ${w.wind_speed}m/s
              </span>
            `;
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
