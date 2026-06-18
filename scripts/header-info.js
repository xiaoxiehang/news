// 统一 header 组件：日期 + 时间 + 天气（根据 IP 自动判断地区）
(function() {
  const WEEKDAYS = ['日','一','二','三','四','五','六'];
  const WEATHER_CODES = {
    0:'☀️晴',1:'🌤️大部晴朗',2:'⛅多云',3:'☁️阴',
    45:'🌫️雾',48:'🌫️雾凇',51:'🌦️小毛毛雨',53:'🌦️毛毛雨',
    61:'🌧️小雨',63:'🌧️中雨',65:'🌧️大雨',71:'🌨️小雪',
    73:'🌨️中雪',75:'🌨️大雪',80:'🌦️阵雨',95:'⛈️雷暴'
  };

  let weatherStr = '';
  let cityName = '';

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

  // 获取 IP 定位城市
  function fetchCity() {
    return fetch('https://ipapi.co/json/')
      .then(r => r.json())
      .then(data => {
        if (data.city) {
          cityName = data.city;
          return { city: data.city, country: data.country_name || '' };
        }
        throw new Error('无法获取城市信息');
      })
      .catch(() => {
        // 备用 IP API
        return fetch('https://ipinfo.io/json')
          .then(r => r.json())
          .then(data => {
            if (data.city) {
              cityName = data.city;
              return { city: data.city, country: data.country || '' };
            }
            throw new Error('无法获取城市信息');
          });
      })
      .catch(() => {
        // 默认使用杭州
        cityName = 'Hangzhou';
        return { city: 'Hangzhou', country: 'China' };
      });
  }

  // 获取城市坐标
  function fetchCityCoords(city) {
    return fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1`)
      .then(r => r.json())
      .then(data => {
        if (data.results && data.results.length > 0) {
          const result = data.results[0];
          return { lat: result.latitude, lon: result.longitude };
        }
        throw new Error('未找到城市坐标');
      })
      .catch(() => {
        // 默认杭州坐标
        return { lat: 30.2741, lon: 120.1551 };
      });
  }

  // 获取天气
  function fetchWeather(lat, lon) {
    fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,weather_code&timezone=auto`)
      .then(r => r.json())
      .then(data => {
        if (data.current) {
          const code = data.current.weather_code || 0;
          const temp = Math.round(data.current.temperature_2m);
          const info = WEATHER_CODES[code] || '';
          weatherStr = `${cityName}${temp}°C ${info}`;
          update();
        }
      })
      .catch(() => {
        weatherStr = `${cityName} 天气加载失败`;
        update();
      });
  }

  // 流程：获取城市 -> 获取坐标 -> 获取天气
  fetchCity()
    .then(loc => fetchCityCoords(loc.city))
    .then(coords => fetchWeather(coords.lat, coords.lon));

  setInterval(update, 1000);
})();
