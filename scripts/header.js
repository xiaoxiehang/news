// 统一 header 组件
(function() {
  const WEEKDAYS = ['星期日','星期一','星期二','星期三','星期四','星期五','星期六'];
  
  function setHeaderDate() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    
    const dateEl = document.getElementById('header-date');
    const weekdayEl = document.getElementById('header-weekday');
    
    if (dateEl) dateEl.textContent = y + '年' + m + '月' + d + '日';
    if (weekdayEl) weekdayEl.textContent = WEEKDAYS[now.getDay()];
  }
  
  setHeaderDate();
})();
