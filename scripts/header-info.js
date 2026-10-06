// 统一 header 副标题：日期 + 星期（静态，不再调天气接口）
(function() {
  const WEEKDAYS = ['日','一','二','三','四','五','六'];
  function pad(n) { return String(n).padStart(2, '0'); }
  function render() {
    const el = document.getElementById('header-subtitle');
    if (!el) return;
    const now = new Date();
    el.textContent = `${now.getFullYear()}年${pad(now.getMonth() + 1)}月${pad(now.getDate())}日 星期${WEEKDAYS[now.getDay()]}`;
  }
  render();
})();
