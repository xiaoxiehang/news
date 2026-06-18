// 统一 footer 组件
(function() {
  const WEATHER_CODES = {
    0:'☀️晴',1:'🌤️大部晴朗',2:'⛅多云',3:'☁️阴',
    45:'🌫️雾',48:'🌫️雾凇',51:'🌦️小毛毛雨',53:'🌦️毛毛雨',
    61:'🌧️小雨',63:'🌧️中雨',65:'🌧️大雨',71:'🌨️小雪',
    73:'🌨️中雪',75:'🌨️大雪',80:'🌦️阵雨',95:'⛈️雷暴'
  };

  const footerHTML = `
    <div id="footer-widget" style="margin-bottom:20px;padding:16px;background:var(--bg-secondary);border-radius:var(--radius);max-width:600px;margin-left:auto;margin-right:auto;text-align:left;">
      <div id="quote-text" style="font-size:14px;color:var(--text-secondary);font-style:italic;margin-bottom:8px;">加载中...</div>
      <div id="quote-author" style="font-size:13px;color:var(--text-tertiary);text-align:right;margin-bottom:12px;"></div>
      <div id="footer-weather" style="padding-top:12px;border-top:1px solid var(--border);font-size:13px;color:var(--text-secondary);">🌡️ 杭州 天气加载中...</div>
    </div>
    <div class="footer-text">每日更新 · 值得关注</div>
    <a href="https://github.com/xiaoxiehang/news" target="_blank" class="footer-link">GitHub 仓库</a>
  `;

  function fetchWeather() {
    fetch('https://api.open-meteo.com/v1/forecast?latitude=30.2741&longitude=120.1551&current=temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m&timezone=Asia/Shanghai')
      .then(r => r.json())
      .then(data => {
        const el = document.getElementById('footer-weather');
        if (!el || !data.current) return;
        const c = data.current;
        const code = c.weather_code || 0;
        const info = WEATHER_CODES[code] || '未知';
        el.innerHTML = `🌡️ 杭州 ${Math.round(c.temperature_2m)}°C ${info} · 💧${c.relative_humidity_2m}% · 🌬️${c.wind_speed_10m}m/s`;
      })
      .catch(() => {
        const el = document.getElementById('footer-weather');
        if (el) el.textContent = '🌡️ 杭州 天气加载失败';
      });
  }

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
      fetchWeather();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
