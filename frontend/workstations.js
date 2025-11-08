// RoughViz is included inline in the HTML via CDN or embedded in the page

// Global configuration
const API_BASE = '';  // Will use relative paths
const PATTERN_COLORS = {
  absolutely: '#ef4444',  // red
  right: '#3b82f6',       // blue
  perfect: '#10b981',     // green
  excellent: '#f59e0b',   // amber
  // Add more patterns here as needed
};

const PATTERN_LABELS = {
  absolutely: 'Absolutely/Completely right',
  right: 'Right',
  perfect: 'Perfect!',
  excellent: 'Excellent!',
};

let workstationData = [];
let selectedWorkstations = new Set();
let visiblePatterns = new Set(['absolutely', 'right', 'perfect', 'excellent']);

// Load patterns from config or use defaults
async function loadPatternConfig() {
  try {
    // Try to get pattern config from the API (if available)
    // For now, we'll use the defaults defined above
    console.log('Using default pattern configuration');
  } catch (error) {
    console.error('Failed to load pattern config:', error);
  }
}

// Fetch data from API
async function fetchWorkstationData() {
  try {
    const response = await fetch(`${API_BASE}/api/by-workstation`);
    if (!response.ok) throw new Error('Failed to fetch data');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching data:', error);
    return [];
  }
}

// Create workstation filter checkboxes
function createWorkstationFilters(data) {
  const filterContainer = document.getElementById('workstation-filter');

  // Clear existing checkboxes (keep title)
  const title = filterContainer.querySelector('.workstation-filter-title');
  filterContainer.innerHTML = '';
  filterContainer.appendChild(title);

  data.forEach(workstation => {
    const totalCount = workstation.history.reduce((sum, day) => {
      return sum + (day.absolutely || 0) + (day.right || 0) +
             (day.perfect || 0) + (day.excellent || 0);
    }, 0);

    const checkboxDiv = document.createElement('div');
    checkboxDiv.className = 'workstation-checkbox';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `ws-${workstation.workstation_id}`;
    checkbox.value = workstation.workstation_id;
    checkbox.checked = true;
    selectedWorkstations.add(workstation.workstation_id);

    checkbox.addEventListener('change', (e) => {
      if (e.target.checked) {
        selectedWorkstations.add(workstation.workstation_id);
      } else {
        selectedWorkstations.delete(workstation.workstation_id);
      }
      updateChart();
    });

    const label = document.createElement('label');
    label.htmlFor = `ws-${workstation.workstation_id}`;
    label.className = 'workstation-label';
    label.innerHTML = `${workstation.workstation_id}<span class="workstation-count">(${totalCount} total)</span>`;

    checkboxDiv.appendChild(checkbox);
    checkboxDiv.appendChild(label);
    filterContainer.appendChild(checkboxDiv);
  });
}

// Process data for the selected workstations
function processSelectedData() {
  // Aggregate data by day for selected workstations
  const dayMap = new Map();

  workstationData.forEach(ws => {
    if (!selectedWorkstations.has(ws.workstation_id)) return;

    ws.history.forEach(day => {
      const key = `${day.day}-${ws.workstation_id}`;
      if (!dayMap.has(day.day)) {
        dayMap.set(day.day, new Map());
      }
      dayMap.get(day.day).set(ws.workstation_id, day);
    });
  });

  // Convert to array and sort by date
  const processedData = [];
  for (const [day, workstations] of dayMap.entries()) {
    const dayData = { day, workstations: {} };
    for (const [wsId, data] of workstations.entries()) {
      dayData.workstations[wsId] = data;
    }
    processedData.push(dayData);
  }

  return processedData.sort((a, b) => a.day.localeCompare(b.day));
}

// Update the chart
function updateChart() {
  console.log('updateChart() called');
  const chartContainer = document.getElementById('chart');
  const noDataMessage = document.getElementById('no-data-message');

  console.log(`Selected workstations: ${Array.from(selectedWorkstations).join(', ')}`);

  if (selectedWorkstations.size === 0) {
    chartContainer.style.display = 'none';
    noDataMessage.style.display = 'block';
    return;
  }

  chartContainer.style.display = 'block';
  noDataMessage.style.display = 'none';

  const processedData = processSelectedData();
  console.log(`Processed data length: ${processedData.length}`);

  if (processedData.length === 0) {
    chartContainer.innerHTML = '<p>No data available for selected workstations</p>';
    return;
  }

  // Prepare data for roughViz - one series per workstation per pattern
  const datasets = [];
  const labels = processedData.map(d => {
    const date = new Date(d.day);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  });

  // Create a dataset for each workstation-pattern combination
  selectedWorkstations.forEach(wsId => {
    Object.keys(PATTERN_COLORS).forEach(pattern => {
      if (!visiblePatterns.has(pattern)) return;

      const data = processedData.map(day => {
        const wsData = day.workstations[wsId];
        return wsData ? (wsData[pattern] || 0) : 0;
      });

      // Only add dataset if it has non-zero values
      if (data.some(v => v > 0)) {
        datasets.push({
          label: `${wsId} - ${PATTERN_LABELS[pattern] || pattern}`,
          data: data,
          color: PATTERN_COLORS[pattern] || '#6b7280',
          workstation: wsId,
          pattern: pattern
        });
      }
    });

    // Add total messages dataset for each workstation
    if (visiblePatterns.has('total_messages')) {
      const data = processedData.map(day => {
        const wsData = day.workstations[wsId];
        if (!wsData || !wsData.total_messages) return 0;
        // Apply square root scale for better visibility
        return Math.sqrt(wsData.total_messages);
      });

      if (data.some(v => v > 0)) {
        datasets.push({
          label: `${wsId} - Total messages (√scale)`,
          data: data,
          color: '#6b7280',
          strokeDash: [5, 3],
          workstation: wsId,
          pattern: 'total_messages'
        });
      }
    }
  });

  // Clear the chart container
  chartContainer.innerHTML = '';

  if (datasets.length === 0) {
    chartContainer.innerHTML = '<p>No data to display for selected patterns</p>';
    return;
  }

  // Create the chart
  try {
    // Check if roughViz is loaded
    if (typeof roughViz === 'undefined') {
      console.error('RoughViz library not loaded');
      chartContainer.innerHTML = '<p>Error: Chart library not loaded. Please refresh the page.</p>';
      return;
    }

    console.log(`Creating chart with ${datasets.length} datasets and ${labels.length} labels`);
    console.log('First dataset sample:', datasets[0]);
    console.log('Labels sample:', labels.slice(0, 5));

    const chartConfig = {
      element: '#chart',
      data: {
        labels: labels,
        values: datasets.map(d => d.data)
      },
      colors: datasets.map(d => d.color),
      strokeDash: datasets.map(d => d.strokeDash || [0]),
      title: '',
      width: Math.min(window.innerWidth - 40, 1000),
      height: 400,
      roughness: 2.5,
      strokeWidth: 2,
      axisStrokeWidth: 1.5,
      axisRoughness: 1,
      font: 'Gaegu',
      fillWeight: 0.35,
      margin: { top: 20, right: 20, bottom: 70, left: 70 },
      interactive: false,
      legend: false,  // We'll use our custom legend
      yLabel: 'Count',
      xLabel: 'Date'
    };

    console.log('Chart config:', chartConfig);
    new roughViz.Line(chartConfig);
    console.log('Chart created successfully');
  } catch (error) {
    console.error('Error creating chart:', error);
    console.error('Error stack:', error.stack);
    chartContainer.innerHTML = '<p>Error creating chart: ' + error.message + '</p>';
  }
}

// Create pattern legend (toggleable)
function createPatternLegend() {
  const legendContainer = document.getElementById('chart-legend');

  // Clear existing legend items except the total messages one
  const existingTotal = legendContainer.querySelector('.legend-item');
  legendContainer.innerHTML = '';

  // Add pattern legend items
  Object.entries(PATTERN_COLORS).forEach(([pattern, color]) => {
    const item = document.createElement('span');
    item.className = 'legend-item';
    item.style.cursor = 'pointer';
    item.dataset.pattern = pattern;

    const colorBox = document.createElement('span');
    colorBox.className = 'legend-color';
    colorBox.style.background = color;
    if (!visiblePatterns.has(pattern)) {
      colorBox.style.opacity = '0.3';
    }

    const label = document.createTextNode(PATTERN_LABELS[pattern] || pattern);

    item.appendChild(colorBox);
    item.appendChild(label);

    item.addEventListener('click', () => {
      if (visiblePatterns.has(pattern)) {
        visiblePatterns.delete(pattern);
        colorBox.style.opacity = '0.3';
      } else {
        visiblePatterns.add(pattern);
        colorBox.style.opacity = '1';
      }
      updateChart();
    });

    legendContainer.appendChild(item);
  });

  // Add total messages legend
  if (existingTotal) {
    existingTotal.style.cursor = 'pointer';
    existingTotal.dataset.pattern = 'total_messages';

    const colorBox = existingTotal.querySelector('.legend-color');
    if (!visiblePatterns.has('total_messages')) {
      colorBox.style.opacity = '0.3';
    }

    existingTotal.addEventListener('click', () => {
      if (visiblePatterns.has('total_messages')) {
        visiblePatterns.delete('total_messages');
        colorBox.style.opacity = '0.3';
      } else {
        visiblePatterns.add('total_messages');
        colorBox.style.opacity = '1';
      }
      updateChart();
    });

    legendContainer.appendChild(existingTotal);
  }
}

// Initialize
async function init() {
  console.log('Initializing workstations page...');
  await loadPatternConfig();

  // Fetch data
  workstationData = await fetchWorkstationData();
  console.log(`Fetched data for ${workstationData.length} workstations`);

  if (workstationData.length === 0) {
    document.getElementById('chart').innerHTML = '<p>No data available</p>';
    document.querySelector('.subtitle').style.opacity = '1';
    document.querySelector('.subtitle').textContent = 'No workstation data available';
    return;
  }

  // Create filters
  createWorkstationFilters(workstationData);

  // Create legend
  createPatternLegend();

  // Initial chart render
  updateChart();

  // Show subtitle
  document.querySelector('.subtitle').style.opacity = '1';

  // Update subtitle with workstation count
  const totalWorkstations = workstationData.length;
  document.querySelector('.subtitle').innerHTML =
    `Viewing data from <span class="highlight">${totalWorkstations}</span> workstation${totalWorkstations > 1 ? 's' : ''}`;
}

// Start when DOM is ready AND roughViz is loaded
function waitForLibrariesAndInit() {
  if (typeof roughViz !== 'undefined') {
    // Libraries are loaded, proceed with init
    init();
  } else {
    // Wait a bit and try again
    setTimeout(waitForLibrariesAndInit, 100);
  }
}

// Start when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', waitForLibrariesAndInit);
} else {
  waitForLibrariesAndInit();
}