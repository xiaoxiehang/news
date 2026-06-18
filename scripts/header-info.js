// 统一 header 组件：日期 + 时间 + 杭州天气
(function() {
  const WEEKDAYS = ['日','一','二','三','四','五','六'];

  function updateTime() {
    const now = new Date();
    const y = now.getFullYear();
    const m = pad(now.getMonth() + 1);
    const d = pad(now.getDate());
    const h = pad(now.getHours());
    const min = pad(now.getMinutes());
    const sec = pad(now.getSeconds());
    const w = WEEKDAYS[now.getDay()];

    // 更新日期
    const dateEl = document.getElementById('header-date');
    if (dateEl) dateEl.textContent = `${y}年${m}月${d}日 周${w}`;

    // 更新时间
    const timeEl = document.getElementById('header-time');
    if (timeEl) timeEl.textContent = `${h}:${min}:${sec}`;
  }

  function fetchWeather() {
    // 杭州坐标
    const url = 'https://api.open-meteo.com/v1/forecast?latitude=30.2741&longitude=120.1551&current=temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m&timezone=Asia/Shanghai';

    fetch(url)
      .then(r => r.json())
      .then(data => {
        const el = document.getElementById('header-weather');
        if (!el || !data.current) return;
        const code = data.current.weather_code || 0;
        const temp = Math.round(data.current.temperature_2m);
        const icon = WEATHER_CODES[code] || '🌡️';
        const desc = WEATHER_DESC[code] || '';
        el.innerHTML = `${icon} 杭州 ${temp}°C ${desc}`;
      })
      .catch(() => {
        const el = document.getElementById('header-weather');
        if (el) el.textContent = '🌡️ 杭州 天气加载中...';
      });
  }

  // 初始化
  updateTime();
  setInterval(updateTime, 1000);
})();
