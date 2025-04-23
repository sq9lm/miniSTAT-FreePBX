const netChart=new Chart(document.getElementById('netChart'),
 {type:'line',data:{labels:[],datasets:[{label:'TX',data:[],borderWidth:1},
                                        {label:'RX',data:[],borderWidth:1}]},
  options:{plugins:{legend:{position:'bottom'}},scales:{x:{display:false},
          y:{beginAtZero:true}}}});

const tempChart = new Chart(document.getElementById('tempChart'), {
  type: 'line',
  data: {
    labels: [],
    datasets: [{
      label: 'Temperatura',
      data: [],
      borderWidth: 1,
      borderColor: 'rgb(255, 99, 132)',
      tension: 0.3
    }]
  },
  options: {
    plugins: {
      legend: { display: true, position: 'bottom' }
    },
    scales: {
      x: { display: false },
      y: { beginAtZero: false }
    }
  }
});

function pushTemp(temp) {
  tempChart.data.labels.push('');
  tempChart.data.datasets[0].data.push(temp);
  if (tempChart.data.labels.length > 50) {
    tempChart.data.labels.shift();
    tempChart.data.datasets[0].data.shift();
  }
  tempChart.update('none');
}

function pushChart(tx,rx){
  netChart.data.labels.push('');
  netChart.data.datasets[0].data.push(tx);
  netChart.data.datasets[1].data.push(rx);
  if(netChart.data.labels.length>50){
     netChart.data.labels.shift();
     netChart.data.datasets.forEach(d=>d.data.shift());
  }
  netChart.update('none');
}

function updCards(sys, ast) {
  // CPU/RAM/Disk bars
  ['cpu', 'ram', 'disk'].forEach(id => {
    $('#' + id + 'Val').text(sys[id] + ' %');
    const bar = $('#' + id + 'Bar .progress-bar');
    bar.parent().show();
    bar.css('width', sys[id] + '%');
  });

  $('#ext_onlineVal').text(ast.ext_online);
  $('#ext_offVal').text(ast.ext_off);
  $('#ext_busyVal').text(ast.ext_busy);
  $('#trunk_onVal').text(ast.trunk_on);
  $('#trunk_offVal').text(ast.trunk_off);

  pushChart(sys.tx, sys.rx);

  // ⬇⬇⬇ NOWE: Dodaj temperaturę do wykresu ⬇⬇⬇
  if (sys.temp !== null && sys.temp !== undefined) {
    pushTemp(sys.temp);
    document.getElementById("tempTitle").innerText = `Temperatura CPU (${sys.temp} °C)`;
    }
}

function tick(){
  fetch('/api/system', { credentials: 'same-origin' })
    .then(r => r.json())
    .then(sys => {
        window._sys = sys;           // zapisz na chwilę
        return fetch('/api/asterisk', { credentials: 'same-origin' });
    })
    .then(r => r.json())
    .then(ast => updCards(window._sys, ast))
    .catch(err => console.error('Fetch error:', err));
}
setInterval(tick, 3000);
tick();

fetch('/api/uptime', { credentials: 'same-origin' })
  .then(r => r.json())
  .then(uptime => {
      document.getElementById("uptimeSys").textContent = uptime.system || "–";
      document.getElementById("uptimeAst").textContent = uptime.asterisk || "–";
  });

