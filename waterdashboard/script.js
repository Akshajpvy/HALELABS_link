let totalCount = 0;
let anomalyCount = 0;
let lastAnomalyTime = "N/A";


//  Firebase config 

// This config will no longer work as it was under a free plan of Firebase and must be changed when a new Database is created
const firebaseConfig = {
  apiKey: "AIzaSyC3HlGFTk8W_kv9rRLgqviRc1HBeW99ZXc",
  authDomain: "hale-lab-7a638.firebaseapp.com",
  databaseURL: "https://hale-lab-7a638-default-rtdb.firebaseio.com",
  projectId: "hale-lab-7a638",
  storageBucket: "hale-lab-7a638.firebasestorage.app",
  messagingSenderId: "512965882466",
  appId: "1:512965882466:web:c9a2ca7a6a690ff2c0973b",
  measurementId: "G-1YBGYFY3DN"
};

firebase.initializeApp(firebaseConfig);

const db = firebase.database();
const ref = db.ref("collaborative_predictions2");


let mseChart;
let bufferedData = [];

window.addEventListener("load", () => {
  const ctx = document.getElementById("mseChart").getContext("2d");
  mseChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label: "MSE",
        data: [],
        borderColor: "blue",
        backgroundColor: "rgba(0, 119, 204, 0.1)",
        pointBackgroundColor: [], 
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: "Reconstruction Error (MSE)" }
        },
        x: {
          title: { display: true, text: "Time" }
        }
      }
    }
  });


  setInterval(updateChartFromBuffer, 3000); 
});


ref.on("child_added", (snapshot) => {
  const data = snapshot.val();
  const { timestamp, instance, mse, prediction } = data;


  const row = document.createElement("tr");
  row.innerHTML = `
    <td>${timestamp}</td>
    <td>${instance}</td>
    <td>${parseFloat(mse).toFixed(5)}</td>
    <td class="${prediction === 'Anomaly' ? 'anomaly' : ''}">${prediction}</td>
  `;
  document.getElementById("log-table").prepend(row);

  totalCount++;
if (prediction === "Anomaly") {
  anomalyCount++;
  lastAnomalyTime = timestamp;
}


document.getElementById("total-count").textContent = totalCount;
document.getElementById("anomaly-count").textContent = anomalyCount;
document.getElementById("anomaly-rate").textContent = ((anomalyCount / totalCount) * 100).toFixed(2) + "%";
document.getElementById("last-anomaly").textContent = lastAnomalyTime;


  
  bufferedData.push({
    time: timestamp.split("T")[1]?.split(".")[0] || timestamp,
    mse: mse,
    isAnomaly: prediction === "Anomaly"
  });

});

// Chart update function
function updateChartFromBuffer() {
  if (!mseChart || bufferedData.length === 0) return;

  bufferedData.forEach(entry => {
    mseChart.data.labels.push(entry.time);
    mseChart.data.datasets[0].data.push(entry.mse);
    mseChart.data.datasets[0].pointBackgroundColor.push(entry.isAnomaly ? "red" : "blue");
  });

 
  const maxPoints = 50;
  if (mseChart.data.labels.length > maxPoints) {
    mseChart.data.labels.splice(0, mseChart.data.labels.length - maxPoints);
    mseChart.data.datasets[0].data.splice(0, mseChart.data.datasets[0].data.length - maxPoints);
    mseChart.data.datasets[0].pointBackgroundColor.splice(0, mseChart.data.datasets[0].pointBackgroundColor.length - maxPoints);
  }

  mseChart.update();
  bufferedData = []; 
}
