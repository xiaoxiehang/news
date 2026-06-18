// 统一 header 组件：日期 + 时间 + 杭州天气
(function() {
  const WEEKDAYS = ['日','一','二','三','四','五','六'];
  const WEATHER_CODES = {
    0:'☀️晴',1:'🌤️大部晴朗',2:'⛅多云',3:'☁️阴',
    45:'🌫️雾',48:'🌫️雾凇',51:'🌦️小毛毛雨',53:'🌦️毛毛雨',
    61:'🌧️小雨',63:'🌧️中雨',65:'🌧️大雨',71:'🌨️小雪',
    73:'🌨️中雪',75:'🌨️大雪',80:'🌦️阵雨',95:'⛈️雷暴'
  };

  let weatherStr = '';

  function pad(n) { return String(n).padStart(2, '0'); }

  function update() {
    const now = new Date();
    const y = now.getFullYear();
    const m = pad(now.getMonth() + 1);
    const d = pad(now.getDate());
    const h = pad(now.getHours());
    const min = pad(now.getMinutes());
    const sec = pad(now.getSeconds());
    const w = WEEKDAYS[now.getDay()];

    const el = document.getElementById('header-subtitle');
    if (!el) return;

    let text = `${y}年${m}月${d}日 周${w} ${h}:${min}:${sec}`;
    if (weatherStr) {
      text += ' · ' + weatherStr;
    }
    el.textContent = text;
  }

  function fetchWeather() {
    fetch('https://api.open-meteo.com/v1/forecast?latitude=30.2741&longitude=120.1551&current=temperature_2m,weather_code&timezone=Asia/Shanghai')
      .then(r => r.json())
      .then(data => {
        if (data.current) {
          const code = data.current.weather_code || 0;
          const temp = Math.round(data.current.temperature_2m);
          const info = WEATHER_CODES[code] || '';
          weatherStr = `杭州${temp}°C ${info}`;
          update();
        }
      })
      .catch(() => {
        weatherStr = '杭州 天气加载失败';
        update();
      });
  }

  fetchWeather();
  setInterval(update, 1000);
})();
