$(document).ready(function(){

    document.getElementById('start').addEventListener('click', function(e){
        e.preventDefault();
        if(document.forms['appForm']['term'].value === ""){
            document.getElementById('userInput').classList.add('is-invalid');
            document.getElementById('error').innerHTML = 'Το πεδίο δε μπορεί να είναι κενό.';
        }else{
            document.forms['appForm'].submit();
        }
    });

    var rows = 0;
    var data = [{value: 0}, {value: 0}, {value: 0}];

    $('#tweets').bind("DOMSubtreeModified", (event) => {
      var table = document.getElementById("tweets");

      if(table.rows.length > rows){
          if(table.rows[0].innerHTML.includes('positive')){
            data[0].value += 1
            rows += 1
            document.getElementById('counter').innerHTML = rows;
          }else if(table.rows[0].innerHTML.includes('neutral')){
            data[1].value += 1
            rows += 1
            document.getElementById('counter').innerHTML = rows;
          }else if(table.rows[0].innerHTML.includes('negative')){
            data[2].value += 1
            rows += 1
            document.getElementById('counter').innerHTML = rows;
          }
      }

    });

    var canvas = document.getElementById('chart');
    var ctx = canvas.getContext('2d');
    var startingData = {
      labels: ['Positive', 'Neutral', 'Negative'],
      datasets: [
          {
            backgroundColor: ['#28a745', '#ffc107', '#dc3545'],
            data: [0, 0, 0]
          }
      ]
    };

    var myLiveChart = new Chart(ctx,{
      type: 'doughnut',
      data: startingData
    });

    setInterval(function(){
      myLiveChart.data.datasets[0].data[0] = data[0].value;
      myLiveChart.data.datasets[0].data[1] = data[1].value;
      myLiveChart.data.datasets[0].data[2] = data[2].value;
      myLiveChart.update();
    }, 500);
});