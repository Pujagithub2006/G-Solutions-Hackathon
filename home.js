function showFilters() {
    const filters = document.getElementById("filters");
    if (filters.style.display === "none") {
      filters.style.display = "block";
    } else {
      filters.style.display = "none";
    }
  }
  
  function requestAmbulance() {
    alert("Ambulance requested! We are tracking your location.");
  }